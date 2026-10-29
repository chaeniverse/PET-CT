# 작업 상태 (핸드오프)

> 작업을 이어받는 에이전트(Claude Code 등)는 이 문서를 가장 먼저 읽는다.
> 마지막 갱신: 2026-10-29 · 갱신할 때는 날짜와 "현재 위치"·"다음 할 일"을 같이 고친다.

## 1. 한 줄 요약

autoPET III LesionTracer(nnU-Net ResEnc-L, 5-fold) 공개 가중치로 파일럿 2명(P01, P02)의 병변 탐지 추론까지 끝났다.
2026-10-26 외부 레포를 다시 받아 파일럿 전 과정(변환 → 추론 → TotalSegmentator → MedGemma 소견)을 처음부터 다시 돌렸고,
10-27 판독 페이지를 서버 없이 여는 방식과 맥 3D Slicer 판독으로 바꿨다. 같은 날 저장소를 새로 시작했다(이전 기록은 `chaeniverse/PET-CT-archive`).
남은 것은 P01·P02 맥 육안 판독과 코호트 100명 일괄 파이프라인(issue #4)이다.

## 2. 반드시 지킬 규칙 (요약 — 원문은 AGENTS.md, docs/data-governance.md)

- 환자 데이터(DICOM·NIfTI·마스크·임상자료)·가중치는 커밋·업로드·채팅 출력 금지. 환자는 P01/P02, C001–C274 가명만.
- 원본 폴더·파일명·DICOM 헤더에 이름·등록번호가 있다. 경로는 상위 폴더까지만 적고, 헤더는 식별 태그를 출력하지 않는다.
- Dropbox 공유 폴더 `.../MM/PET_MRD` 는 읽기 전용. 쓰기 전에 사용자에게 묻는다.
- 모델 코드를 새로 만들지 않는다. 공개 레포 명령 우선, 연결 코드는 사용자 승인 후.
- 시각화가 아닌 코드(.py·.sh)는 사용자가 친다. 에이전트는 고칠 곳을 채팅으로 주고 `/check-typed` 로 검사한다(AGENTS.md).
- 결과는 수치·서술로만 기록(영상 캡처 커밋 금지).

## 3. 어디에 무엇이 있나

| 무엇 | 위치 |
|---|---|
| 이 저장소 (워크스테이션) | `/chlee/PET-CT` (chlee 홈 = `/chlee`) |
| 원본 DICOM 복사본 (워크스테이션) | 파일럿: `~/autopet3/dicom_pilot/P01` (1515 files), `P02` (3742 files). 코호트: `~/autopet3/dicom/C001…C274` (외장하드 274명, 328 GB, 2026-10-23 전송 확인 완료) |
| 가명 대응표 사본 (워크스테이션) | `~/autopet3/private/PETCT_pseudonym_map.tsv` (700/600, 내용 출력 금지, ③단계 레지스트리 결합 전용). 원본은 외장하드 |
| 파일럿 결과 (SeriesTime 기준, 2026-10-26 재실행) | 변환 `~/autopet3/work_series/P0x/`, 모델 입력 `~/autopet3/input_series/P0x_000{0,1}.nii.gz`, 추론 `~/autopet3/output_series/P0x.nii.gz` |
| 코호트 결과 (예정, 아직 비어 있음) | 변환 `~/autopet3/work/C###/`, 모델 입력 `~/autopet3/input/C###_000{0,1}.nii.gz`, 추론 `~/autopet3/output/C###.nii.gz` |
| 장기·골격 분할 결과 | `~/autopet3/totalseg/<case>/seg.nii.gz` (CT 격자, 117 라벨), 라벨 이름 표 `~/autopet3/totalseg/classes_total.json` |
| LLM 소견 | 입력 `~/autopet3/llm_input/<case>/`, 결과 `~/autopet3/llm/<case>_llm.json`, vLLM 로그 `~/autopet3/logs/` |
| 판독 페이지 (워크스테이션 생성본) | `~/autopet3/review/<case>_후보확인.html`, Slicer 용 영상 `~/autopet3/review/<case>_viewer/` |
| 후보 확인 판독 (맥) | 맥은 보기·판정만 한다. `Dropbox/Work/PIPET/과제/혈액내과/PET-MRD/autopet_review/`(후보확인 HTML·뷰어 NIfTI·판정 CSV·Slicer 점). 맥 로컬 도구 `PET-MRD/tools/petreview.sh`(git 밖, 사용법은 [guides/review-results.md](guides/review-results.md) §2) |
| 모델 가중치 | `~/autopet3/weights/Dataset222_AutoPETIII_2024/autoPET3_Trainer__nnUNetResEncUNetLPlansMultiTalent__3d_fullres_bs3/` (fold_0–4) |
| 외부 레포·환경 | `~/PET-CT/third_party/` (gitignored, 2026-10-26 재설치). 레포마다 uv `.venv`: autopet-3-submission(추론), TCIA_processing(변환), TotalSegmentator(v2.18.0, 가중치·설정 `~/autopet3/weights/totalseg` = `TOTALSEG_HOME_DIR`), vllm(LLM 서빙). autoPET·autoDS-PET 는 코드 출처 |
| 실험 기록 | `experiments/2026-10-08_autopet3-pilot/README.md` 가 지금 없다(2026-10-26 지워짐). §5 참고 |
| 회의록 (Obsidian) | `/Users/chaehyun/Library/CloudStorage/Dropbox/Obsidian Vault/01. PIPET/PET-CT/YYYY-MM-DD PET-CT 회의록.md` |
| 연구계획 | 공유 폴더 `회의 자료/[2026-09-27] PET FL-DS 자동산출 연구계획.pptx` |

## 4. 지금까지 한 일 (2026-10-08 ~ 10-28)

1. 저장소 뼈대·데이터 규칙·문서 체계
2. 워크스테이션 환경: uv venv, torch `2.11.0+cu128`, autopet-3-submission(`nnunetv2` 2.5.1 fork, commit `257afc3`) 설치
3. GPU 드라이버 신규 설치: 납품 상태엔 드라이버가 없었음 → `nvidia-driver-580-open` 580.178.04 (Secure Boot ON, Canonical 서명 모듈) → `cuda True`, `sm_120`
4. 가중치 다운로드 (Zenodo 14007247, md5 `566016409b0bd14770c0b57c1f2873f1` 일치)
5. 원자료 점검 → 사용할 시리즈 확정 ([data/index.md](data/index.md))
6. 변환 스크립트 `scripts/prepare_autopet_input.py` (TCIA_processing 함수 수정 없이 호출)
7. 맥 → 워크스테이션 DICOM 복사(P01/P02 가명 폴더로) → 변환 → 추론 완료
8. 후보 확인 HTML 페이지. 2026-10-21: 환경 재설치·재추론으로 재현 확인, lock(`env/`),
   LLM 의견 틀(`viewer_volumes.py`, `llm_opinions.py`, `llm_review.py`), 09-28 비교, 미세조정·LLM 계획 문서
9. 2026-10-22: 설치는 가이드 단계별 명령으로만 적는다(재현은 `env/*.lock.txt`). 추론 가이드를 변환·추론·결과 확인·TotalSegmentator 네 문서로 나눴다.
   SUV 기준 시각을 SeriesTime 으로 정했다.
   TotalSegmentator v2.18.0 환경([guides/totalsegmentator.md](guides/totalsegmentator.md), 사용 통계 끔)과 P01·P02 시험 분할(115/117 라벨, 필요한 라벨 모두 있음)
10. 2026-10-23: 직접 친 코드 검수 스킬 `/check-typed`(`.claude/skills/check-typed/`). 채팅 원본 사본(`~/.cache/petct-typed-ref/`)과 대조, 문법·린트(ruff 0.17.1, shellcheck 0.11.0)·데이터 보호 점검
11. 2026-10-23: 코호트 장비 분포 기록(data/index.md). 로컬 MedGemma 1.5 4B(vLLM 0.32.0, 127.0.0.1:8100)로 후보 그림 + 수치 소견을 카드 "LLM 의견" 칸에 넣었다
12. 2026-10-26: `third_party/` 를 지우고 다시 받아 파일럿 전 과정을 다시 돌렸다(변환 → 추론 → TotalSegmentator → 해부 정보 `--totalseg` → MedGemma 프롬프트 `fl-candidate-img-v3`).
    LLM 소견은 P01 16 후보 모두 `focal_lesion` 0.95, P02 2 후보 중 1개 `focal_lesion` 0.95·1개 의견 없음 → 변별이 없어 참고용
13. 2026-10-27: 저장소 새로 시작. PR #1 Copilot 리뷰 규칙, #2 판독 페이지를 서버 없이(더블클릭) 열기, #3 Slicer 도구막대(점 찍기 P·구조 색 L)·3D SUV MIP·페이지의 petreview:// 버튼.
    페이지 안 3D 보기(NiiVue)는 빼고 맥 3D Slicer 로 판독한다
14. 2026-10-28: PR #5 decisions.md 를 지금 유효한 결정 표로 줄였다. issue #4(코호트 100명 일괄 파이프라인)를 열었다

## 5. 다음 할 일 (우선순위 순)

- [x] 코호트 DICOM 전송 확인 (2026-10-23) — 274명 모두 로그 `rsync=0`·`src = dst`, 현재 장수 재집계 일치, `rsync -n` 크기·시각 비교 차이 0
- [x] 후보 카드 해부 정보 — `make_review_html.py --totalseg` 로 구조 이름·간/혈액풀 대비·규칙 DS(autoDS-PET `fc6bc13`)를 붙인다(2026-10-26)
- [ ] 파일럿 실험 기록 다시 쓰기 — `experiments/2026-10-08_autopet3-pilot/README.md` 가 2026-10-26 지워졌고, 워크스테이션 백업(`~/backup`)도 2026-10-28 지웠다.
  10-22 판은 깃허브 `chaeniverse/PET-CT-archive` 이력에만 있다(10-23 이후 내용은 없음). 10-26 재실행 결과는 기록하지 않았다. 되살릴 방법은 사용자가 정한다
- [ ] P01·P02 end-to-end 파일럿 (코호트 100명 전에) — 맥 판독 → 판정 CSV 를 워크스테이션 `~/autopet3/labels/` 로 → 정답 마스크 → 평가·미세조정 경로 시험.
  절차: [guides/review-results.md](guides/review-results.md) §2-1 "맥에서 보기·판정", §2-2 "맥 3D Slicer"
  - HTML 을 더블클릭해 연다(서버 없음). 판정은 브라우저에 쌓이고, Slicer 점을 불러와 합친 뒤 "결과 CSV 저장"(저장 창, 2026-10-29) 으로 `FL_labels_<case>.csv` 를 맥 판독 폴더에 바로 저장한다
  - 후보별 참 / 거짓 / 불확실, index lesion. 후보 밖 추가 위치(MIP 클릭·Slicer 점)도 줄마다 참 / 거짓 / 불확실을 고른다. LLM 의견은 참고용(동의 여부 안 받음)
  - 2026-10-29 페이지를 바꿨다(추가 위치 판정, LLM 동의 제거, 저장 창, 저장 키 v2). 첫 CSV 2개는 이전 형식이라 버리고, 새 페이지에서 처음부터 다시 판정했다
  - 2026-10-29 새 형식 CSV 2개를 `~/autopet3/labels/` 로 받았다(21열, 모든 줄 판정·좌표 있음). P01 후보 16개(참 10·거짓 4·불확실 2)·추가 5개(참 4·불확실 1), P02 후보 2개(참 1·거짓 1)·추가 4개(참 3·불확실 1). index lesion 은 고르지 않았다.
  - 2026-10-29 ⑦ 정답 마스크를 만들었다(`~/autopet3/labels/masks/`). P01 병변 19.3 mL·무시 43.7 mL, P02 병변 1.9 mL·무시 26.8 mL. 후보 18개가 모두 모델 마스크 성분과 맞았다. 추가 참 7개 초안(3.4–20.6 mL)은 모두 상자 끝에 닿아 무시(2)로 두었고, P01 A2 초안은 모델 후보 성분과 겹친다. 다음은 추가 참 초안을 Slicer 에서 다시 그릴 곳·방법 정하기
  - 특히 볼 곳: P02 천골 섭취(09-28 규칙 후보, 모델 미검출 — 놓친 병변인지), P01 기록 #02(규칙 후보와 15 mm 거리)
- [ ] 코호트 100명 일괄 파이프라인 — [issue #4](https://github.com/chaeniverse/PET-CT/issues/4). 단계마다 PR 하나, 가이드·decisions 를 같은 PR 에서 고친다
  - ① 시리즈 고르기(환자별 목록 → 규칙 추천 → `case, ct_desc, pt_desc` 표), PROPCPS 7명 SUV·장비 3종(Vision 600·TruePoint·Discovery 710) 정규화 확인
  - ② 변환(`--suv-time series`, `work`·`input`) ③ 추론 ④ TotalSegmentator ⑤ LLM 소견 → 페이지
  - ⑥ 판정 CSV 를 워크스테이션으로 보내는 규칙 — 2026-10-28 정함(`~/autopet3/labels/`, 데이터 거버넌스·미세조정 문서 수정). 맥 `petreview.sh send` 는 아직 없다(지금은 가이드의 rsync 명령)
  - ⑦ 판정 CSV → 정답 마스크 — `scripts/labels_from_review.py`(2026-10-29 P01·P02 실행). 추가 참은 배경 보정 50% 초안을 무시(2)로 두고 Slicer 확인 뒤 병변으로 합친다(합치는 단계는 아직 없음. 정답 마스크는 맥 → 워크스테이션 한 방향 규칙이라 맥 Slicer 로 보내려면 데이터 거버넌스 결정이 먼저다)
- [ ] 코호트 전 검토 — 전처리·정규화 문헌 조사(검색 키워드: [methods/preprocessing-literature.md](methods/preprocessing-literature.md)), GE Discovery 710 환자의 SeriesTime 이 AcquisitionTime 보다 늦은지 확인, 시리즈 선택 기준 선행연구, 연결 코드에 대응하는 공개 repo 가 있는지, LLM 소견 모델 비교(MedGemma 외 PETAR 가중치 요청, RADIANT-PET, Qwen3-VL 등)
- [ ] P02 체중 확인 — 헤더 체중이 성인 기준으로 낮다. 틀렸다면 SUV 가 작게 계산돼 병변을 놓쳤을 수 있다.
  실제 값을 받으면 재변환 필요 → 현재 스크립트엔 체중 덮어쓰기 옵션이 없으므로 추가 전 사용자 승인
- [ ] 다음 비교 모델 선정, 라벨링 계획(자체 nnU-Net 학습용), FL-DS 산출 설계 ([models/index.md](models/index.md), 연구계획 pptx)

## 6. 알려진 함정

| 상황 | 내용 |
|---|---|
| while-read + scp/ssh | 루프 안 scp/ssh 가 stdin 을 먹음 → `< /dev/null` |
| uv venv | `pip` 없음 → `uv pip install`. 외부 레포엔 uv.lock 없음 → `uv sync`/`uv add` 금지 |
| torch ≥ 2.6 | 추론 전 `export TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` (fork 의 `torch.load` 가 weights_only 미지정) |
| P02 CT 시리즈명 | `"CT  3 3.0 Br38"` — CT 뒤 공백 두 칸 |
| P01 Modality | CT·PET 모두 `NM` (SOP Class 는 정상) → 스크립트가 복사본에서만 교정 |
| SUV 기준 시각 | TCIA 원본은 폴더에서 처음 잡힌 PET 파일 1장의 AcquisitionTime 을 써서 결과가 파일 순서에 좌우된다(P01 맥 0.981 / 워크스테이션 1.0). 변환은 항상 `--suv-time series`(2026-10-22 결정). 로그 `suv_time_reference` 확인 |
| GitHub | private 레포. git 은 SSH 별칭 `github-petct`, `gh` 는 keyring 로그인. `gh` 토큰은 PET-CT 저장소만 보여 `PET-CT-archive` 는 브라우저로 본다. PR 본문 초안은 `.pr/*.md` |
| 브라우저 | `google-chrome`(deb) 사용 |
| 3D 보기(WebGL2, 2026-10-26 페이지 3D 를 빼고 Slicer 로 바꿔 지금은 해당 없음) | 원격 데스크톱(GPU 화면 없음)의 Chrome 은 WebGL2 가 꺼져 "Unable to initialize WebGL2". 소프트웨어 렌더링으로 따로 연다: `google-chrome --user-data-dir=$HOME/.config/chrome-viewer --use-angle=swiftshader --enable-unsafe-swiftshader "<주소>"` |
| TotalSegmentator 설정 | 실행마다 `TOTALSEG_HOME_DIR` 를 읽는다. 비어 있는 터미널에서 돌리면 `~/.totalsegmentator/` 에 사용 통계가 켜진 설정이 새로 생긴다 → 돌리기 전 `echo "$TOTALSEG_HOME_DIR"` |
| 드라이버 | Blackwell 은 `-open` 드라이버만. Secure Boot 환경에선 `ubuntu-drivers install nvidia:580-open`(서명 모듈) |

## 7. 작업 방식 메모

- 문서는 한국어, 짧은 평서문. 구조는 `AGENTS.md → docs/index.md → 기준 문서`.
- 굵게(`**…**`)는 정말 중요한 곳(데이터 보호, 되돌리기 어려운 작업 경고)에만 쓴다(AGENTS.md 규칙).
- 커밋·푸시·PR 은 사용자가 하라고 할 때만 한다. 브랜치 `타입/설명`, 커밋 `타입: 요약`, PR 은 작업 묶음 단위·Squash and merge([guides/git-workflow.md](guides/git-workflow.md)).
  PR 본문은 `.github/pull_request_template.md` (데이터 보호 체크리스트 필수), 초안은 `.pr/` (gitignored).
- 변경 시 관련 문서(가이드·decisions·status)를 같은 변경 단위에서 갱신.
- 역할 나눔(2026-10-22): 코드·문서·커밋·PR 은 워크스테이션 클론 `/chlee/PET-CT` 에서만 한다. 맥(Cowork 세션 포함)은 Dropbox 판독 폴더에서 보기와 판정만 하고, 맥 클론은 쓰지 않는다.
