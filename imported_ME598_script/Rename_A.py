# -*- coding: utf-8 -*-
# ============================================================
# Icepak Macro: Rename Imported Solids by Parent Group Prefix
# ------------------------------------------------------------
# 用于将从 STEP 导入的多个 OpenCASCADESTEPtranslator# 节点
# 按其父节点名称自动加前缀重命名。
# 适用于结构：OpenCASCADESTEPtranslator8/9/10 ...
# ============================================================

import ScriptEnv
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")

oProject = oDesktop.GetActiveProject()
oDesign  = oProject.GetActiveDesign()
oEditor  = oDesign.SetActiveEditor("3D Modeler")

# ========== 用户自定义映射表 ==========
# 左边是 Model 树中父节点名称；
# 右边是希望赋予该组几何体的前缀名称。
PARENT_PREFIX_MAP = {
    "OpenCASCADESTEPtranslator8": "PCB",
    "OpenCASCADESTEPtranslator9": "Heatsink",
    "OpenCASCADESTEPtranslator10": "ColdPlate",
}
# ======================================

def get_child_objects(parent_name):
    try:
        return list(oEditor.GetChildObject(parent_name))
    except:
        return []

def rename(old_name, new_name):
    if old_name == new_name:
        return
    try:
        oEditor.RenameObject(old_name, new_name)
        print(f"[OK] {old_name} -> {new_name}")
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
        except:
            print(f"[WARN] Rename failed for {old_name}")

def seq_label(n): return f"{n:02d}"

total = 0
for parent, prefix in PARENT_PREFIX_MAP.items():
    children = get_child_objects(parent)
    if not children:
        continue
    for i, ch in enumerate(children, start=1):
        new_name = f"{prefix}_{seq_label(i)}"
        rename(ch, new_name)
        total += 1

print(f"[DONE] Renamed {total} solids by parent prefix mapping.")
