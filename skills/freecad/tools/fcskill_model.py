"""Load FreeCAD model scripts and read their parameters.

A model is a Python file with simple top-level parameter assignments, each
optionally followed by a comment that describes it, and a build() function
that returns a Part.Shape (or a list of shapes):

    width = 60.0          # [20:200] Width in mm
    style = "round"       # [round, square] Corner style
    add_grip = True       # Add grip notches

    def build():
        import Part
        return Part.makeBox(width, width, 10)

Overrides replace the literal value of a top-level assignment before the file
runs. Override values are parsed with ast.literal_eval, never executed.
"""
import ast
import os
import re
import sys

_BRACKET = re.compile(r"^\[([^\]]*)\]\s*(.*)$")
_SCALARS = (bool, int, float, str, type(None))
_WORDS = {"true": True, "false": False, "none": None}


def _type_name(value):
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (list, tuple)):
        return "array"
    return "other"


def _literal(node):
    try:
        return True, ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError):
        return False, None


def _param_nodes(tree):
    """Map name -> assignment node for top-level `name = literal` and `name: type = literal`.
    If a name is assigned twice, the last assignment wins (it is the one that takes effect)."""
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        elif isinstance(node, ast.AnnAssign) and node.value is not None and node.simple:
            target = node.target
        else:
            continue
        if isinstance(target, ast.Name) and _literal(node.value)[0]:
            found[target.id] = node
    return found


def read_params(path):
    """Return the model's parameters as a list of dicts (the model is not run)."""
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    lines = source.splitlines()
    params = []
    for name, node in _param_nodes(ast.parse(source, filename=path)).items():
        if name.startswith("_"):
            continue  # private by convention
        _, value = _literal(node.value)
        tail = lines[node.end_lineno - 1][node.end_col_offset:]
        comment = tail.split("#", 1)[1].strip() if "#" in tail else ""
        entry = {"name": name, "value": value, "type": _type_name(value)}
        m = _BRACKET.match(comment)
        if m:
            inner, comment = m.group(1).strip(), m.group(2).strip()
            if ":" in inner and "," not in inner:
                entry["range"] = inner
            else:
                entry["options"] = [o.strip() for o in inner.split(",") if o.strip()]
        if comment:
            entry["description"] = comment
        params.append(entry)
    return params


def parse_override(text):
    """Turn 'name=value' into (name, value). The value is a Python literal; true/false/none
    in any case are booleans/None; anything else that is not a literal becomes a string."""
    if "=" not in text:
        raise ValueError("override must look like name=value, got: %r" % text)
    name, raw = text.split("=", 1)
    name, raw = name.strip(), raw.strip()
    if not name.isidentifier():
        raise ValueError("not a parameter name: %r" % name)
    if raw.lower() in _WORDS:
        return name, _WORDS[raw.lower()]
    try:
        value = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        value = raw
    return name, value


def _check_type(name, default, value):
    def is_number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    ok = (default is None
          or (isinstance(default, bool) and isinstance(value, bool))
          or (is_number(default) and is_number(value))
          or (isinstance(default, str) and isinstance(value, str))
          or (isinstance(default, (list, tuple)) and isinstance(value, (list, tuple)))
          or (isinstance(default, (dict, set)) and isinstance(value, type(default))))
    if not ok:
        raise ValueError("parameter %s expects %s like its default %r, got %r"
                         % (name, _type_name(default), default, value))


def _value_node(value):
    if isinstance(value, _SCALARS):
        return ast.Constant(value)
    return ast.parse(repr(value), mode="eval").body


def load_shape(path, overrides=None):
    """Run the model with overrides applied and return (shape, used_params)."""
    import Part  # only available inside FreeCAD

    overrides = dict(overrides or {})
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source, filename=path)
    known = _param_nodes(tree)
    unknown = sorted(set(overrides) - set(known))
    if unknown:
        raise ValueError("unknown parameter(s): %s (known: %s)"
                         % (", ".join(unknown), ", ".join(sorted(known)) or "none"))
    for name, value in overrides.items():
        node = known[name]
        _check_type(name, _literal(node.value)[1], value)
        node.value = ast.copy_location(_value_node(value), node.value)
    ast.fix_missing_locations(tree)

    folder = os.path.dirname(os.path.abspath(path))
    namespace = {"__name__": "fcskill_user_model", "__file__": path}
    sys.path.insert(0, folder)  # let a model import helper files next to it
    try:
        exec(compile(tree, path, "exec"), namespace)
        build = namespace.get("build")
        if not callable(build):
            raise ValueError("model must define build() returning a Part.Shape")
        shape = build()
    except SystemExit as exc:
        raise RuntimeError("the model called sys.exit(%r); build() must return a shape instead"
                           % (exc.code,))
    finally:
        if folder in sys.path:
            sys.path.remove(folder)

    if isinstance(shape, (list, tuple)):
        if not shape:
            raise ValueError("build() returned an empty list")
        shape = Part.makeCompound(list(shape))
    if not isinstance(shape, Part.Shape):
        raise ValueError("build() returned %s, expected a Part.Shape" % type(shape).__name__)
    if shape.isNull() or not shape.Faces:
        raise ValueError("build() returned an empty shape (no faces)")
    used = {name: namespace.get(name) for name in known}
    return shape, used
