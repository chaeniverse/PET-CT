#!/usr/bin/env python
"""판정 CSV(FL_labels_<case>.csv) + autoPET 마스크 -> 정답 마스크 초안 (issue #4 ⑦).

판정 페이지에서 받은 후보별·추가 위치별 참/거짓/불확실을 복셀 마스크로 바꾼다.
후보 = 모델 마스크의 연결성분(autoPET 공식 평가와 같은 val_script.con_comp, cc3d 18-연결)이고,
CSV 의 후보 좌표(SUVmax 위치, RAS mm)가 든 성분을 그 후보로 본다.

  후보 참 -> 그 성분을 남긴다(1)        후보 거짓 -> 지운다(0)        후보 불확실·미판정 -> 무시(2)
  추가 참 -> 점 근처 SUV 꼭짓점에서 배경 보정 50% 이상으로 이어진 영역(EANM 2015 A50 방식, SUVmax 기준)을 초안으로 만든다.
            골수종 병변은 대비가 낮아 초안이 골수로 새기 쉬우므로, Slicer 에서 윤곽을 확인하기 전까지 정답 마스크에는 무시(2)로 둔다
  추가 불확실 -> 점 주변 구(기본 반지름 10 mm)를 무시(2)      추가 거짓 -> 그대로(배경)
  CSV 에 없는 성분 -> 무시(2)

값 2 는 nnU-Net 의 ignore 라벨(가장 큰 값, dataset.json 에 "ignore": 2)로 쓰려는 것이다.

입력 (<base> = ~/autopet3):
  <labels>/FL_labels_<case>.csv     (기본 <labels> = <base>/labels)
  <input>/<case>_0001.nii.gz        SUV (파일럿은 --input ~/autopet3/input_series)
  <output>/<case>.nii.gz            autoPET 마스크 (파일럿은 --output ~/autopet3/output_series)
출력 (기본 <labels>/masks, 폴더 700·파일 600, 저장소 안은 거부):
  <case>.nii.gz          정답 마스크 초안 (0 배경, 1 병변, 2 무시)
  <case>_added.nii.gz    추가 참 초안 영역에 A 번호를 넣은 파일(Slicer 에서 윤곽을 확인·수정하는 출발점)

데이터 보호: 출력은 환자 마스크다. 저장소·클라우드에 두지 않는다. 화면 출력은 케이스 가명과 수치뿐이다.
"""
import argparse
import csv
import os
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))   # 같은 폴더의 모듈을 어디서 실행해도 찾게
from val_script import con_comp  # noqa: E402  (autoPET 공식 평가 val_script.py 의 연결성분 정의)

REPO = Path(__file__).resolve().parents[1]
LESION, IGNORE = 1, 2


def to_vox(inv, row, shape):
    """CSV 줄의 RAS mm -> 복셀 번호. 영상 밖이면 None."""
    ijk = np.rint(inv @ [float(row["x_mm"]), float(row["y_mm"]), float(row["z_mm"]), 1.0])[:3].astype(int)
    return tuple(ijk) if all(0 <= i < n for i, n in zip(ijk, shape)) else None


def box(p, r, shape):
    """p 를 가운데 둔 반경 r(복셀) 상자. 영상 경계에서 자른다."""
    return tuple(slice(max(pi - ri, 0), min(pi + ri + 1, n)) for pi, ri, n in zip(p, r, shape))


def grow(suv, p, sp, args):
    """점 p 근처(search-mm 상자)의 SUV 꼭짓점 q 를 찾고, 배경(q 에서 20-30 mm 껍질의 중앙값) 보정 임계값
    bg + frac×(SUVmax - bg) 이상으로 q 와 이어진 영역(grow-mm 상자 안)을 돌려준다."""
    sl = box(p, [max(1, round(args.search_mm / s)) for s in sp], suv.shape)
    q = tuple(s.start + i for s, i in zip(sl, np.unravel_index(np.argmax(suv[sl]), suv[sl].shape)))
    shell = sphere(q, sp, 30, suv.shape) & ~sphere(q, sp, 20, suv.shape)
    bg = float(np.median(suv[shell]))
    thr = bg + args.frac * (float(suv[q]) - bg)
    sl = box(q, [max(1, round(args.grow_mm / s)) for s in sp], suv.shape)
    cc = con_comp((suv[sl] >= thr).astype(np.uint8))
    sub = cc == cc[tuple(qi - s.start for qi, s in zip(q, sl))]
    edge = any(sub.take(0, axis=a).any() or sub.take(-1, axis=a).any() for a in range(3))
    region = np.zeros(suv.shape, bool)
    region[sl] = sub
    return q, bg, thr, region, edge


def sphere(p, sp, mm, shape):
    sl = box(p, [max(1, round(mm / s)) for s in sp], shape)
    grid = np.ogrid[sl]
    d2 = sum(((g - pi) * s) ** 2 for g, pi, s in zip(grid, p, sp))
    m = np.zeros(shape, bool)
    m[sl] = d2 <= mm ** 2
    return m


def build(case, args):
    f_csv, f_suv, f_seg = args.labels / f"FL_labels_{case}.csv", args.input / f"{case}_0001.nii.gz", args.output / f"{case}.nii.gz"
    for f in (f_csv, f_suv, f_seg):
        if not f.exists():
            sys.exit(f"[{case}] 입력 없음: {f.parent.name}/{f.name}")
    seg_img, suv_img = nib.load(str(f_seg)), nib.load(str(f_suv))
    if seg_img.shape != suv_img.shape or not np.allclose(seg_img.affine, suv_img.affine, atol=1e-3):
        sys.exit(f"[{case}] SUV·마스크 격자가 다르다: {suv_img.shape} {seg_img.shape}")
    suv = suv_img.get_fdata(dtype=np.float32)
    lab = con_comp((np.asanyarray(seg_img.dataobj) > 0).astype(np.uint8)).astype(np.int32)
    inv, sp = np.linalg.inv(seg_img.affine), [float(z) for z in seg_img.header.get_zooms()[:3]]
    vox_ml = float(np.prod(sp)) / 1000
    with open(f_csv, encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["research_id"] == case]

    out = (lab > 0).astype(np.uint8)
    added = np.zeros(lab.shape, np.uint8)
    seen, n_lab = set(), {}
    for r in (r for r in rows if r["type"] == "candidate"):
        p = to_vox(inv, r, lab.shape)
        comp = int(lab[p]) if p else 0
        if comp == 0:
            sys.exit(f"[{case}] 후보 {r['candidate_id']}(기록 #{r['record_no']}) 좌표가 모델 마스크 성분 밖이다. 페이지와 마스크가 같은 추론 결과인지 확인한다")
        label = r["label"] or "미판정"
        out[lab == comp] = {"true": LESION, "false": 0}.get(label, IGNORE)
        seen.add(comp)
        n_lab[label] = n_lab.get(label, 0) + 1
    unseen = set(range(1, int(lab.max()) + 1)) - seen
    for comp in unseen:
        out[lab == comp] = IGNORE
    print(f"[{case}] 후보 {sum(n_lab.values())}개 {n_lab}" + (f", CSV 에 없는 성분 {len(unseen)}개는 무시(2)" if unseen else ""))

    for r in (r for r in rows if r["type"] == "added"):
        name, label, p = r["candidate_id"], r["label"] or "미판정", to_vox(inv, r, lab.shape)
        if p is None:
            print(f"   {name} {label}: 좌표가 영상 밖이다 - 건너뜀")
            continue
        if label == "true":
            q, bg, thr, region, edge = grow(suv, p, sp, args)
            if (lab[region] > 0).any():
                print(f"   {name}: 초안 영역이 모델 후보 성분과 겹친다(같은 병변인지 확인)")
            out[region & (out == 0)] = IGNORE
            added[region] = int(name.lstrip("A"))
            shift = float(np.linalg.norm(np.subtract(q, p) * sp))
            print(f"   {name} 참: 꼭짓점 SUV {suv[q]:.2f} (점에서 {shift:.0f} mm), 배경 {bg:.2f}, 임계 {thr:.2f}, 초안 {region.sum() * vox_ml:.1f} mL -> 무시(2)"
                  + (" - 상자 끝에 닿음(새어 나감, Slicer 에서 다시 그린다)" if edge else ""))
        elif label == "false":
            if out[p] == LESION:
                print(f"   {name} 거짓: 그 점이 참 병변 안에 있다(확인)")
        else:
            m = sphere(p, sp, args.unsure_mm, lab.shape) & (out == 0)
            out[m] = IGNORE
            print(f"   {name} {label}: 반지름 {args.unsure_mm:g} mm 구를 무시(2)")

    args.out.mkdir(parents=True, exist_ok=True)
    args.out.chmod(0o700)
    for arr, f in ((out, args.out / f"{case}.nii.gz"), (added, args.out / f"{case}_added.nii.gz")):
        img = nib.Nifti1Image(arr, seg_img.affine, seg_img.header)
        img.set_data_dtype(np.uint8)
        nib.save(img, str(f))
        os.chmod(f, 0o600)
    print(f"[{case}] 병변 {(out == LESION).sum() * vox_ml:.1f} mL, 무시 {(out == IGNORE).sum() * vox_ml:.1f} mL -> {args.out / (case + '.nii.gz')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cases", nargs="+", help="케이스 가명 (예: P01 P02)")
    ap.add_argument("--base", type=Path, default=Path.home() / "autopet3", help="기본 폴더 (기본 ~/autopet3)")
    ap.add_argument("--input", type=Path, help="SUV 폴더 (기본 <base>/input)")
    ap.add_argument("--output", type=Path, help="autoPET 마스크 폴더 (기본 <base>/output)")
    ap.add_argument("--labels", type=Path, help="판정 CSV 폴더 (기본 <base>/labels)")
    ap.add_argument("--out", type=Path, help="정답 마스크 폴더 (기본 <labels>/masks). 저장소 안은 거부")
    ap.add_argument("--frac", type=float, default=0.5, help="추가 참 초안의 배경 보정 비율 (기본 0.5, EANM 2015 A50 방식)")
    ap.add_argument("--search-mm", type=float, default=5, help="찍은 점 주변에서 SUV 꼭짓점을 찾는 상자 반경 mm (기본 5)")
    ap.add_argument("--grow-mm", type=float, default=20, help="초안 영역이 퍼질 수 있는 상자 반경 mm (기본 20)")
    ap.add_argument("--unsure-mm", type=float, default=10, help="추가 불확실 점 주변을 무시할 구의 반지름 mm (기본 10)")
    args = ap.parse_args()
    base = args.base.expanduser().resolve()
    args.input = (args.input.expanduser() if args.input else base / "input").resolve()
    args.output = (args.output.expanduser() if args.output else base / "output").resolve()
    args.labels = (args.labels.expanduser() if args.labels else base / "labels").resolve()
    args.out = (args.out.expanduser() if args.out else args.labels / "masks").resolve()
    if args.out == REPO or REPO in args.out.parents:
        sys.exit(f"출력 폴더가 저장소 안이다({args.out}). 환자 마스크는 저장소 밖에 둔다.")
    for case in args.cases:
        build(case, args)


if __name__ == "__main__":
    main()
