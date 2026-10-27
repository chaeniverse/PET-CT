#!/usr/bin/env python
"""autoPET 마스크를 병변(연결성분)별로 요약한다: 병변 수·총 부피, 병변별 부피·SUVmax·SUVmean·z.

계산은 공개 코드에 맡긴다.
  - 병변 나누기: autoPET 공식 평가 val_script.con_comp (cc3d 18-연결)
  - 병변별 부피·최댓값·평균: SimpleITK LabelIntensityStatisticsImageFilter
이 파일은 둘을 잇고 표로 출력만 한다. 번호는 부피 큰 순(같으면 SUVmax 큰 순)이고, 후보확인 페이지의 '기록 #' 과 같다.

사용 (autoPET venv):
  python scripts/summarize_lesions.py P01 P02 --input ~/autopet3/input_series --output ~/autopet3/output_series
  python scripts/summarize_lesions.py C001 C002      # 코호트는 기본 폴더 ~/autopet3/input, ~/autopet3/output
"""
import argparse
from pathlib import Path

import numpy as np
import SimpleITK as sitk

from val_script import con_comp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="+", help="케이스 가명 (예: P01 C001)")
    ap.add_argument("--input", type=Path, default=Path.home() / "autopet3" / "input", help="SUV(<case>_0001) 폴더")
    ap.add_argument("--output", type=Path, default=Path.home() / "autopet3" / "output", help="autoPET 마스크 폴더")
    ap.add_argument("--top", type=int, default=20, help="부피 큰 순으로 몇 개까지 보일지 (기본 20)")
    args = ap.parse_args()

    for c in args.cases:
        seg_img = sitk.ReadImage(str(args.output / f"{c}.nii.gz"))
        suv_img = sitk.ReadImage(str(args.input / f"{c}_0001.nii.gz"), sitk.sitkFloat32)
        seg = (sitk.GetArrayFromImage(seg_img) > 0).astype(np.uint8)

        lab_img = sitk.GetImageFromArray(con_comp(seg).astype(np.uint32))   # 병변 번호를 매긴 영상
        lab_img.CopyInformation(seg_img)                                     # 좌표·간격을 마스크와 같게
        stats = sitk.LabelIntensityStatisticsImageFilter()
        stats.Execute(lab_img, suv_img)

        rows = []
        for lbl in stats.GetLabels():
            bbox = stats.GetBoundingBox(lbl)                                 # (x, y, z, 크기x, 크기y, 크기z)
            rows.append((stats.GetPhysicalSize(lbl) / 1000, stats.GetMaximum(lbl), stats.GetMean(lbl), bbox[2] + bbox[5] // 2))
        rows.sort(key=lambda t: (-round(t[0], 6), -t[1]))
        total = sum(r[0] for r in rows)
        print(f"\n{c}: lesions={len(rows)} total={total:.2f} mL")
        for k, (vol, mx, mn, z) in enumerate(rows[:args.top], 1):
            print(f"  #{k:02d} vol {vol:7.2f} mL  SUVmax {mx:6.2f}  SUVmean {mn:5.2f}  slice z~{z}")


if __name__ == "__main__":
    main()