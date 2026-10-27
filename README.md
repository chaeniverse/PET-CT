# PET-CT

다발골수종(MM) FDG PET/CT에서 골수종 병변을 자동 탐지하고, FL-DS score 를 산출한 뒤
임상 레지스트리와 결합해 무진행생존(PFS)을 예측하는 **end-to-end AI 파이프라인** 연구 저장소.

> 이 저장소에는 **코드·설정·문서만** 둔다. 환자 영상·임상자료·마스크·모델 가중치는 커밋하지 않는다.
> 규칙은 [docs/data-governance.md](docs/data-governance.md).

## 파이프라인

| 단계 | 내용 | 상태 |
|---|---|---|
| ① 병변 탐지 | PET/CT 전신 영상에서 골수종 병변 segmentation. 여러 오픈소스 모델을 비교한다 | 🟡 파일럿 2명 추론 완료, 육안 검토 중 |
| ② FL-DS 산출 | 탐지된 병변으로 FL-DS score 자동 계산 | ⚪ 예정 |
| ③ 레지스트리 결합 | 임상 레지스트리 변수와 영상 지표 결합 | ⚪ 예정 |
| ④ PFS 예측 | 생존 모형으로 PFS 예측·검증 | ⚪ 예정 |

연구계획·선행연구·스키마: 공유 폴더 `회의 자료/[2026-09-27] PET FL-DS 자동산출 연구계획.pptx`

## 비교 대상 모델

[docs/models/index.md](docs/models/index.md) 에서 관리한다.

## 실행 환경

워크스테이션(JupyterHub, 계정 `chlee`) — RTX 5090 32GB · Ryzen 9 9950X3D · DDR5 128GB · NVMe 4TB.
자세한 주의점(특히 RTX 5090 ↔ PyTorch CUDA 12.8+)은 [docs/environment.md](docs/environment.md).

---

## 저장소 구성

| 경로 | 역할 |
|---|---|
| `AGENTS.md` · `CLAUDE.md` | 에이전트 작업 규칙 (데이터 유출 금지·공유 폴더 읽기 전용) |
| `docs/` | 기준 문서 — SoT, 결정 기록, 데이터 거버넌스, 환경, 가이드 |
| `docs/data/` | 원자료 인벤토리 (가명·시리즈 구성만, 식별정보 없음) |
| `docs/models/` | 비교할 모델 목록과 상태 |
| `experiments/` | 실험별 기록 (설정·수치·관찰). 워크스테이션 로컬에만 두고 깃허브에 올리지 않는다(`.gitignore`) |
| `third_party/` | 외부 레포 clone 위치 (내용은 커밋하지 않음) |
| `.github/` | PR·이슈 템플릿 |
| `.claude/skills/` | Claude Code 프로젝트 스킬. `check-typed`: 직접 친 코드를 채팅 원본과 대조·문법·린트·데이터 보호 검사 |

PET-CT 관련 문헌 정리(웹앱)는 별도 비공개 저장소 `chaeniverse/petct-paper-scrap` 에서 한다.

## 참고 레포

- nnU-Net v2 — <https://github.com/MIC-DKFZ/nnUNet>
- autoPET III LesionTracer 제출 코드 — <https://github.com/MIC-DKFZ/autopet-3-submission>
- autoPET III LesionTracer 가중치 (Zenodo) — <https://zenodo.org/records/14007247>
- autoPET DICOM→NIfTI(SUV·CTres) 변환 — <https://github.com/lab-midas/TCIA_processing>
- autoPET 공식 평가 지표(Dice·위양성/위음성 부피, cc3d 18-연결) — <https://github.com/lab-midas/autoPET>
- 장기·골격 분할(기준 SUV·골 이름) — <https://github.com/wasserth/TotalSegmentator>
- 3D 판독(맥) — 3D Slicer <https://github.com/Slicer/Slicer>
