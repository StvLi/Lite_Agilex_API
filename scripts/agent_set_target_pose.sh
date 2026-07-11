#!/usr/bin/env bash
# Function 2：设置目标位姿并导航（JSON stdout）
# 用法: ./scripts/agent_set_target_pose.sh <x> <y> <theta_deg>
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/env.sh"
exec python -m agilex_client.agent_api set-target-pose "$@"
