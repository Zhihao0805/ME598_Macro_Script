# -*- coding: utf-8 -*-
# ============================================================
# Icepak Macro: Rename Solids by Geometry Heuristics
# ------------------------------------------------------------
# 自动分析几何厚度/体积，将实体命名为 FR4_base、GPU_Package、
# Copper_xx 等。适合没有明显父节点结构的导入模型。
# ============================================================

import math
import ScriptEnv
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")

oProject = oDesktop.GetActiveProject()
oDesign  = oProject.GetActiveDesign()
oEditor  = oDesign.SetActiveEditor("3D Modeler")

# ===== 启发式判定参数 (mm) =====
HEU_FR4_THICK_RANGE   = (1.2, 2.2)    # FR4 常见厚度 1.6 mm
HEU_GPU_PKG_THICK_RG  = (2.0, 5.0)    # GPU 封装厚度
HEU_CU_SHEET_THICK_RG = (0.02, 0.15)  # 铜层厚度
# =================================

def get_bbox(obj):
    try:
        b = oEditor.GetObjectBoundingBox(obj)
        return tuple(float(v) for v in b)
    except:
        return (0,0,0,0,0,0)

def bbox_sizes(b):
    dx = abs(b[3]-b[0]); dy = abs(b[4]-b[1]); dz = abs(b[5]-b[2])
    return dx, dy, dz

def bbox_vol(b):
    dx, dy, dz = bbox_sizes(b)
    return dx*dy*dz

def rename(old_name, new_name):
    if old_name == new_name: return True
    try:
        oEditor.RenameObject(old_name, new_name)
        print(f"[OK] {old_name} -> {new_name}")
        return True
    except:
        try:
            oEditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Geometry3DAttributeTab",
                        ["NAME:PropServers", old_name],
                        ["NAME:ChangedProps", ["NAME:Name", "Value:=", new_name]]
                    ]
                ]
            )
            print(f"[OK] {old_name} -> {new_name}")
            return True
        except:
            print(f"[WARN] Rename failed for {old_name}")
            return False

def seq_label(n): return f"{n:02d}"

solids = list(oEditor.GetObjectsInGroup("Solids"))

# 分类容器
fr4, gpu, copper, others = [], [], [], []

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
# FR4：体积最大者为 FR4_base
if fr4:
    fr4_sorted = sorted(fr4, key=lambda t: -bbox_vol(t[1]))
    if rename(fr4_sorted[0][0], "FR4_base"): renamed += 1
    for i, (s, _) in enumerate(fr4_sorted[1:], start=1):
        if rename(s, f"FR4_extra_{seq_label(i)}"): renamed += 1

# GPU Package
if gpu:
    gpu_sorted = sorted(gpu, key=lambda t: -bbox_vol(t[1]))
    if rename(gpu_sorted[0][0], "GPU_Package"): renamed += 1
    for i, (s, _) in enumerate(gpu_sorted[1:], start=1):
        if rename(s, f"GPU_Sub_{seq_label(i)}"): renamed += 1

# Copper sheets
for i, (s, _) in enumerate(sorted(copper, key=lambda t: -bbox_vol(t[1])), start=1):
    if rename(s, f"Copper_{seq_label(i)}"): renamed += 1

# Others
for i, (s, _) in enumerate(sorted(others, key=lambda t: -bbox_vol(t[1])), start=1):
    if rename(s, f"Imported_{seq_label(i)}"): renamed += 1

print(f"[DONE] Renamed {renamed} solids by geometry heuristics.")
