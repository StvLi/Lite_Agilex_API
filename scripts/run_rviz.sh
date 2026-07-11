#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-15}"
RVIZ_CFG="${ROOT_DIR}/ros2_ws/src/agilex_chassis_bridge/rviz/chassis_map.rviz"
exec "${SCRIPT_DIR}/run_ros2.sh" rviz2 -d "${RVIZ_CFG}"
