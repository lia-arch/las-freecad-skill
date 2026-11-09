"""Headless preview images of a Part.Shape, drawn with matplotlib (no GUI needed).

matplotlib paints triangles back to front by their average depth, so large
triangles are subdivided and faces pointing away from the camera are dropped
(back-face culling) to keep hollow parts readable."""
import math
import os

# view name -> (elevation, azimuth) in degrees; FreeCAD is Z-up, "front" looks along +Y.
VIEWS = {
    "iso": (35.264, -45.0),
    "front": (0.0, -90.0),
    "back": (0.0, 90.0),
    "left": (0.0, 180.0),
    "right": (0.0, 0.0),
    "top": (90.0, -90.0),
    "bottom": (-90.0, -90.0),
}
DEFAULT_VIEWS = ("iso", "front", "back", "left", "right", "top")

BACKGROUND = "#1d1f21"
MODEL_RGB = (0.98, 0.62, 0.22)
TEXT_COLOR = "#c5c8c6"
MAX_TRIANGLES = 120000


def _pyplot():
    try:
        import matplotlib
    except ImportError:
        raise RuntimeError("previews need matplotlib in FreeCAD's Python; "
                           "export an STL and open it in your slicer instead")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _subdivide(polys, max_edge):
    """Split triangles at their edge midpoints until no edge is longer than max_edge."""
    import numpy as np
    for _ in range(8):
        edges = np.linalg.norm(polys - np.roll(polys, -1, axis=1), axis=2).max(axis=1)
        big = edges > max_edge
        if not big.any() or len(polys) + 3 * big.sum() > MAX_TRIANGLES:
            break
        a, b, c = polys[big, 0], polys[big, 1], polys[big, 2]
        ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
        split = np.concatenate([np.stack(t, axis=1) for t in
                                ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca))])
        polys = np.concatenate([polys[~big], split])
    return polys


def _mesh(shape):
    import numpy as np
    bb = shape.BoundBox
    points, triangles = shape.tessellate(max(bb.DiagonalLength * 0.002, 0.01))
    if not triangles:
        raise RuntimeError("the shape has no faces to draw")
    pts = np.array([(p.x, p.y, p.z) for p in points], dtype=float)
    polys = _subdivide(pts[np.array(triangles, dtype=int)], bb.DiagonalLength / 25.0)
    normals = np.cross(polys[:, 1] - polys[:, 0], polys[:, 2] - polys[:, 0])
    length = np.linalg.norm(normals, axis=1)
    keep = length > 0
    return polys[keep], normals[keep] / length[keep][:, None], bb


def _draw(plt, polys, normals, bb, out_png, view, size, title):
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    elev, azim = VIEWS[view]
    e, a = math.radians(elev), math.radians(azim)
    to_camera = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
    facing = normals @ to_camera
    front = facing > 1e-6  # back-face culling
    light = np.array([-0.45, -0.55, 0.70])
    light /= np.linalg.norm(light)
    shade = (0.30 + 0.45 * np.clip(normals[front] @ light, 0, 1)
             + 0.25 * np.clip(facing[front], 0, 1))
    colors = np.clip(np.outer(shade, MODEL_RGB), 0, 1)

    width, height = size
    fig = plt.figure(figsize=(width / 100.0, height / 100.0), dpi=100, facecolor=BACKGROUND)
    ax = fig.add_axes([0, 0, 1, 0.93], projection="3d", facecolor=BACKGROUND)
    # Edges in the face color hide the hairline seams between triangles.
    ax.add_collection3d(Poly3DCollection(polys[front], facecolors=colors,
                                         edgecolors=colors, linewidths=0.3))
    lengths = [max(bb.XLength, 1e-3), max(bb.YLength, 1e-3), max(bb.ZLength, 1e-3)]
    ax.set_xlim(bb.XMin, bb.XMin + lengths[0])
    ax.set_ylim(bb.YMin, bb.YMin + lengths[1])
    ax.set_zlim(bb.ZMin, bb.ZMin + lengths[2])
    ax.set_box_aspect(lengths, zoom=0.9)
    ax.set_proj_type("ortho")
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    label = "%s | %s | %.1f x %.1f x %.1f mm" % (title, view, bb.XLength, bb.YLength, bb.ZLength)
    fig.text(0.02, 0.965, label, color=TEXT_COLOR, fontsize=10, va="center")
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    fig.savefig(out_png, dpi=100, facecolor=BACKGROUND)
    plt.close(fig)
    return out_png


def render_views(shape, out_paths, size=(800, 600), title=""):
    """Render several views of one shape. out_paths maps view name -> png path."""
    for view in out_paths:
        if view not in VIEWS:
            raise ValueError("unknown view %r (choose from %s)" % (view, ", ".join(VIEWS)))
    plt = _pyplot()
    polys, normals, bb = _mesh(shape)
    return [_draw(plt, polys, normals, bb, path, view, size, title)
            for view, path in out_paths.items()]
