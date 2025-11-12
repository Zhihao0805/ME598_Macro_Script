# -*- coding: utf-8 -*-
# ============================================================
# Icepak Macro (IronPython 2.7)
# Rename imported solids by their parent-group prefix.
# Works for imported STEP trees like: OpenCASCADESTEPtranslator8/9/10...
# ============================================================

import ScriptEnv
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")

oProject = oDesktop.GetActiveProject()
oDesign  = oProject.GetActiveDesign()
oEditor  = oDesign.SetActiveEditor("3D Modeler")

# ---------- User mapping: parent node name -> new name prefix ----------
# Keys must match the parent names in the Model tree.
PARENT_PREFIX_MAP = {
    "OpenCASCADESTEPtranslator8":  "PCB",
    "OpenCASCADESTEPtranslator9":  "Heatsink",
    "OpenCASCADESTEPtranslator10": "ColdPlate",
}
# ----------------------------------------------------------------------

def get_children(parent_name):
    """Return a list of direct children under a parent node."""
    try:
        return list(oEditor.GetChildObject(parent_name))
    except:
        return []

def rename_safe(old_name, new_name):
    """Rename object; fall back to ChangeProperty if RenameObject is unavailable."""
    if not old_name or old_name == new_name:
        return False
    try:
        # Some ICEPAK builds have RenameObject; try it first.
        oEditor.RenameObject(old_name, new_name)
        print "[OK] {0} -> {1}".format(old_name, new_name)
        return True
    except:
        pass
    # Fallback path (most stable across versions)
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
    """Return 2-digit zero-padded counter as string."""
    return "%02d" % n

total = 0
# iteritems() is faster/more Py2-native than items()
for parent, prefix in PARENT_PREFIX_MAP.iteritems():
    children = get_children(parent)
    if not children:
        print "[INFO] No children under {0}".format(parent)
        continue
    # Python 2.7 supports enumerate with start, but we keep it explicit for portability
    idx = 1
    for ch in children:
        new_name = "{0}_{1}".format(prefix, seq2(idx))
        if rename_safe(ch, new_name):
            total += 1
        idx += 1

print "[DONE] Renamed {0} solids by parent prefix mapping.".format(total)
