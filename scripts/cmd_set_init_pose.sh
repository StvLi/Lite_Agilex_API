#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
X="${1:?用法: $0 <x> <y> [theta_deg]}"
Y="${2:?用法: $0 <x> <y> [theta_deg]}"
THETA="${3:-0}"
exec "${SCRIPT_DIR}/run_ros2.sh" ros2 service call /agilex/set_initial_pose agilex_msgs/srv/SetInitialPose \
  "{x: ${X}, y: ${Y}, theta_deg: ${THETA}}"
