# LLM 보조 의견

후보 확인 페이지에 LLM 의견을 참고로 얹는 방법과 앞으로의 확장 방향을 정리한다.
지금(2026-10-26)은 워크스테이션 안의 MedGemma 1.5 4B(vLLM)에 후보마다 그림 1장·수치·해부 값을 보내 6분류 판정과 근거를 받는다.
실행 절차는 [MedGemma 가이드](../guides/medgemma.md) §7.

## 1. 원칙 (회의 결정)

- 화면의 주인공은 모델이 표시한 병변과 전문의 판정이다. LLM 이 판단을 앞세우면 판독이 LLM 에 끌려간다.
- 그래서 LLM 의견은 카드 오른쪽에 얹고, "LLM 은 이렇게 판단했는데 맞습니까?"를 묻는 데까지만 쓴다.
- 기본값으로 전문의가 자기 판정을 먼저 골라야 LLM 의견이 보인다(머리말 체크박스로 끌 수 있다).
- CSV 에 `llm_verdict`·`llm_confidence`·`llm_agree` 가 남는다. 판정(`label`)과 비교해 LLM 이 얼마나 맞았는지 나중에 센다.
  LLM 의견은 학습 정답으로 쓰지 않는다.

## 2. 구성

| 파일 | 하는 일 |
|---|---|
| `scripts/llm_opinions.py` | 입력·출력 형식(스키마), 빈 틀 만들기, 검사, 페이지용 읽기. `make_review_html.py` 와 `llm_review.py` 가 함께 쓴다 |
| `scripts/llm_review.py` | `<case>_llm.json` 의 후보마다 LLM 을 불러 `opinion` 을 채운다(프롬프트 v3) |
| `scripts/anatomy.py` | TotalSegmentator 분할로 후보의 구조 이름·간/혈액풀 대비·규칙 DS 를 구한다(autoDS-PET 함수, §5-1) |
| `~/autopet3/llm/<case>_llm.json` | 후보별 입력 수치와 LLM 의견(저장소 밖, 맥으로 보내는 review 폴더 밖) |

순서: `make_review_html.py --totalseg … --llm-input-only`(후보 그림·빈 틀 생성, HTML 없음) → `llm_review.py`(의견 채움) → `make_review_html.py --totalseg … --llm-opinion ~/autopet3/llm`(페이지에 표시).
`--llm-opinion` 을 주지 않으면 LLM 칸은 비어 나온다. `--totalseg` 는 두 번 모두 같게 준다(입력값이 다르면 멈춘다).

LLM 입력은 `llm_opinions.FEATURES` 의 값뿐이다: SUVmax·SUVpeak·SUVmean·부피·HU·좌표, 그리고 `--totalseg` 일 때 `site`·`r_liver`·`r_mbp`·`ds_rule`.

판정(`verdict`)은 6분류다(2026-10-26, 프롬프트 v2 부터): `focal_lesion`(국소 골병변), `diffuse`(미만성 골수 섭취), `extramedullary`(골수외 병변),
`physiologic`(생리적 섭취), `false_positive`(위양성: 염증·골절 등), `unsure`(불확실). 전문의 판정은 참/거짓/불확실 그대로다.

## 3. 지금: 워크스테이션 안의 로컬 LLM 서버 (vLLM)

"로컬 서버"는 공개 가중치 LLM 을 워크스테이션 GPU 에 올려 두고 같은 컴퓨터 안에서 HTTP 로 부르는 방식이다.
예: Ollama, vLLM. 둘 다 OpenAI 와 같은 형식의 주소(`/v1/chat/completions`)를 연다. 우리는 vLLM 0.32.0 으로 127.0.0.1:8100 을 연다.
서버 없이 `transformers` 로 모델을 직접 불러오는 방식도 있지만, `llm_review.py` 가 OpenAI 호환 형식으로 짜여 있어 모델을 바꿀 때 주소·이름만 바꾸면 되는 서버 방식을 쓴다.

- 호출 형식은 API 와 같다. 다만 주소가 `127.0.0.1` 이라 요청이 워크스테이션 밖으로 나가지 않는다.
  인터넷 연결이 필요 없고 호출당 비용도 없다.
- 준비물은 서버 프로그램 설치와 공개 모델 가중치 내려받기다. 모델 크기는 GPU 메모리(32 GB) 안에서 고른다.
- `llm_review.py` 는 주소가 localhost 가 아니면 거부한다.
  후보 수치표(SUV·부피·HU·좌표)도 환자 파생물이라 외부로 보낼 수 없기 때문이다([데이터 거버넌스](../data-governance.md) §1).

## 4. 나중에: 외부 API 확장 (확장성 고려)

외부 API(상용 LLM)는 성능이나 운영 면에서 이점이 있을 수 있어 확장 대상으로 남겨 둔다. 다만 아래가 모두 갖춰지기 전에는 쓰지 않는다.

1. 연구실·기관 승인. IRB 계획서와 데이터 반출 범위를 확인한다.
2. 데이터 거버넌스 문서 개정. 어떤 필드를, 어느 서비스로 보낼 수 있는지 허용 표에 적는다.
3. 서비스 조건 확인. 입력을 학습에 쓰지 않는지, 보관 기간, 처리 지역, 기관 계약(데이터 처리 계약) 여부를 본다.
4. 보내는 필드는 최소로 한다. `llm_opinions.FEATURES` 의 수치만 보내고, 영상·마스크·식별정보·날짜는 보내지 않는다.

코드에서 바꿀 곳은 정해 두었다.
- `llm_review.py` 의 `check_local()`: localhost 만 허용하는 부분을 "승인된 주소 목록(설정 파일)"으로 바꾼다.
- `ask()`: OpenAI 호환 형식이 아닌 서비스라면 요청 모양을 맞추는 부분만 추가한다.
- 모델 이름·프롬프트 버전은 `<case>_llm.json` 에 이미 남으므로 결과 추적은 그대로 된다.

## 5. 입력을 더 알차게 하는 방법

수치만 받는 LLM 은 위치를 해부학 이름으로 알 수 없어 판단 근거가 약하다. 아래 두 가지를 순서대로 고려한다.

### 5-1. 골 이름과 기준 장기 대비 비율 (기존 코드 재사용)

09-28 시험실행(`공유 폴더/파이프라인 시험실행 2026-09-28/scripts`)이 이미 계산하는 값이다.
09-28 에서 골 이름·간/MBP 대비·규칙 DS 는 모두 TotalSegmentator 분할(`total`)에서 나왔다. 기준 영역 규칙은 autoDS-PET 규칙을 재구현한 것이다.
09-28 은 분할을 뼈 안 후보 탐색·장기 제외에도 썼지만, 그 역할은 우리 파이프라인에서 학습 모델이 대신한다.
자세한 용도·조건·한계는 실험 기록 `experiments/2026-10-08_autopet3-pilot/README.md`(워크스테이션 로컬) "09-28 에서 TotalSegmentator 의 역할" 절.

1. CT 장기·골격 분할: TotalSegmentator 공식 CLI(`--task total --ml`)를 원본 해상도 CT 에 돌린다([TotalSegmentator 가이드](../guides/totalsegmentator.md)).
   추론 환경과 따로 venv 를 둔다(v2.18.0). 2026-10-22 P01·P02 시험 분할에서 GPU 메모리가 최고 약 19 GB 로 충분해,
   09-28 `seg_chunked.py` 처럼 영상을 나눠 돌릴 필요가 없었다. 필요한 라벨(간·대동맥·심장·T4–T8·L3–L5·늑골)이 두 케이스 모두 나왔다.
2. 기준 SUV: `fl_candidates.py` 의 기준 영역 규칙을 그대로 쓴다. 간(10 mm 침식, 중앙값)과 종격동 혈액풀(MBP, T4–T8 대동맥, 심장 제외)이다.
   공개 저장소 autoDS-PET(MIT, `fc6bc13`)이 같은 규칙을 코드로 갖고 있어 그 함수(`LiverROI`·`AortaMBP`·`assign_ds`)를 쓴다.
   SUV 는 우리 입력(`<case>_0001.nii.gz`)을 쓴다.
3. 모델 후보마다 SUVmax 위치의 구조 이름(`site`)과 `r_liver`(SUVmax ÷ 간 중앙값), `r_mbp`, 규칙 DS(`ds_rule`)를 구한다.
   분할은 SUV 격자로 nearest-neighbour 로 옮긴다(autoDS-PET `resample_to_reference`). SUVmax 자리가 구조 밖이면 후보 안에서 가장 많이 겹친 구조를 쓴다.
4. 이 값들을 `llm_opinions.FEATURES` 에 추가하고(프롬프트 v3) 페이지 카드에도 보이게 한다.

2026-10-26 적용: `scripts/anatomy.py`, `make_review_html.py --totalseg`([TotalSegmentator 가이드](../guides/totalsegmentator.md) §5–§6).
09-28 의 `bone` 은 `site` 로 이름을 바꿨다(뼈 밖 구조·`unlabeled` 도 들어가므로).

간·MBP 대비 비율이 생기면 규칙 DS(2: ≤MBP, 3: ≤간, 4: ≤2×간, 5: >2×간)도 함께 계산할 수 있다.

### 5-2. 영상 조각을 보는 멀티모달 모델 (로컬 한정)

2026-10-23 적용: 로컬 MedGemma 1.5 4B(vLLM, [가이드](../guides/medgemma.md)). `make_review_html.py --llm-input-only` 가 후보마다 2×2 그림(PET 축상·관상·시상 + CT 축상)을
`~/autopet3/llm_input/<case>/<기록#>.png` 로 만들고(맥으로 보내는 review 폴더 밖), `llm_review.py --images` 가 수치와 함께 보낸다.

- 카드의 PET 3면·CT 축상면을 붙인 2×2 PNG 1장을 OpenAI 호환 형식의 `image_url`(data URI)로 보낸다.
- 영상은 외부로 절대 보내지 않는다. 워크스테이션 안의 멀티모달 모델일 때만 쓴다(4절의 외부 API 확장 대상에서도 제외).
- 프롬프트에 그림 표시 규칙(칸 배치, SUV 0–8 반전 회색조, 빨간 윤곽 = 이 후보, 주황 = 다른 후보)과 6분류 정의, 해부 값의 뜻을 적었다(`llm_review.py` 의 `SYSTEM_IMG`).
