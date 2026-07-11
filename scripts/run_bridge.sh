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
exec ros2 run agilex_chassis_bridge chassis_bridge
