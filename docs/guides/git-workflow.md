# Git 작업 흐름

PR 을 열면 `.github/pull_request_template.md` 가 기본 양식으로 쓰인다.

## 브랜치

- 기준 브랜치는 `main`. 작업은 `main` 에서 분기해 PR 로 병합한다.
- 이름은 `타입/간단한-설명`.

| 접두사 | 용도 | 예시 |
|---|---|---|
| `feat/` | 새 기능·파이프라인 단계 | `feat/fl-ds-calc` |
| `fix/` | 버그 수정 | `fix/suv-time-ref` |
| `exp/` | 실험 기록 | `exp/autopet3-pilot` |
| `docs/` | 문서 | `docs/data-inventory` |
| `refactor/` | 동작 변경 없는 구조 개선 | `refactor/io-utils` |
| `chore/` | 설정·환경 | `chore/init-scaffold` |
| `test/` | 테스트 | `test/suv-factor` |

## 커밋

- 작업 브랜치에서 변경을 쌓아 두고, 많이 바뀌었을 때 한 번 커밋한다. 작은 수정마다 커밋하지 않는다.
- 에이전트(Claude 등)는 한 덩어리가 끝나면 "커밋할까요?" 라고 묻기만 한다. 커밋·푸시·PR 은 사용자가 하라고 할 때만 한다.
- 메시지는 Conventional Commits, 소문자 타입. `<타입>: <요약>` 한 줄, 명령형·현재형. 나중에 이력에서 찾기 쉬운 한국어 요약으로 쓴다.
  - 예: `docs: autoPET III 추론 가이드 추가`, `feat: Slicer 도구막대와 3D MIP`

## Issue

- 며칠 이상 걸리거나 나중에 할 큰 일에만 만든다(예: 코호트 변환·추론, FL-DS 산출). 작은 수정은 issue 없이 바로 브랜치를 딴다.
- issue 는 `.github/ISSUE_TEMPLATE/task.md` 로 쓰고, 그 일을 끝내는 PR 본문에 `Closes #번호` 를 적는다.

## PR

- PR 은 작업 묶음 하나가 끝났을 때 연다(예: issue 의 한 단계). 브랜치 하나 = PR 하나이고, 요약이 한 문장으로 안 되면 나눈다.
- 작은 수정(오타·경로·문구)은 따로 PR 을 만들지 않고 진행 중인 묶음에 넣는다.
- PR 위에 PR 을 쌓지 않는다. 앞 PR 을 머지한 뒤 main 에서 다음 브랜치를 딴다.
- 머지는 "Squash and merge" 로 한다. 브랜치의 커밋이 몇 개든 main 에는 PR 하나가 커밋 하나로 남는다.
  저장소 Settings → General → Pull Requests 에서 "Allow squash merging" 만 켜 두고, "Automatically delete head branches" 를 켜 머지한 브랜치를 지운다.
- 제목은 커밋과 같은 `타입: 요약` 형식.
- 본문은 템플릿(요약·목적·주요 변경 사항·테스트 체크리스트)을 채운다. **테스트 체크리스트의 데이터 보호 항목은 빼지 않는다.**

## AI 리뷰 (Copilot)

PR 을 열면 Copilot 이 요약과 줄 단위 의견을 단다(Copilot 유료 플랜 필요). 리뷰 규칙은 `.github/copilot-instructions.md` 에 있다(앞 4,000자만 읽음).

- 켜는 법: GitHub 오른쪽 위 프로필 사진 → Copilot settings → Code review → "Automatic Copilot code review" 를 켠다(내가 여는 PR 에 자동 리뷰). 한 번만 받을 때는 PR 의 Reviewers 에서 Copilot 을 고른다
  - 저장소 Rulesets 의 같은 규칙은 개인 계정의 private 저장소에서는 적용되지 않는다(GitHub Team 조직 필요)
- Copilot 은 PR 대상 브랜치(main)의 `copilot-instructions.md` 를 읽는다. 규칙을 바꾸면 main 에 머지된 뒤부터 적용된다
- 봇은 PR 의 코드 차이를 외부(GitHub)로 보내 분석한다. **PR 본문·댓글에 환자 정보를 쓰지 않는다.**
- 봇 의견은 참고다. 반영하지 않을 때는 이유를 답글로 남기고 resolve 한다

## 커밋 전 점검

```bash
git status
git diff --cached --name-only | grep -Ei '\.(dcm|nii(\.gz)?|mha|nrrd|npy|npz|pth|pt|csv|xlsx?|zip)$' && echo "STOP: 데이터 파일이 스테이징됨"
```

직접 친 코드는 커밋 전에 Claude Code 에서 `/check-typed` 로 검사한다([스킬](../../.claude/skills/check-typed/SKILL.md)).
채팅에서 받은 원본과 줄 단위로 대조하고, 문법(`bash -n`·`ast`), 린트(`ruff`·`shellcheck`), 데이터 파일 스테이징을 본다. 고칠 곳만 알려 주고 파일은 고치지 않는다.

## 커밋하면 안 되는 것

- 환자 영상·마스크·임상자료·가중치·압축파일 (`.gitignore` 로 막혀 있지만 `git add -f` 금지)
- 노트북 출력 셀(식별정보가 찍힐 수 있음) — 출력 지우고 커밋
- 비밀키·토큰·`.env`
