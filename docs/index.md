# PET-CT 문서 지도

| 갈래 | 문서 | 다루는 것 |
|---|---|---|
| **현재 상태** | [status.md](status.md) | 핸드오프 — 현재 위치, 다음 할 일, 알려진 함정. 이어받을 때 가장 먼저 |
| 기준(SoT) | [sot.md](sot.md) | 범위·파이프라인 단계·저장소 경계 |
| 데이터 거버넌스 | [data-governance.md](data-governance.md) | 데이터가 어디에 있고, 어디로 가면 안 되는지 |
| 결정 기록 | [decisions.md](decisions.md) | 지금 유효한 결정(한 줄씩)과 공개 코드 출처 |
| 실행 환경 | [environment.md](environment.md) | 워크스테이션 사양, GPU·PyTorch 주의점 |
| 원자료 | [data/index.md](data/index.md) | 가명 환자별 시리즈 구성·변환 시 주의점 |
| 모델 | [models/index.md](models/index.md) | 비교 대상 모델과 진행 상태 |
| 방법 | [methods/autopet3-pipeline.md](methods/autopet3-pipeline.md) · [methods/finetune-from-review.md](methods/finetune-from-review.md) · [methods/llm-assist.md](methods/llm-assist.md) · [methods/preprocessing-literature.md](methods/preprocessing-literature.md) | 입력 구성·전처리·시리즈 선택 이유·5-fold 앙상블·코드와 문헌 · 판정 CSV 로 미세조정하는 계획 · LLM 보조 의견 틀과 확장 계획 · SUV 기준 시각 근거와 전처리·정규화 문헌 검색 키워드 |
| 실험 | `experiments/` (워크스테이션 로컬 전용, 깃허브에 없음) | 실험별 설정·수치 결과·관찰 |
| 가이드 | [guides/dicom-to-nifti.md](guides/dicom-to-nifti.md) · [guides/autopet3-inference.md](guides/autopet3-inference.md) · [guides/review-results.md](guides/review-results.md) · [guides/totalsegmentator.md](guides/totalsegmentator.md) · [guides/medgemma.md](guides/medgemma.md) · [guides/git-workflow.md](guides/git-workflow.md) | DICOM → NIfTI 변환, autoPET III 환경·추론, 결과 수치 요약·후보 확인 페이지·맥 판독, CT 장기·골격 분할, 후보 소견용 로컬 VLM(MedGemma·vLLM), 브랜치·커밋·PR |

## 우선순위

- 데이터 규칙([data-governance.md](data-governance.md))이 다른 모든 문서보다 앞선다.
- 절차가 바뀌면 해당 가이드와 [decisions.md](decisions.md) 표의 그 줄을 같은 변경 단위에서 함께 고친다. 바뀐 경위는 PR 본문에 적는다.
