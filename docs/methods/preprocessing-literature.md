# 입력 전처리 근거와 문헌 조사 키워드

코호트 100명 추론(issue #4) 전에 입력 전처리·정규화가 더 필요한지 판단하려고 정리한다.
1절은 지금 정한 SUV 기준 시각의 근거, 2절은 지금 입력에 실제로 들어가는 처리, 3절은 코호트 전에 확인할 질문, 4–5절은 문헌 검색 키워드와 출발점 문헌이다.
문헌 검색은 `/lit-search`, `/petct-paper-scrap` 또는 `chaeniverse/petct-paper-scrap` 에이전트에 4절 키워드를 넣어 한다.

## 1. SUV 기준 시각을 SeriesTime 으로 한 근거 (2026-10-22 결정)

SUV 는 "병변의 방사능 농도 ÷ (몸 전체에 남아 있는 주사량 ÷ 체중)" 이다.
주사한 F-18 은 반감기 약 110분으로 줄어들기 때문에, 주사량을 "어느 시각 기준으로" 줄여 계산할지 정해야 한다.

| DICOM 시각 | 뜻 |
|---|---|
| SeriesTime (0008,0031) | 이 시리즈(PET 검사 한 번)가 시작된 시각. 시리즈 안 모든 슬라이스에 같은 값 |
| AcquisitionTime (0008,0032) | 이 슬라이스의 데이터를 찍기 시작한 시각. 전신 PET 은 침대를 몇 번 옮기며(bed position) 찍으므로 침대 위치마다 값이 다르다 |
| DecayCorrection (0054,1102) = START | 스캐너가 영상 값을 이미 "검사 시작 시각" 기준으로 붕괴 보정해 두었다는 표시 |

- 영상 값이 검사 시작 시각 기준이면, 주사량도 같은 시각까지 줄여야 비율이 맞는다. QIBA 의 제조사 중립 SUV 계산법은 이 시각으로 SeriesTime 을 쓴다.
  예외로 SeriesTime 이 AcquisitionTime 보다 늦으면(재구성 후 새 시리즈로 저장해 SeriesTime 이 생성 시각이 된 경우) GE 비공개 태그나 시리즈 안 가장 이른 AcquisitionTime 을 쓴다.
- TCIA_processing 원본(`calculate_suv_factor`)은 폴더에서 처음 읽힌 PET 파일 한 장의 AcquisitionTime 을 쓴다.
  어느 침대 위치의 파일이 먼저 읽히느냐에 따라 기준 시각이 몇 분 달라지고, 그만큼 SUV 가 달라진다(몇 분 차이면 몇 %).
- 그래서 변환 코드(TCIA 함수)는 고치지 않고, `prepare_autopet_input.py --suv-time series` 가 결과 SUV 에 SeriesTime 기준 비율을 곱한다. 로그 `suv_time_reference` 로 확인한다.
- 남은 점: autoPET 학습 데이터는 TCIA 원본 방식으로 만들어졌다. 우리 입력과 기준 시각이 다를 수 있다.
- 코호트에서 확인할 것: GE Discovery 710 환자는 SeriesTime 이 AcquisitionTime 보다 늦은지 본다(위 예외에 해당하면 기준 시각을 따로 정한다).

## 2. 지금 입력에 들어가는 처리

| 단계 | 하는 일 | 코드 |
|---|---|---|
| 시리즈 고르기 | 헤더 `SeriesInstanceUID` 로 묶고, `SeriesDescription` 이 `--ct-desc`·`--pt-desc` 와 같고 SOP Class 가 CT·PET 인 시리즈 하나씩 | `scripts/prepare_autopet_input.py` `scan_series`·`pick` |
| SUV 변환 | 체중·주사량·붕괴 보정으로 PET 값을 SUV 로 | TCIA_processing `calculate_suv_factor`·`convert_pet` + `--suv-time series` |
| CTres | CT 를 PET 격자(같은 행렬·간격)로 다시 샘플링 | TCIA_processing `resample_ct` |
| 모델 안 재샘플링 | 입력을 학습 기준 간격 3.0 × 2.04 × 2.04 mm 로 바꾼다. 슬라이스 수는 맞출 필요가 없다 | nnU-Net 추론(plans) |
| 모델 안 세기 정규화 | CT·SUV 모두 학습 데이터 기준 0.5–99.5 백분위로 자른 뒤 평균·표준편차로 표준화(CTNormalization) | nnU-Net 추론(plans) |

장비 간 보정(하모나이제이션)은 하지 않는다.

## 3. 코호트 전에 답할 질문

- 장비 3종(Siemens Vision 600·TruePoint, GE Discovery 710)의 재구성 조건(PSF·TOF·필터) 차이가 SUV 와 탐지에 영향을 주는가. EARL 같은 재구성 맞추기나 사후 필터가 필요한가.
- ComBat 은 주로 라디오믹스 특징값 보정에 쓴다. 영상 분할 모델 입력에 쓴 선례가 있는가.
- PET Units 가 PROPCPS 인 7명의 SUV 를 어떻게 계산하는가.
- 슬라이스 두께·촬영 범위(전신 vs 두개저–대퇴)가 다를 때 처리할 것이 있는가.
- 골수종 FDG PET/CT 병변 탐지 연구는 어떤 전처리를 썼는가.

## 4. 검색 키워드

SUV 기준 시각

- `SUV calculation DICOM decay correction reference time`
- `Series Time vs Acquisition Time SUV`
- `QIBA vendor-neutral SUV pseudo-code`
- `SUV calculation accuracy software implementation`
- `digital reference object SUV`
- `DecayCorrection START DICOM PET`
- `GE post-processing Series Time SUV error`
- `PET DICOM header errors quantification`

장비·기관 차이

- `multicenter PET harmonization`
- `EARL harmonization SUV`
- `PET reconstruction harmonization post-reconstruction filtering`
- `scanner variability SUV PSF TOF`

ComBat

- `ComBat harmonization PET`
- `ComBat radiomics multicenter`
- `image-level harmonization deep learning PET`

딥러닝 일반화

- `domain shift PET/CT segmentation`
- `multi-vendor generalization lesion segmentation PET`
- `autoPET generalization multi-center`
- `intensity normalization PET deep learning`

입력 구성

- `voxel spacing resampling nnU-Net PET`
- `slice thickness variability CT segmentation`
- `field of view whole-body vs skull base mid-thigh PET`

단위·SUV

- `PET Units PROPCPS Bq/ml DICOM`
- `SUV body weight error`

골수종 특화

- `multiple myeloma FDG PET/CT deep learning lesion segmentation`
- `automated focal lesion detection myeloma PET`
- `IMPeTUs criteria`
- `Deauville score myeloma`

## 5. 출발점 문헌·자료 (2026-10-28 확인)

| 자료 | 링크 | 쓰는 곳 |
|---|---|---|
| QIBA, SUV vendor-neutral pseudo-code (2018-06-26) | <https://qibawiki.rsna.org/images/8/86/SUV_vendorneutral_pseudocode_20180626_DAC.pdf> | SeriesTime 기준, 예외 처리(1절) |
| Pierce LA et al. A digital reference object to analyze calculation accuracy of PET standardized uptake value. Radiology 2015;277:538–545 | PMID [25989387](https://pubmed.ncbi.nlm.nih.gov/25989387/) | 소프트웨어마다 SUV 계산이 다른 문제 |
| Boellaard R et al. FDG PET/CT: EANM procedure guidelines for tumour imaging, version 2.0. Eur J Nucl Med Mol Imaging 2015;42:328–354 | PMID [25452219](https://pubmed.ncbi.nlm.nih.gov/25452219/) | SUV 정량·EARL·41% 임계값 |
| Technical Note: Vendor-Specific Approach for Standardized Uptake Value Calculation (2024) | <https://arxiv.org/abs/2410.13348> | QIBA 계산법이 놓치는 제조사별 경우 |
| autoPET II 데이터 설명(CT 를 PET 해상도로 재샘플링, SUV 변환, CTres·SUV 권장) | <https://autopet-ii.grand-challenge.org/dataset> | CTres·SUV 입력의 근거 |
| TCIA_processing(autoPET 데이터 변환 코드) | <https://github.com/lab-midas/TCIA_processing> | 변환 함수 원본 |
| Gatidis S, Kuestner T. FDG-PET-CT-Lesions [Dataset]. TCIA 2022 | DOI [10.7937/gkr0-xv29](https://doi.org/10.7937/gkr0-xv29) | autoPET 학습 데이터 |
