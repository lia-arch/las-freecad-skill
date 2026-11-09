#!/bin/bash
# Export a model using parameter values from a JSON file, e.g. {"width": 80, "add_grip": false}.
# Usage: render-with-params.sh model.py output.stl params.json [-D name=value ...]
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
if [ $# -lt 3 ]; then echo "Usage: $0 model.py output.(stl|3mf|step) params.json [-D name=value ...]"; exit 1; fi
MODEL="$1"; OUTPUT="$2"; PARAMS="$3"; shift 3
run_fc export "$MODEL" "$OUTPUT" --params "$PARAMS" "$@"
