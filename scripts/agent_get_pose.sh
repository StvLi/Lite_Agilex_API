#!/usr/bin/env bash
# Function 1：获取当前位姿（JSON stdout）
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/env.sh"
exec python -m agilex_client.agent_api get-pose "$@"
