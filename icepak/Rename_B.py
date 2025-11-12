# -*- coding: utf-8 -*-
# ============================================================
# Icepak Macro (IronPython 2.7)
# Rename solids by improved geometry heuristics:
#  - FR4 by thickness window
#  - GPU_Package: largest planform area among "not-too-thick" parts
#  - GPU_Sub_*: parts whose XY center falls inside GPU_Package XY box (with margin)
#  - Copper_*: very thin sheets
#  - Imported_*: the rest
# ============================================================

import ScriptEnv
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")

oProject = oDesktop.GetActiveProject()
oDesign  = oProject.GetActiveDesign()
oEditor  = oDesign.SetActiveEditor("3D Modeler")

# ---------- Heuristic thresholds (mm) ----------
HEU_FR4_THICK_RANGE    = (1.2, 2.2)     # FR4 around 1.6 mm
HEU_CU_SHEET_THICK_MAX = 0.20           # very thin copper layers
HEU_GPU_THICK_MAX      = 8.0            # GPU pieces are usually "not too thick"
HEU_GPU_THICK_MIN      = 0.15           # exclude foils
GPU_XY_MARGIN          = 2.0            # expand XY box when collecting GPU_Sub
# ----------------------------------------------

def get_bbox(name):
    try:
        b = oEditor.GetObjectBoundingBox(name)
        return (float(b[0]), float(b[1]), float(b[2]),
                float(b[3]), float(b[4]), float(b[5]))
    except:
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

def bbox_sizes(b):
    return (abs(b[3]-b[0]), abs(b[4]-b[1]), abs(b[5]-b[2]))

def bbox_center(b):
    return ((b[0]+b[3])*0.5, (b[1]+b[4])*0.5, (b[2]+b[5])*0.5)

def bbox_area_xy(b):
    dx, dy, _ = bbox_sizes(b)
    return dx*dy

def bbox_vol(b):
    dx, dy, dz = bbox_sizes(b)
    return dx*dy*dz

def rename_safe(old_name, new_name):
    if not old_name or old_name == new_name:
        return False
    try:
        oEditor.RenameObject(old_name, new_name)
        print "[OK] {0} -> {1}".format(old_name, new_name)
        return True
    except:
        pass
    try:
        oEditor.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:Geometry3DAttributeTab",
                    ["NAME:PropServers", old_name],
                    ["NAME:ChangedProps",
                        ["NAME:Name", "Value:=", new_name]
                    ]
                ]
            ]
        )
        print "[OK] {0} -> {1}".format(old_name, new_name)
        return True
    except Exception as e:
        print "[WARN] Rename failed for {0}: {1}".format(old_name, e)
        return False

def seq2(n): return "%02d" % n

# ---- collect solids ----
try:
    solids = list(oEditor.GetObjectsInGroup("Solids"))
except:
    solids = []

# pre-compute geometry cache
info = []
for s in solids:
    b = get_bbox(s)
    dx, dy, dz = bbox_sizes(b)
    tmin = min(dx, dy, dz)
    area = bbox_area_xy(b)
    ctr  = bbox_center(b)
    info.append({"name": s, "bbox": b, "dx": dx, "dy": dy, "dz": dz,
                 "tmin": tmin, "area": area, "ctr": ctr, "vol": bbox_vol(b)})

# ---- classify FR4 (by thickness window, largest volume -> FR4_base) ----
fr4 = [d for d in info if HEU_FR4_THICK_RANGE[0] <= d["tmin"] <= HEU_FR4_THICK_RANGE[1]]
fr4_sorted = sorted(fr4, key=lambda d: -d["vol"])
renamed = 0

if fr4_sorted:
    if rename_safe(fr4_sorted[0]["name"], "FR4_base"): renamed += 1
    i = 1
    for d in fr4_sorted[1:]:
        if rename_safe(d["name"], "FR4_extra_{0}".format(seq2(i))): renamed += 1
        i += 1

# ---- identify GPU_Package (largest XY area among "not-too-thick") ----
candidates = [d for d in info
              if (HEU_GPU_THICK_MIN <= d["tmin"] <= HEU_GPU_THICK_MAX)
              and (d["name"] not in [x["name"] for x in fr4])]
gpu_pkg = None
if candidates:
    gpu_pkg = sorted(candidates, key=lambda d: -d["area"])[0]
    if rename_safe(gpu_pkg["name"], "GPU_Package"): renamed += 1

# ---- copper: very thin foils anywhere ----
copper = [d for d in info
          if (d["tmin"] <= HEU_CU_SHEET_THICK_MAX)
          and (gpu_pkg is None or d["name"] != gpu_pkg["name"])]
i = 1
for d in sorted(copper, key=lambda d: -d["vol"]):
    if rename_safe(d["name"], "Copper_{0}".format(seq2(i))): renamed += 1
    i += 1

# ---- GPU_Sub: objects whose XY center falls in GPU_Package XY bounds (+margin) ----
if gpu_pkg:
    bx = gpu_pkg["bbox"]
    xmin, ymin, zmin, xmax, ymax, zmax = bx
    xmin -= GPU_XY_MARGIN; ymin -= GPU_XY_MARGIN
    xmax += GPU_XY_MARGIN; ymax += GPU_XY_MARGIN

    subs = []
    for d in info:
        if d["name"] in ["FR4_base"] or d["name"].startswith("FR4_") \
           or d["name"].startswith("Copper_") or d["name"] == "GPU_Package":
            continue
        cx, cy, _ = d["ctr"]
        if (xmin <= cx <= xmax) and (ymin <= cy <= ymax):
            subs.append(d)

    subs = sorted(subs, key=lambda d: -d["vol"])
    i = 1
    for d in subs:
        if rename_safe(d["name"], "GPU_Sub_{0}".format(seq2(i))): renamed += 1
        i += 1

# ---- remaining parts ----
used = set()
for s in oEditor.GetObjectsInGroup("Solids"):
    used.add(s)
# names we already assigned (fetch again from tree is safer)
assigned = set(["FR4_base"])
assigned.update([n for n in used if str(n).startswith(("FR4_extra_", "Copper_", "GPU_Sub_"))])
assigned.add("GPU_Package")

others = [d for d in info if d["name"] not in assigned]
i = 1
for d in sorted(others, key=lambda d: -d["vol"]):
    if rename_safe(d["name"], "Imported_{0}".format(seq2(i))): renamed += 1
    i += 1

print "[DONE] Renamed {0} solids with improved GPU detection.".format(renamed)
