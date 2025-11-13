# -*- coding: utf-8 -*-
# ============================================================
# FreeCAD Macro: Rubin-like GPU PCB + Main Conductive Paths
# Thickened version for Icepak finite-volume stability
# Includes ONLY 8 thermal vias (grid removed)
#
# Usage:
#   1) Place this file in your FreeCAD Macro directory.
#   2) FreeCAD → Macro → Macros… → Select this macro → Execute.
#   3) STEP files will be exported automatically.
#
# Output:
#   pcb_base.step
#   gpu_pkg_and_heat_sources.step
#   copper_paths_thickened.step
#
# Author: Zhihao Jin (UIUC), Engineering Workflow with ChatGPT
# ============================================================

import os
import math

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:
    import FreeCAD as App
    Gui = None

import Part


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

def mm(val):
    """Convert to float mm."""
    return float(val)

def frange(start, stop, step):
    """Floating-point range generator."""
    vals = []
    x = float(start)
    if step == 0:
        return vals
    if step > 0:
        while x <= stop + 1e-9:
            vals.append(round(x, 6))
            x += step
    else:
        while x >= stop - 1e-9:
            vals.append(round(x, 6))
            x += step
    return vals

def ensure_doc(name="Rubin_PCB_Model_Thick"):
    """Create new FreeCAD document."""
    doc = App.newDocument(name)
    if Gui:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
    return doc

def add_box(doc, name, L, W, T, center=(0,0,0)):
    """Create a solid box centered at (x,y,z)."""
    x, y, z = center
    box = Part.makeBox(mm(L), mm(W), mm(T))
    # Move from corner to center-based placement
    box.translate(App.Vector(mm(x - L/2.0), mm(y - W/2.0), mm(z)))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = box
    return obj

def add_cylinder(doc, name, d, h, axis="Z", center=(0,0,0)):
    """Create a cylinder as a solid (vias or mounting holes)."""
    r = mm(d/2.0)

    if axis.upper() == "Z":
        cyl = Part.makeCylinder(r, mm(h))
        x, y, z = center
        cyl.translate(App.Vector(mm(x), mm(y), mm(z)))

    elif axis.upper() == "X":
        cyl = Part.makeCylinder(
            r, mm(h),
            App.Vector(mm(center[0]), mm(center[1]), mm(center[2])),
            App.Vector(1,0,0)
        )

    elif axis.upper() == "Y":
        cyl = Part.makeCylinder(
            r, mm(h),
            App.Vector(mm(center[0]), mm(center[1]), mm(center[2])),
            App.Vector(0,1,0)
        )

    else:
        raise ValueError("axis must be X/Y/Z")

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = cyl
    return obj

def bool_cut(doc, name, base_obj, tool_obj):
    """Subtract tool_obj from base_obj."""
    cut_shape = base_obj.Shape.cut(tool_obj.Shape)
    res = doc.addObject("Part::Feature", name)
    res.Shape = cut_shape
    base_obj.Visibility = False
    tool_obj.Visibility = False
    return res

def export_step(objs, out_path):
    """Export objects as STEP file."""
    try:
        Part.export(objs, out_path)
        App.Console.PrintMessage(f"Exported STEP: {out_path}\n")
    except Exception as e:
        App.Console.PrintError(f"STEP export failed for {out_path}: {e}\n")

def get_export_folder(doc, default_folder=""):
    """Determine export folder."""
    folder = default_folder.strip()
    if folder:
        return folder
    if doc.FileName:
        return os.path.dirname(doc.FileName)
    return os.path.expanduser("~")


# ------------------------------------------------------------
# PARAMETER DEFINITIONS (edit these as needed)
# ------------------------------------------------------------

PARAMS = {
    # PCB dimensions (mm)
    "L_board": 260.0,
    "W_board": 100.0,
    "t_board": 1.6,

    # Thickened copper layers (for Icepak mesh stability)
    "t_cu_top": 0.3,
    "t_cu_bot": 0.3,

    # GPU package
    "gpu_pkg_size": 58.0,
    "gpu_pkg_height": 3.0,

    # Heating elements (3×2)
    "heat_nx": 3,
    "heat_ny": 2,
    "heat_w": 9.5,
    "heat_h": 14.0,
    "heat_gap": 1.0,
    "heat_thickness": 0.5,

    # Copper path widths (mm)
    "vdd_core_width": 6.0,
    "vdd_aux_width": 4.0,
    "gnd_ring_width": 8.0,
    "mem_bus_width": 2.5,
    "thermal_bridge_width": 3.0,

    # Margins
    "edge_clearance": 3.0,
    "mount_edge_offset": 7.5,

    # Mounting hole diameter
    "mount_hole_diam": 3.4,

    # Thermal-via diameter
    "via_d": 0.6,

    # Export
    "export_folder": r"C:\Users\jzh_0\Desktop\ME598_script\ME598_Macro_Script\FreeCAD_results",
}


# ------------------------------------------------------------
# MODEL CONSTRUCTION
# ------------------------------------------------------------

doc = ensure_doc()
p = PARAMS

L = p["L_board"]; W = p["W_board"]; T = p["t_board"]


# -----------------------------
# 1) FR-4 PCB Base
# -----------------------------
pcb = add_box(doc, "FR4_base", L, W, T, center=(0,0,0))


# -----------------------------
# 2) Mounting Holes
# -----------------------------
mh = p["mount_hole_diam"]
off = p["mount_edge_offset"]

hole_coords = [
    ( L/2 - off,  W/2 - off),
    ( L/2 - off, -W/2 + off),
    (-L/2 + off,  W/2 - off),
    (-L/2 + off, -W/2 + off),
    ( L/4,  W/2 - off),
    ( L/4, -W/2 + off),
    (-L/4,  W/2 - off),
    (-L/4, -W/2 + off),
]

hole_objs = []
for i, (cx, cy) in enumerate(hole_coords):
    cyl = add_cylinder(doc, f"MountHole_{i+1}", mh, T+0.1,
                       axis="Z", center=(cx, cy, -0.05))
    hole_objs.append(cyl)

cut_base = pcb
for i, ho in enumerate(hole_objs):
    cut_base = bool_cut(doc, f"FR4_base_cut_{i+1}", cut_base, ho)
pcb = cut_base


# -----------------------------
# 3) GPU Package
# -----------------------------
pkg = add_box(
    doc, "GPU_Package",
    p["gpu_pkg_size"], p["gpu_pkg_size"], p["gpu_pkg_height"],
    center=(0,0,T)
)


# -----------------------------
# 4) Heating Elements (3 × 2)
# -----------------------------
nx, ny = p["heat_nx"], p["heat_ny"]
hw, hh = p["heat_w"], p["heat_h"]
gap = p["heat_gap"]

total_w = nx*hw + (nx-1)*gap
total_h = ny*hh + (ny-1)*gap

x0 = -total_w/2 + hw/2
y0 = -total_h/2 + hh/2

heat_objs = []
for iy in range(ny):
    for ix in range(nx):
        cx = x0 + ix*(hw+gap)
        cy = y0 + iy*(hh+gap)
        h_block = add_box(
            doc, f"Heat_{iy*nx+ix+1}",
            hw, hh, p["heat_thickness"],
            center=(cx, cy, T + p["gpu_pkg_height"])
        )
        heat_objs.append(h_block)


# -----------------------------
# 5) Top Copper Paths (Thickened)
# -----------------------------
t_cu = p["t_cu_top"]
edge = p["edge_clearance"]
ring_w = p["gnd_ring_width"]

copper_objs = []

# 5.1 VDD core path
vdd_len = (L/2 - edge) - (-p["gpu_pkg_size"]/2)
vdd_core = add_box(
    doc, "Copper_VDD_core",
    vdd_len, p["vdd_core_width"], t_cu,
    center=(( (L/2-edge) + (-p["gpu_pkg_size"]/2) )/2,
           -p["gpu_pkg_size"]/2 - p["vdd_core_width"]/2,
           T + p["gpu_pkg_height"])
)
copper_objs.append(vdd_core)

# 5.2 VDD auxiliary
vdd_aux_len = (L/2 - edge) - (p["gpu_pkg_size"]/2)
vdd_aux = add_box(
    doc, "Copper_VDD_aux",
    vdd_aux_len, p["vdd_aux_width"], t_cu,
    center=(( (L/2-edge) + (p["gpu_pkg_size"]/2) )/2,
           0.0,
           T + p["gpu_pkg_height"])
)
copper_objs.append(vdd_aux)

# 5.3 MEM / IO bus
mem_len = (p["gpu_pkg_size"]/2) - (-L/2 + edge)
mem_bus = add_box(
    doc, "Copper_MEM_bus",
    mem_len, p["mem_bus_width"], t_cu,
    center=(( (-L/2+edge) + (p["gpu_pkg_size"]/2) )/2,
           p["gpu_pkg_size"]/2 + p["mem_bus_width"]/2,
           T + p["gpu_pkg_height"])
)
copper_objs.append(mem_bus)

# 5.4 Thermal bridges (L/R)
tb_w = p["thermal_bridge_width"]
tb_len = p["gpu_pkg_size"]

tb_L = add_box(
    doc, "Copper_ThermalBridge_L",
    tb_len, tb_w, t_cu,
    center=(0.0,
            -p["gpu_pkg_size"]/2 - 2*tb_w,
            T + p["gpu_pkg_height"])
)
tb_R = add_box(
    doc, "Copper_ThermalBridge_R",
    tb_len, tb_w, t_cu,
    center=(0.0,
            p["gpu_pkg_size"]/2 + 2*tb_w,
            T + p["gpu_pkg_height"])
)
copper_objs.extend([tb_L, tb_R])

# 5.5 GND ring (top)
outer = p["gpu_pkg_size"] + 2*ring_w

g_top = add_box(
    doc, "Copper_GND_ring_Top",
    outer, ring_w, t_cu,
    center=(0.0,
            p["gpu_pkg_size"]/2 + ring_w/2,
            T + p["gpu_pkg_height"])
)

g_bot = add_box(
    doc, "Copper_GND_ring_Bot",
    outer, ring_w, t_cu,
    center=(0.0,
            -p["gpu_pkg_size"]/2 - ring_w/2,
            T + p["gpu_pkg_height"])
)

g_left = add_box(
    doc, "Copper_GND_ring_Left",
    ring_w, outer, t_cu,
    center=(-p["gpu_pkg_size"]/2 - ring_w/2,
           0.0,
           T + p["gpu_pkg_height"])
)

g_right = add_box(
    doc, "Copper_GND_ring_Right",
    ring_w, outer, t_cu,
    center=(p["gpu_pkg_size"]/2 + ring_w/2,
           0.0,
           T + p["gpu_pkg_height"])
)

copper_objs.extend([g_top, g_bot, g_left, g_right])


# -----------------------------
# 6) Bottom Copper Plane
# -----------------------------
bot_cu = add_box(
    doc, "Copper_GND_Plane_Bot",
    L - 2*edge, W - 2*edge, p["t_cu_bot"],
    center=(0, 0, 0)
)
copper_objs.append(bot_cu)


# -----------------------------
# 7) **Only 8 Thermal Vias**
# -----------------------------
via_objs = []

via_d = p["via_d"]
x_off = p["gpu_pkg_size"]/2 - 5.0
y_off = p["gpu_pkg_size"]/2 - 5.0

via_positions = [
    ( x_off,  y_off),   # Top-right
    (-x_off,  y_off),   # Top-left
    ( x_off, -y_off),   # Bottom-right
    (-x_off, -y_off),   # Bottom-left
    ( 0.0,    y_off),   # Mid-top
    ( 0.0,   -y_off),   # Mid-bottom
    ( x_off,  0.0),     # Mid-right
    (-x_off,  0.0),     # Mid-left
]

z_via = -0.05
via_h = T + p["gpu_pkg_height"] + t_cu + 0.1

for i, (vx, vy) in enumerate(via_positions):
    v = add_cylinder(
        doc,
        name=f"Via_{i+1}",
        d=via_d,
        h=via_h,
        axis="Z",
        center=(vx, vy, z_via)
    )
    via_objs.append(v)


# ------------------------------------------------------------
# EXPORT STEP FILES
# ------------------------------------------------------------

export_dir = get_export_folder(doc, p["export_folder"])
try:
    os.makedirs(export_dir, exist_ok=True)
except Exception:
    pass

export_step([pcb], os.path.join(export_dir, "pcb_base.step"))
export_step([pkg] + heat_objs, os.path.join(export_dir, "gpu_pkg_and_heat_sources.step"))
export_step(copper_objs + via_objs, os.path.join(export_dir, "copper_paths_thickened.step"))

if Gui:
    Gui.ActiveDocument.ActiveView.fitAll()
    App.Console.PrintMessage("Thickened model with 8 thermal vias exported.\n")
