#!/bin/bash
# Render the six standard views (iso, front, back, left, right, top) as <name>_<view>.png.
# Usage: multi-preview.sh model.py output_dir/ [--size 800x600] [-D name=value ...]
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
if [ $# -lt 2 ]; then echo "Usage: $0 model.py output_dir/ [--size 800x600] [-D name=value ...]"; exit 1; fi
MODEL="$1"; OUTPUT_DIR="$2"; shift 2
run_fc multi-preview "$MODEL" "$OUTPUT_DIR" "$@"
