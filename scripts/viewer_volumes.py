#!/usr/bin/env python
"""맥 3D Slicer 판독용 파일을 만든다: 가벼운 NIfTI(CT·SUV·마스크, --totalseg 이면 구조 라벨)와 Slicer 로 여는 스크립트.

맥 판독 폴더(Dropbox)로 보내므로 원본(CT float64, P02 기준 1 GB 이상)보다 작게
  - CT 는 int16, SUV 는 int16(0.002 단위, NIfTI scl_slope 로 복원, 최대 65.5), 마스크는 uint8 로 줄이고
  - 복셀이 max_vox 보다 많으면 각 축을 f 배 묶는다(SUV·마스크는 최댓값, CT 는 평균 → 뜨거운 점이 묻히지 않는다).
수치(SUVmax·부피)는 카드에 원본 해상도로 계산된 값을 쓴다. Slicer 는 위치 확인·판독용이다.

출력: <out>/<case>_viewer/  (저장소 밖. 영상이므로 맥 판독 폴더 밖으로 옮기지 않는다)
  ct·suv·mask.nii.gz, candidates.json(후보 번호·RAS 좌표), open_in_slicer.py
  그리고 <out>/<case>_Slicer열기.command (맥 Finder 에서 더블클릭하면 이 폴더의 open_in_slicer.py 로 Slicer 가 열린다)
  구조 라벨이 있으면 labels.nii.gz(라벨 번호는 섞이면 안 되므로 묶을 때 가운데 복셀을 그대로 쓴다)와 이름표 labels.ctbl
  (맥 판독 폴더로 보내는 예외, data-governance.md §2)
Slicer 에서 찍은 점은 Slicer 가 같은 폴더의 slicer_points.csv 에 쓴다(맥에서만 생긴다).
"""
import json
import math
from pathlib import Path

import nibabel as nib
import numpy as np


def block_reduce(a, f, how):
    if f == 1:
        return a
    n = [s // f * f for s in a.shape]
    if how == "nearest":                     # 라벨: 각 묶음의 가운데 복셀
        return a[f // 2:n[0]:f, f // 2:n[1]:f, f // 2:n[2]:f]
    a = a[:n[0], :n[1], :n[2]].reshape(n[0] // f, f, n[1] // f, f, n[2] // f, f)
    return a.max(axis=(1, 3, 5)) if how == "max" else a.mean(axis=(1, 3, 5))


def label_colors(n):
    """라벨 n 개의 색(0 = 투명). 이웃 번호끼리 구별되게 색상환을 황금각으로 돈다."""
    def c(x):
        return int(round(255 * min(max(x, 0), 1)))
    rgb = [[0, 0, 0]]
    for i in range(1, n):
        h = (i * 0.618034) % 1 * 6
        rgb.append([c(abs(h - 3) - 1), c(2 - abs(h - 2)), c(2 - abs(h - 4))])
    return rgb


SLICER_SCRIPT = r'''# 3D Slicer 로 이 폴더의 영상을 연다(make_review_html.py 가 만든 파일, 고치지 않는다).
# 보통은 판독 폴더의 <case>_Slicer열기.command 를 Finder 에서 더블클릭해 연다. 터미널로 열 때:
#   cd <판독 폴더>/<case>_viewer && /Applications/Slicer.app/Contents/MacOS/Slicer --python-script open_in_slicer.py
# 누락 병변: P 키로 점 찍기를 켜고 끈다. 찍기·옮기기·지우기를 할 때마다 slicer_points.csv 에 쓴다(페이지에서 파일로 고른다).
# 구조 라벨(TotalSegmentator) 색은 처음에 숨겨 둔다. L 키로 켜고 끈다. 숨겨도 Data Probe·찍은 점에는 구조 이름이 나온다.
import csv
import json
import os

import qt
import slicer
import vtk

D = os.getcwd()
CASE = "__CASE__"    # 점 파일에 케이스 가명을 남겨, 페이지가 다른 케이스 파일을 받지 않게 한다


def f(name):
    return os.path.join(D, name)


if not os.path.exists(f("ct.nii.gz")):
    raise SystemExit("ct.nii.gz 가 없다. <case>_viewer 폴더에서 실행한다: " + D)

ct = slicer.util.loadVolume(f("ct.nii.gz"))
ct.GetDisplayNode().SetAutoWindowLevel(False)
ct.GetDisplayNode().SetWindowLevelMinMax(__CT_MIN__, __CT_MAX__)
suv = slicer.util.loadVolume(f("suv.nii.gz"))
# SUV 는 0.002 단위 정수 + scl_slope 로 저장했다. 기울기를 적용하지 않고 읽혔으면(정수형) 창을 저장값 단위로 맞춘다
k = 1.0 if suv.GetImageData().GetScalarType() in (vtk.VTK_FLOAT, vtk.VTK_DOUBLE) else 1.0 / __SUV_STEP__
suv.GetDisplayNode().SetAndObserveColorNodeID("vtkMRMLPETProceduralColorNodePET-Heat")
suv.GetDisplayNode().SetAutoWindowLevel(False)
suv.GetDisplayNode().SetWindowLevelMinMax(0, __SUV_MAX__ * k)
lesion = slicer.util.loadSegmentation(f("mask.nii.gz"))
if lesion.GetSegmentation().GetNumberOfSegments():
    lesion.GetSegmentation().GetNthSegment(0).SetName("autoPET 병변")
    lesion.GetSegmentation().GetNthSegment(0).SetColor(1, 0, 0)
lab = colors = None
if os.path.exists(f("labels.nii.gz")):
    colors = slicer.util.loadColorTable(f("labels.ctbl"))
    lab = slicer.util.loadLabelVolume(f("labels.nii.gz"), {"colorNodeID": colors.GetID()})
slicer.util.setSliceViewerLayers(background=ct, foreground=suv, foregroundOpacity=0.5, label=lab, labelOpacity=0.0)
slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
lesion.CreateClosedSurfaceRepresentation()

# 후보 번호: 페이지 카드 번호(기록 #). 잠가 둔다
cands = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "후보")
with open(f("candidates.json"), encoding="utf-8") as fh:
    for c in json.load(fh):
        cands.AddControlPoint(c["mm"], f"{c['id']} (#{c['record_no']:02d})")
cands.SetLocked(True)
cands.GetDisplayNode().SetSelectedColor(0.12, 0.22, 0.39)

# 누락 병변: 찍은 점을 RAS mm 로 slicer_points.csv 에 쓴다. 전에 찍은 점이 있으면 이어서 연다
added = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "누락 병변")
added.GetDisplayNode().SetSelectedColor(1, 0.55, 0)
POINTS = f("slicer_points.csv")
if os.path.exists(POINTS):
    with open(POINTS, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            added.AddControlPoint([float(r["x"]), float(r["y"]), float(r["z"])])


def structure_at(ras):
    """그 점의 구조 이름(TotalSegmentator 라벨). 라벨이 없거나 영상 밖이면 빈 칸."""
    if lab is None:
        return ""
    m = vtk.vtkMatrix4x4()
    lab.GetRASToIJKMatrix(m)
    i, j, kk = [int(round(v)) for v in m.MultiplyPoint(list(ras) + [1.0])[:3]]
    a = slicer.util.arrayFromVolume(lab)   # (k, j, i)
    if 0 <= kk < a.shape[0] and 0 <= j < a.shape[1] and 0 <= i < a.shape[2]:
        return colors.GetColorName(int(a[kk, j, i]))
    return ""


def save_points(*_):
    rows = []
    for n in range(added.GetNumberOfControlPoints()):
        p = [0.0, 0.0, 0.0]
        added.GetNthControlPointPositionWorld(n, p)
        rows.append([CASE, n + 1, round(p[0], 1), round(p[1], 1), round(p[2], 1), structure_at(p)])
    with open(POINTS, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["case", "n", "x", "y", "z", "structure"])
        w.writerows(rows)


# 기존 점 파일은 좌표와 구조 이름을 그대로 두고 case 열만 추가한다.
if os.path.exists(POINTS):
    with open(POINTS, newline="", encoding="utf-8") as fh:
        legacy = csv.reader(fh)
        header = next(legacy, [])
        legacy_rows = list(legacy)
    if header == ["n", "x", "y", "z", "structure"]:
        with open(POINTS, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["case", "n", "x", "y", "z", "structure"])
            w.writerows([CASE] + row for row in legacy_rows)


for ev in (slicer.vtkMRMLMarkupsNode.PointPositionDefinedEvent, slicer.vtkMRMLMarkupsNode.PointEndInteractionEvent,
           slicer.vtkMRMLMarkupsNode.PointRemovedEvent):
    added.AddObserver(ev, save_points)

# P 키: 누락 병변 점 찍기 켜기/끄기
selection = slicer.app.applicationLogic().GetSelectionNode()
interaction = slicer.app.applicationLogic().GetInteractionNode()


def toggle_place():
    if interaction.GetCurrentInteractionMode() == interaction.Place:
        interaction.SetCurrentInteractionMode(interaction.ViewTransform)
        return
    selection.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
    selection.SetActivePlaceNodeID(added.GetID())
    interaction.SetPlaceModePersistence(1)
    interaction.SetCurrentInteractionMode(interaction.Place)


place_key = qt.QShortcut(qt.QKeySequence("P"), slicer.util.mainWindow())
place_key.connect("activated()", toggle_place)

# L 키: 구조 라벨 색 켜기/끄기(처음에는 꺼 둠)
def toggle_labels():
    if lab is None:
        return
    for name in slicer.app.layoutManager().sliceViewNames():
        comp = slicer.app.layoutManager().sliceWidget(name).sliceLogic().GetSliceCompositeNode()
        comp.SetLabelOpacity(0.0 if comp.GetLabelOpacity() > 0 else 0.4)


label_key = qt.QShortcut(qt.QKeySequence("L"), slicer.util.mainWindow())
label_key.connect("activated()", toggle_labels)
if cands.GetNumberOfControlPoints():
    p0 = [0.0, 0.0, 0.0]
    cands.GetNthControlPointPositionWorld(0, p0)
    slicer.modules.markups.logic().JumpSlicesToLocation(p0[0], p0[1], p0[2], True)
slicer.util.delayDisplay("P 키: 누락 병변 점 찍기 켜기/끄기 · L 키: 구조 라벨 색 켜기/끄기. 찍은 점은 페이지의 'Slicer 에서 찍은 점 불러오기'로 가져간다.", 4000)
'''


COMMAND = """#!/bin/sh
# __CASE__ 를 3D Slicer 로 연다(make_review_html.py 가 만든 파일). 맥 Finder 에서 더블클릭한다.
cd "$(dirname "$0")/__CASE___viewer" || exit 1
# 같은 케이스 Slicer 가 이미 열려 있으면 새로 열지 않는다(두 창이 같은 slicer_points.csv 를 덮어쓰지 않게)
if pgrep -f "__CASE___viewer/open_in_slicer.py" >/dev/null; then
  echo "__CASE__ Slicer 가 이미 열려 있다. 그 창을 쓴다."
  osascript -e 'tell application "Slicer" to activate' >/dev/null 2>&1
  exit 0
fi
exec /Applications/Slicer.app/Contents/MacOS/Slicer --python-script "$PWD/open_in_slicer.py"
"""


def write_labels(vdir, labels, names, f, aff):
    """구조 라벨(SUV 격자, nibabel 축 순서)과 Slicer 이름표를 쓴다. 분할을 다시 돌렸을 수 있으므로 매번 새로 쓴다."""
    p = vdir / "labels.nii.gz"
    save(block_reduce(labels, f, "nearest").astype(np.uint8), aff, p)
    t = vdir / "labels.ctbl"
    t.write_text("".join(f"{i} {n} {r} {g} {b} {0 if i == 0 else 255}\n" for i, (n, (r, g, b)) in enumerate(zip(names, label_colors(len(names))))),
                 encoding="utf-8")
    for q in (p, t):
        q.chmod(0o600)
    return p


def scaled_affine(aff, f):
    """f 배 묶은 격자의 affine. 새 복셀 i 의 중심 = 원래 복셀 f*i + (f-1)/2."""
    out = aff.copy()
    out[:3, :3] = aff[:3, :3] * f
    out[:3, 3] = (aff @ np.r_[[(f - 1) / 2] * 3, 1])[:3]
    return out


SUV_STEP = 0.002


def save(arr, aff, path, slope=None):
    img = nib.Nifti1Image(arr, aff)
    if slope is not None:
        img.header.set_slope_inter(slope, 0)
    img.set_qform(aff, code=1)
    img.set_sform(aff, code=1)
    nib.save(img, str(path))


def write(case, f_ct, f_suv, f_seg, out_dir, cands, max_vox=30e6, labels=None, names=None, ct_window=(-200, 1200), suv_max=8.0):
    """Slicer 용 파일을 만들고 {"ct","suv","mask"[,"labels"]} 경로와 묶음 배수 f 를 돌려준다.
    CT·SUV·마스크는 입력보다 새 파일이 있으면 다시 만들지 않는다. 후보 목록·Slicer 스크립트는 늘 쓴다.
    cands = [{"id", "record_no", "mm"}, …] (페이지 카드 번호와 같다).
    labels 를 주면 구조 라벨·이름표를 쓰고, 주지 않으면 예전에 만든 구조 라벨 파일을 지운다(옛 분할이 맥으로 가지 않게)."""
    vdir = Path(out_dir) / f"{case}_viewer"
    paths = {k: vdir / f"{k}.nii.gz" for k in ("ct", "suv", "mask")}
    newest_in = max(Path(p).stat().st_mtime for p in (f_ct, f_suv, f_seg))
    seg_img = nib.load(str(f_seg))
    n = int(np.prod(seg_img.shape[:3]))
    f = max(1, math.ceil((n / max_vox) ** (1 / 3)))
    aff = scaled_affine(seg_img.affine, f)
    vdir.mkdir(parents=True, exist_ok=True)
    script = SLICER_SCRIPT
    for k, v in (("__CT_MIN__", ct_window[0]), ("__CT_MAX__", ct_window[1]), ("__SUV_MAX__", suv_max), ("__SUV_STEP__", SUV_STEP)):
        script = script.replace(k, repr(float(v)))
    script = script.replace("__CASE__", case)
    for name, text in (("open_in_slicer.py", script), ("candidates.json", json.dumps(cands, ensure_ascii=False))):
        (vdir / name).write_text(text, encoding="utf-8")
        (vdir / name).chmod(0o600)
    command = Path(out_dir) / f"{case}_Slicer열기.command"     # 맥 Finder 에서 더블클릭하면 터미널이 이 스크립트를 실행한다
    command.write_text(COMMAND.replace("__CASE__", case), encoding="utf-8")
    command.chmod(0o700)
    if labels is not None:
        paths["labels"] = write_labels(vdir, labels, names, f, aff)
    else:
        for k in ("labels.nii.gz", "labels.ctbl"):
            (vdir / k).unlink(missing_ok=True)
    if all(p.exists() and p.stat().st_mtime > newest_in for p in paths.values()) \
            and nib.load(str(paths["suv"])).get_data_dtype() == np.int16:   # 예전 float32 SUV 파일이면 다시 만든다
        return paths, f

    save(block_reduce(np.asanyarray(seg_img.dataobj) > 0, f, "max").astype(np.uint8), aff, paths["mask"])
    suv = nib.load(str(f_suv)).get_fdata(dtype=np.float32)
    # SUV 는 0.002 단위 정수로 저장해 크기를 절반 이하로(맥 판독 폴더로 보내므로). 보기 범위(0–8)에서는 차이가 없다
    save(np.clip(np.round(block_reduce(suv, f, "max") / SUV_STEP), 0, 32767).astype(np.int16), aff, paths["suv"], slope=SUV_STEP)
    del suv
    ct = nib.load(str(f_ct)).get_fdata(dtype=np.float32)
    save(np.clip(np.round(block_reduce(ct, f, "mean")), -1024, 3071).astype(np.int16), aff, paths["ct"])
    for p in paths.values():
        p.chmod(0o600)
    return paths, f
