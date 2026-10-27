# autoPET III LesionTracer 로 병변 탐지 추론하기

워크스테이션(JupyterHub ▸ Terminal, 계정 `chlee`)에서 진행한다. 학습은 하지 않고 공개 가중치로 추론만 한다.

파이프라인 순서와 가이드:

1. [DICOM → NIfTI 변환](dicom-to-nifti.md) — 코호트 복사, 변환 환경, SUV·CTres 만들기
2. autoPET III 추론 — 이 문서
3. [결과 확인](review-results.md) — 병변 수치 요약, 후보 확인 페이지·맥 판독
4. [TotalSegmentator 장기·골격 분할](totalsegmentator.md) — 후보 카드의 골 이름·기준 SUV
5. [MedGemma 로컬 VLM](medgemma.md) — 후보 카드의 소견(LLM 의견 칸)

- 코드: <https://github.com/MIC-DKFZ/autopet-3-submission> (Apache-2.0) — nnU-Net v2 를 수정한 버전이 레포 안에 들어 있다
- 가중치: <https://zenodo.org/records/14007247> — `autoPET-3-LesionTracer.zip`, 3.8 GB, md5 `566016409b0bd14770c0b57c1f2873f1`, CC BY 4.0
- 논문: Rokuss et al., *From FDG to PSMA: A Hitchhiker's Guide to Multitracer, Multicenter Lesion Segmentation in PET/CT Imaging*, arXiv:2409.09478

---

## 0. 상태 확인 · 폴더 배치

```bash
nvidia-smi            # RTX 5090 표시, 드라이버 CUDA ≥ 12.8, 다른 사용자 점유 여부
```

워크스테이션 배치 (코드는 저장소 안, 데이터·가중치·결과는 저장소 밖):

```
/chlee/   (= ~)
├── PET-CT/                               ← git clone chaeniverse/PET-CT
│   └── third_party/
│       └── autopet-3-submission/         ← autoPET III 코드 (gitignored)
│           └── .venv/                    ← uv 가상환경
└── autopet3/                             ← 저장소 밖: 데이터·가중치·결과
    ├── weights/
    ├── work_series/ · input_series/ · output_series/   ← 파일럿(P01·P02)
    └── work/ · input/ · output/                        ← 코호트(C###)
```

## 1. 저장소 받기 · uv 확인

```bash
cd ~
git clone https://github.com/chaeniverse/PET-CT.git     # private 이면 GitHub 인증 필요(PAT 또는 gh auth login)

source ~/.local/bin/env
uv --version
```

## 2. autoPET III 코드 받기 · 가상환경

```bash
cd ~/PET-CT/third_party
git clone https://github.com/MIC-DKFZ/autopet-3-submission.git     # 기본 브랜치 master (마지막 커밋 2024-10-29)
cd autopet-3-submission
git checkout 257afc3                # 파일럿과 같은 커밋으로 고정 (실험 기록 참고)
git rev-parse --short HEAD          # 실험 기록에 남길 커밋 해시

uv venv --python 3.11
source .venv/bin/activate
ls                                   # pyproject.toml · setup.py 만 있음 (requirements.txt · uv.lock 없음)
```

- 이 레포는 패키지 이름이 `nnunetv2`(2.5.1)인 nnU-Net 수정본이다. 같은 venv 에 업스트림 `nnunetv2` 를 따로 설치하지 않는다.
- `uv.lock` 이 없으므로 `uv sync` · `uv add` 는 쓰지 않는다(외부 레포의 pyproject 를 바꾸게 됨). `uv pip install` 만 쓴다.
- uv 로 만든 venv 에는 `pip` 이 없다. `pip install …` 대신 항상 `uv pip install …`.

## 3. PyTorch(cu128+) → 코드 설치

`env/autopet3.lock.txt`(`uv pip freeze` 결과)가 있으면 그 버전 그대로 설치한다. 파일럿과 같은 환경을 다시 만들 때는 이쪽이다.

```bash
uv pip install -r ~/PET-CT/env/autopet3.lock.txt --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match
uv pip install -e . --no-deps                           # 레포 코드만 연결(의존성은 lock 에서 이미 설치)
python -c "import torch;print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_arch_list())"
#   → True, 그리고 목록에 sm_120 이 있어야 함
nnUNetv2_predict_from_modelfolder -h                    # 명령이 잡히면 설치 완료
```

- lock 의 torch 는 `+cu128` 판이라 PyTorch 저장소(`--extra-index-url`)에서 받는다. `--index-strategy unsafe-best-match` 는 두 저장소 중 lock 에 적힌 버전이 있는 곳을 고르게 한다.

lock 이 없을 때(처음 설치하거나 패키지를 바꿀 때)는 아래 순서로 설치하고 lock 을 새로 쓴다.
순서가 중요하다. PyTorch 를 먼저 넣어야 한다(nnU-Net 공식 경고). pyproject 는 `torch>=2.1.2` 만 요구하므로,
먼저 넣은 cu128 torch 가 그대로 유지된다.

```bash
# [pytorch.org/get-started/locally] 에서 Linux·Pip·CUDA 12.8 이상을 골라 나온 index-url 사용
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
python -c "import torch;print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_arch_list())"
#   → True, 그리고 목록에 sm_120 이 있어야 함

uv pip install -e .
python -c "import torch;print(torch.__version__)"      # 위와 같은 버전인지(바뀌지 않았는지) 재확인
nnUNetv2_predict_from_modelfolder -h                    # 명령이 잡히면 설치 완료

uv pip freeze --exclude-editable > ~/PET-CT/env/autopet3.lock.txt   # lock 새로 쓰기. 같은 변경 단위로 커밋한다
```

`uv pip freeze` 는 지금 켜진 venv(`VIRTUAL_ENV`)를 기준으로 적는다. 반드시 이 레포의 venv 를 켠 상태에서 실행한다.

> 확인할 두 가지: ① `uv pip install -e .` 뒤에도 torch 버전이 처음 설치한 것과 같아야 한다(코드 설치가 torch 를 다른 버전으로 바꿔 깔면 GPU 를 못 쓸 수 있다).
> ② `get_arch_list()` 목록에 `sm_120` 이 있어야 한다(RTX 5090 을 지원하는 빌드라는 뜻). 둘 중 하나라도 아니면 추론으로 넘어가지 말고 멈춘 뒤 상의한다.

## 4. nnU-Net 경로 환경변수

`predict_from_modelfolder` 는 이 경로들을 직접 쓰지 않지만, 설정돼 있지 않으면 경고가 나온다.

`~/.bashrc` 에 이미 세 줄이 있으면(`grep nnUNet_ ~/.bashrc`) `cat >> ~/.bashrc` 는 건너뛴다. 다시 붙이면 중복된다.

```bash
mkdir -p ~/nnUNet_data/{nnUNet_raw,nnUNet_preprocessed,nnUNet_results}
cat >> ~/.bashrc <<'RC'
export nnUNet_raw="$HOME/nnUNet_data/nnUNet_raw"
export nnUNet_preprocessed="$HOME/nnUNet_data/nnUNet_preprocessed"
export nnUNet_results="$HOME/nnUNet_data/nnUNet_results"
RC
source ~/.bashrc && source ~/PET-CT/third_party/autopet-3-submission/.venv/bin/activate
```

## 5. 가중치 내려받기

```bash
mkdir -p ~/autopet3/weights && cd ~/autopet3/weights
wget -O autoPET-3-LesionTracer.zip "https://zenodo.org/records/14007247/files/autoPET-3-LesionTracer.zip?download=1"
md5sum autoPET-3-LesionTracer.zip        # 566016409b0bd14770c0b57c1f2873f1 이어야 함
unzip autoPET-3-LesionTracer.zip
find . -maxdepth 5 -type d -name "fold_*"   # fold_0~fold_4 가 들어 있는 상위 폴더 = MODEL_FOLDER
```

MODEL_FOLDER 안의 `dataset.json` 에서 입력 채널 이름과 출력 라벨을 확인해 둔다.

```bash
cat <MODEL_FOLDER>/dataset.json
```

## 6. 추론

입력 `~/autopet3/input_series/<case>_000{0,1}.nii.gz` 는 [변환 가이드](dicom-to-nifti.md)로 만든다. 코호트는 `-i ~/autopet3/input -o ~/autopet3/output` 으로 바꾼다.

```bash
source ~/PET-CT/third_party/autopet-3-submission/.venv/bin/activate
MODEL=~/autopet3/weights/Dataset222_AutoPETIII_2024/autoPET3_Trainer__nnUNetResEncUNetLPlansMultiTalent__3d_fullres_bs3
export TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1     # PyTorch 2.6 이상에서 체크포인트 로딩
nnUNetv2_predict_from_modelfolder -i ~/autopet3/input_series -o ~/autopet3/output_series -m "$MODEL" -device cuda
```

- 모델 `dataset.json`: 채널 0·1 모두 이름이 `CT`(둘 다 CT식 정규화로 학습됨), 라벨 `tumor: 1`. 입력 순서는 0 = CTres, 1 = SUV.
- 기본값은 5개 fold 앙상블 + TTA. 결과는 `output_series/P01.nii.gz`, `output_series/P02.nii.gz` (PET 격자의 병변 마스크, 0/1).
- 빠른 확인만 할 때는 `-f 0`(fold 하나), `--disable_tta`. 메모리 오류 시 `-npp 1 -nps 1`.

결과 확인은 [결과 확인 가이드](review-results.md)로 이어진다.
