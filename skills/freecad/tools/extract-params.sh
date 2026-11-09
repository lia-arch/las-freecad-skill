#!/bin/bash
# List a model's customizable parameters (read from the file; the model is not run).
# Usage: extract-params.sh model.py [--json]
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
if [ $# -lt 1 ]; then echo "Usage: $0 model.py [--json]"; exit 1; fi
run_fc params "$@"
