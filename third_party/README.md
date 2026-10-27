# third_party

외부 레포를 clone 해 두는 자리. 이 폴더의 내용은 커밋하지 않는다(`.gitignore`).

| 폴더 | 원본 | 용도 |
|---|---|---|
| `autopet-3-submission/` | https://github.com/MIC-DKFZ/autopet-3-submission | autoPET III LesionTracer 추론 |
| `TCIA_processing/` | https://github.com/lab-midas/TCIA_processing | DICOM → NIfTI(SUV·CTres) |
| `nnUNet/` | https://github.com/MIC-DKFZ/nnUNet | 자체 학습 단계에서 사용 예정 |
| `autoPET/` | https://github.com/lab-midas/autoPET (commit `468179b`) | 공식 평가 `val_script.py` 원본. `scripts/val_script.py` 는 이 파일을 고치지 않고 그대로 복사한 것(2026-10-26) |
| `TotalSegmentator/` | https://github.com/wasserth/TotalSegmentator (v2.18.0, commit `184fa47`) | CT 장기·골격 분할(골 이름·기준 SUV). 가중치는 `~/autopet3/weights/totalseg` |
| `autoDS-PET/` | https://github.com/Sara-Peluso/autoDS-PET (MIT, commit `fc6bc13`) | 간·혈액풀 기준 SUV 와 규칙 DS 함수. 설치 없이 `scripts/anatomy.py` 가 불러 쓴다 |
| `vllm/` | https://github.com/vllm-project/vllm (PyPI `vllm==0.32.0`, clone 없음) | MedGemma 로컬 서빙 venv 자리. 가중치는 `~/autopet3/weights/medgemma-1.5-4b-it` |
