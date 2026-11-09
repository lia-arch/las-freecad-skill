---
name: freecad
description: "Design 3D-printable parts as parametric FreeCAD Python scripts and run them headless: build-check the solid, render six preview images, list the tunable parameters, and export STL, 3MF, OBJ or STEP. Use when someone wants a part, bracket, box, holder, adapter or any printable object designed or modified."
---

# FreeCAD parts for 3D printing

You describe a part, Claude writes it as a small Python script, and FreeCAD builds it in the
background with `freecadcmd`. No FreeCAD window is opened at any point.

## Setup

- FreeCAD 1.0 or newer: https://www.freecad.org/downloads.php
- The scripts look for `freecadcmd` on PATH, then in `/Applications/FreeCAD.app`.
  If it lives somewhere else, set `FREECADCMD=/full/path/to/freecadcmd`.
- Preview images are drawn with the matplotlib copy that ships inside FreeCAD. No other
  installs are needed.
- A model script is real Python and runs as the current user. Run only scripts you wrote
  or have read.

## The loop: write, check, look, export

Every part goes through four steps, in this order, each time it changes.

1. **Write** `part.py` (format below).
2. **Check** that it builds into a closed, valid solid:
   `tools/validate.sh part.py`. Fix every line that says `PROBLEM`.
3. **Look** at it: `tools/multi-preview.sh part.py previews/` writes six images
   (iso, front, back, left, right, top). Open each one with the read tool.
   Passing the check only proves the solid is closed. It does not prove it is the part
   that was asked for. The pictures catch the rest: a hole on the wrong face, a lid
   floating above the bed, a cut that took away too much, a size that is off. Each image
   header prints the overall size in millimetres, so compare it with the request.
4. **Export** for the slicer: `tools/export.sh part.py part.3mf`.

Do not hand over a part whose images you have not looked at.

## Model file format

Parameters go at the top as plain `name = value` lines (`name: float = value` works too).
A `build()` function returns the finished shape. Returning a list puts several parts in one
export file; place them apart yourself so they do not overlap.

```python
# Cable clip
cable_diameter = 6.0   # [3:12] Cable thickness in mm
clip_width = 10.0      # [6:20] Width of the clip in mm
screw_hole = True      # Add a mounting hole under the cable

def build():
    import FreeCAD as App
    import Part
    r, base, wall = cable_diameter / 2, 3.0, 1.5
    cx, cz = r + 3, base + r                        # centre of the cable channel
    body = Part.makeBox(2 * r + 6, clip_width, base + 2 * r + wall)
    channel = Part.makeCylinder(r, clip_width, App.Vector(cx, 0, cz), App.Vector(0, 1, 0))
    gap = 1.5 * r                                   # narrower than the cable, so it snaps in
    slot = Part.makeBox(gap, clip_width, r + wall, App.Vector(cx - gap / 2, 0, cz))
    clip = body.cut(channel).cut(slot)
    if screw_hole:
        # cut a little past both faces of the floor, so no paper-thin skin is left behind
        clip = clip.cut(Part.makeCylinder(1.6, base + 1, App.Vector(cx, clip_width / 2, -0.5)))
    return clip
```

- A comment after a parameter can give limits or choices: `# [min:max]`,
  `# [min:step:max]`, `# [choice1, choice2]`, or just a description.
- Only literal values count as parameters: numbers, `True`/`False`, text, lists.
  Start a name with `_` to keep it out of the list.
- Millimetres throughout, Z pointing up. Model the part in the orientation it prints in,
  resting on Z = 0.
- `extract-params.sh` reads these lines without running your code, so keep parameter values
  plain literals: no arithmetic, no function calls.
- When cutting holes or slots, make the cutter overshoot the faces it passes through.
  A cut that ends exactly on a face leaves a zero-thickness skin that fails export.
- Worked examples: `examples/parametric_box.py`, `examples/phone_stand.py`.

## Commands

| Command | Result |
|---|---|
| `tools/validate.sh part.py` | Builds it and reports size, volume and solid count. Exits 1 on a problem. |
| `tools/multi-preview.sh part.py out/` | Writes `out/<name>_<view>.png` for six views |
| `tools/preview.sh part.py view.png --view top` | One image. Views: iso, front, back, left, right, top, bottom. `--size 1200x900` |
| `tools/extract-params.sh part.py [--json]` | Lists parameters straight from the file, without running it |
| `tools/export.sh part.py out.stl` | `.stl`, `.3mf` or `.obj` meshes. `.step`, `.stp` or `.brep` for other CAD programs. |
| `tools/render-with-params.sh part.py out.stl values.json` | Exports with values from a JSON object |

**Changing a value for one run:** `-D name=value` works on validate, preview,
multi-preview and export, and can repeat. The value is read as a Python literal
(`-D clip_width=14`, `-D screw_hole=false`, `-D 'label="A"'`). `true` and `false` work in
any capitalisation, and a bare word becomes text. The new value must be the same kind as the
default (a number for a number, text for text), and a misspelled name stops the run with an
error instead of being ignored.

**Mesh detail:** `--tolerance 0.02` (mm, from 0.001 to 10) on export. Smaller values give smoother curves
and bigger files. Every mesh export also checks that the result is watertight.

## Printable by design

- Walls: at least two nozzle widths (0.8 mm with a 0.4 mm nozzle). 1.2 mm or more is
  sturdier.
- Overhangs: keep them within 45 degrees of vertical. Use a chamfer instead of a fillet
  on downward-facing edges, or plan for supports.
- Fit: printed holes come out a little small. Add 0.2 to 0.4 mm to diameters that must
  take a screw or a peg. Parts that slide together need about 0.3 mm of play on each side.
- Bridges longer than about 10 mm sag. A large flat face on the bed sticks best.

## Sharing a design

For a MakerWorld or Printables page, export a 3MF and use the iso render as the cover
image. `tools/extract-params.sh part.py --json` turns the parameter comments into a
ready-made "what you can change" section for the description.

## FreeCAD cheat sheet

```python
import FreeCAD as App, Part
V = App.Vector
Part.makeBox(x, y, z, V(px, py, pz))               # box with its corner at a point
Part.makeCylinder(r, h, V(base), V(axis))          # cylinder along any axis
Part.makeCone(r1, r2, h, V(base), V(axis))         # cone or tapered peg
Part.makeSphere(r, V(center))
Part.makeTorus(R, r)
a.fuse(b)   a.cut(b)   a.common(b)                 # join, subtract, overlap
a.fuse([b, c, d]).removeSplitter()                 # join many, merge coplanar faces
s.makeFillet(radius, edges)  s.makeChamfer(size, edges)
s.translate(V(dx, dy, dz))   s.rotate(V(0,0,0), V(0,0,1), degrees)   # change s itself
s.mirror(V(0,0,0), V(1,0,0))                       # gives a mirrored copy
Part.Face(Part.makePolygon([V(...), ..., first])).extrude(V(0, 0, h))  # outline -> prism
Part.makeCompound([a, b])                          # separate parts, one plate
s.BoundBox.XLength  s.Volume  s.isValid()  s.Solids
```

To round only the upright edges of a box:
`[e for e in s.Edges if abs(e.Vertexes[0].X - e.Vertexes[1].X) < 1e-9 and abs(e.Vertexes[0].Y - e.Vertexes[1].Y) < 1e-9]`.
