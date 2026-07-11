#!/usr/bin/env bash
# 自动加载 ROS2 + agilex_msgs，然后执行传入命令。
# 用法: ./scripts/run_ros2.sh ros2 topic list
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-15}"

if [[ ! -f "${ROOT_DIR}/ros2_ws/install/setup.bash" ]]; then
  echo "未找到 ros2_ws/install/setup.bash，请先运行: ${ROOT_DIR}/scripts/bootstrap_once.sh" >&2
  exit 1
fi

set +u
source /opt/ros/jazzy/setup.bash
source "${ROOT_DIR}/ros2_ws/install/setup.bash"
set -u

cd "${ROOT_DIR}"
exec "$@"
