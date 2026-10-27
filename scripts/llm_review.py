#!/usr/bin/env python
"""<case>_llm.json 의 후보마다 LLM 의견을 받아 채운다. 그다음 make_review_html.py --llm-opinion <폴더> 로 페이지를 만들면 카드 오른쪽에 보인다.

데이터 보호
  - LLM에 보내는 것은 llm_opinions.FEATURES 의 수치(SUV·부피·HU·좌표)이고, --images 를 주면 후보 그림 1장 (make_review_html.py --llm-input-only 가 <base>/llm_input/<case>/<기록#>.png 로 만든 PET·CT 단면)을 더한다. 식별정보는 보내지 않는다.
  - 수치표·그림은 환자 파생물이라 외부 API 로 보낼 수 없다(데이터 거버넌스 §1).
    그래서 이 컴퓨터 안에서 도는 서버(localhost)만 허용한다. 예: Ollama, vLLM 의 OpenAI 호환 주소.
  
사용 (워크스테이션)
  python scripts/llm_review.py P01 P02 --model <로컬 모델 이름> [--base-url http://127.0.0.1:11434/v1] [--overwrite]
  python scripts/llm_review.py P01 P02 --model medgemma-1.5-4b-it --base-url http://127.0.0.1:8100/v1 --images    # VLM, 그림 포함
"""
import argparse
import base64
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm_opinions  # noqa: E402

PROMPT_VERSION = "fl-candidate-v3"          # 수치만. v2 = 판정 6분류, v3 = 해부 값(site·r_liver·r_mbp·ds_rule)
PROMPT_VERSION_IMG = "fl-candidate-img-v3"  # 그림 + 수치 (--images). v2 = 판정 6분류, v3 = 해부 값
ANATOMY = """해부 값(CT 분할 TotalSegmentator 에서 나옴, 분할이 없으면 null):
- site: 후보 SUVmax 위치의 구조 이름(영문, 예: vertebrae_L3, rib_left_5, hip_right, sacrum, femur_left, liver, kidney_right).
  "unlabeled" 는 분할된 구조 밖(연부조직·지방 등)이다.
- r_liver = SUVmax ÷ 간 기준 SUV, r_mbp = SUVmax ÷ 종격동 혈액풀 기준 SUV.
- ds_rule = 위 두 기준으로 정한 규칙 점수(2: ≤혈액풀, 3: ≤간, 4: ≤간×2, 5: >간×2).
- site 가 뼈(척추·늑골·골반·천골·대퇴골·상완골·견갑골·쇄골·흉골·두개골)면 골병변·미만성 쪽을,
  신장·요로·방광·심장·뇌·장·간 같은 생리적 섭취 장기면 생리적 섭취 쪽을, 뼈 밖 연부조직이면 골수외 병변 쪽을 함께 고려한다. 이름만으로 단정하지 않는다."""
CATEGORIES = """판정 분류(verdict) - 하나만 고른다:
- "focal_lesion": 뼈 안의 국소 골수종 병변
- "diffuse": 한 점이 아니라 골수 전반(척추·골반 등)에 퍼진 미만성 섭취
- "extramedullary": 뼈 밖 연부조직·장기의 골수종 병변
- "physiologic": 생리적 섭취(뇌·심장·신장·요로·방광·장·갈색지방·근육 등)
- "false_positive": 병변이 아닌 다른 원인(염증·감염·골절·퇴행성 변화·인공물·잡음 등)
- "unsure": 위 분류로 판단하기 어려움"""
VERDICT_LIST = '"focal_lesion" | "diffuse" | "extramedullary" | "physiologic" | "false_positive" | "unsure"'
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}

SYSTEM = """당신은 다발골수종 환자의 FDG PET/CT 를 판독하는 핵의학 전문의다.
자동 분할 모델이 표시한 후보 1개의 수치만 받는다. 영상은 볼 수 없다.
할 일: 이 후보를 아래 분류 중 하나로 판단한다.
""" + CATEGORIES + """
""" + ANATOMY + """
규칙:
- 주어진 수치만 근거로 한다. 수치로 판단하기 어렵거나 위치가 애매하면 "unsure" 를 고른다. 추측으로 확신하지 않는다.
- CT HU 가 높으면 골 안일 가능성, 매우 낮으면(-100 이하) 지방·공기 쪽일 가능성을 고려한다.
- 부피가 0.1 mL 이하로 매우 작으면 잡음 가능성을 고려한다.
- 좌표는 RAS mm(x 양수 = 환자 오른쪽, y 양수 = 앞, z 양수 = 머리 쪽)이며 기준점은 장비마다 다르므로 해부학 위치로 단정하지 않는다.
출력: 아래 JSON 한 개만. 다른 글은 쓰지 않는다.
{"verdict": """ + VERDICT_LIST + """, "confidence": 0~1 사이 숫자, "rationale": "한국어 한두 문장"}"""
SYSTEM_IMG = """당신은 다발골수종 환자의 FDG PET/CT 를 판독하는 핵의학 전문의다.
자동 분할 모델이 표시한 후보 1개의 수치와 그림 1장을 받는다.
그림(2X2): 왼쪽 위 = PET 축상면, 오른쪽 위 = PET 관상면, 왼쪽 아래 = PET 시상면, 오른쪽 아래 = CT 축상면.
- 각 칸은 후보의 SUVmax 위치를 가운데 둔 가로·세로 120 mm 범위다. 가장자리 남색 눈금이 가운데를 가리킨다.
- PET 은 SUV 0-8 반전 회색조(검을수록 섭취가 높다), CT 는 -200~1200 HU 회색조다.
- 빨간 윤곽 = 이 후보, 주황 윤곽 = 다른 후보. 축상면은 환자 오른쪽이 화면 왼쪽이다.
할 일: 후보의 위치(어느 뼈 또는 장기)와 섭취 양상을 짧게 서술하고, 아래 분류 중 하나로 판단한다.
""" + CATEGORIES + """
""" + ANATOMY + """
규칙:
- 그림과 주어진 수치에 보이는 것만 근거로 한다. 애매하면 "unsure" 를 고른다. 추측으로 확신하지 않는다.
- SUV·부피·HU 는 주어진 값만 쓴다. 새 수치를 만들어 쓰지 않는다.
출력: 아래 JSON 한 개만. 다른 글은 쓰지 않는다.
{"verdict": """ + VERDICT_LIST + """, "confidence": 0~1 사이 숫자, "rationale": "한국어 두세 문장: 위치·섭취 양상 소견과 판단 근거"}"""


def check_local(base_url):
    host = urllib.parse.urlparse(base_url).hostname
    if host not in LOCAL_HOSTS:
        sys.exit(f"외부 주소({host})로는 보내지 않는다. 이 컴퓨터에서 도는 LLM 서버(localhost)만 쓴다.")


def ask(base_url, model, features, timeout, image=None):
    text = "후보 수치:\n" + json.dumps(features, ensure_ascii=False)
    if image is None:
        system, user = SYSTEM, text
    else:        # OPENAI 호환 형식: 글 + 그림(data URI). 그림은 이 컴퓨터의 서버로만 간다(check_local)
        uri = "data:image/png;base64," + base64.b64encode(image.read_bytes()).decode()
        system, user = SYSTEM_IMG, [{"type": "text", "text": text}, {"type": "image_url", "image_url": {"url": uri}}]
    body = {"model": model, "temperature": 0, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}]}
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        text = json.load(r)["choices"][0]["message"]["content"]
    op = json.loads(text[text.find("{"):text.rfind("}") + 1])      # 앞뒤에 글이 붙어 와도 JSON 부분만
    verdict, why = str(op.get("verdict", "")).lower(), str(op.get("rationale", ""))[:400]
    if verdict not in llm_opinions.VERDICTS:                        # 약속과 다른 답은 불확실로 낮춘다
        verdict, why = "unsure", f"(형식 밖 응답: {verdict}) {why}"
    conf = op.get("confidence")
    return {"verdict": verdict, "confidence": round(min(max(float(conf), 0), 1), 2) if isinstance(conf, (int, float)) else None,
            "rationale": why}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cases", nargs="+")
    ap.add_argument("--dir", type=Path, default=Path.home() / "autopet3" / "llm", help="<case>_llm.json 이 있는 폴더 (기본 ~/autopet3/llm)")
    ap.add_argument("--base-url", default="http://127.0.0.1:11434/v1", help="OpenAI 호환 로컬 서버 주소 (기본 Ollama)")
    ap.add_argument("--model", required=True, help="로컬 서버에 올린 모델 이름")
    ap.add_argument("--overwrite", action="store_true", help="이미 의견이 있는 후보도 다시 묻는다")
    ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--images", nargs="?", type=Path, const=Path.home() / "autopet3" / "llm_input", default=None, help="후보 그림도 보낸다(VLM). 값을 주지 않으면 ~/autopet3/llm_input/<case>/<기록#>.png")
    args = ap.parse_args()
    check_local(args.base_url)

    for case in args.cases:
        path = args.dir.expanduser() / f"{case}_llm.json"
        if not path.exists():
            sys.exit(f"{path} 가 없다. 먼저 make_review_html.py --llm-input-only 를 돌리면 빈 틀이 생긴다.")
        doc = json.loads(path.read_text(encoding="utf-8"))
        n = 0
        for key, c in doc["candidates"].items():
            if c.get("opinion") and not args.overwrite:
                continue
            image = None
            if args.images:
                image = args.images.expanduser() / case / f"{int(key):02d}.png"
                if not image.exists():
                    print(f"[{case}] 기록 #{int(key):02d} 그림 없음({image.name}) - make_review_html.py --llm-input-only 를 다시 돌린다")
                    continue
            try:
                c["opinion"] = ask(args.base_url, args.model, c["input"], args.timeout, image)
                n += 1
                print(f"[{case}] 기록 #{int(key):02d} -> {c['opinion']['verdict']} ({c['opinion']['confidence']})")
            except Exception as e:                                      # 한 후보가 실패해도 나머지는 계속
                print(f"[{case}] 기록 #{int(key):02d} 실패: {e}")
        doc.update(model=args.model, prompt_version=PROMPT_VERSION_IMG if args.images else PROMPT_VERSION, created=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        errs = llm_opinions.validate(doc)
        if errs:
            sys.exit(f"[{case}] 결과 형식 오류 — 저장하지 않음:\n  " + "\n  ".join(errs))
        path.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"[{case}] 의견 {n}개 채움 -> {path}")
    print(f"\n이제 make_review_html.py ... --llm-opinion {args.dir} 로 페이지를 만들면 LLM 의견이 나타난다.")


if __name__ == "__main__":
    main()
