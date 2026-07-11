#!/usr/bin/env bash
# 在任意终端调用 ros2 CLI（service / topic / interface）前执行：
#   source scripts/ros2_env.sh
# 未 source 时 agilex_msgs 不可见，会出现 "The passed service type is invalid"。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-15}"

set +u
source /opt/ros/jazzy/setup.bash
if [[ ! -f "${ROOT_DIR}/ros2_ws/install/setup.bash" ]]; then
  echo "未找到 ros2_ws/install/setup.bash，请先运行: ./scripts/build_ros_ws.sh" >&2
  return 1 2>/dev/null || exit 1
fi
source "${ROOT_DIR}/ros2_ws/install/setup.bash"
set -u
