# 원자료 인벤토리

## 파일럿 (P01·P02)

원본: Dropbox `PET_MRD/CT_image/` 아래 공유 폴더(읽기 전용). 환자별 폴더 1개, 시리즈 구분 없이 `.dcm` 이 한 폴더에 섞여 있다.
식별정보는 적지 않는다. 확인일 2026-10-08.

| 항목 | P01 | P02 |
|---|---|---|
| 장비 | GE Discovery 710 | Siemens Biograph Vision 600 |
| 파일 · 시리즈 | 1,515개 · 8개 (MPR·MIP·Fusion·Dose Report 등 파생 시리즈 포함) | 3,742개 · 10개 |
| 사용할 CT 시리즈 | `Torso Standard 2.0mm` — 488장, 512×512, HU(RescaleIntercept −1024) | `CT 3 3.0 Br38` — 842장, 512×512, 3 mm (`CT LUNG` 1.5 mm 는 쓰지 않음) |
| 사용할 PET 시리즈 | `PETWB` — 299장, 192×192, 3.65 mm | `PET AC` — 842장, 440×440, 1.65 mm (`PET Respiratory Gated` 는 쓰지 않음) |
| PET 단위·보정 | Units=BQML, 감쇠·산란·붕괴 보정됨, DecayCorrection=START | Units=BQML, 보정 완료, DecayCorrection=START |
| SUV 계산 정보 | 투여량·투여 시각·반감기·체중 모두 있음 | 모두 있음 |
| 촬영 범위 | 두개저~대퇴 부근(약 97 cm) — 전신(vertex–toe) 아님 | — |

- ⚠️ P01: CT·PET 모두 Modality 태그가 `NM` 으로 기록돼 있다(SOP Class 는 정상: CT Image Storage / PET Image Storage).
  Modality 로 CT/PT 를 고르는 변환 스크립트(`tcia_dicom_to_nifti.py`)는 그대로는 이 환자를 인식하지 못한다.
- ⚠️ P02: 헤더의 체중 값이 성인 기준으로 낮다 → 실제 값인지 확인 필요(SUVbw 에 직접 영향)

## 공통 주의점

- **SUV 기준 시각.** DecayCorrection=START 이면 붕괴 보정 기준은 시리즈 시작 시각(SeriesTime)이다.
  `tcia_dicom_to_nifti.py` 는 AcquisitionTime 을 쓰는데, 두 환자 모두 AcquisitionTime 이 SeriesTime 보다
  10~14분 늦게 기록된 파일이 있어 SUV 가 약 7~9% 과대 계산될 수 있다. 변환 전 처리 방침을 정한다.
- 시리즈가 섞여 있으므로 변환 전에 시리즈별 폴더로 나눠야 한다(복사본에서).
- 원본 폴더의 압축파일 1개는 Dropbox 온라인 전용 상태라 열리지 않았다. 파일명에 식별정보가 있으니 경로를 옮겨 적지 않는다.

## 코호트 (C001–C274) 장비 분포

2026-10-23 확인. 환자 폴더마다 처음 잡힌 PET 파일 1장의 헤더(제조사·모델·Units·면내 간격)만 집계했다. 시리즈별 확인은 변환 전에 다시 한다.

| 장비 | 환자 수 | PET 면내 간격(대표) |
|---|---|---|
| Siemens Biograph Vision 600 | 104 | 1.65 mm |
| Siemens Biograph TruePoint (Biograph40) | 92 | 4.07 mm |
| GE Discovery 710 | 78 | 3.65 mm |

- PET 면내 간격 기타: 5.71 mm 4명, 5.09 mm 3명, 6.69 mm 2명, 5.8 mm 2명(재구성 설정이 다른 시리즈로 보임).
- Units: BQML 267명, PROPCPS 7명. 지금 변환 코드는 BQML 기준으로 SUV 를 계산하므로, PROPCPS 7명은 처음 잡힌 파일이
  보조 시리즈(비감쇠보정 등)인지, 주 시리즈 자체가 PROPCPS 인지 변환 전에 확인한다.
- autoPET 학습 데이터의 FDG 는 Siemens Biograph mCT 한 대(Tübingen) 영상이다(Gatidis et al., Sci Data 2022). 우리 코호트의 세 장비는 모두 학습 FDG 와 다르다.

