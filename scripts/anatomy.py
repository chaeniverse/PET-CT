#!/usr/bin/env python
"""TotalSegmentator 분할로 후보마다 해부 위치와 기준 SUV 대비 비율을 붙인다(make_review_html.py --totalseg 가 부른다).

계산은 공개 코드에 맡긴다.
  - 분할: TotalSegmentator --task total --ml 결과(CT 격자, 117 라벨)를 읽기만 한다. 분할은 가이드 명령으로 따로 돌린다
  - CT 격자 -> PET 격자: autoDS-PET imaging.geometry.resample_to_reference (nearest-neighbour)
  - 간·종격동 혈액풀(MBP) 기준값: autoDS-PET roi.LiverROI·AortaMBP 의 extract 기본값
    (간 10 mm 침식 중앙값, T4–T8 높이 대동맥·심장 제외 중앙값)
  - 규칙 DS: autoDS-PET deauville.assign_ds (2: ≤MBP, 3: ≤간, 4: ≤2×간, 5: >2×간)
이 파일은 그 셋을 잇고, 후보 SUVmax 위치의 라벨 번호를 이름으로 바꾼다.

입력: <totalseg>/<case>/seg.nii.gz, 라벨 이름 표 <totalseg>/classes_total.json (TotalSegmentator class_map["total"])
"""
import json
import sys
from pathlib import Path

import numpy as np
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "third_party" / "autoDS-PET"))   # Sara-Peluso/autoDS-PET (fc6bc13), 설치하지 않고 함수만 쓴다
from autods_pet.deauville import assign_ds  # noqa: E402
from autods_pet.imaging.geometry import resample_to_reference  # noqa: E402
from autods_pet.roi import AortaMBP, LiverROI  # noqa: E402

UNLABELED = "unlabeled"   # 분할된 구조 밖(연부조직·지방 등)


def names(totalseg_dir):
    """라벨 번호 -> 이름 목록(0 = unlabeled). 페이지·3D 보기·Slicer 이름표가 모두 이 목록을 쓴다."""
    m = {int(k): v for k, v in json.loads((Path(totalseg_dir) / "classes_total.json").read_text(encoding="utf-8")).items()}
    return [UNLABELED] + [m.get(i, f"label_{i}") for i in range(1, max(m) + 1)]


def load(case, totalseg_dir, f_suv):
    """분할을 SUV 격자로 옮기고 기준값을 구한다. 분할 파일이 없으면 None.
    labels 는 SUV 파일과 같은 축 순서(nibabel 이 읽는 순서)의 uint8 배열이다."""
    f_seg = Path(totalseg_dir) / case / "seg.nii.gz"
    if not f_seg.exists():
        return None
    pet = sitk.ReadImage(str(f_suv), sitk.sitkFloat32)
    seg = resample_to_reference(sitk.ReadImage(str(f_seg), sitk.sitkUInt8), pet)
    liver = LiverROI().extract(seg, pet).stats.get("median")
    mbp = AortaMBP().extract(seg, pet).stats.get("median")
    lab = sitk.GetArrayFromImage(seg).transpose(2, 1, 0)   # SimpleITK (z, y, x) -> nibabel (x, y, z)
    return {"labels": np.ascontiguousarray(lab), "names": names(totalseg_dir), "liver": liver, "mbp": mbp}


def card_fields(anat, lab, p, sl, m, suvmax):
    """후보 1개의 해부 정보. lab = 페이지와 같은 축(RAS)으로 돌린 labels, p = SUVmax 위치, sl·m = 후보의 상자와 그 안의 마스크.
    SUVmax 자리가 구조 밖이면 후보 안에서 가장 많이 겹친 구조를 쓴다."""
    k = int(lab[p])
    if k == 0:
        ids = np.bincount(lab[sl][m].ravel(), minlength=len(anat["names"]))
        ids[0] = 0
        k = int(ids.argmax())
    liver, mbp = anat["liver"], anat["mbp"]
    ok = all(v is not None and v > 0 for v in (liver, mbp))   # 간·대동맥이 촬영 범위 밖이면 비율을 내지 않는다
    return {"site": anat["names"][k] if k < len(anat["names"]) else f"label_{k}",
            "r_liver": round(suvmax / liver, 2) if ok else None,
            "r_mbp": round(suvmax / mbp, 2) if ok else None,
            "ds_rule": assign_ds(suvmax, mbp, liver) if ok else None}
