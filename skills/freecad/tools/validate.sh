#!/bin/bash
# Check that a model builds into valid, closed, printable solids.
# Usage: validate.sh model.py [-D name=value ...] [--params params.json]
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
if [ $# -lt 1 ]; then echo "Usage: $0 model.py [-D name=value ...] [--params file.json]"; exit 1; fi
run_fc validate "$@"
