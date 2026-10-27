# MedGemma — 후보 카드 소견용 로컬 의료 VLM

후보 확인 페이지의 카드마다 "LLM 의견" 칸에 영상-언어 모델(VLM)의 소견을 넣는다. 모델은 Google 의 범용 의료 VLM MedGemma 1.5 4B 이고,
공개 서빙 도구 vLLM 으로 워크스테이션 안(127.0.0.1)에서만 돌린다. 환자 영상·수치는 워크스테이션 밖으로 나가지 않는다.

- 모델: <https://huggingface.co/google/medgemma-1.5-4b-it> — Gemma 3 기반 4B, 2026-01-13 공개. 입력은 글과 영상(896×896), 출력은 글
  - 다루는 영상: 흉부 X선, 3D CT·MRI, 병리, 안저, 피부. PET 은 학습 목록에 없다. 소견은 전문의 판정과 비교해 따로 평가한다
  - 공식 용도: 개발의 출발점. 출력은 진단·치료 결정에 바로 쓰지 않고 예비 의견으로 다룬다(모델 카드)
- 약관: [Health AI Developer Foundations Terms](https://developers.google.com/health-ai-developer-foundations/terms). Hugging Face 에서 동의해야 받을 수 있다(즉시 승인)
  - 약관의 "Clinical Use" 정의에 연구의 일부로 진단·치료에 쓰는 것이 들어간다. 우리는 판독 보조 의견 표시와 일치도 평가에만 쓴다. IRB 승인 범위는 사용자가 확인한다
  - 가중치를 다른 사람에게 넘길 때는 약관 사본도 함께 줘야 한다. 우리는 `~/autopet3/weights/` 밖으로 옮기지 않는다
- 서빙: vLLM <https://github.com/vllm-project/vllm> (Apache-2.0) 0.32.0. OpenAI 호환 주소를 열어 `scripts/llm_review.py` 가 그대로 부른다

## 1. 약관 동의 · 토큰 (브라우저, 사용자 본인)

1. Hugging Face 에 로그인하고 모델 페이지에서 약관에 동의한다.
2. Settings ▸ Access Tokens 에서 Read 권한 토큰을 만든다. 토큰은 비밀번호와 같다. 채팅·문서·저장소에 붙이지 않는다.

## 2. C 컴파일러 (관리자 계정, 1회)

vLLM 은 서버를 띄울 때 Triton 이 GPU 커널을 그 자리에서 컴파일한다. 이때 C 컴파일러(gcc)가 필요하다.
워크스테이션에는 처음에 gcc 가 없어 `Failed to find C compiler` 로 서버가 멈췄다. 2026-10-23 관리자 계정(`pipet`)으로 설치했다(다시 만들 때만 필요).

```bash
sudo apt update && sudo apt install -y build-essential
gcc --version | head -1                               # chlee 계정에서도 보이면 된다
```

`--enforce-eager` 로 컴파일을 끄는 방법은 쓰지 않는다. 주의 연산(TRITON_ATTN)도 Triton 커널이라 컴파일러가 어차피 필요하다.

## 3. vLLM 환경 (워크스테이션)

외부 레포를 clone 하지 않고 PyPI 패키지만 설치하므로, 자리만 `third_party/vllm/` 에 만든다. autoPET·TotalSegmentator 와 venv 를 따로 둔다
(vLLM 은 torch 버전을 정확히 고정한다: 0.32.0 은 `torch==2.13.0`).

```bash
mkdir -p ~/PET-CT/third_party/vllm && cd ~/PET-CT/third_party/vllm
uv venv --python 3.12
source .venv/bin/activate

uv pip install vllm==0.32.0 --torch-backend=auto     # 드라이버(580, CUDA 13.0)를 보고 맞는 torch 빌드를 고른다
vllm download-kernels                                 # vLLM 공식 설치 단계(미리 빌드된 커널 받기)
python -c "import torch, vllm;print(vllm.__version__, torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_arch_list())"
#   → 0.32.0, True, 그리고 목록에 sm_120 이 있어야 함

uv pip freeze > ~/PET-CT/env/vllm.lock.txt            # 처음 한 번. 커밋한다
```

lock 이 생긴 뒤 같은 환경을 다시 만들 때는 venv 를 켠 다음 아래 순서로 한다.
lock 의 `flashinfer-cubin`·`flashinfer-jit-cache*` 는 PyPI 에 없고 `vllm download-kernels` 가 flashinfer 저장소에서 받는 커널이라, lock 을 그대로 넣으면 `No solution found` 로 멈춘다(2026-10-26).
그 줄만 빼고 설치한 뒤 커널을 받는다.

```bash
uv pip install -r <(grep -vE '^flashinfer-(cubin|jit-cache)' ~/PET-CT/env/vllm.lock.txt) --torch-backend=auto
vllm download-kernels
python -c "import torch, vllm;print(vllm.__version__, torch.__version__, torch.cuda.is_available(), torch.cuda.get_arch_list())"   # 0.32.0, True, sm_120
diff <(uv pip freeze) ~/PET-CT/env/vllm.lock.txt      # 아무것도 나오지 않으면 lock 과 같다
```

### 사용 통계 끄기

vLLM 은 기본값으로 익명 사용 통계(GPU·모델 구조·설정 등)를 보낸다. 서버를 한 번도 띄우기 전에 끈다. 공식 문서의 두 방법을 모두 쓴다.

```bash
mkdir -p ~/.config/vllm && touch ~/.config/vllm/do_not_track
grep -q VLLM_NO_USAGE_STATS ~/.bashrc || printf 'export VLLM_NO_USAGE_STATS=1\nexport DO_NOT_TRACK=1\n' >> ~/.bashrc
source ~/.bashrc && echo "$VLLM_NO_USAGE_STATS $DO_NOT_TRACK"      # 1 1
```

## 4. 가중치 받기 (처음 한 번)

```bash
source ~/PET-CT/third_party/vllm/.venv/bin/activate
hf auth login                                          # 1절 토큰을 붙여 넣는다(화면에 보이지 않음)
REV=$(python -c "from huggingface_hub import model_info;print(model_info('google/medgemma-1.5-4b-it').sha)"); echo "$REV"
hf download google/medgemma-1.5-4b-it --revision "$REV" --local-dir ~/autopet3/weights/medgemma-1.5-4b-it
chmod -R go-rwx ~/autopet3/weights/medgemma-1.5-4b-it
du -sh ~/autopet3/weights/medgemma-1.5-4b-it           # 약 8–9 GB
hf auth logout                                         # 다 받았으면 토큰을 지운다
```

- `REV`(모델 커밋 해시)는 실험 기록에 남긴다. 같은 가중치인지 나중에 확인할 수 있다.
- 받은 뒤에는 인터넷이 필요 없다. 서버는 오프라인 모드로 띄운다.

## 5. 서버 띄우기 · 끄기

포트 8000·8001 은 워크스테이션에서 이미 쓰고 있어 8100 을 쓴다. 주소는 127.0.0.1 로만 연다(다른 컴퓨터에서 접속 불가).

```bash
source ~/PET-CT/third_party/vllm/.venv/bin/activate
mkdir -p ~/autopet3/logs
HF_HUB_OFFLINE=1 nohup vllm serve ~/autopet3/weights/medgemma-1.5-4b-it \
  --served-model-name medgemma-1.5-4b-it --host 127.0.0.1 --port 8100 \
  --dtype bfloat16 --max-model-len 8192 --gpu-memory-utilization 0.45 \
  --limit-mm-per-prompt '{"image": 4}' > ~/autopet3/logs/vllm_medgemma.log 2>&1 &
tail -f ~/autopet3/logs/vllm_medgemma.log             # "Application startup complete" 가 보이면 Ctrl+C
```

- `--gpu-memory-utilization 0.45`: GPU 32 GB 중 약 14 GB 만 잡는다. 기본값(0.9)이면 autoPET·TotalSegmentator 를 같이 못 돌린다.
- `--limit-mm-per-prompt`: 요청 하나에 그림 4장까지(카드의 PET 3면 + CT 축상면).
- 끌 때: `pkill -f "vllm serve"`. 쓰지 않을 때는 꺼 둔다(공용 GPU).

## 6. 동작 확인 (환자 데이터 없이)

```bash
curl -s http://127.0.0.1:8100/v1/models | python -m json.tool | grep '"id"'      # "medgemma-1.5-4b-it"
curl -s http://127.0.0.1:8100/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "medgemma-1.5-4b-it", "max_tokens": 120,
  "messages": [{"role": "user", "content": "In one sentence, what does SUVmax mean in FDG PET?"}]}' \
  | python -c "import json,sys;print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

한 문장 답이 나오면 된다. 후보 그림·수치·해부 값으로 소견을 받는 단계는 §7 이다.

## 7. 후보 소견 받기 → 후보 확인 페이지에 넣기

서버는 ②(소견 받기) 동안만 켜 둔다. ①과 ④는 서버 없이 돌아가므로 ①은 서버를 띄우기 전에 해 둬도 된다.
맥에서 HTML 을 열 때는 서버·모델이 필요 없다(소견이 글자로 HTML 안에 들어간다).

```bash
cd ~/PET-CT
AP=~/PET-CT/third_party/autopet-3-submission/.venv/bin/python
# ① 후보 그림과 빈 의견 틀만 만든다(HTML 은 만들지 않음). 그림은 맥으로 보내지 않는 ~/autopet3/llm_input/<case>/<기록#>.png
#    (PET 3면 + CT 축상면, 2×2), 빈 틀은 ~/autopet3/llm/<case>_llm.json
$AP scripts/make_review_html.py P01 P02 --input ~/autopet3/input_series --output ~/autopet3/output_series --totalseg ~/autopet3/totalseg --llm-input-only
# ② 후보마다 그림 + 수치를 로컬 MedGemma 에 보내 <case>_llm.json 을 채운다(서버가 켜져 있어야 한다, §5)
$AP scripts/llm_review.py P01 P02 --model medgemma-1.5-4b-it --base-url http://127.0.0.1:8100/v1 --images
pkill -f "vllm serve"                                   # ③ 서버 끄기
# ④ 의견 폴더를 주고 페이지를 만들면 카드 오른쪽 "LLM 의견" 칸에 판정·근거가 들어간다
$AP scripts/make_review_html.py P01 P02 --input ~/autopet3/input_series --output ~/autopet3/output_series --totalseg ~/autopet3/totalseg --llm-opinion ~/autopet3/llm
```

- `--llm-opinion` 을 주지 않으면 LLM 칸은 "아직 없음"으로 비어 나온다. 의견 파일은 읽지도 만들지도 않는다.
- `--totalseg` 는 해부 값(구조 이름·간/혈액풀 대비·규칙 DS)을 LLM 입력에 넣는다([TotalSegmentator 가이드](totalsegmentator.md) §6). ①과 ④에 같은 값을 준다.
  해부 값 없이 받은 결과와 비교하려면 `--totalseg` 없이 ①–④ 를 따로 돌리고 `--dir`·`--llm-opinion` 폴더를 나눈다.
- 판정은 6분류다: `focal_lesion`(국소 골병변), `diffuse`(미만성 골수 섭취), `extramedullary`(골수외 병변), `physiologic`(생리적 섭취),
  `false_positive`(위양성: 염증·골절 등), `unsure`(불확실). 전문의 판정 버튼(참/거짓/불확실)은 그대로다.
- 이미 의견이 있는 후보는 건너뛴다. 프롬프트·모델을 바꿔 다시 받을 때는 ②에 `--overwrite` 를 붙인다.
- `<case>_llm.json` 에 모델 이름과 프롬프트 버전(`fl-candidate-img-v3`, 해부 값 포함)이 남는다. 바꾸면 버전을 올린다.
- 다시 추론해 후보가 바뀌면 ①·④가 옛 `<case>_llm.json` 을 알아보고 멈춘다(옛 의견이 다른 후보에 붙지 않게). 옛 파일을 지우거나 옮긴 뒤 ①부터 다시 한다.
- 맥에서는 평소처럼 review 폴더를 받아 연다([결과 확인 가이드](review-results.md) §2-1, Slicer 는 §2-2). 판독 전 "내 판정 전에는 LLM 의견 숨기기"를 켠다.
