# TotalSegmentator — CT 장기·골격 분할

후보 카드에 붙일 골 이름과 기준 SUV(간·혈액풀)는 CT 장기·골격 분할을 바탕으로 한다. 분할은 공개 도구 TotalSegmentator 의 공식 명령으로만 한다.

- 코드: <https://github.com/wasserth/TotalSegmentator> (Apache-2.0) — v2.18.0, 태그 커밋 `184fa47`
- `--task total`(117개 라벨)은 라이선스 없이 쓴다. `vertebrae_body` 같은 일부 태스크만 라이선스가 필요하다(지금은 쓰지 않는다).
- 논문: Wasserthal et al., *TotalSegmentator: Robust Segmentation of 104 Anatomic Structures in CT Images*, Radiology: AI 2023 (doi:10.1148/ryai.230024)

## 1. 코드 받기 · 가상환경

```bash
cd ~/PET-CT/third_party
git clone https://github.com/wasserth/TotalSegmentator.git     # 기본 브랜치 master
cd TotalSegmentator
git checkout 184fa47                # v2.18.0 (2026-08-12) 으로 고정
git describe --tags                 # v2.18.0 이 나와야 함

uv venv --python 3.11
source .venv/bin/activate
```

- autoPET 환경과 venv 를 따로 둔다. TotalSegmentator 는 공식 `nnunetv2`(2.8.x)를 설치하는데, autoPET 레포는 같은 이름의 수정본(2.5.1)이라 한 venv 에 두면 부딪힌다.
- [추론 가이드](autopet3-inference.md) §2 와 같이 `uv sync` · `uv add` 는 쓰지 않고 `uv pip install` 만 쓴다.

## 2. PyTorch(cu128+) → 코드 설치

[추론 가이드](autopet3-inference.md) §3 과 같은 순서다. PyTorch 를 먼저 넣는다(`setup.py` 는 `torch>=2.1.2` 만 요구).
아래는 lock 이 없을 때(처음 설치)의 순서다. lock 이 생긴 뒤 같은 환경을 다시 만들 때는 이 절 끝의 lock 설치를 쓴다.

```bash
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
python -c "import torch;print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_arch_list())"
#   → True, 그리고 목록에 sm_120 이 있어야 함

uv pip install -e .
python -c "import torch;print(torch.__version__)"      # 위와 같은 버전인지 재확인
uv pip show nnunetv2 | grep Version                     # 공식 nnunetv2 (2.8.x)
TotalSegmentator --help | head -3                       # 명령이 잡히면 설치 완료

uv pip freeze --exclude-editable > ~/PET-CT/env/totalseg.lock.txt   # 처음 한 번만. 이 파일은 커밋한다
```

`uv pip freeze` 는 지금 켜진 venv(`VIRTUAL_ENV`)를 기준으로 적는다. 반드시 TotalSegmentator venv 를 켠 상태에서 실행한다.

lock 이 생긴 뒤 같은 환경을 다시 만들 때는 §1 다음에 아래를 쓴다. 추론 가이드 §3 의 lock 설치와 같은 형식이다.

```bash
uv pip install -r ~/PET-CT/env/totalseg.lock.txt --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match
uv pip install -e . --no-deps
python -c "import torch;print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_arch_list())"   # True, sm_120
TotalSegmentator --help | head -3
```

## 3. 가중치·설정 위치 · 사용 통계 끄기

`TOTALSEG_HOME_DIR` 아래에 설정 파일 `config.json` 과 가중치(`nnunet/results/`)가 생긴다. 지정하지 않으면 `~/.totalsegmentator` 로 간다.
TotalSegmentator 는 실행할 때마다 이 값을 읽으므로 `~/.bashrc` 에 넣는다. 이미 있으면(`grep TOTALSEG_HOME_DIR ~/.bashrc`) 다시 붙이지 않는다.

```bash
grep -q TOTALSEG_HOME_DIR ~/.bashrc || echo 'export TOTALSEG_HOME_DIR="$HOME/autopet3/weights/totalseg"' >> ~/.bashrc
source ~/.bashrc && echo "$TOTALSEG_HOME_DIR"           # /chlee/autopet3/weights/totalseg
mkdir -p -m 700 "$TOTALSEG_HOME_DIR"                    # 다른 사용자가 못 읽게
```

TotalSegmentator 는 기본값으로 실행마다 익명 사용 통계(태스크·옵션·버전 등)를 `stats.totalsegmentator.com` 으로 보낸다.
데이터 거버넌스상 외부 전송을 하지 않으므로, 분할을 한 번도 돌리기 전에 끈다. 레포의 설정 함수(`totalsegmentator/config.py`)를 그대로 쓴다.

```bash
python -c "from totalsegmentator.config import setup_totalseg, set_config_key; setup_totalseg(); set_config_key('send_usage_stats', False)"
cat "$TOTALSEG_HOME_DIR/config.json"                    # "send_usage_stats": false 인지 확인
```

- `setup_totalseg()` 는 설정 파일이 없을 때 만들기만 한다(이때 기본값 `true`). 이미 있으면 그대로 읽는다.
- `TOTALSEG_HOME_DIR` 가 비어 있는 터미널에서 돌리면 `~/.totalsegmentator/config.json` 이 새로 생기고 통계가 켜진 상태가 된다. 돌리기 전에 `echo "$TOTALSEG_HOME_DIR"` 로 확인한다.

라벨 번호 → 이름 표는 공식 명령 `totalseg_info` 로 받아 둔다(GPU·가중치 없이 바로 나온다). 후보 카드의 구조 이름·Slicer 이름표에 쓴다.
`make_review_html.py --totalseg` 가 `<분할 폴더>/classes_total.json` 을 읽으므로 분할 결과 폴더에 둔다(2026-10-26).

```bash
mkdir -p -m 700 ~/autopet3/totalseg
totalseg_info --classes -ta total --json > ~/autopet3/totalseg/classes_total.json
python -c "import json;d=json.load(open('$HOME/autopet3/totalseg/classes_total.json'));print(len(d), d['5'], d['51'])"   # 117 liver heart
```

## 4. 분할 실행

입력은 변환 단계에서 나온 원본 해상도 CT(`work/<case>/nifti/CT.nii.gz`, 파일럿은 `work_series`)다. 모델 입력용 `CTres`(PET 격자)가 아니다.
공식 CLI 한 줄로 돌린다. `--ml` 을 주면 라벨 117개가 한 파일에 들어간다. TotalSegmentator 가 안에서 1.5 mm 로 리샘플해 분할하고, 결과는 입력 CT 와 같은 격자로 저장한다.

```bash
source ~/PET-CT/third_party/TotalSegmentator/.venv/bin/activate
echo "$TOTALSEG_HOME_DIR"                     # 비어 있으면 멈춘다(§3)
totalseg_download_weights -t total            # 처음 한 번. 약 1.4 GB 가 $TOTALSEG_HOME_DIR/nnunet/results 에 받아진다
mkdir -p -m 700 ~/autopet3/totalseg/P01 ~/autopet3/totalseg/P02
time TotalSegmentator -i ~/autopet3/work_series/P01/nifti/CT.nii.gz -o ~/autopet3/totalseg/P01/seg.nii.gz --task total --ml
time TotalSegmentator -i ~/autopet3/work_series/P02/nifti/CT.nii.gz -o ~/autopet3/totalseg/P02/seg.nii.gz --task total --ml
```

- 결과 `~/autopet3/totalseg/<case>/seg.nii.gz` 는 환자 영상에서 나온 마스크다. 저장소·클라우드로 옮기지 않는다.

## 5. 기준 영역 함수(autoDS-PET) 받기

간·종격동 혈액풀(MBP) 기준값과 규칙 DS 는 공개 저장소 autoDS-PET(MIT)의 함수로 계산한다. 설치하지 않고 함수만 쓰므로 venv 를 만들지 않는다.
`scripts/anatomy.py` 가 이 폴더를 경로에 넣어 `LiverROI`·`AortaMBP`·`resample_to_reference`·`assign_ds` 를 부른다(SimpleITK·numpy 만 필요, autoPET venv 에서 돈다).

```bash
cd ~/PET-CT/third_party && git clone https://github.com/Sara-Peluso/autoDS-PET.git
git -C ~/PET-CT/third_party/autoDS-PET rev-parse --short HEAD     # fc6bc13 이어야 한다. 다르면 git -C … checkout fc6bc13
```

## 6. 후보 확인 페이지·LLM 에 넣기

`make_review_html.py --totalseg ~/autopet3/totalseg` 를 주면 후보마다 아래가 붙는다(2026-10-26).

- 카드: 위치(후보 SUVmax 자리의 구조 이름, 그 자리가 구조 밖이면 후보 안에서 가장 많이 겹친 구조) · 간 대비 · 혈액풀 대비 · 규칙 DS(2: ≤혈액풀, 3: ≤간, 4: ≤간×2, 5: >간×2)
- 머리말: 기준 SUV(간 10 mm 침식 중앙값, T4–T8 높이 대동맥·심장 제외 중앙값). 분할을 SUV 격자로 nearest-neighbour 로 옮겨 SUV 격자에서 계산한다
- LLM 입력: `site`·`r_liver`·`r_mbp`·`ds_rule`(프롬프트 v3). `--llm-input-only` 와 페이지 생성에 같은 `--totalseg` 를 준다. 다르면 의견 파일의 후보가 다르다며 멈춘다
- Slicer: 구조 라벨 층(`<case>_viewer/labels.nii.gz`)과 이름표(`labels.ctbl`). 마우스 위치의 구조 이름이 Data Probe 에, Slicer 에서 찍은 누락 병변 점에도 구조 이름이 붙는다
- 분할 파일이 없는 케이스는 알리고 해부 정보 없이 만든다. `--totalseg` 없이 다시 만들면 예전 구조 라벨 파일을 지운다

`<case>_viewer/` 의 구조 라벨·이름표는 맥 판독 폴더로 가는 예외다([데이터 거버넌스](../data-governance.md) §2). 원본 해상도 분할(`~/autopet3/totalseg/`)은 워크스테이션 밖으로 보내지 않는다.
