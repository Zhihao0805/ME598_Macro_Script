# -*- coding: utf-8 -*-
# IronPython macro for AEDT/Icepak: Rename solids by simple geometry heuristics (Python 2.7 syntax)

import ScriptEnv
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")

try:
    oDesktop = ScriptEnv.GetDesktop()
except:
    pass

oProject = oDesktop.GetActiveProject()
oDesign  = oProject.GetActiveDesign()
oEditor  = oDesign.SetActiveEditor("3D Modeler")

# ======= 参数（单位：mm；STEP 常为 mm）=======
HEU_FR4_THICK_RANGE   = (1.2, 2.2)    # FR4 常见 ~1.6 mm
HEU_GPU_PKG_THICK_RG  = (2.0, 5.0)    # GPU 封装厚度几毫米
HEU_CU_SHEET_THICK_RG = (0.02, 0.15)  # 铜箔 20~150 μm
# ===========================================

def get_bbox(obj):
    # 返回 (xmin, ymin, zmin, xmax, ymax, zmax) -> float
    try:
        b = oEditor.GetObjectBoundingBox(obj)
        # IronPython 返回的是字符串，需要转 float
        return (float(b[0]), float(b[1]), float(b[2]),
                float(b[3]), float(b[4]), float(b[5]))
    except:
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

def sizes_from_bbox(b):
    dx = abs(b[3] - b[0])
    dy = abs(b[4] - b[1])
    dz = abs(b[5] - b[2])
    return (dx, dy, dz)

def vol_from_bbox(b):
    s = sizes_from_bbox(b)
    return s[0] * s[1] * s[2]

def rename_obj(old_name, new_name):
    if old_name == new_name:
        return True
    try:
        oEditor.RenameObject(old_name, new_name)
        print("[OK] " + old_name + " -> " + new_name)
        return True
    except:
        try:
            oEditor.ChangeProperty([
                "NAME:AllTabs",
                [
                    "NAME:Geometry3DAttributeTab",
                    ["NAME:PropServers", old_name],
                    ["NAME:ChangedProps", ["NAME:Name", "Value:=", new_name]]
                ]
            ])
            print("[OK] " + old_name + " -> " + new_name)
            return True
        except:
            print("[WARN] Rename failed: " + old_name)
            return False

def seq2(n):
    return ("%02d" % n)

# 收集所有实体
solids = list(oEditor.GetObjectsInGroup("Solids"))

fr4_list   = []  # (name, bbox)
gpu_list   = []
copper_list= []
others     = []

for s in solids:
    b = get_bbox(s)
    dx, dy, dz = sizes_from_bbox(b)
    tmin = min(dx, dy, dz)

    if HEU_FR4_THICK_RANGE[0] <= tmin <= HEU_FR4_THICK_RANGE[1]:
        fr4_list.append((s, b))
    elif HEU_GPU_PKG_THICK_RG[0] <= tmin <= HEU_GPU_PKG_THICK_RG[1]:
        gpu_list.append((s, b))
    elif HEU_CU_SHEET_THICK_RG[0] <= tmin <= HEU_CU_SHEET_THICK_RG[1]:
        copper_list.append((s, b))
    else:
        others.append((s, b))

renamed = 0

# FR4：体积最大者作为 FR4_base
if len(fr4_list) > 0:
    fr4_list_sorted = sorted(fr4_list, key=lambda t: -vol_from_bbox(t[1]))
    if rename_obj(fr4_list_sorted[0][0], "FR4_base"):
        renamed += 1
    i = 1
    for item in fr4_list_sorted[1:]:
        if rename_obj(item[0], "FR4_extra_" + seq2(i)):
            renamed += 1
        i += 1

# GPU Package：体积最大者为 GPU_Package
if len(gpu_list) > 0:
    gpu_sorted = sorted(gpu_list, key=lambda t: -vol_from_bbox(t[1]))
    if rename_obj(gpu_sorted[0][0], "GPU_Package"):
        renamed += 1
    i = 1
    for item in gpu_sorted[1:]:
        if rename_obj(item[0], "GPU_Sub_" + seq2(i)):
            renamed += 1
        i += 1

# 铜片/铜箔
i = 1
for item in sorted(copper_list, key=lambda t: -vol_from_bbox(t[1])):
    if rename_obj(item[0], "Copper_" + seq2(i)):
        renamed += 1
    i += 1

# 其他：统一 Imported_##
i = 1
for item in sorted(others, key=lambda t: -vol_from_bbox(t[1])):
    if rename_obj(item[0], "Imported_" + seq2(i)):
        renamed += 1
    i += 1

print("[DONE] Renamed %d solids by geometry heuristics." % renamed)

