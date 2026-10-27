# 결정 기록

## 2026-10-08 · 병변 탐지 첫 모델로 autoPET III LesionTracer 가중치를 쓴다

nnU-Net 은 데이터로 직접 학습시키는 프레임워크라 공식 MM 가중치가 없다. 정답 마스크가 없는 2명으로는
학습할 수 없으므로, FDG/PSMA 전신 PET/CT 병변으로 이미 학습된 autoPET III 1위 모델(LesionTracer,
nnU-Net ResEnc-L 기반, 5-fold)을 가져와 **추론만** 한다.

- 장점: nnU-Net 생태계 그대로(`nnUNetv2_predict_from_modelfolder`), 가중치 공개(CC BY 4.0), 코드 Apache-2.0.
- 한계: 학습 데이터가 림프종·흑색종·폐암·전립선암 중심이다. 골수 침범·작은 용골성 병변·미만성 섭취를 놓치거나
  생리적 섭취를 병변으로 잡을 수 있다. 파일럿 결과는 "가능성 확인"으로만 해석한다.

## 2026-10-08 · 모델 입력은 autoPET 관례(CTres + SUV)를 따른다

autoPET 데이터는 PET 을 SUV 로 바꾸고 CT 를 PET 격자로 리샘플한 `SUV.nii.gz`·`CTres.nii.gz` 를 제공하고
이를 입력으로 권장한다. 학습 분포와 맞추기 위해 같은 형태로 만든다
(`_0000` = CTres, `_0001` = SUV).

## 2026-10-08 · 데이터·가중치는 저장소 밖에 둔다

환자 데이터는 기관 밖으로 나가면 안 되고, 가중치(3.8 GB)는 Git 에 맞지 않는다. 둘 다 `.gitignore` 로 막고
워크스테이션·외장하드에만 둔다.

## 2026-10-08 · 입력 변환은 TCIA_processing 함수를 그대로 쓰고, 연결 코드만 둔다

autoPET 학습 데이터가 이 코드로 만들어졌으므로 같은 변환을 써야 입력 분포가 맞는다. 다만 원 스크립트는
`환자/검사/시리즈` 구조·Modality 태그·SEG 존재를 가정해 우리 데이터(시리즈 혼재, P01 Modality=NM, SEG 없음)에 바로 못 쓴다.
그래서 `scripts/prepare_autopet_input.py` 가 시리즈 선택·복사·복사본 Modality 교정만 하고, 변환 함수는 수정 없이 호출한다.
SUV 기준 시각은 원본과 같은 AcquisitionTime 을 기본으로 두고, SeriesTime 기준과의 비율을 로그에 남긴다
(FL-DS 처럼 SUV 절대값이 중요한 단계에서는 `--suv-time series` 를 검토). → 2026-10-22 SeriesTime 으로 바꿈(아래).

## 2026-10-22 · 실험 기록(`experiments/`)은 깃허브에 올리지 않는다

사용자 결정. 실험 기록은 워크스테이션 로컬 `~/PET-CT/experiments/` 에만 두고 `.gitignore` 로 추적하지 않는다.

## 2026-10-22 · 분석·학습은 공개 저장소 코드로, 직접 만든 코드는 시각화·연결만

사용자 결정. 병변 탐지·평가·미세조정은 공개 저장소의 코드와 공식 명령을 쓰고, 우리 데이터와 프로젝트에 맞추는 것은 미세조정으로 한다.
이 저장소에서 직접 만든 코드는 시각화(후보 확인 페이지·3D 뷰어)와 데이터 연결(변환·전송·설치)로 한정한다.

| 역할 | 공개 저장소 |
|---|---|
| 병변 탐지 모델·학습 트레이너 | https://github.com/MIC-DKFZ/autopet-3-submission |
| 학습·추론·평가·미세조정 프레임워크 | https://github.com/MIC-DKFZ/nnUNet (미세조정: `documentation/pretraining_and_finetuning.md`, 불확실 영역: `documentation/ignore_label.md`, 평가: `nnUNetv2_evaluate_folder`) |
| autoPET 공식 평가 지표(Dice·위양성 부피·위음성 부피, 18-연결 성분) | https://github.com/lab-midas/autoPET (`val_script.py`) |
| DICOM → SUV·CTres 변환 | https://github.com/lab-midas/TCIA_processing |
| 장기·골격 분할(기준 SUV, 골 이름) | https://github.com/wasserth/TotalSegmentator |
| Deauville 기준 영역(간·MBP)·점수 규칙 | https://github.com/Sara-Peluso/autoDS-PET (MIT, commit `fc6bc13`, 후보 카드 단계에서 사용 예정) |
| 3D 뷰어(시각화) | https://github.com/niivue/niivue |

- `prepare_autopet_input.py` 는 TCIA_processing 함수를 수정 없이 부르는 연결 코드라 유지한다.

## 2026-10-22 · SUV 기준 시각을 SeriesTime 으로 한다

변환 때 SUV 감쇠 보정 기준을 `--suv-time series`(SeriesTime)로 한다. 이유:

1. 정의: 두 케이스 모두 DICOM `DecayCorrection = START` 다. 영상 값이 스캔 시작 기준으로 이미 보정돼 있어,
   투여량도 스캔 시작(SeriesTime)까지 감쇠시켜야 SUV 정의가 맞는다(QIBA SUV 계산 방식과 같음).
2. 재현성: TCIA 원본은 폴더에서 처음 잡힌 PET 파일 1장의 AcquisitionTime 을 쓴다. 다중 베드·연속 이동 영상은 장마다 시각이 달라,
   같은 데이터도 컴퓨터마다 SUV 가 달라졌다(P01 맥 0.981 / 워크스테이션 1.0). SeriesTime 은 모든 장에 같다.
3. 모델 영향이 작다: 같은 가중치로 두 기준을 비교한 결과(`scripts/compare_runs.py`)
   - P01: 비율 1.0000, 병변 15개 35.9 mL, Dice 1.000(같은 결과)
   - P02: 비율 0.9545, 병변 2개 2.41 → 2.35 mL, Dice 0.987. 병변 수·위치는 같고 경계만 약간 줄었다.

autoPET 학습 데이터는 TCIA 원본 방식이라 같은 흔들림이 섞여 있지만, 위 비교처럼 이 정도 차이에는 출력이 거의 변하지 않는다.
09-28 규칙 기반 시험실행(SeriesTime 기준)과도 SUV 가 같아진다. 이 결정은 이슈 'SUV 감쇠 보정 기준 시각'을 마무리한다.

## 2026-10-22 · 환경 설치는 가이드의 단계별 명령 하나로만 적는다

설치 절차는 가이드([추론](guides/autopet3-inference.md)·[변환](guides/dicom-to-nifti.md)·[TotalSegmentator](guides/totalsegmentator.md))에만 둔다.

- 재현은 `env/*.lock.txt`(`uv pip freeze` 결과)가 맡는다. lock 은 그대로 커밋해 두고, 추론 가이드 §3·변환 가이드 §2·TotalSegmentator 가이드 §2 의 lock 설치 명령으로 같은 버전을 다시 설치한다.
- 스크립트가 하던 GPU 확인(`sm_120`)은 가이드의 확인 줄이 같은 일을 한다.
- TotalSegmentator 환경도 스크립트 없이 가이드로만 설치한다.

## 2026-10-22 · TotalSegmentator v2.18.0 을 별도 환경에서, 사용 통계를 끄고 쓴다

후보 카드의 골 이름과 기준 SUV(간·MBP)를 위해 CT 장기·골격 분할을 TotalSegmentator 공식 CLI(`--task total --ml`)로 한다.

- 버전: v2.18.0(태그 커밋 `184fa47`, Apache-2.0). `third_party/TotalSegmentator` 에 clone 해 editable 로 설치하고 lock 은 `env/totalseg.lock.txt`.
- 환경: autoPET 과 다른 venv. 공식 `nnunetv2` 2.8.1 은 torch 2.11.0+cu128 과 그대로 동작한다.
- 가중치·설정: `TOTALSEG_HOME_DIR=~/autopet3/weights/totalseg`. autoDS-PET 도 같은 CLI 를 subprocess 로 부르므로 나중에 같은 버전·같은 폴더를 쓴다.
- 사용 통계: 기본값은 실행마다 `stats.totalsegmentator.com` 으로 보낸다. 데이터 거버넌스에 따라 첫 실행 전에 `send_usage_stats=false` 로 끈다.
- 입력: 원본 해상도 CT(`work*/<case>/nifti/CT.nii.gz`). 결과는 CT 격자이므로, PET 격자 값과 맞출 때 리샘플한다.
- 적용(2026-10-22): P01·P02 시험 분할.

## 2026-10-23 · 가명 대응표 사본을 워크스테이션에 둔다

외장하드에만 두던 코호트 가명 대응표(`C###` ↔ 원본 폴더 이름)의 사본을 워크스테이션 `~/autopet3/private/` 에 둔다(사용자 결정).
대응표는 영상 분석에는 쓰지 않지만, 영상 결과를 임상 레지스트리(PFS)와 결합하는 ③단계에서 필요하다.

- 위치: 저장소 밖 `~/autopet3/private/PETCT_pseudonym_map.tsv`. 폴더 700·파일 600(홈 `/chlee` 도 750 이라 다른 계정은 들어올 수 없다).
- 저장소: 위치가 저장소 밖이고, `.gitignore` 가 `*.tsv`·`*pseudonym_map*` 를 막는다.
- 출력 금지: 내용은 화면·로그·문서·채팅에 내지 않는다. 옮긴 뒤 확인은 줄 수와 SHA-256 해시로만 한다.
- 외장하드 원본은 그대로 둔다.

## 2026-10-23 · 후보 카드 소견은 로컬 MedGemma 1.5 4B 로 받는다

후보 확인 페이지의 "LLM 의견" 칸에 영상-언어 모델 소견을 넣는다. 판정을 돕는 참고 의견이고, 진단에 쓰지 않는다.

- 모델: Google MedGemma 1.5 4B(<https://huggingface.co/google/medgemma-1.5-4b-it>), Health AI Developer Foundations 약관. PET 학습 이력은 없다.
- 검토한 다른 후보(2026-10-23 조사)
  - PETAR(병변 마스크 → 소견, PET 학습, arXiv 2510.27680): 가장 맞는 형태지만 가중치 미공개, 코드 라이선스 없음 → 저자에게 요청, 받으면 교체 검토
  - RADIANT-PET(후보별 병변/생리적 섭취 판정, 수치 글만 사용): 라이선스 미확인
- 서빙: vLLM 0.32.0, 127.0.0.1:8100, 오프라인(`HF_HUB_OFFLINE=1`), 사용 통계 끔.
- 입력: 카드의 2D 그림(PET 3면·CT 축상면, 빨간 윤곽)과 수치. MedGemma 의 3D 입력은 CT·MRI 만 지원해 PET 3D 는 넣지 않는다.
- 평가: 소견·판정을 전문의 판정과 비교한다.

## 2026-10-26 · `scripts/val_script.py` 를 autoPET 원본 그대로 쓴다

사용자 결정. 원본(lab-midas/autoPET `val_script.py`, commit `468179b`)을 고치지 않고 그대로 복사한다. 이전 사본은 성분 개수 함수(`count_comp`)를 더하고 `__main__` 을 새로 쓴 수정본이었다.

- 이유: 요약(`summarize_lesions.py`)·후보 확인 페이지(`make_review_html.py`)가 쓰는 것은 `con_comp` 하나이고, 이 함수는 원본과 수정본이 같다. 원본 그대로 두면 `cmp` 로 원본과 같은지 바로 확인할 수 있다.
- 두 스크립트는 고치지 않는다(같은 `scripts/` 폴더에서 `val_script` 를 그대로 불러온다).
- 잃는 것: 두 마스크 폴더를 비교하던 명령(Dice·위양성/위음성 부피·성분 개수). 원본 `__main__` 은 `sys.argv` 를 두 값으로 풀어 `ValueError` 가 나므로 명령으로는 쓰지 않는다.
  비교가 다시 필요하면 nnU-Net 공식 `nnUNetv2_evaluate_folder` 를 먼저 검토한다.

## 2026-10-26 · LLM 소견은 따로 받아 `--llm-opinion` 으로만 페이지에 넣고, 판정은 6분류로 한다

사용자 결정. 소견을 받는 단계와 페이지를 만드는 단계를 나눈다.

- 흐름: `make_review_html.py --llm-input-only`(후보 그림 `~/autopet3/llm_input/`·빈 틀 `~/autopet3/llm/<case>_llm.json`, HTML 없음) → `llm_review.py`(기본 폴더 `~/autopet3/llm`) → `make_review_html.py --llm-opinion ~/autopet3/llm`.
  `--llm-opinion` 을 주지 않으면 LLM 칸은 비어 나오고, 의견 파일·후보 그림을 만들지 않는다.
- 이유: 소견 유무를 페이지를 만들 때 고를 수 있고, 평소 페이지 생성 때 환자 그림(`llm_input/`)이 새로 생기지 않는다.
  후보 고르기·그림 그리기는 `make_review_html.py` 안에 그대로 두어 기록 번호가 한 곳에서만 정해진다.
- 안전장치: 의견 파일의 후보 입력값이 지금 마스크의 후보와 다르면(재추론 등) 멈춘다(`llm_opinions.check_same`). 옛 의견이 다른 카드에 붙지 않게 한다.
- 판정 6분류: `focal_lesion`·`diffuse`·`extramedullary`·`physiologic`·`false_positive`·`unsure`. 프롬프트 버전을 v2(`fl-candidate-v2`·`fl-candidate-img-v2`)로 올렸다.
  옛 3분류(`true`·`false`·`unsure`) 파일은 형식 오류로 읽지 않는다. 전문의 판정 버튼은 참/거짓/불확실 그대로 두고, LLM 칸만 6분류로 보인다.

## 2026-10-26 · 후보에 TotalSegmentator 해부 정보를 붙이고, 3D 보기·Slicer 에 구조 라벨을 보인다

사용자 결정. 분할·카드·LLM 입력·3D 보기를 나누지 않고 한 번에 붙인다.

- 계산: `scripts/anatomy.py`(연결 코드)가 TotalSegmentator `--task total --ml` 결과를 읽고, autoDS-PET(MIT, `fc6bc13`) 함수로 계산한다.
  분할 → SUV 격자는 `resample_to_reference`(nearest-neighbour), 기준 SUV 는 `LiverROI`(간 10 mm 침식 중앙값)·`AortaMBP`(T4–T8 대동맥·심장 제외 중앙값) 기본값, 규칙 DS 는 `assign_ds`(2×간).
  09-28 시험실행과 같은 규칙을 직접 다시 짜지 않고 공개 코드로 쓴다.
- 후보 값: `site`(SUVmax 자리의 구조 이름, 구조 밖이면 후보 안에서 가장 많이 겹친 구조)·`r_liver`·`r_mbp`·`ds_rule`. 카드와 LLM 입력(프롬프트 v3)에 넣는다.
- 3D 보기: 구조 라벨 층과 이름표, 관상·시상 한 화면, 전체화면(Fullscreen API). 브라우저는 맥 프로그램을 띄울 수 없고 맥의 `slicer://` 등록은 서명 문제로 불안정해,
  "Slicer 로 열기" 는 맥 터미널에 붙여 넣을 명령을 복사해 주고 `<case>_viewer/open_in_slicer.py` 를 실행하게 한다.
- 데이터: 뷰어용 구조 라벨·이름표·Slicer 스크립트를 맥 판독 폴더에 두는 예외를 둔다([데이터 거버넌스](data-governance.md) §2). 원본 해상도 분할은 워크스테이션에만 둔다.
- 라벨 이름 표는 공식 `totalseg_info --classes -ta total --json` 결과를 `~/autopet3/totalseg/classes_total.json` 에 둔다.

## 2026-10-26 · 페이지 안 3D(NiiVue)를 빼고 맥 3D Slicer 로 3D 판독한다

사용자 결정. 페이지 안 3D 는 작고 도구가 적어 판독에 맞지 않는다. 3D 는 Slicer 에서 보고, Slicer 에서 찍은 누락 병변을 판정 CSV 에 합친다.

- 실행: 맥 판독 폴더에서 `python3 review_server.py`(페이지 파일 제공 + `/slicer/<case>` 로 Slicer 실행 + `/goto/<case>` 로 위치 이동). 127.0.0.1 전용, 판독 페이지 요청(Origin)·가명 케이스만 받는다.
  브라우저는 맥 프로그램을 띄울 수 없고 `slicer://` 등록은 서명 문제로 불안정해, 이미 쓰던 로컬 서버가 대신 띄운다.
- Slicer: `open_in_slicer.py`(viewer_volumes.py 가 생성)가 CT·SUV·병변·후보 번호·구조 라벨을 열고, P 키로 찍은 점을 `slicer_points.csv`(RAS mm·구조 이름)에 쓴다. 페이지가 그 파일을 불러와 누락 병변(`source=slicer`)으로 합친다.
- 다른 도구(ITK-SNAP·OHIF·Horos)는 점 기록 스크립트·서버 준비·플러그인 면에서 Slicer 보다 무거워 쓰지 않는다. 좌표는 페이지·Slicer 모두 RAS mm 라 변환이 없다.
- 페이지 HTML 에 3D 영상을 넣지 않아 가벼워졌다. `--viewer-server`·`--mac-dir` 옵션은 없앴다. 2026-10-22 출처 표의 NiiVue 는 더 쓰지 않는다.

## 2026-10-27 · 판독 페이지는 서버 없이 더블클릭으로 연다

사용자 결정. 로컬 서버(`review_server.py`)를 띄우는 단계를 없앤다.

- 페이지: HTML 을 더블클릭(`file://`)해 연다. 판정·누락 병변 추가·CSV 내보내기는 서버 없이 된다.
- Slicer 열기: `<case>_Slicer열기.command` 를 Finder 에서 더블클릭한다(브라우저는 맥 프로그램을 띄울 수 없다).
- Slicer 에서 찍은 점: 페이지의 파일 선택으로 `slicer_points.csv` 를 고른다(`file://` 페이지는 옆 파일을 바로 읽을 수 없다).
- 잃는 것: 페이지에서 Slicer 를 후보 위치로 옮기던 기능. Slicer 의 Markups "후보" 목록으로 대신한다.
- 구조 라벨 색은 기본으로 숨기고 L 키로 켠다. 숨겨도 Data Probe·찍은 점에는 구조 이름이 나온다.

## 2026-10-27 · PR 리뷰에 GitHub Copilot 을 쓴다

사용자 결정. 혼자 작업하면서 놓치는 부분을 줄이려고 PR 마다 Copilot 코드 리뷰를 받는다(Gemini Code Assist 는 쓰지 않는다).

- 켜는 법: 개인 Copilot settings → Code review → Automatic Copilot code review. 개인 계정의 private 저장소에는 Rulesets 가 적용되지 않는다.
- 리뷰 규칙: `.github/copilot-instructions.md`(데이터 보호·공개 코드 우선·문서 동반·PR 크기, 한국어). main 에 머지된 규칙을 읽는다.
- 외부 분석 범위: Copilot 은 PR 의 코드 차이를 GitHub 로 보내 분석한다. 이 저장소에는 환자 데이터가 없는 코드·설정·문서만 있으므로 그 범위로 한정되고, PR 본문·댓글에도 환자 정보를 쓰지 않는다.
- 봇 의견은 참고다. 반영하지 않을 때는 이유를 답글로 남긴다. 머지된 PR 에 달린 의견은 다음 PR 에서 반영한다(첫 적용: PR #1 의 "결정 기록 누락" 의견).
