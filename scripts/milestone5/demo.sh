#!/usr/bin/env bash
# Start with bash ~/metroai-milestone5/demo.sh after copying into Cloud Shell.
set -euo pipefail
METRO_SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ -f "$METRO_SCRIPT_DIR/scripts/milestone5/record_demo.py" ]]; then
  METRO_DEMO_ROOT="$METRO_SCRIPT_DIR"
else
  METRO_DEMO_ROOT=$(cd -- "$METRO_SCRIPT_DIR/../.." && pwd)
fi
exec python3 -u "$METRO_DEMO_ROOT/scripts/milestone5/record_demo.py" "$@"
