# 에이전트 문서 안내

작업을 이어받을 때는 **[docs/status.md](docs/status.md)(현재 위치·다음 할 일·함정)를 가장 먼저** 읽고,
그다음 [docs/index.md](docs/index.md)에서 작업에 해당하는 기준 문서를 확인한다.

- 범위·파이프라인 단계·저장소 경계: [SoT](docs/sot.md)
- 데이터 취급 규칙: [데이터 거버넌스](docs/data-governance.md)
- 지금 하는 일(병변 탐지 파일럿): 가이드 [변환](docs/guides/dicom-to-nifti.md) → [추론](docs/guides/autopet3-inference.md) → [결과 확인](docs/guides/review-results.md) · [TotalSegmentator](docs/guides/totalsegmentator.md) · [방법 설명](docs/methods/autopet3-pipeline.md) · 실험 기록 `experiments/2026-10-08_autopet3-pilot/README.md`(워크스테이션 로컬 전용)
- 프로젝트 소개와 저장소 구성: [README](README.md)

가장 중요한 규칙 — 셋 다 예외 없다.

1. **데이터 유출 금지 · 익명성 보장.** 환자 영상(DICOM·NIfTI)·임상자료·마스크·가중치를 커밋하지 않고,
   세션 밖(클라우드 업로드·외부 서비스·채팅 출력)으로 내보내지 않는다. 환자 이름·등록번호·생년월일·검사일시 등
   식별정보는 문서·커밋·출력 어디에도 적지 않는다. 환자는 `P01`, `P02` … 가명으로만 부른다.
2. **공유 폴더는 읽기 전용.** Dropbox `연구_PIPET/PIPET_Hematology/MM/PET_MRD` 는 결과 공유 폴더다.
   생성·수정·이동·삭제가 필요하면 반드시 사용자에게 먼저 묻는다.
3. **모델 코드를 새로 창조하지 않는다.** 공개 레포(nnU-Net, autoPET 제출 코드 등)의 공식 명령·스크립트를 우선 쓰고,
   불가피한 연결 코드(형식 변환 등)는 사용자 승인 후에만 추가한다.
   병변 탐지·평가·미세조정은 공개 저장소 코드와 공식 명령으로 하고, 직접 만드는 코드는 시각화와 데이터 연결로 한정한다
   (출처 표: [docs/decisions.md](docs/decisions.md) "공개 코드 출처").

시각화가 아닌 코드(.py·.sh)는 에이전트가 직접 고치지 않고, 채팅으로 전문이나 고칠 곳을 주면 사용자가 친다.
코드를 줄 때는 완성된 파일 전체를 `~/.cache/petct-typed-ref/<저장소 기준 경로>` 에 사본으로 저장하고,
사용자가 다 쳤다고 하면 [check-typed 스킬](.claude/skills/check-typed/SKILL.md)로 대조·문법·린트·데이터 보호를 검사해 고칠 곳만 알린다.

요구사항·기술 결정·가이드의 본문은 `docs/`에 두고 이 파일에는 복사하지 않는다.
Markdown(`.md`)을 쓸 때 굵게(`**…**`)는 데이터 보호 규칙이나 되돌리기 어려운 작업 경고처럼 정말 중요한 곳에만 쓴다. 강조가 필요 없는 문장·표·목록에는 쓰지 않는다.
실험을 돌리면 `experiments/<날짜>_<이름>/README.md` 에 설정·결과 요약(수치·관찰만, 영상 없이)을 남긴다.
`experiments/` 는 워크스테이션 로컬에만 두고 깃허브에 올리지 않는다(`.gitignore`, 2026-10-22 결정). 커밋·PR 에 넣지 않는다.
큰 단계를 마치면 [docs/status.md](docs/status.md)의 "현재 위치"·"다음 할 일"을 같은 변경 단위에서 갱신한다.
