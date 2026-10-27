# 방법: autoPET III LesionTracer 병변 탐지 파이프라인

파일럿(P01, P02)에서 실제로 한 처리를 방법 기술 수준으로 정리한다. 연구 보고·논문 방법 섹션의 초안으로 쓴다.
nnU-Net 설정값은 워크스테이션의 모델 `plans.json` 에서 옮겼다(2026-10-21).

## 1. 입력 구성 — 무엇을 어떤 모양으로 넣었나

- DICOM 1개 파일 = 축상(axial) 단면 1장. 환자 폴더의 수천 장을 전부 쓰지 않고, CT 1개·PET 1개 시리즈만 골랐다(§3).
- 각 시리즈의 단면을 ImagePositionPatient 순으로 z축에 쌓아 3D 볼륨으로 만든다(`dicom2nifti`).
- CT 를 PET 격자로 리샘플(CTres) → CT·PET 이 같은 shape. 예: P01 192×192×299 (3.65×3.65×3.27 mm).
- nnU-Net 이 CTres(`_0000`)·SUV(`_0001`)를 채널로 쌓는다 → 배열 (C=2, X, Y, Z), 네트워크 입력은 배치 포함 (1, 2, 192, 192, 192).
- 전신을 한 번에 넣지 않고 192³ 패치 sliding window(겹침 50%, Gaussian 가중)로 예측해 이어 붙인다.
  패치 수: P01 27개, P02 45개.

## 2. 전처리

### (가) DICOM → 모델 입력 (`scripts/prepare_autopet_input.py` + TCIA_processing)

| 단계 | 내용 |
|---|---|
| 시리즈 선택·복사 | SeriesDescription + SOP Class 로 CT·PET 원본 시리즈만 복사(원본 불변). P01 은 복사본 Modality `NM`→`CT`/`PT` |
| DICOM→NIfTI | `dicom2nifti` (reorient=True). Rescale Slope/Intercept 적용 → CT=HU, PET=Bq/mL |
| SUV | SUVbw = PET(Bq/mL) × 체중(g) / 붕괴보정 투여량(Bq). 붕괴보정 시각 SeriesTime(`--suv-time series`, 2026-10-22 결정. TCIA 원본은 첫 파일 AcquisitionTime) |
| CTres | `nilearn.image.resample_to_img(CT, PET, fill_value=-1024)` |

### (나) nnU-Net 추론 내부 (학습 때의 `plans.json` 을 그대로 적용)

1. 0 이 아닌 영역으로 crop
2. 목표 spacing 으로 리샘플: 3.0 × 2.036 × 2.036 mm (z, y, x — `configurations.3d_fullres.spacing`).
   P01(면내 3.646 mm)은 면내를 늘리고, P02(1.65 mm)는 줄인다. 학습셋 중앙 크기는 300×400×400 복셀
3. 강도 정규화: 두 채널 이름이 모두 `CT` → 두 채널 모두 CTNormalization
   (학습셋 전경 강도의 0.5–99.5 백분위로 clip 후, 학습셋 전경 평균·표준편차로 z-score). 통계값(`foreground_intensity_properties_per_channel`):

   | 채널 | clip 범위(0.5–99.5 백분위) | 평균 | 표준편차 |
   |---|---|---|---|
   | 0 = CTres (HU) | −832.1 ~ 1127.8 | 107.7 | 286.3 |
   | 1 = SUV | 1.043 ~ 51.21 | 7.064 | 7.960 |

   SUV 채널도 CT 식 정규화라, 학습셋 전경 기준 SUV 1.04 아래와 51.2 위는 잘린다. SUV 를 몇 % 다르게 계산하면([status.md](../status.md) 함정 표 'SUV 기준 시각') 정규화 뒤 값도 그만큼 옮겨 간다
4. Sliding window 예측(패치 192 × 192 × 192, `patch_size`), 미러링 TTA. 정규화에 마스크는 쓰지 않는다(`use_mask_for_norm` = False)
5. 5개 fold 모델 앙상블(softmax 평균, §7) → 원래 spacing 으로 되돌림 → argmax (라벨 0/1)

## 3. 사용한 시리즈와 이유

| | 사용 | 제외 |
|---|---|---|
| P01 (GE Discovery 710, 1515장) | CT `Torso Standard 2.0mm` 488장, PET `PETWB` 299장 (= 787장) | Fusion MPR 4종, MIP, Dose Report |
| P02 (Siemens Biograph Vision 600, 3742장) | CT `CT  3 3.0 Br38` 842장, PET `PET AC` 842장 (= 1684장) | CT LUNG, PET Respiratory Gated, Fusion 3종, Coronal 재구성, Radial MIP, Patient Protocol |

제외 이유: 파생(재표시) 영상은 중복이고 정량값(Units)이 없거나 색이 입혀져 SUV 계산 불가 / 폐 재구성·호흡동기 PET 은
목적과 잡음 특성이 다름 / 보고서·프로토콜은 비영상 / 모델의 학습 입력 형태(전신 CT 1 + 감쇠보정 전신 PET 1)와 맞춰야 함.

## 4. NIfTI 로 바꾼 이유와 화질

- nnU-Net 은 DICOM 을 읽지 않는다(NIfTI·NRRD·MHA 등 볼륨 파일만). 시리즈가 섞인 단면 파일을 볼륨으로 묶는 단계가 어차피 필요하다.
- DICOM→NIfTI 와 gzip 은 무손실: 화소값(HU, Bq/mL)·spacing·방향(affine) 보존. 환자 정보 헤더가 빠져 익명성에도 유리하다.
- 손실이 생기는 곳은 CT→PET 격자 리샘플(CTres) 하나. 의도된 것(학습 데이터와 동일). 예: P01 CT 0.98 mm → 3.65 mm.
  원 해상도 CT 는 `~/autopet3/work_series/P0x/nifti/CT.nii.gz` 에 남아 있다. 보간 overshoot 로 CT 최솟값이 −3977 HU 같은 비물리값이 될 수 있다.

## 5. 환자마다 장수가 다를 때

- 장수(슬라이스 수)를 맞출 필요 없다. 완전 합성곱 + 패치 예측이라 길이가 다르면 패치 수만 달라진다.
- 공간: nnU-Net 이 mm 단위 목표 spacing 으로 리샘플. 강도: SUV 변환(체중·투여량·시간 보정) + 학습셋 고정 통계 정규화.
- 남는 한계: 장비 간(GE vs Siemens) SUV 차이는 보정하지 않았다 → FL-DS 단계에서 harmonization(EARL 등) 검토.

## 6. 5-fold 의 의미

- 개발팀(DKFZ)이 학습 때 5-fold 교차검증(4/5 학습·1/5 검증 × 5회)을 해서 모델 5개(`fold_0`–`fold_4`)가 나왔다.
- nnU-Net 은 추론 때 이 5개를 앙상블한다(각자 확률 예측 → 평균). 우리 쪽에서 교차검증을 한 것이 아니다.
- 진행바가 환자당 5줄인 이유. `-f 0` 으로 단일 모델만 쓸 수도 있다.

## 7. 병변을 세는 기준 — 연결성분과 18-연결

모델 출력은 복셀마다 0(배경)·1(병변)이 적힌 마스크다. "병변 몇 개"는 1 인 복셀 중 서로 붙어 있는 것끼리 한 덩어리로 묶어서 센다.
이 덩어리를 연결성분(connected component)이라 하고, 묶는 일은 공개 라이브러리 cc3d(https://github.com/seung-lab/connected-components-3d)가 한다.

### "붙어 있다"의 기준

2D 그림(바둑판)으로 먼저 보면, 가운데 칸의 이웃은 두 종류다.

```
. # .      # = 변으로 맞닿은 이웃 4칸 (위·아래·왼쪽·오른쪽)
# X #      * = 꼭짓점으로만 맞닿은 이웃 4칸 (대각선)
. # .
* . *  ←  대각선 칸들은 '꼭짓점만' 닿는다
```

3D 에서는 복셀(작은 정육면체) 하나를 둘러싼 이웃이 26개이고, 닿는 방식이 셋이다.

| 기준 | 붙어 있다고 보는 이웃 | 개수 |
|---|---|---|
| 6-연결 | 면이 맞닿은 이웃(앞뒤·좌우·위아래) | 6 |
| 18-연결 | 면 + 모서리(선)가 맞닿은 이웃 | 18 |
| 26-연결 | 면 + 모서리 + 꼭짓점 하나만 닿은 이웃 | 26 |

기준이 느슨할수록(26) 대각선으로 스치듯 닿은 조각도 한 병변으로 합쳐지고, 엄격할수록(6) 따로 센다.

### 우리가 쓰는 기준

- autoPET 공식 평가 코드(lab-midas/autoPET `val_script.py` 의 `con_comp`)가 18-연결을 쓴다. 공식 지표(Dice·위양성·위음성 부피)와 숫자를 맞추려고 우리도 18-연결로 통일했다(2026-10-22).
  요약(`summarize_lesions.py`)·후보 확인 페이지(`make_review_html.py`)가 모두 같은 `con_comp` 를 부른다.
  `scripts/val_script.py` 는 원본(commit `468179b`)을 고치지 않고 그대로 복사한 것이다(2026-10-26).
- 그 전에는 scipy 26-연결로 셌다. P01 의 0.09 mL 성분은 두 조각이 꼭짓점 하나로만 닿아 있어 26-연결에서는 1개, 18-연결에서는 0.04 mL 2개가 된다.
  그래서 P01 병변 수가 15 → 16 이 됐다. 큰 병변과 P02 는 같다.
- 병변 번호는 부피 큰 순이고, 부피가 같으면 SUVmax 큰 순이다. 요약 표의 `#` 과 페이지의 '기록 #' 이 같다.

## 8. 코드와 문헌

| 역할 | 코드 | 문헌 |
|---|---|---|
| 병변 탐지 모델 | https://github.com/MIC-DKFZ/autopet-3-submission (commit `257afc3`) | Rokuss et al., *From FDG to PSMA: A Hitchhiker's Guide to Multitracer, Multicenter Lesion Segmentation in PET/CT Imaging*, arXiv:2409.09478 (2024) |
| 가중치 | https://zenodo.org/records/14007247 (CC BY 4.0) | 위와 같음 |
| 프레임워크 | https://github.com/MIC-DKFZ/nnUNet | Isensee et al., Nature Methods 18:203–211 (2021); Isensee et al., *nnU-Net Revisited*, MICCAI 2024, arXiv:2404.09556 |
| 사전학습(MultiTalent) | — | Ulrich et al., *MultiTalent*, MICCAI 2023, arXiv:2303.14444 |
| DICOM→SUV·CTres | https://github.com/lab-midas/TCIA_processing (commit `fb7b074`) | Gatidis et al., *A whole-body FDG-PET/CT dataset with manually annotated tumor lesions*, Scientific Data (2022) |
| 챌린지 | — | Gatidis et al., *Results from the autoPET challenge on fully automated lesion segmentation in oncologic PET/CT imaging*, Nature Machine Intelligence (2024) |
| 연결 스크립트 | `scripts/prepare_autopet_input.py` (이 저장소) | — |
| 후보 확인 페이지 | `scripts/make_review_html.py` + `scripts/review_template.html` (이 저장소, 공유 폴더 프로토타입의 화면 구성을 따름) | — |
