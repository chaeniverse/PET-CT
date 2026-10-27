#!/usr/bin/env python
"""autoPET 추론 결과 -> FL 후보 확인 HTML (케이스당 파일 1개, 브라우저에서 바로 연다).

공유 폴더의 'FL 후보확인 도구 프로토타입'과 같은 화면을 autoPET 출력으로 채운다.
후보 = 모델 마스크의 연결성분. autoPET 공식 평가와 같은 함수(val_script.con_comp, cc3d 18-연결)로 세고,
화면에는 SUVmax 순으로 놓는다. 번호(기록 #)는 부피 큰 순(같으면 SUVmax 큰 순)이라 summarize_lesions.py 표와 같다.

입력 (<base> = ~/autopet3, 폴더는 --input / --output 으로 바꿀 수 있다):
  <base>/input/<case>_0000.nii.gz   CTres
  <base>/input/<case>_0001.nii.gz   SUV
  <base>/output/<case>.nii.gz       autoPET 마스크
  파일럿(SeriesTime 기준)은 --input ~/autopet3/input_series --output ~/autopet3/output_series
출력:
  <out>/<case>_후보확인.html       (기본 <out> = <base>/review)

데이터 보호: 출력 HTML 에는 PET/CT 영상 조각이 base64 로 들어 있다.
저장소 안에는 쓰지 않으며(시도하면 멈춘다), 커밋·업로드·공유 폴더 복사를 하지 않는다.
화면 출력은 케이스 가명과 수치뿐이다.

3D 보기(3D Slicer, 맥): Slicer 용 NIfTI·후보 목록·open_in_slicer.py 를 <out>/<case>_viewer/ 에, Finder 에서 더블클릭하는
<out>/<case>_Slicer열기.command 를 만든다(viewer_volumes.py). 페이지는 HTML 을 더블클릭해 열고, Slicer 에서 찍은 누락 병변 점은
페이지의 파일 선택으로 불러온다. 서버는 쓰지 않고, 페이지 안에는 3D 영상을 넣지 않는다.
LLM 의견(llm_opinions.py):
  --llm-input-only      HTML 대신 VLM 에 줄 후보 그림(<base>/llm_input/<case>/)과 빈 의견 틀(<base>/llm/<case>_llm.json)만 만든다
  --llm-opinion <폴더>  그 폴더의 <case>_llm.json 을 카드 오른쪽에 얹는다. 주지 않으면 LLM 칸은 비운다
해부 정보(anatomy.py, autoDS-PET):
  --totalseg <폴더>     <폴더>/<case>/seg.nii.gz(TotalSegmentator)로 후보마다 구조 이름·간/혈액풀 대비·규칙 DS 를 붙이고,
                        Slicer 에 구조 라벨을 겹친다. LLM 입력에도 들어가므로 --llm-input-only 와 페이지 생성에 같은 값을 준다
"""
import argparse
import base64
import io
import json
import os
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))   # 같은 폴더의 모듈을 어디서 실행해도 찾게
import llm_opinions  # noqa: E402
import viewer_volumes  # noqa: E402
from val_script import con_comp  # noqa: E402  (autoPET 공식 평가 val_script.py 의 연결성분 정의)

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = Path(__file__).resolve().with_name("review_template.html")
MODEL = "autoPET III LesionTracer (Zenodo 14007247), 5-fold + TTA"
NAVY, RED, ORANGE = (31, 56, 100), (192, 0, 0), (255, 140, 0)


def load_ras(path, dtype=None):
    """NIfTI 를 RAS 축 순서로 읽는다(축 뒤집기만, 보간 없음). 마스크는 dtype=None 으로 원래 정수형 유지."""
    img = nib.load(str(path))
    ornt = nib.orientations.io_orientation(img.affine)
    data = np.asanyarray(img.dataobj) if dtype is None else img.get_fdata(dtype=dtype)
    return img, ornt, nib.orientations.apply_orientation(data, ornt), img.affine @ nib.orientations.inv_ornt_aff(ornt, img.shape)


def png_uri(rgb):
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def gray(img2d, vmin, vmax, invert):
    g = np.clip((img2d - vmin) / (vmax - vmin), 0, 1)
    return ((1 - g if invert else g) * 255).astype(np.uint8)


def screen(a2d):
    """RAS 단면 (가로축, 세로축) -> 화면 배열. 축상: 환자 오른쪽=왼쪽·앞=위, 관상: 오른쪽=왼쪽·머리=위, 시상: 앞=왼쪽·머리=위."""
    return a2d.T[::-1, ::-1]


def crop_cube(a, p, r, fill):
    """p 를 가운데 둔 (2r+1)^3 상자. 영상 밖은 fill 로 채워 p 가 항상 정중앙에 오게 한다."""
    out = np.full([2 * ri + 1 for ri in r], fill, dtype=a.dtype)
    lo = [pi - ri for pi, ri in zip(p, r)]
    src = tuple(slice(max(l, 0), min(l + 2 * ri + 1, n)) for l, ri, n in zip(lo, r, a.shape))
    dst = tuple(slice(s.start - l, s.stop - l) for s, l in zip(src, lo))
    out[dst] = a[src]
    return out


def tile(img2d, lab2d, cur, vmin, vmax, invert, size):
    rgb = np.array(Image.fromarray(gray(img2d, vmin, vmax, invert)).resize((size, size), Image.BILINEAR).convert("RGB"))
    if lab2d is not None:
        for m, color in (((lab2d > 0) & (lab2d != cur), ORANGE), (lab2d == cur, RED)):
            m = np.array(Image.fromarray(m.astype(np.uint8) * 255).resize((size, size), Image.NEAREST)) > 0
            rgb[m & ~ndimage.binary_erosion(m)] = color
    c, t = size // 2, max(6, size // 18)          # 가장자리 눈금: 가운데(=SUVmax 위치)를 가리킨다
    rgb[c - 1:c + 1, :t] = rgb[c - 1:c + 1, -t:] = NAVY
    rgb[:t, c - 1:c + 1] = rgb[-t:, c - 1:c + 1] = NAVY
    return png_uri(rgb)


def write_llm_images(img_dir, cards):
    """로컬 VLM(llm_review.py --images)에 줄 후보 그림. 카드의 네 칸을 2×2 로 붙인 한 장: 위 = PET 축상·관상, 아래 = PET 시상·CT 축상.
    맥으로 보내는 review 폴더 밖(<base>/llm_input/<case>/<기록#>.png)에 둔다. VLM 이 정사각형으로 줄이므로 2×2 로 비율을 지킨다."""
    img_dir.mkdir(parents=True, exist_ok=True)
    img_dir.chmod(0o700)
    for c in cards:
        t = [Image.open(io.BytesIO(base64.b64decode(c[k].split(",", 1)[1]))).convert("RGB") for k in ("ax", "co", "sa", "ct")]
        w, h = t[0].size
        grid = Image.new("RGB", (2 * w, 2 * h), "white")
        for i, im in enumerate(t):
            grid.paste(im, ((i % 2) * w, (i // 2) * h))
        f = img_dir / f"{c['record_no']:02d}.png"
        grid.save(f)
        f.chmod(0o600)


def build(case, base, out_dir, args):
    f_ct, f_suv, f_seg = args.input / f"{case}_0000.nii.gz", args.input / f"{case}_0001.nii.gz", args.output / f"{case}.nii.gz"
    for f in (f_ct, f_suv, f_seg):
        if not f.exists():
            sys.exit(f"[{case}] 입력 없음: {f.parent.name}/{f.name}")

    seg_img = nib.load(str(f_seg))
    seg_raw = np.asanyarray(seg_img.dataobj) > 0
    # summarize_lesions.py 표와 번호를 맞추려고 원래 축 순서에서 성분을 센다(같은 부피끼리의 순서가 축 방향에 따라 달라짐)
    lab_raw = con_comp(seg_raw.astype(np.uint8)).astype(np.int32)
    n = int(lab_raw.max())
    vox_ml = float(np.prod(seg_img.header.get_zooms()[:3])) / 1000

    ornt = nib.orientations.io_orientation(seg_img.affine)
    lab = nib.orientations.apply_orientation(lab_raw, ornt)
    _, ornt_suv, suv, aff = load_ras(f_suv, np.float32)
    _, _, ct, aff_ct = load_ras(f_ct, np.float32)
    aff_seg = seg_img.affine @ nib.orientations.inv_ornt_aff(ornt, seg_img.shape)
    if suv.shape != lab.shape or ct.shape != lab.shape or not (np.allclose(aff, aff_ct, atol=1e-3) and np.allclose(aff, aff_seg, atol=1e-3)):
        sys.exit(f"[{case}] CT·SUV·마스크 격자가 다르다: {ct.shape} {suv.shape} {lab.shape}")
    sp = np.sqrt((aff[:3, :3] ** 2).sum(axis=0))
    anat = lab_anat = None
    if args.totalseg:         # autoDS-PET 를 부르므로 --totalseg 를 줄 때만 불러온다
        import anatomy
        anat = anatomy.load(case, args.totalseg, f_suv)
        if anat is None:
            print(f"[{case}] 분할 없음({args.totalseg / case / 'seg.nii.gz'}) - 해부 정보 없이 만든다")
        else:
            lab_anat = nib.orientations.apply_orientation(anat["labels"], ornt_suv)
    # 기록 # = 부피 큰 순, 부피가 같으면 SUVmax 큰 순(summarize_lesions.py 와 같은 규칙)
    sizes = ndimage.sum_labels(lab > 0, lab, index=np.arange(1, n + 1))
    smax = ndimage.maximum(suv, lab, index=np.arange(1, n + 1))
    record_no = {int(lbl): k for k, lbl in enumerate(sorted(range(1, n + 1), key=lambda l: (-sizes[l - 1], -smax[l - 1])), 1)}
    r = [max(1, int(round(args.crop_mm / s))) for s in sp]
    rp = [max(1, int(round(6.2 / s))) for s in sp]    # SUVpeak 근사: 꼭짓점 주변 약 12 mm 정육면체 평균(09-28 시험실행과 같은 방식)

    cards = []
    for lbl, sl in enumerate(ndimage.find_objects(lab), 1):
        if sl is None:
            continue
        m = lab[sl] == lbl
        vol = float(m.sum()) * vox_ml
        if vol < args.min_vol:
            continue
        v = np.where(m, suv[sl], -np.inf)
        p = tuple(int(s.start + q) for s, q in zip(sl, np.unravel_index(np.argmax(v), v.shape)))
        peak = crop_cube(suv, p, rp, np.float32(np.nan))
        hu = crop_cube(ct, p, [1, 1, 1], np.float32(np.nan))
        cs, cc, cl = crop_cube(suv, p, r, np.float32(0)), crop_cube(ct, p, r, np.float32(-1000)), crop_cube(lab, p, r, 0)
        views = [(cs[:, :, r[2]], cl[:, :, r[2]]), (cs[:, r[1], :], cl[:, r[1], :]), (cs[r[0], :, :], cl[r[0], :, :])]
        ax, co, sa = [tile(screen(a), screen(b), lbl, 0, args.suv_max, True, args.tile) for a, b in views]
        cards.append(dict(
            suvmax=round(float(suv[p]), 2), suvpeak=round(float(np.nanmean(peak)), 2), suvmean=round(float(suv[sl][m].mean()), 2),
            vol=round(vol, 2), hu=int(round(float(np.nanmean(hu)))), record_no=record_no[lbl],
            vox=list(p), mm=[round(float(x), 1) for x in (aff @ np.r_[p, 1])[:3]],
            ax=ax, co=co, sa=sa, ct=tile(screen(cc[:, :, r[2]]), screen(cl[:, :, r[2]]), lbl, *args.ct_window, False, args.tile)))
        cards[-1].update(anatomy.card_fields(anat, lab_anat, p, sl, m, float(suv[p])) if anat
                         else {"site": None, "r_liver": None, "r_mbp": None, "ds_rule": None})
    cards.sort(key=lambda c: -c["suvmax"])
    for k, c in enumerate(cards, 1):
        c["id"] = k

    if args.llm_input_only:   # VLM 에 줄 그림과 빈 의견 틀만 만들고 HTML 은 만들지 않는다
        write_llm_images(base / "llm_input" / case, cards)
        llm_path = args.llm_opinion / f"{case}_llm.json"
        if llm_opinions.write_stub(llm_path, case, cards):
            print(f"[{case}] LLM 의견 빈 틀 작성 -> {llm_path}")
        print(f"[{case}] 후보 그림 {len(cards)}장 -> {base / 'llm_input' / case}")
        return

    # 관상면 MIP: 물리 비율대로 늘린다. 클릭 위치 -> mm 변환에 쓸 격자 정보(nx, nz, jc, affine)를 같이 넣는다.
    nx, ny, nz = suv.shape
    mip = screen(suv.max(axis=1))
    w = args.mip_width
    h = int(round(w * nz * sp[2] / (nx * sp[0])))
    mip_rgb = np.array(Image.fromarray(gray(mip, 0, args.suv_max, True)).resize((w, h), Image.BILINEAR).convert("RGB"))
    # MIP 의 각 점이 어느 깊이(y)에서 왔는지: MIP 를 클릭하면 이 깊이로 3D 위치를 정한다
    depth = np.ascontiguousarray(screen(suv.argmax(axis=1)).astype("<u2"))

    llm_ops, llm_meta = {}, {}
    if args.llm_opinion:      # 주면 그 폴더의 <case>_llm.json 을 읽고, 주지 않으면 LLM 칸은 비운다
        llm_path = args.llm_opinion / f"{case}_llm.json"
        if not llm_path.exists():
            print(f"[{case}] LLM 의견 파일 없음({llm_path}) - LLM 칸은 비운다")
        llm_ops, llm_meta = llm_opinions.load(llm_path, cards)
    for c in cards:
        c["llm"] = llm_ops.get(c["record_no"])

    if not args.no_viewer:     # 맥 3D Slicer 용 파일(페이지 안에는 넣지 않는다)
        viewer_volumes.write(case, f_ct, f_suv, f_seg, out_dir, [{"id": c["id"], "record_no": c["record_no"], "mm": c["mm"]} for c in cards],
                             args.viewer_max_mvox * 1e6, labels=anat["labels"] if anat else None,
                             names=anat["names"] if anat else None, ct_window=args.ct_window, suv_max=args.suv_max)

    note = f"후보 = autoPET 마스크 연결성분 {len(cards)}개" + (f" (부피 {args.min_vol} mL 미만 {n - len(cards)}개 제외)" if n > len(cards) else "")
    note += f" · SUV 창 0–{args.suv_max:g} · 판독 FL-DS: {args.reader_ds.get(case, '미입력')}"
    if anat:
        ref = " · ".join(f"{k} {v:.2f}" if v else f"{k} 없음" for k, v in (("간", anat["liver"]), ("혈액풀", anat["mbp"])))
        note += f" · 기준 SUV {ref} (autoDS-PET)"
    if case in args.note:
        note += " · " + args.note[case]
    data = dict(case=case, model=MODEL, note=note, cards=cards, slicer=not args.no_viewer, llm_meta=llm_meta,
                mip=dict(src=png_uri(mip_rgb), nx=nx, nz=nz, jc=(ny - 1) / 2, aff=[[float(x) for x in row] for row in aff[:3]],
                         depth=base64.b64encode(depth.tobytes()).decode()))

    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("__TITLE__", f"FL 후보 확인 · {case}").replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    out = out_dir / f"{case}_후보확인.html"
    out.write_text(html, encoding="utf-8")
    os.chmod(out, 0o600)
    print(f"[{case}] 후보 {len(cards)}개 (성분 {n}개), {out.stat().st_size / 1e6:.1f} MB -> {out}")
    for c in cards:
        print(f"   후보 {c['id']:2d}  기록 #{c['record_no']:02d}  SUVmax {c['suvmax']:6.2f}  부피 {c['vol']:6.2f} mL  CT {c['hu']:5d} HU")


def kv(items):
    d = {}
    for it in items or []:
        k, _, v = it.partition("=")
        d[k] = v
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cases", nargs="+", help="케이스 가명 (예: P01 P02)")
    ap.add_argument("--base", type=Path, default=Path.home() / "autopet3", help="input/ 과 output/ 이 있는 폴더 (기본 ~/autopet3)")
    ap.add_argument("--input", type=Path, help="CTres·SUV 폴더 (기본 <base>/input)")
    ap.add_argument("--output", type=Path, help="autoPET 마스크 폴더 (기본 <base>/output)")
    ap.add_argument("--out", type=Path, help="HTML 을 둘 폴더 (기본 <base>/review). 저장소 안은 거부")
    ap.add_argument("--suv-max", type=float, default=8.0, help="PET 회색조 위쪽 끝 SUV (기본 8, 09-28 시험실행과 같음)")
    ap.add_argument("--ct-window", type=float, nargs=2, default=[-200, 1200], metavar=("MIN", "MAX"), help="CT 창 HU (기본 -200 1200)")
    ap.add_argument("--crop-mm", type=float, default=60, help="후보 그림의 반경 mm (기본 60)")
    ap.add_argument("--tile", type=int, default=150, help="후보 그림 한 칸의 픽셀 (기본 150)")
    ap.add_argument("--mip-width", type=int, default=480, help="MIP 그림 가로 픽셀 (기본 480)")
    ap.add_argument("--min-vol", type=float, default=0.0, help="이보다 작은 성분(mL)은 후보에서 뺀다 (기본 0 = 모두)")
    ap.add_argument("--reader-ds", action="append", metavar="CASE=값", help="머리말에 표시할 판독 FL-DS (예: P01=4). 여러 번 쓸 수 있다")
    ap.add_argument("--note", action="append", metavar="CASE=문장", help="머리말에 덧붙일 메모 (예: 'P02=체중 확인 전 SUV')")
    ap.add_argument("--no-viewer", action="store_true", help="Slicer 용 파일을 만들지 않는다(페이지의 Slicer 버튼은 동작하지 않는다)")
    ap.add_argument("--viewer-max-mvox", type=float, default=30, help="Slicer 용 영상의 최대 복셀 수(백만). 넘으면 축마다 묶어 줄인다 (기본 30)")
    ap.add_argument("--llm-opinion", type=Path, metavar="DIR", help="LLM 의견 폴더. 그 안의 <case>_llm.json 을 카드에 넣는다. 주지 않으면 LLM 칸은 비운다")
    ap.add_argument("--llm-input-only", action="store_true", help="HTML 대신 VLM 에 줄 후보 그림(<base>/llm_input)과 빈 의견 틀(--llm-opinion 폴더, 기본 <base>/llm)만 만든다")
    ap.add_argument("--totalseg", type=Path, metavar="DIR", help="TotalSegmentator 결과 폴더(<DIR>/<case>/seg.nii.gz, <DIR>/classes_total.json). 주면 후보에 해부 정보를 붙이고 Slicer 에 구조 라벨을 겹친다")
    args = ap.parse_args()
    args.reader_ds, args.note = kv(args.reader_ds), kv(args.note)
    args.totalseg = args.totalseg.expanduser().resolve() if args.totalseg else None

    base = args.base.expanduser().resolve()
    args.input = (args.input.expanduser() if args.input else base / "input").resolve()
    args.output = (args.output.expanduser() if args.output else base / "output").resolve()
    out_dir = (args.out.expanduser() if args.out else base / "review").resolve()
    if out_dir == REPO or REPO in out_dir.parents:
        sys.exit(f"출력 폴더가 저장소 안이다({out_dir}). 영상이 든 HTML 은 저장소 밖에 둔다.")
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.llm_opinion or args.llm_input_only:
        args.llm_opinion = (args.llm_opinion.expanduser() if args.llm_opinion else base / "llm").resolve()
        if args.llm_opinion == REPO or REPO in args.llm_opinion.parents:
            sys.exit(f"LLM 의견 폴더가 저장소 안이다({args.llm_opinion}). 환자 수치가 든 파일은 저장소 밖에 둔다.")
    if args.llm_input_only:
        args.llm_opinion.mkdir(parents=True, exist_ok=True)
        args.llm_opinion.chmod(0o700)
    for case in args.cases:
        build(case, base, out_dir, args)
    if args.llm_input_only:
        print(f"\n다음: llm_review.py 로 의견을 받은 뒤 make_review_html.py ... --llm-opinion {args.llm_opinion}")
        return
    (out_dir / "review_server.py").unlink(missing_ok=True)    # 예전 방식(로컬 서버) 파일이 맥으로 가지 않게
    print(f"\n맥 판독 폴더로 받은 뒤 {args.cases[0]}_후보확인.html 을 더블클릭해 연다. Slicer 는 {args.cases[0]}_Slicer열기.command 를 더블클릭한다.")


if __name__ == "__main__":
    main()
