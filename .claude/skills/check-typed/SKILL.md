---
name: check-typed
description: 사용자가 채팅에서 받은 코드를 직접 타이핑한 뒤 검수한다. 원본 사본과 줄 단위 대조, 문법(bash -n·ast), 린트(ruff·shellcheck), 데이터 보호 점검을 하고 고칠 곳만 알려 준다(파일은 고치지 않는다). 사용자가 "/check-typed", "다 쳤어", "다 입력했어", "타이핑 끝", "작업 완료했어", "다 했어"처럼 코드 입력을 마쳤다고 말하면 쓴다.
allowed-tools: Read, Bash(git status:*), Bash(git diff:*), Bash(git ls-files:*), Bash(diff:*), Bash(ls:*), Bash(bash -n:*), Bash(python3 -I -c:*), Bash(uvx:*)
---

# 직접 친 코드 검수 (check-typed)

이 저장소에서는 시각화가 아닌 코드(.py·.sh)를 Claude 가 직접 고치지 않는다. Claude 는 채팅으로 전문이나 고칠 곳을 주고, 사용자가 손으로 친다.
이 스킬은 사용자가 친 결과를 검사해 **고칠 곳만 보고한다. 파일을 고치거나 지우지 않는다.**

## 원본 사본 규칙 (코드를 줄 때)

Claude 가 채팅으로 코드를 줄 때마다, 사용자가 쳐서 만들 **완성된 파일 전체**를 저장소 밖 같은 상대 경로에 저장해 둔다.

```
~/.cache/petct-typed-ref/<저장소 기준 경로>      예: ~/.cache/petct-typed-ref/scripts/setup/foo.sh
```

- 일부만 고치는 diff 를 줄 때도, 그 diff 를 반영한 뒤의 파일 전체를 저장한다.
- 같은 파일을 다시 주면 덮어쓴다. 사본에는 코드만 들어가고 환자 데이터는 들어가지 않는다.

## 1. 검사할 파일 정하기

- 사용자가 파일을 지정했으면 그 파일만 본다(`/check-typed scripts/foo.py`).
- 지정하지 않았으면 `git status --porcelain` 에서 새로 생기거나 바뀐 `.py`·`.sh` 파일을 고른다.
  `third_party/`, `experiments/` 는 제외한다. 사본이 있는 파일(`~/.cache/petct-typed-ref/` 아래)을 먼저 본다.
- 대상이 없으면 "검사할 파일이 없다"고 말하고 끝낸다.

## 2. 원본과 대조

사본이 있으면 줄 단위로 비교한다.

```bash
diff -u ~/.cache/petct-typed-ref/<경로> <경로>        # 모든 차이
diff -uw ~/.cache/petct-typed-ref/<경로> <경로>       # 공백 차이를 뺀 차이
```

- 두 결과를 비교해, 공백만 다른 줄(들여쓰기·줄 끝 공백·마지막 줄바꿈)과 내용이 다른 줄을 나눠 보고한다.
- 셸의 `[ … ]` 안 공백, 파이썬 들여쓰기처럼 공백이 동작을 바꾸는 곳은 공백 차이라도 "고쳐야 함"으로 올린다.
- 주석 문구만 다른 줄은 "선택"으로 둔다. 사용자가 일부러 바꿨을 수 있다.
- 사본이 없으면 대조는 건너뛰고 그렇다고 적는다.

## 3. 문법 검사

```bash
bash -n <파일.sh>
python3 -I -c "import ast,sys; ast.parse(open(sys.argv[1]).read(), sys.argv[1])" <파일.py>
```

`py_compile` 은 저장소 안에 `__pycache__` 를 만들므로 쓰지 않는다.

## 4. 린트 (공개 도구, 버전 고정)

```bash
uvx -q ruff@0.17.1 check --no-cache --output-format concise <파일.py>
uvx -q --from 'shellcheck-py==0.11.0.1' shellcheck -f gcc <파일.sh>
```

- 처음 한 번 `uvx` 가 도구를 내려받는다. 코드나 데이터를 밖으로 보내지 않는다.
- 공개 레포에서 가져온 파일(`scripts/val_script.py`, `scripts/tcia_dicom_to_nifti.py` 등 출처 표 `scripts/THIRD_PARTY_LICENSES.md`)은 원본 스타일 경고가 많다.
  사용자가 고친 줄과 관련된 경고만 보고한다.
- 문법 오류·정의되지 않은 이름(F821)·쓰지 않는 import(F401)·셸 문법 오류(SC1xxx)·따옴표 누락(SC2086 등)은 "고쳐야 함", 나머지 스타일은 "선택"이다.

## 5. 데이터 보호 점검

```bash
git status --porcelain
git diff --cached --name-only | grep -Ei '\.(dcm|nii(\.gz)?|mha|nrrd|npy|npz|pth|pt|csv|xlsx?|zip|html)$'
```

- 스테이징됐거나 새로 생긴 파일 중 위 확장자가 있으면 **멈추라고** 알린다.
- 검사 대상 코드에 환자 이름·등록번호·생년월일·검사일시, 원본 DICOM 폴더 이름, 외장하드 가명 대응표 내용이 문자열로 들어가 있지 않은지 읽어서 확인한다.
  찾으면 위치(파일·줄 번호)만 알리고, 그 값은 채팅에 옮겨 적지 않는다.
- 출력 경로가 저장소 안(`~/PET-CT/…`)을 가리키는 코드가 새로 생겼으면 알린다. 데이터·결과는 `~/autopet3/` 아래에만 둔다.

## 6. 보고 형식

한국어로, 파일별로 짧게 쓴다.

```
## scripts/foo.py — 고쳐야 함 2 · 선택 1
| 줄 | 구분 | 내용 | 고치는 법 |
|---|---|---|---|
| 12 | 고쳐야 함 | 모듈 이름 오타 `totalsegmentor` | `totalsegmentator` |
| 30 | 고쳐야 함 | `]` 앞 공백 없음 (shellcheck SC1020) | `"$DIR/.venv" ]` |
| 41 | 선택 | 주석 문구가 원본과 다름 | 그대로 둬도 됨 |
```

- 고칠 곳은 diff 조각으로도 보여 준다(`-` 지금 줄, `+` 고칠 줄).
- 모두 통과하면 검사한 항목(대조·문법·린트·데이터)을 한 줄로 알리고 끝낸다.
- 파일을 고치지 않는다. 사용자가 고친 뒤 다시 부르면 처음부터 다시 검사한다.
