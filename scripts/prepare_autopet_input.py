#!/usr/bin/env python
"""DICOM(환자 1명, 시리즈 섞인 폴더) -> autoPET III / nnU-Net 입력 (CTres=_0000, SUV=_0001).

변환 자체는 autoPET 주최측 코드(lab-midas/TCIA_processing, tcia_dicom_to_nifti.py)의
dcm2nii_CT / dcm2nii_PET / resample_ct 함수를 수정 없이 그대로 호출한다.
이 스크립트가 하는 일은 그 앞뒤 연결뿐이다.

  1) 시리즈가 섞인 폴더에서 지정한 CT·PET 시리즈만 골라 시리즈별 폴더로 '복사'한다(원본 불변).
  2) Modality 태그가 SOP Class 와 다르면(예: NM) 복사본에서만 CT/PT 로 고친다.
  3) TCIA 함수로 CT.nii.gz / PET.nii.gz / SUV.nii.gz / CTres.nii.gz 를 만든다(SEG 없음).
  4) nnU-Net 이름 규칙으로 복사한다: <case>_0000.nii.gz(CTres), <case>_0001.nii.gz(SUV).
  5) 식별정보 없는 변환 기록(conversion_log.json)을 남긴다.

데이터 보호: 환자 이름·ID·날짜를 출력하거나 기록하지 않는다. 케이스는 --case-id(P01 등)로만 부른다.
"""
import argparse
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import nibabel as nib
import numpy as np
import pydicom

CT_SOP = {"1.2.840.10008.5.1.4.1.1.2", "1.2.840.10008.5.1.4.1.1.2.1"}
PT_SOP = {"1.2.840.10008.5.1.4.1.1.128", "1.2.840.10008.5.1.4.1.1.130"}


def hhmmss_to_sec(t):
    t = str(t)
    return float(t[:2]) * 3600 + float(t[2:4]) * 60 + float(t[4:])


def scan_series(dicom_dir):
    series = defaultdict(list)
    for f in sorted(p for p in Path(dicom_dir).rglob("*") if p.is_file()):
        try:
            ds = pydicom.dcmread(str(f), stop_before_pixels=True)
        except Exception:
            continue
        uid = ds.get("SeriesInstanceUID")
        if uid:
            series[uid].append((f, ds))
    return series


def pick(series, desc, sop_set, label):
    hits = [v for v in series.values()
            if str(v[0][1].get("SeriesDescription", "")).strip() == desc.strip()
            and str(v[0][1].get("SOPClassUID", "")) in sop_set]
    if len(hits) != 1:
        found = sorted({(str(v[0][1].get("SeriesDescription", "")), str(v[0][1].get("SOPClassUID", "")), len(v))
                        for v in series.values()})
        sys.exit(f"[{label}] SeriesDescription='{desc}' 인 시리즈가 {len(hits)}개입니다. 후보(설명, SOPClass, 장수): {found}")
    return hits[0]


def copy_series(items, dst, modality):
    dst.mkdir(parents=True, exist_ok=True)
    fixed = 0
    for i, (f, hdr) in enumerate(items):
        out = dst / f"{i:05d}.dcm"
        if hdr.get("Modality") != modality:
            ds = pydicom.dcmread(str(f))
            ds.Modality = modality
            ds.save_as(str(out))
            fixed += 1
        else:
            shutil.copy2(f, out)
    return fixed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dicom-dir", required=True, help="환자 1명의 DICOM 폴더(시리즈 섞여 있어도 됨)")
    ap.add_argument("--case-id", required=True, help="가명 케이스 ID, 예: P01")
    ap.add_argument("--ct-desc", required=True, help="사용할 CT 시리즈의 SeriesDescription (정확히 일치)")
    ap.add_argument("--pt-desc", required=True, help="사용할 PET 시리즈의 SeriesDescription (정확히 일치)")
    ap.add_argument("--tcia-repo", default=str(Path(__file__).resolve().parent), help="tcia_dicom_to_nifti.py가 있는 폴더 (기본: scripts/ 의 원본 그대로 복사본)")
    ap.add_argument("--work-dir", required=True, help="중간 산출물 폴더 (정렬 복사본, CT/PET/SUV/CTres)")
    ap.add_argument("--out-dir", required=True, help="nnU-Net 입력 폴더")
    ap.add_argument("--suv-time", choices=["acquisition", "series"], default="acquisition",
                    help="SUV 붕괴보정 기준 시각. acquisition=TCIA 원본 그대로(기본, autoPET 학습데이터와 동일), "
                         "series=SeriesTime 기준으로 SUV 재조정")
    a = ap.parse_args()

    sys.path.insert(0, str(Path(a.tcia_repo).resolve()))
    import tcia_dicom_to_nifti as tcia  # noqa: E402  (lab-midas/TCIA_processing fb7b074 원본 그대로 복사, 수정 없이 사용)

    case_dir = Path(a.work_dir) / a.case_id
    if case_dir.exists():
        sys.exit(f"{case_dir} 가 이미 있습니다. 지우거나 다른 --work-dir 을 쓰세요.")
    sorted_dir, nii_dir = case_dir / "sorted", case_dir / "nifti"
    nii_dir.mkdir(parents=True)

    series = scan_series(a.dicom_dir)
    ct_items = pick(series, a.ct_desc, CT_SOP, "CT")
    pt_items = pick(series, a.pt_desc, PT_SOP, "PT")
    fixed_ct = copy_series(ct_items, sorted_dir / "CT", "CT")
    fixed_pt = copy_series(pt_items, sorted_dir / "PT", "PT")
    print(f"[{a.case_id}] CT {len(ct_items)}장, PT {len(pt_items)}장 복사 (Modality 수정: CT {fixed_ct}, PT {fixed_pt})")

    # --- upstream 변환 (수정 없이 호출) ---
    tcia.dcm2nii_CT(str(sorted_dir / "CT"), nii_dir)
    tcia.dcm2nii_PET(sorted_dir / "PT", nii_dir)
    tcia.resample_ct(nii_dir)

    # --- SUV 기준 시각 기록 (upstream 은 첫 PET 파일의 AcquisitionTime 사용) ---
    first_pt = next((sorted_dir / "PT").glob("*.dcm"))
    ds = pydicom.dcmread(str(first_pt), stop_before_pixels=True)
    r = ds.RadiopharmaceuticalInformationSequence[0]
    inj = hhmmss_to_sec(r.RadiopharmaceuticalStartTime)
    hl = float(r.RadionuclideHalfLife)
    dt_acq = hhmmss_to_sec(ds.AcquisitionTime) - inj
    dt_ser = hhmmss_to_sec(ds.SeriesTime) - inj
    # SUV ∝ 1/decayed_dose ∝ 2^(dt/hl) → series 기준 SUV = acquisition 기준 SUV × 2^((dt_ser-dt_acq)/hl)
    ratio_series_over_acq = float(0.5 ** ((dt_acq - dt_ser) / hl))

    suv_path = nii_dir / "SUV.nii.gz"
    if a.suv_time == "series":
        img = nib.load(str(suv_path))
        data = (img.get_fdata() * ratio_series_over_acq).astype(np.float32)
        nib.save(nib.Nifti1Image(data, img.affine, img.header), str(suv_path))

    # --- nnU-Net 입력으로 복사 ---
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(nii_dir / "CTres.nii.gz", out / f"{a.case_id}_0000.nii.gz")
    shutil.copy(suv_path, out / f"{a.case_id}_0001.nii.gz")

    # --- 점검 · 기록 (식별정보 없음) ---
    ctres, suv = nib.load(str(out / f"{a.case_id}_0000.nii.gz")), nib.load(str(out / f"{a.case_id}_0001.nii.gz"))
    c, s = ctres.get_fdata(), suv.get_fdata()
    same_grid = ctres.shape == suv.shape and np.allclose(ctres.affine, suv.affine, atol=1e-3)
    log = {
        "case_id": a.case_id,
        "ct_series": {"desc": a.ct_desc, "n": len(ct_items), "manufacturer": str(ct_items[0][1].get("Manufacturer", ""))},
        "pt_series": {"desc": a.pt_desc, "n": len(pt_items), "units": str(pt_items[0][1].get("Units", "")),
                      "decay_correction": str(pt_items[0][1].get("DecayCorrection", ""))},
        "modality_tag_fixed": {"CT": fixed_ct, "PT": fixed_pt},
        "suv_time_reference": a.suv_time,
        "suv_minutes_after_injection": {"acquisition": round(dt_acq / 60, 2), "series": round(dt_ser / 60, 2)},
        "suv_ratio_series_over_acquisition": round(ratio_series_over_acq, 4),
        "grid": {"shape": list(suv.shape), "spacing_mm": [round(float(z), 3) for z in suv.header.get_zooms()[:3]],
                 "ctres_suv_same_grid": bool(same_grid)},
        "ct_hu": {"min": round(float(c.min()), 1), "p50": round(float(np.percentile(c, 50)), 1), "max": round(float(c.max()), 1)},
        "suv": {"p50": round(float(np.percentile(s, 50)), 3), "p99": round(float(np.percentile(s, 99)), 3),
                "p99_9": round(float(np.percentile(s, 99.9)), 3), "max": round(float(s.max()), 3)},
    }
    (case_dir / "conversion_log.json").write_text(json.dumps(log, indent=2, ensure_ascii=False))
    print(json.dumps(log, indent=2, ensure_ascii=False))
    if not same_grid:
        sys.exit("경고: CTres 와 SUV 의 격자가 다릅니다. 추론 전에 확인이 필요합니다.")


if __name__ == "__main__":
    main()
