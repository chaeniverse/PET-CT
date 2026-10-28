# 결정 기록

지금 유효한 결정만 한 줄씩 둔다. 결정이 바뀌면 그 줄을 고치고, 바뀐 경위는 PR 본문에 적는다.
2026-10-27 이전의 자세한 기록은 git 기록과 이전 저장소(`chaeniverse/PET-CT-archive`)의 PR 에 있다.

## 지금 유효한 결정

| 영역 | 결정 | 이유 | 자세히 |
|---|---|---|---|
| 데이터 | 환자 영상·마스크·임상자료·가중치는 워크스테이션·외장하드에만 둔다. 맥 판독 폴더에는 페이지·Slicer 용 NIfTI(구조 라벨 포함)·판정 CSV·Slicer 점만 둔다 | 기관 밖 유출 금지 | [데이터 거버넌스](data-governance.md) |
| 가명 대응표 | 사본을 워크스테이션 `~/autopet3/private/`(700·600)에 두고 레지스트리 결합에만 쓴다 | ③단계 결합에 필요 | [데이터 거버넌스](data-governance.md) §3 |
| 판정 CSV | 지금은 맥 판독 폴더에만 둔다. 워크스테이션으로 보내는 규칙은 issue #4 ⑥ 에서 정한다 | 미세조정 전까지 이동 불필요 | [결과 확인](guides/review-results.md) §2-1 |
| 실험 기록 | `experiments/` 는 워크스테이션 로컬에만 두고 깃허브에 올리지 않는다 | 수치·관찰도 환자 파생물 | [AGENTS](../AGENTS.md) |
| 코드 원칙 | 탐지·평가·미세조정·기준 SUV 는 공개 코드로 한다. 직접 만든 코드는 시각화·데이터 연결만 | 검증된 구현을 그대로 쓴다 | 아래 "공개 코드 출처" |
| 탐지 모델 | autoPET III LesionTracer 공개 가중치(5-fold + TTA)로 추론만 한다 | FDG·PSMA 전신 PET/CT 로 학습된 1위 모델. 자체 학습 데이터가 아직 없다 | [추론](guides/autopet3-inference.md), [방법](methods/autopet3-pipeline.md) |
| 입력 변환 | CTres(`_0000`)+SUV(`_0001`). TCIA_processing 함수를 고치지 않고 `prepare_autopet_input.py` 로 연결한다 | 학습 데이터와 같은 변환 | [변환](guides/dicom-to-nifti.md) |
| SUV 기준 시각 | SeriesTime(`--suv-time series`) | 파일 순서에 결과가 좌우되지 않게(DecayCorrection=START) | [변환](guides/dicom-to-nifti.md) §3 |
| 병변 세기 | cc3d 18-연결(`val_script.con_comp`, autoPET 원본 그대로 복사) | autoPET 공식 지표와 숫자를 맞춘다 | [방법](methods/autopet3-pipeline.md) §7 |
| 환경 | 외부 레포마다 uv venv. 설치는 가이드 명령으로, 버전은 `env/*.lock.txt` 로 재현한다 | 재현 | [환경](environment.md) |
| 해부 정보 | TotalSegmentator v2.18.0(사용 통계 끔) + autoDS-PET 함수로 구조 이름·간/혈액풀 대비·규칙 DS 를 붙인다(`--totalseg`) | 판독·LLM 에 위치 정보 | [TotalSegmentator](guides/totalsegmentator.md) §5–6 |
| LLM 소견 | 로컬 MedGemma 1.5 4B(vLLM, 127.0.0.1:8100), 6분류, 해부 값 포함(프롬프트 v3). `--llm-opinion` 을 줄 때만 페이지에 넣는다 | 환자 데이터를 밖으로 보내지 않는다 | [MedGemma](guides/medgemma.md) §7, [LLM 보조](methods/llm-assist.md) |
| 판독 페이지 | HTML 을 더블클릭해 연다(서버 없음). 판정은 브라우저에 쌓이고 CSV 로 내려받는다 | 단순하게 | [결과 확인](guides/review-results.md) §2 |
| 3D 판독 | 맥 3D Slicer. 페이지 "Slicer 로 보기"(petreview:// 연결 앱 → `petreview.sh slicer`), 도구막대 점 찍기(P)·구조 색(L), 3D 칸 SUV MIP, Slicer 용 영상은 PET 원래 해상도(상한 170M 복셀) | 페이지 안 3D 는 작고 도구가 적다 | [결과 확인](guides/review-results.md) §2-2 |
| 누락 병변 점 | Slicer 점은 `<case>_viewer/slicer_points.csv`(case 열)에 저장하고, 페이지에서 불러와 결과 CSV 에 `source=slicer` 로 합친다 | 더블클릭한 페이지는 옆 파일을 바로 읽을 수 없다 | [결과 확인](guides/review-results.md) §2-2 |
| 작업 방식 | 브랜치에 변경을 쌓고 사용자가 말할 때만 커밋·푸시·PR(에이전트는 묻기만). PR 은 작업 묶음 단위, Squash and merge. 시각화 아닌 코드는 사용자가 치고 check-typed, PR 은 Copilot 리뷰 | 이력을 읽기 쉽게(main 에는 PR 당 커밋 하나). 오타와 설계 문제를 각각 잡는다 | [Git 흐름](guides/git-workflow.md) |
| 문서 | 한국어 짧은 평서문. 굵게는 데이터 보호 경고에만 쓴다 | 읽기 쉽게 | [AGENTS](../AGENTS.md) |

## 공개 코드 출처

| 역할 | 공개 저장소 |
|---|---|
| 병변 탐지 모델·학습 트레이너 | <https://github.com/MIC-DKFZ/autopet-3-submission> (`257afc3`) |
| 학습·추론·평가·미세조정 프레임워크 | <https://github.com/MIC-DKFZ/nnUNet> (미세조정 `documentation/pretraining_and_finetuning.md`, 불확실 영역 `documentation/ignore_label.md`, 평가 `nnUNetv2_evaluate_folder`) |
| autoPET 공식 평가(18-연결 성분) | <https://github.com/lab-midas/autoPET> (`val_script.py`, `468179b`) |
| DICOM → SUV·CTres 변환 | <https://github.com/lab-midas/TCIA_processing> (`fb7b074`) |
| 장기·골격 분할 | <https://github.com/wasserth/TotalSegmentator> (v2.18.0) |
| 간·혈액풀 기준 영역·규칙 DS | <https://github.com/Sara-Peluso/autoDS-PET> (MIT, `fc6bc13`) |
| 3D 판독(맥) | <https://github.com/Slicer/Slicer> (3D Slicer 5.12) |
| 로컬 LLM 서빙 | <https://github.com/vllm-project/vllm> (0.32.0), 모델 <https://huggingface.co/google/medgemma-1.5-4b-it> |
