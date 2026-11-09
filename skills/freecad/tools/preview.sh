#!/bin/bash
# Render one preview image.
# Usage: preview.sh model.py output.png [--view iso|front|back|left|right|top|bottom] [--size 800x600] [-D name=value ...]
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
if [ $# -lt 2 ]; then echo "Usage: $0 model.py output.png [--view iso] [--size 800x600] [-D name=value ...]"; exit 1; fi
MODEL="$1"; OUTPUT="$2"; shift 2
run_fc preview "$MODEL" "$OUTPUT" "$@"
