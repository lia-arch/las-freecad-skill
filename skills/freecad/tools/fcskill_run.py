"""Command runner executed by freecadcmd. The shell wrappers pass arguments as
FCSKILL_ARGC / FCSKILL_ARG_<n> environment variables because freecadcmd treats
extra command-line arguments as files to open."""
import argparse
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import fcskill_model  # noqa: E402
import fcskill_render  # noqa: E402

MESH_FORMATS = (".stl", ".3mf", ".obj")
CAD_FORMATS = (".step", ".stp", ".brep")


for _stream in (sys.stdout, sys.stderr):
    try:  # a C/POSIX locale would make the console ASCII-only
        _stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, ValueError):
        pass


def say(*parts):
    text = " ".join(str(p) for p in parts)
    try:
        print(text, flush=True)
    except UnicodeEncodeError:  # console still cannot take UTF-8: escape, never crash
        print(text.encode("ascii", "backslashreplace").decode("ascii"), flush=True)


def overrides_from(args):
    values = {}
    if getattr(args, "params", None):
        with open(args.params, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("--params file must hold a JSON object of name: value")
        values.update(data)
    for text in getattr(args, "define", None) or []:
        name, value = fcskill_model.parse_override(text)
        values[name] = value
    return values


def build(args):
    shape, used = fcskill_model.load_shape(args.model, overrides_from(args))
    return shape


def check(shape):
    """Return (problems, facts) for a printable-solid check."""
    problems, bb = [], shape.BoundBox
    if shape.isNull():
        return ["the shape is empty"], {}
    if not shape.isValid():
        problems.append("geometry is not valid (check booleans and fillets)")
    if not shape.Solids:
        problems.append("no closed solids: only faces or shells, which cannot be printed")
    for i, solid in enumerate(shape.Solids, 1):
        if any(not sh.isClosed() for sh in solid.Shells):
            problems.append("solid %d has an open shell" % i)
        if solid.Volume <= 0:
            problems.append("solid %d has no volume (inside-out?)" % i)
    solids = shape.Solids
    if 1 < len(solids) <= 60:
        for i in range(len(solids)):
            for j in range(i + 1, len(solids)):
                if (solids[i].BoundBox.intersect(solids[j].BoundBox)
                        and solids[i].common(solids[j]).Volume > 1e-6):
                    problems.append("solids %d and %d overlap: fuse them, or move them apart"
                                    % (i + 1, j + 1))
    facts = {"size_mm": [round(bb.XLength, 3), round(bb.YLength, 3), round(bb.ZLength, 3)],
             "volume_mm3": round(shape.Volume, 2), "solids": len(shape.Solids),
             "faces": len(shape.Faces)}
    return problems, facts


def cmd_validate(args):
    problems, facts = check(build(args))
    say("Model: %s" % args.model)
    for key, value in facts.items():
        say("  %-11s %s" % (key + ":", value))
    if facts.get("solids", 0) > 1:
        say("  note: %d separate solids (fine for a print plate, e.g. box + lid)" % facts["solids"])
    for p in problems:
        say("  PROBLEM: " + p)
    say("FAILED" if problems else "OK: valid closed solid(s)")
    return 1 if problems else 0


def cmd_export(args):
    shape = build(args)
    problems, _ = check(shape)
    for p in problems:
        say("  PROBLEM: " + p)
    out, ext = args.output, os.path.splitext(args.output)[1].lower()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if ext in CAD_FORMATS:
        (shape.exportBrep if ext == ".brep" else shape.exportStep)(out)
        say("Wrote %s (%d bytes)" % (out, os.path.getsize(out)))
    elif ext in MESH_FORMATS:
        import MeshPart
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=args.tolerance,
                                      AngularDeflection=0.2, Relative=False)
        mesh.write(out)
        say("Wrote %s (%d triangles, %d bytes)" % (out, mesh.CountFacets, os.path.getsize(out)))
        if not mesh.isSolid() or mesh.hasNonManifolds():
            problems.append("exported mesh is not watertight")
            say("  PROBLEM: exported mesh is not watertight")
    else:
        raise ValueError("unsupported format %r (use %s)" % (ext, ", ".join(MESH_FORMATS + CAD_FORMATS)))
    return 1 if problems else 0


def parse_size(text):
    m = re.match(r"^(\d+)x(\d+)$", text.strip().lower())
    if not m:
        raise ValueError("--size must look like 800x600, got %r" % text)
    w, h = int(m.group(1)), int(m.group(2))
    if not (16 <= w <= 8000 and 16 <= h <= 8000):
        raise ValueError("--size must be 16 to 8000 pixels on each side")
    return w, h


def tolerance(text):
    value = float(text)
    if not 0.001 <= value <= 10:
        raise argparse.ArgumentTypeError("must be between 0.001 and 10 mm")
    return value


def cmd_preview(args):
    if not args.output.lower().endswith(".png"):
        raise ValueError("preview output must be a .png file path, got %r" % args.output)
    shape = build(args)
    title = os.path.splitext(os.path.basename(args.model))[0]
    fcskill_render.render_views(shape, {args.view: args.output}, parse_size(args.size), title)
    say("Wrote %s" % args.output)
    return 0


def cmd_multi_preview(args):
    shape = build(args)
    base = os.path.splitext(os.path.basename(args.model))[0]
    paths = {v: os.path.join(args.output_dir, "%s_%s.png" % (base, v))
             for v in fcskill_render.DEFAULT_VIEWS}
    for path in fcskill_render.render_views(shape, paths, parse_size(args.size), base):
        say("Wrote %s" % path)
    return 0


def cmd_params(args):
    params = fcskill_model.read_params(args.model)
    if args.json:
        say(json.dumps(params, indent=2))
        return 0
    say("Parameters in: %s" % args.model)
    say("%-20s %-15s %-9s %s" % ("NAME", "VALUE", "TYPE", "CONSTRAINT/DESC"))
    for p in params:
        limit = p.get("range") or ", ".join(p.get("options", []))
        desc = " ".join(x for x in ("[%s]" % limit if limit else "", p.get("description", "")) if x)
        say("%-20s %-15s %-9s %s" % (p["name"], repr(p["value"]), p["type"], desc))
    return 0


def parser():
    top = argparse.ArgumentParser(prog="fcskill")
    sub = top.add_subparsers(dest="command", required=True)

    def model_cmd(name, func, help_text):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("model")
        p.add_argument("-D", "--define", action="append", metavar="NAME=VALUE",
                       help="override a parameter (repeatable)")
        p.add_argument("--params", metavar="FILE.json", help="JSON object of parameter overrides")
        p.set_defaults(func=func)
        return p

    model_cmd("validate", cmd_validate, "check the model builds into valid closed solids")
    p = model_cmd("export", cmd_export, "export STL, 3MF, OBJ, STEP or BREP")
    p.add_argument("output")
    p.add_argument("--tolerance", type=tolerance, default=0.02, help="mesh deviation in mm")
    p = model_cmd("preview", cmd_preview, "render one PNG view")
    p.add_argument("output")
    p.add_argument("--view", default="iso", choices=sorted(fcskill_render.VIEWS))
    p.add_argument("--size", default="800x600")
    p = model_cmd("multi-preview", cmd_multi_preview, "render the six standard views")
    p.add_argument("output_dir")
    p.add_argument("--size", default="800x600")
    p = sub.add_parser("params", help="list the model's parameters")
    p.add_argument("model")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_params)
    return top


def main():
    count = int(os.environ.get("FCSKILL_ARGC", "0"))
    argv = [os.environ.get("FCSKILL_ARG_%d" % i, "") for i in range(count)]
    try:
        args = parser().parse_args(argv)
    except SystemExit as exc:  # argparse usage errors and --help
        return exc.code if isinstance(exc.code, int) else 2
    try:
        return args.func(args)
    except Exception as exc:  # report, never let FreeCAD re-run the file
        say("ERROR: %s: %s" % (type(exc).__name__, exc))
        return 1
    except SystemExit as exc:  # something tried to end the run early
        say("ERROR: the run was cut short by sys.exit(%r)" % (exc.code,))
        return 1


_code = main()
say("__FCSKILL_END__ %d" % _code)  # the shell wrapper treats a missing marker as a crash
sys.stdout.flush()
sys.stderr.flush()
sys.exit(_code)
