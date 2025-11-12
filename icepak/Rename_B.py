# -*- coding: utf-8 -*-
# ============================================================
# Icepak Macro (IronPython 2.7)
# Rename solids by geometry heuristics (thickness/volume).
# Useful when the import has no clear parent grouping.
# Heuristics assume mm model units.
# ============================================================

import ScriptEnv
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")

oProject = oDesktop.GetActiveProject()
oDesign  = oProject.GetActiveDesign()
oEditor  = oDesign.SetActiveEditor("3D Modeler")

# -------- Heuristic thresholds (in mm) --------
HEU_FR4_THICK_RANGE   = (1.2, 2.2)    # Typical FR4 thickness around 1.6 mm
HEU_GPU_PKG_THICK_RG  = (2.0, 5.0)    # Typical GPU package thickness
HEU_CU_SHEET_THICK_RG = (0.02, 0.15)  # Typical copper layer thickness
# ---------------------------------------------

def get_bbox(name):
    """Get bounding box (xmin, ymin, zmin, xmax, ymax, zmax) as floats."""
    try:
        b = oEditor.GetObjectBoundingBox(name)
        return (float(b[0]), float(b[1]), float(b[2]),
                float(b[3]), float(b[4]), float(b[5]))
    except:
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

def bbox_sizes(b):
    """Return (dx, dy, dz) in mm."""
    return (abs(b[3] - b[0]), abs(b[4] - b[1]), abs(b[5] - b[2]))

def bbox_vol(b):
    """Return volume proxy (dx*dy*dz)."""
    dx, dy, dz = bbox_sizes(b)
    return dx * dy * dz

def rename_safe(old_name, new_name):
    """Rename with fallback path."""
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

def seq2(n):
    return "%02d" % n

# Collect all solid bodies in the design
try:
    solids = list(oEditor.GetObjectsInGroup("Solids"))
except:
    solids = []

# Buckets
fr4, gpu, copper, others = [], [], [], []

# Classify by thickness heuristic (min of dx, dy, dz)
for s in solids:
    b = get_bbox(s)
    dx, dy, dz = bbox_sizes(b)
    tmin = min(dx, dy, dz)

    if HEU_FR4_THICK_RANGE[0] <= tmin <= HEU_FR4_THICK_RANGE[1]:
        fr4.append((s, b))
    elif HEU_GPU_PKG_THICK_RG[0] <= tmin <= HEU_GPU_PKG_THICK_RG[1]:
        gpu.append((s, b))
    elif HEU_CU_SHEET_THICK_RG[0] <= tmin <= HEU_CU_SHEET_THICK_RG[1]:
        copper.append((s, b))
    else:
        others.append((s, b))

renamed = 0

# FR4: largest volume as base
if fr4:
    fr4_sorted = sorted(fr4, key=lambda t: -bbox_vol(t[1]))
    if rename_safe(fr4_sorted[0][0], "FR4_base"):
        renamed += 1
    i = 1
    for s, _ in fr4_sorted[1:]:
        if rename_safe(s, "FR4_extra_{0}".format(seq2(i))):
            renamed += 1
        i += 1

# GPU package: largest volume as GPU_Package
if gpu:
    gpu_sorted = sorted(gpu, key=lambda t: -bbox_vol(t[1]))
    if rename_safe(gpu_sorted[0][0], "GPU_Package"):
        renamed += 1
    i = 1
    for s, _ in gpu_sorted[1:]:
        if rename_safe(s, "GPU_Sub_{0}".format(seq2(i))):
            renamed += 1
        i += 1

# Copper sheets
i = 1
for s, _ in sorted(copper, key=lambda t: -bbox_vol(t[1])):
    if rename_safe(s, "Copper_{0}".format(seq2(i))):
        renamed += 1
    i += 1

# Others
i = 1
for s, _ in sorted(others, key=lambda t: -bbox_vol(t[1])):
    if rename_safe(s, "Imported_{0}".format(seq2(i))):
        renamed += 1
    i += 1

print "[DONE] Renamed {0} solids by geometry heuristics.".format(renamed)
