# 결과 확인 — 수치 요약 · 후보 확인 페이지

[autoPET III 추론](autopet3-inference.md) 결과(파일럿 `~/autopet3/output_series/<case>.nii.gz`, 코호트 `~/autopet3/output/<case>.nii.gz`)를 수치로 요약하고, 후보 확인 페이지로 판독한다.

## 1. 자동 수치 요약 (워크스테이션)

마스크를 autoPET 공식 평가와 같은 연결성분(cc3d 18-연결, `scripts/val_script.py` 의 `con_comp`)으로 나눠 병변 수·부피·SUVmax 를 센다.
번호는 부피 큰 순이고 후보 확인 페이지의 '기록 #' 과 같다.

```bash
source ~/PET-CT/third_party/autopet-3-submission/.venv/bin/activate
cd ~/PET-CT && python scripts/summarize_lesions.py P01 P02 --input ~/autopet3/input_series --output ~/autopet3/output_series   # 코호트는 C001 … (기본 폴더 input·output)
```

## 2. 후보 확인 페이지 (브라우저)

공유 폴더 `후보확인 프로토타입` 의 FL 후보 확인 도구와 같은 화면을 autoPET 출력으로 만든다.
[`scripts/make_review_html.py`](../../scripts/make_review_html.py) 가 마스크의 연결성분(autoPET 공식 평가와 같은 18-연결, `val_script.con_comp`)을 후보로 삼아
케이스마다 HTML 한 장을 만든다. 카드는 SUVmax 순이고, 각 카드의 '기록 #' 은 `summarize_lesions.py` 표 번호(부피 순, 같으면 SUVmax 순)와 같다.

| 화면 | 내용 |
|---|---|
| 관상면 MIP | 후보 번호. 클릭하면 열린 Slicer 가 그 점의 가장 뜨거운 깊이로 간다 |
| 3D 보기(3D Slicer) | "Slicer 로 보기"(맥 Slicer 실행), "Slicer 에서 찍은 점 불러오기"(누락 병변 목록에 합침). 페이지 안에는 3D 영상을 넣지 않는다(§2-2) |
| 후보 카드 | PET 축상·관상·시상 + CT 축상, SUVmax·SUVpeak·SUVmean·부피·HU, 위치(구조 이름)·간/혈액풀 대비·규칙 DS(`--totalseg`) |
| 판정 | 참/거짓/불확실, index lesion, 메모, 놓친 병변 추가(MIP 클릭 또는 3D 십자선), CSV 내려받기 |
| LLM 의견 | 6분류 판정·확신도·근거(`--llm-opinion`), "맞다/아니다" |

옵션에 따라 채워지는 칸이 다르다.

- `--totalseg ~/autopet3/totalseg`: 카드 위치 줄, 머리말 기준 SUV, Slicer 구조 라벨([TotalSegmentator 가이드](totalsegmentator.md) §6). 주지 않으면 이 칸들이 빠진다
- `--llm-opinion ~/autopet3/llm`: LLM 의견 칸. 주지 않으면 "아직 없음"으로 비어 나온다. 소견 받는 법은 [MedGemma 가이드](medgemma.md) §7

```bash
cd ~/PET-CT
~/PET-CT/third_party/autopet-3-submission/.venv/bin/python scripts/make_review_html.py P01 P02 --input ~/autopet3/input_series --output ~/autopet3/output_series --totalseg ~/autopet3/totalseg --llm-opinion ~/autopet3/llm --note "P02=헤더 체중 확인 전 SUV"
```

- 출력: `~/autopet3/review/<case>_후보확인.html`, Slicer 용 `<case>_viewer/`(CT·SUV·마스크, 후보 목록, `--totalseg` 이면 구조 라벨·이름표, `open_in_slicer.py`), 맥에서 쓸 `review_server.py`(저장소 `scripts/` 에서 복사).
  **영상이 들어 있으므로 저장소·다른 클라우드·공유 폴더로 옮기지 않는다.** 허용 위치는 [데이터 거버넌스](../data-governance.md) §2. 저장소 안을 출력 폴더로 주면 스크립트가 멈춘다.

### 2-1. 맥에서 보기·판정

역할 나눔(2026-10-22): 코드·문서·커밋은 워크스테이션 `~/PET-CT` 에서만 하고, 맥은 보기와 판정만 한다.
맥 판독 폴더는 `~/Library/CloudStorage/Dropbox/Work/PIPET/과제/혈액내과/PET-MRD/autopet_review/` 이고,
판정 CSV 는 맥 판독 폴더에만 둔다(워크스테이션·저장소로 보내지 않는다). CSV 를 요약해 실험 기록에 옮기는 방법은 아직 정하지 않았다.
맥 로컬 도구 `PET-MRD/tools/petreview.sh`(저장소 밖, fetch·open·collect·status·stop)가 아래 명령들을 묶어 둔 것이다.
도구 없이 손으로 할 때(맥 터미널, zsh):

```zsh
WS=chlee@pipet-cmccpt          # 연구실 안이면 chlee@192.168.0.251
DST="$HOME/Library/CloudStorage/Dropbox/Work/PIPET/과제/혈액내과/PET-MRD/autopet_review"
rsync -av "${WS}:autopet3/review/" "$DST/" && chmod -R go-rwx "$DST"
python3 "$DST/review_server.py"                                   # 판독하는 동안 켜 둔다(127.0.0.1:8765, Ctrl+C 로 끔)
open -a "Google Chrome" "http://127.0.0.1:8765/P01_후보확인.html"
# 판정이 끝나면 "결과 CSV 내려받기" → FL_labels_<case>.csv 를 $DST 에 저장한다
# (Chrome 설정 > 다운로드 > "다운로드 전에 각 파일의 저장 위치 확인" 을 켜 두면 바로 $DST 에 저장할 수 있다)
```

- 열기: `review_server.py` 주소(`http://127.0.0.1:8765/…`)로 연다. 더블클릭(`file://`)으로도 카드·판정은 되지만 Slicer 버튼이 동작하지 않고,
  판정은 주소별 브라우저 저장소에 `fl-review:<case>` 키로 쌓이므로 한 가지 주소로만 연다(`file://` 와 서버 주소, 포트가 다르면 판정이 이어지지 않는다).
- `review_server.py` 는 판독 폴더 파일을 주는 것(`python3 -m http.server` 와 같음)에 더해, 페이지 버튼으로 Slicer 를 띄우고(`/slicer/<case>`) 열린 Slicer 를 옮긴다(`/goto/<case>`).
  127.0.0.1 에서만 열리고, 판독 페이지에서 온 요청과 가명 케이스(`P01`, `C001`)만 받는다.
- 후보 번호(SUVmax 순)가 바뀐 새 HTML 을 받으면 이전 판정이 다른 카드에 붙는다. 진행 표시를 먼저 보고, 필요하면 CSV 를 받아 둔 뒤 "판정 모두 지우기".
- rsync 에 `--delete` 를 쓰지 않는다(맥 쪽 CSV 를 지우지 않도록).
- 맥에서 판독하면 CSV 를 판독 폴더(`$DST`)에 저장한다(Downloads 에 남기지 않는다).
- CSV 좌표는 RAS mm(Slicer 와 같은 좌표계)다. 놓친 병변은 MIP 를 클릭하면 그 점의 최대 SUV 깊이로(`source=mip`), Slicer 에서 찍으면 그 점으로(`source=slicer`, 메모에 구조 이름) x·y·z 가 모두 남는다.

### 2-2. 맥 3D Slicer 로 3D 판독

페이지의 "Slicer 로 보기" 를 누르면 `review_server.py` 가 Slicer 를 띄운다(브라우저는 맥 프로그램을 직접 띄울 수 없어 서버가 대신 연다).
Slicer 는 `<case>_viewer/open_in_slicer.py` 를 실행해 CT 바탕에 SUV(PET-Heat, 0–8)·autoPET 병변(빨강)·후보 번호(남색 점, `카드 번호 (#기록)`)·구조 라벨(이름 포함, `--totalseg` 일 때)을 4분할로 연다.
영상은 Slicer 용으로 줄인 파일이다(수치는 카드 값을 쓴다).

| 하는 일 | 방법 |
|---|---|
| 후보 위치로 가기 | 페이지 카드의 "Slicer 에서 보기", MIP 클릭, 누락 병변 목록의 "Slicer" → 열린 Slicer 가 그 위치로 간다(`goto.json`, 0.5 초마다 확인) |
| 누락 병변 찍기 | Slicer 에서 P 키로 점 찍기를 켜고 끈다. 찍기·옮기기·지우기마다 `<case>_viewer/slicer_points.csv`(RAS mm·구조 이름)에 쓴다. 다시 열면 이어서 보인다 |
| 페이지로 가져오기 | 페이지의 "Slicer 에서 찍은 점 불러오기" → 3번 누락 병변 목록에 합쳐지고 결과 CSV 에 `source=slicer` 로 남는다 |
| 구조 이름 보기 | Slicer 에서 마우스를 올리면 아래 Data Probe 칸에 구조 이름이 나온다 |

손으로 열 때(서버 없이, 맥 터미널):

```zsh
cd "$DST/P01_viewer" && /Applications/Slicer.app/Contents/MacOS/Slicer --python-script open_in_slicer.py
```

Slicer 설치(맥 터미널, 처음 한 번). Homebrew 판은 Intel 빌드라 Apple Silicon 맥은 Rosetta 2 가 먼저 있어야 한다(macOS 14 이상).

```zsh
softwareupdate --install-rosetta --agree-to-license      # Apple Silicon 이고 Rosetta 가 없을 때만
brew install --cask slicer                               # /Applications/Slicer.app
```

- 처음에는 `Slicer --version` 이 아무것도 내지 않고 멈출 수 있다(macOS 가 처음 여는 앱을 막거나 Rosetta 가 없을 때). `open /Applications/Slicer.app` 로 한 번 열어 확인 창을 통과한 뒤(또는 Finder 에서 오른쪽 클릭 → 열기) 다시 한다.
