#!/bin/bash
# Shared helpers: find FreeCAD's command-line binary and run fcskill_run.py with it.

TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

find_freecadcmd() {
    # 1. Explicit override
    if [ -n "$FREECADCMD" ]; then
        if [ -x "$FREECADCMD" ]; then
            echo "$FREECADCMD"; return 0
        fi
        echo "Error: FREECADCMD is set to '$FREECADCMD', which is not an executable file." >&2
        return 1
    fi
    # 2. On PATH (Linux packages, Homebrew, conda)
    for name in freecadcmd FreeCADCmd freecad.cmd; do
        if command -v "$name" >/dev/null 2>&1; then
            command -v "$name"; return 0
        fi
    done
    # 3. macOS app bundles (FreeCAD 1.x and older layouts)
    for app in "/Applications/FreeCAD.app" "$HOME/Applications/FreeCAD.app"; do
        for bin in "$app/Contents/Resources/bin/freecadcmd" "$app/Contents/MacOS/FreeCADCmd"; do
            if [ -x "$bin" ]; then
                echo "$bin"; return 0
            fi
        done
    done
    return 1
}

check_freecad() {
    if ! FREECADCMD_BIN="$(find_freecadcmd)"; then
        echo "Error: FreeCAD's command-line program (freecadcmd) was not found." >&2
        echo "Install FreeCAD 1.0 or newer from https://www.freecad.org/downloads.php," >&2
        echo "or set FREECADCMD=/path/to/freecadcmd." >&2
        exit 127
    fi
}

# run_fc <command> [args...] : run a fcskill command inside FreeCAD, keep its exit code.
run_fc() {
    check_freecad
    local i=0 arg
    export FCSKILL_ARGC=$#
    for arg in "$@"; do
        export "FCSKILL_ARG_$i=$arg"
        i=$((i + 1))
    done
    export PYTHONUTF8=1   # keeps non-ASCII paths working under a C/POSIX locale
    local status
    FCSKILL_LOG="$(mktemp "${TMPDIR:-/tmp}/fcskill.XXXXXX")" || return 1
    trap 'rm -f "$FCSKILL_LOG"' EXIT INT TERM
    "$FREECADCMD_BIN" "$TOOLS_DIR/fcskill_run.py" >"$FCSKILL_LOG" 2>&1
    status=$?
    # FreeCAD prints a banner and progress noise; show only what matters to the caller.
    tr '\r\t' '\n ' <"$FCSKILL_LOG" | sed $'s/\x1b\\[[0-9;]*m//g' | grep -Ev \
        '^__FCSKILL_END__|^[[:space:]]*$|^[[:space:]]*\(?[0-9]+ ?%\)?|^Checking topology|WorkSession|Step File Name|^FreeCAD [0-9]|^\(C\) [0-9]{4}|^FreeCAD is free|^saving\.*$' || true
    # fcskill_run.py prints an end marker; without it FreeCAD died or was stopped early.
    if ! grep -q '^__FCSKILL_END__ ' "$FCSKILL_LOG"; then
        echo "ERROR: FreeCAD stopped before the command finished (exit $status)." >&2
        [ "$status" -eq 0 ] && status=1
    fi
    rm -f "$FCSKILL_LOG"
    return $status
}
