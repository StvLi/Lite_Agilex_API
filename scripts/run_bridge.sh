#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-15}"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/env.sh"
set +u
source /opt/ros/jazzy/setup.bash
source "${ROOT_DIR}/ros2_ws/install/setup.bash"
set -u

# ros2 run 使用系统 Python（非 conda），确保 websockets 等依赖可用
if ! /usr/bin/python3 -c "import websockets, PIL, requests" 2>/dev/null; then
  echo "正在为系统 Python 安装桥接依赖 ..."
  "${SCRIPT_DIR}/install_ros_deps.sh"
fi

exec ros2 run agilex_chassis_bridge chassis_bridge
