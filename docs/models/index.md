# 비교 대상 모델

| 모델 | 기반 | 학습 데이터 | 가중치 | 사용 방식 | 상태 |
|---|---|---|---|---|---|
| autoPET III LesionTracer | nnU-Net v2 ResEnc-L (5-fold) | autoPET III: FDG + PSMA 전신 PET/CT | [Zenodo 14007247](https://zenodo.org/records/14007247) · CC BY 4.0 | 추론만 | 🟡 진행 중 |
| nnU-Net v2 (자체 학습) | nnU-Net v2 | 우리 데이터(라벨 필요) | — | 라벨 확보 후 학습 | ⚪ 대기 |
| (추가 예정) | | | | | |

## 공통 평가 계획 (초안)

- 파일럿: 핵의학 전문의 육안 검토 — 병변 탐지 여부, 위양성(생리적 섭취) 유형
- 라벨 확보 후: lesion-wise 민감도·FP/환자, Dice, FL-DS 일치도
