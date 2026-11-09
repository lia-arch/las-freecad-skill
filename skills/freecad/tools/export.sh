#!/bin/bash
# Export a model. The format follows the extension: .stl .3mf .obj (mesh) or .step .stp .brep (CAD).
# Usage: export.sh model.py output.stl [-D name=value ...] [--params file.json] [--tolerance 0.02]
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
if [ $# -lt 2 ]; then echo "Usage: $0 model.py output.(stl|3mf|obj|step|brep) [-D name=value ...]"; exit 1; fi
MODEL="$1"; OUTPUT="$2"; shift 2
run_fc export "$MODEL" "$OUTPUT" "$@"
