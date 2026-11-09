# Storage box with a press-fit lid, laid out side by side for printing.

# --- Box ---
width = 60.0             # [20:200] Outside size along X, mm
depth = 40.0             # [20:200] Outside size along Y, mm
height = 30.0            # [10:150] Outside height, mm
wall_thickness = 2.0     # [1:0.5:5] Thickness of the walls and floor, mm

# --- Lid ---
include_lid = True       # Print a lid next to the box
lid_height = 8.0         # [5:30] Lid height including the lip, mm
lid_tolerance = 0.3      # [0.1:0.1:0.8] Play between the lip and the box wall, mm

# --- Style ---
corner_radius = 3.0      # [0:10] Rounding of the upright corners, mm
add_grip = True          # Finger notches along the lid edge


def rounded_block(w, d, h, r, x=0.0, y=0.0, z=0.0):
    """A w x d x h block at (x, y, z) whose four upright edges are rounded to r."""
    import FreeCAD as App
    import Part

    block = Part.makeBox(w, d, h, App.Vector(x, y, z))
    r = min(r, min(w, d) / 2.0 - 0.01)
    if r <= 0:
        return block
    upright = [e for e in block.Edges
               if abs(e.Vertexes[0].X - e.Vertexes[1].X) < 1e-9
               and abs(e.Vertexes[0].Y - e.Vertexes[1].Y) < 1e-9]
    return block.makeFillet(r, upright)


def make_box():
    t = wall_thickness
    outside = rounded_block(width, depth, height, corner_radius)
    cavity = rounded_block(width - 2 * t, depth - 2 * t, height, max(0.0, corner_radius - t),
                           t, t, t)  # taller than the box, so the top stays open
    return outside.cut(cavity)


def make_lid():
    import FreeCAD as App
    import Part

    t, play = wall_thickness, lid_tolerance
    lip = lid_height * 0.6
    plate = rounded_block(width, depth, t, corner_radius)
    plug = rounded_block(width - 2 * (t + play), depth - 2 * (t + play), lip,
                         max(0.0, corner_radius - t), t + play, t + play, t - lip)
    lid = plate.fuse(plug)
    if add_grip:
        for x in (width * 0.3, width * 0.7):
            for y in (-1.0, depth - 4.0):
                notch = Part.makeCylinder(3, 5, App.Vector(x, y, t / 2), App.Vector(0, 1, 0))
                lid = lid.cut(notch)
    return lid.removeSplitter()


def build():
    import FreeCAD as App

    parts = [make_box()]
    if include_lid:
        lid = make_lid()
        # Turn the lid over so its flat top prints on the bed, then set it beside the box.
        lid.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 180)
        bb = lid.BoundBox
        lid.translate(App.Vector(width + 10 - bb.XMin, -bb.YMin, -bb.ZMin))
        parts.append(lid)
    return parts
