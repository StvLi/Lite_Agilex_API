#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-15}"
export LITE_AGILEX_API_ROOT="${ROOT_DIR}"
export PYTHONPATH="${ROOT_DIR}/ros2_ws/src/agilex_chassis_bridge:${ROOT_DIR}/python:${PYTHONPATH:-}"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/env.sh"
set +u
source /opt/ros/jazzy/setup.bash
source "${ROOT_DIR}/ros2_ws/install/setup.bash"
set -u
# 使用 conda Python 启动，确保 websockets/Pillow 等依赖可用（ros2 run 走系统 Python）
exec python "${ROOT_DIR}/ros2_ws/src/agilex_chassis_bridge/agilex_chassis_bridge/chassis_bridge_node.py"
