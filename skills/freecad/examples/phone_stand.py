# Phone or tablet stand: a leaning backrest, a front lip and two side braces.
# Axes: X runs front to back, Y across the device, Z up.

# --- Device ---
device_width = 80.0      # [50:200] Width of the phone or tablet, mm
device_thickness = 12.0  # [6:20] Thickness including any case, mm

# --- Stand ---
stand_angle = 65.0       # [45:85] Backrest tilt measured from the table, degrees
stand_depth = 80.0       # [50:150] Length of the base, front to back, mm
stand_height = 100.0     # [60:200] Length of the backrest, mm

# --- Build ---
material_thickness = 4.0  # [2:0.5:8] Plate thickness, mm
slot_depth = 15.0         # [10:30] Room in front of the device for its bottom edge, mm

# --- Extras ---
cable_hole = True        # Hole in the slot floor for a charging cable
cable_diameter = 15.0    # [8:25] Size of the cable hole, mm
add_feet = True          # Small feet under the base


def _prism(points_xz, y0, length):
    """Extrude a closed XZ polygon along +Y."""
    import FreeCAD as App
    import Part

    pts = [App.Vector(x, y0, z) for x, z in points_xz]
    face = Part.Face(Part.makePolygon(pts + [pts[0]]))
    return face.extrude(App.Vector(0, length, 0))


def build():
    import math
    import FreeCAD as App
    import Part

    t, w = material_thickness, device_width
    a = math.radians(stand_angle)
    lip_h = t + slot_depth * math.tan(math.radians(90 - stand_angle))
    x0 = t + slot_depth + device_thickness          # where the back support meets the base
    foot = t / math.sin(a)                           # flat bottom width of the leaning support
    run, rise = stand_height * math.cos(a), stand_height * math.sin(a)

    base = Part.makeBox(stand_depth, w, t)
    lip = Part.makeBox(t, w, lip_h)
    support = _prism([(x0, t), (x0 + foot, t), (x0 + foot + run, t + rise), (x0 + run, t + rise)], 0, w)
    g_run, g_rise = 0.6 * run, 0.6 * rise
    gusset = [(x0 + foot, t), (x0 + foot + g_run, t), (x0 + foot + g_run, t + g_rise)]
    side_l = _prism(gusset, 0, t)
    side_r = _prism(gusset, w - t, t)

    stand = base.fuse([lip, support, side_l, side_r])
    if cable_hole:
        hole = Part.makeCylinder(cable_diameter / 2, t + 2, App.Vector((t + x0) / 2, w / 2, -1))
        stand = stand.cut(hole)
    if add_feet:
        for x in (10.0, stand_depth - 10.0):
            for y in (10.0, w - 10.0):
                stand = stand.fuse(Part.makeCone(5, 4, 2, App.Vector(x, y, -2), App.Vector(0, 0, 1)))
    stand = stand.removeSplitter()
    stand.translate(App.Vector(0, 0, -stand.BoundBox.ZMin))  # sit on the print bed
    if run + foot + x0 > stand_depth:
        print("note: the back support overhangs the base; increase stand_depth or stand_angle")
    return stand
