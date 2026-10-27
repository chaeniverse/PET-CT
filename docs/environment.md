# 실행 환경

## 워크스테이션

| 항목 | 사양 |
|---|---|
| GPU | NVIDIA RTX 5090 32GB (Blackwell, compute capability `sm_120`) |
| CPU | AMD Ryzen 9 9950X3D (16C/32T) |
| RAM | DDR5 128GB |
| 저장장치 | NVMe 4TB (Samsung 9100 PRO) · HDD 8TB (WD Red Plus) |
| OS | Ubuntu 26.04, 커널 7.0 (HWE) |

## 주의점

- 가상환경은 uv 로 만든다. 외부 레포마다 그 폴더 안에 `.venv` 를 둔다(`uv venv --python 3.11`).
  uv venv 에는 `pip` 이 없으므로 `uv pip install` 을 쓰고, `uv.lock` 이 없는 외부 레포에서는 `uv sync`·`uv add` 를 쓰지 않는다.
  대신 설치된 버전을 `env/*.lock.txt`(`uv pip freeze` 결과)로 저장소에 남기고, 가이드의 lock 설치 명령(`uv pip install -r env/<이름>.lock.txt …`, [추론](guides/autopet3-inference.md) §3 · [변환](guides/dicom-to-nifti.md) §2 · [TotalSegmentator](guides/totalsegmentator.md) §2)으로 그 버전 그대로 다시 설치한다.
  패키지를 바꾸면 lock 을 다시 쓰고 같은 변경 단위로 커밋한다.

- RTX 5090 은 CUDA 12.8 이상으로 빌드된 PyTorch(cu128+)에서만 동작한다. pytorch.org 설치 선택기에서
  CUDA 12.8 이상을 고른다. 설치 후 `torch.cuda.get_arch_list()` 에 `sm_120` 이 있어야 한다.
- nnU-Net 은 PyTorch 를 먼저 설치한 뒤 설치한다(공식 문서 경고).
- 외부 레포가 오래된 torch 버전을 고정(pin)해 두었으면 pip 가 torch 를 다운그레이드할 수 있다.
  설치 로그에서 torch 가 바뀌는지 확인한다.
- TotalSegmentator 는 autoPET 과 다른 venv 에 둔다(공식 `nnunetv2` 2.8.1 과 autoPET 수정본 2.5.1 이 같은 이름이라 부딪힌다).
  가중치·설정은 `TOTALSEG_HOME_DIR=~/autopet3/weights/totalseg`(`~/.bashrc`), 사용 통계는 끈다([TotalSegmentator 가이드](guides/totalsegmentator.md) §3).
- vLLM(MedGemma 서빙)도 별도 venv(`third_party/vllm/.venv`, Python 3.12)에 둔다. vLLM 이 torch 버전을 정확히 고정하기 때문이다.
  사용 통계는 끄고(`~/.config/vllm/do_not_track`, `VLLM_NO_USAGE_STATS=1`), 서버는 127.0.0.1:8100 으로만 연다([MedGemma 가이드](guides/medgemma.md)).
- 전처리·추론 입출력은 NVMe 쪽 경로에 둔다. HDD 는 보관용.
- 공용 GPU 이므로 시작 전 `nvidia-smi` 로 다른 사용자의 점유를 확인한다.
