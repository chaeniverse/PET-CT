#!/usr/bin/env python
"""후보 확인 페이지에 얹는 LLM 의견의 틀(입력·출력 형식)을 정한다. LLM 을 부르는 코드는 아직 없다.

원칙
  - 화면의 주인공은 병변 표시와 전문의 판정이다. LLM 의견은 카드 오른쪽에 참고로 얹고,
    "LLM 은 이렇게 판단했는데 맞는가"를 전문의에게 묻는 데까지만 쓴다.
  - LLM 에게 줄 수 있는 것은 FEATURES 의 수치뿐이다. 영상·마스크·식별정보는 넣지 않는다.
    외부 LLM API 로 보내는 것은 데이터 거버넌스상 금지이며, 쓰려면 기관 내부(온프레미스) 모델이어야 한다.

파일 <base>/llm/<case>_llm.json (make_review_html.py --llm-input-only 가 빈 틀을 만든다)
  {
    "case": "P01", "schema": 1,
    "model": null, "prompt_version": null, "created": null,      # LLM 을 돌린 쪽이 채운다
    "candidates": {
      "3": {                                                     # 키 = record_no (실험 기록 번호)
        "input":   {"suvmax": 6.28, "suvpeak": ..., "vol_ml": ..., "ct_hu": ..., "mm": [x, y, z],
                    "site": "vertebrae_L3", "r_liver": 2.1, "r_mbp": 3.4, "ds_rule": 5},   # 해부 값은 --totalseg 일 때만, 아니면 null
        "opinion": null                                          # 또는 아래 형식
      }
    }
  }
  opinion = {"verdict": VERDICTS 중 하나, "confidence": 0~1 또는 null, "rationale": "짧은 근거"}

사용
  python scripts/llm_opinions.py check ~/autopet3/llm/P01_llm.json    # 형식 검사
"""
import json
import sys
from pathlib import Path

SCHEMA = 1
# 판정 6분류(2026-10-26). 국소 골병변 / 미만성 골수 섭취 / 골수외 병변 / 생리적 섭취 / 위양성(염증·골절 등) / 불확실
VERDICTS = {"focal_lesion", "diffuse", "extramedullary", "physiologic", "false_positive", "unsure"}
# 카드 값 이름 -> LLM 입력 이름. 여기에 없는 값(영상 조각 등)은 LLM 쪽으로 나가지 않는다.
FEATURES = {"suvmax": "suvmax", "suvpeak": "suvpeak", "suvmean": "suvmean", "vol": "vol_ml", "hu": "ct_hu", "mm": "mm",
            "site": "site", "r_liver": "r_liver", "r_mbp": "r_mbp", "ds_rule": "ds_rule"}   # 해부 값(anatomy.py, 2026-10-26)


def features(card):
    return {dst: card[src] for src, dst in FEATURES.items()}


def stub(case, cards):
    return {"case": case, "schema": SCHEMA, "model": None, "prompt_version": None, "created": None,
            "candidates": {str(c["record_no"]): {"input": features(c), "opinion": None} for c in cards}}


def check_same(doc, path, cards):
    """파일의 후보 목록이 지금 마스크의 후보와 같은지 본다. 다르면(재추론 등) 옛 의견이 다른 후보에 붙지 않게 멈춘다."""
    old = {k: c["input"] for k, c in doc["candidates"].items()}
    new = {str(c["record_no"]): features(c) for c in cards}
    if json.loads(json.dumps(old)) != json.loads(json.dumps(new)):
        sys.exit(f"{Path(path).name} 의 후보가 지금 마스크와 다르다. 옛 파일을 지우거나 옮긴 뒤 다시 만든다.")


def write_stub(path, case, cards):
    """빈 틀을 쓴다. 이미 파일이 있으면(LLM 결과가 채워졌을 수 있으므로) 건드리지 않는다."""
    path = Path(path)
    if path.exists():
        check_same(json.loads(path.read_text(encoding="utf-8")), path, cards)
        return False
    path.write_text(json.dumps(stub(case, cards), indent=1, ensure_ascii=False), encoding="utf-8")
    path.chmod(0o600)
    return True


def validate(doc):
    """틀린 곳을 문장 목록으로 돌려준다. 빈 목록이면 통과."""
    errs = []
    if doc.get("schema") != SCHEMA:
        errs.append(f"schema 가 {SCHEMA} 이 아니다: {doc.get('schema')}")
    for key, c in (doc.get("candidates") or {}).items():
        op = c.get("opinion")
        if op is None:
            continue
        if op.get("verdict") not in VERDICTS:
            errs.append(f"후보 {key}: verdict 는 {sorted(VERDICTS)} 중 하나여야 한다 ({op.get('verdict')!r})")
        conf = op.get("confidence")
        if conf is not None and not (isinstance(conf, (int, float)) and 0 <= conf <= 1):
            errs.append(f"후보 {key}: confidence 는 0~1 또는 null ({conf!r})")
        if not isinstance(op.get("rationale", ""), str):
            errs.append(f"후보 {key}: rationale 는 문자열")
    return errs


def load(path, cards=None):
    """페이지에 넣을 형태로 읽는다: ({record_no: opinion}, {"model":..., "prompt_version":...}). 파일이 없으면 빈 값.
    cards 를 주면 후보 목록이 같은지 먼저 본다."""
    path = Path(path)
    if not path.exists():
        return {}, {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    if cards is not None:
        check_same(doc, path, cards)
    errs = validate(doc)
    if errs:
        sys.exit(f"{path.name} 형식 오류:\n  " + "\n  ".join(errs))
    ops = {int(k): c["opinion"] for k, c in doc["candidates"].items() if c.get("opinion")}
    return ops, {"model": doc.get("model"), "prompt_version": doc.get("prompt_version")}


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "check":
        sys.exit("사용: python scripts/llm_opinions.py check <case>_llm.json")
    d = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    e = validate(d)
    n = sum(1 for c in d.get("candidates", {}).values() if c.get("opinion"))
    print("\n".join(e) if e else f"형식 정상 · 후보 {len(d.get('candidates', {}))}개 중 의견 {n}개")
    sys.exit(1 if e else 0)
