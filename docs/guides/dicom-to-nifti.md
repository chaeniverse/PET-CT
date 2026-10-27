# DICOM → NIfTI 변환 (autoPET 입력 만들기)

원본 DICOM 을 autoPET III 입력(`<case>_0000` = CTres, `<case>_0001` = SUV)으로 바꾼다. 추론은 [autoPET III 추론 가이드](autopet3-inference.md).
uv 와 폴더 배치는 [추론 가이드](autopet3-inference.md) §0–1.

모델은 autoPET 데이터 형태로 학습됐다 — PET 은 SUV(체중 기준), CT 는 PET 격자로 리샘플(CTres).
변환은 autoPET 주최측 코드 [`lab-midas/TCIA_processing`](https://github.com/lab-midas/TCIA_processing)
`tcia_dicom_to_nifti.py` 의 함수(`dcm2nii_CT`, `dcm2nii_PET`, `resample_ct`)를 수정 없이 호출한다.
우리 데이터 구조에 맞추는 연결 부분만 [`scripts/prepare_autopet_input.py`](../../scripts/prepare_autopet_input.py) 가 맡는다
(시리즈 선택·시리즈별 복사·복사본의 Modality 교정·nnU-Net 이름 규칙·식별정보 없는 로그).

## 1. 외장하드 코호트를 워크스테이션으로 복사 (맥 터미널, 밤새 실행 가능)

외장하드 `/Volumes/EXTERNAL/PET-CT/` 의 환자 폴더(이름에 등록번호·이름·검사일시가 있음)를 가명 `C001…` 폴더로 복사한다.
[`scripts/copy_cohort_dicom.sh`](../../scripts/copy_cohort_dicom.sh) 가 하는 일:

- 처음 한 번 폴더명 정렬 순서로 가명 대응표를 만든다. 대응표 `PETCT_pseudonym_map.tsv` 원본은 외장하드에 생긴다.
  사본은 워크스테이션 `~/autopet3/private/`(폴더 700·파일 600, 저장소 밖)에만 두고, 저장소·Dropbox·맥 판독 폴더·채팅에는 두지 않는다(2026-10-23 결정, [데이터 거버넌스](../data-governance.md) §3).
- 환자별로 `rsync` 한 뒤 원본·대상 장수를 비교해 로그(`PETCT_transfer_log.txt`, 가명·숫자만)에 남긴다.
- 끊기면 다시 실행한다. 같은 대응표를 쓰고, 이미 받은 파일은 건너뛴다.

```bash
ssh -o BatchMode=yes chlee@pipet-cmccpt true && echo OK      # 키 로그인 확인. 안 되면 ssh-copy-id chlee@pipet-cmccpt
cp ~/Documents/GitHub/PET-CT/scripts/copy_cohort_dicom.sh ~/petct_copy.sh
nohup caffeinate -ims bash ~/petct_copy.sh > /dev/null 2>&1 &
tail -f /Volumes/EXTERNAL/PETCT_transfer_log.txt                 # C001 rsync=0 src=N dst=N 이 보이면 정상
```

- 맥북은 덮개를 열고 충전기를 꽂아 둔다(덮개를 닫으면 `caffeinate` 로도 잠든다). 외장하드를 빼지 않는다.
- 연구실 내부망이면 스크립트의 `WS` 를 `chlee@192.168.0.251` 로 바꾸면 빠르다. 멈출 때는 `pkill -f petct_copy.sh`.
- 끝난 뒤 확인: `grep -c "rsync=0" …log.txt` 가 환자 수(274)와 같고, `rsync=0` 이 아니거나 `src ≠ dst` 인 줄이 없으면 된다.
  오류 파일 `PETCT_transfer_errors.txt` 에는 원본 경로(식별정보)가 찍힐 수 있으니 붙여 넣지 않는다.

## 2. 변환 환경 (워크스테이션, 1회)

```bash
cd ~/PET-CT/third_party
git clone https://github.com/lab-midas/TCIA_processing.git
cd TCIA_processing
git checkout fb7b074                # 파일럿과 같은 커밋으로 고정
uv venv --python 3.11 && source .venv/bin/activate
uv pip install -r ~/PET-CT/env/tcia.lock.txt         # 파일럿과 같은 버전 그대로
python -c "import SimpleITK, dicom2nifti, nibabel, pydicom; print('import ok')"
```

- lock 이 없을 때(처음 설치하거나 패키지를 바꿀 때)는 레포의 `requirements.txt` 로 설치하고 lock 을 새로 쓴다:
  `uv pip install -r requirements.txt && uv pip freeze > ~/PET-CT/env/tcia.lock.txt`

## 3. 변환 실행

```bash
cd ~/PET-CT && source third_party/TCIA_processing/.venv/bin/activate
COMMON="--work-dir $HOME/autopet3/work_series --out-dir $HOME/autopet3/input_series --suv-time series"
python scripts/prepare_autopet_input.py --dicom-dir ~/autopet3/dicom_pilot/P01 --case-id P01 --ct-desc "Torso Standard 2.0mm" --pt-desc "PETWB" $COMMON
python scripts/prepare_autopet_input.py --dicom-dir ~/autopet3/dicom_pilot/P02 --case-id P02 --ct-desc "CT  3 3.0 Br38" --pt-desc "PET AC" $COMMON
ls ~/autopet3/input_series        # P01_0000, P01_0001, P02_0000, P02_0001
```

- 파일럿(P01·P02)은 `work_series`·`input_series`·`output_series` 에 쓰고, `work`·`input`·`output` 은 코호트(C###)용이다.
  코호트를 변환할 때는 `COMMON` 의 폴더를 `work`·`input` 으로 바꾼다.
- 각 케이스 `~/autopet3/work_series/<case>/conversion_log.json`(코호트는 `work/<case>/`) 에서 `ctres_suv_same_grid: true`, SUV 분포를 확인한다.
- SUV 는 SeriesTime 기준(`--suv-time series`)으로 만든다(2026-10-22 결정, [decisions.md](../decisions.md)).
  TCIA 원본(acquisition)은 폴더에서 처음 잡힌 PET 파일 1장의 AcquisitionTime 을 써서 컴퓨터마다 결과가 달라질 수 있다.
  로그의 `suv_time_reference` 가 `series` 인지 확인한다. acquisition 대비 비율은 `suv_ratio_series_over_acquisition` 에 남는다.
