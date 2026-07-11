#!/usr/bin/env bash
# 人类可读别名 → agent_get_map.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/agent_get_map.sh" "$@"
