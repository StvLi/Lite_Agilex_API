#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/run_ros2.sh" ros2 service call /agilex/get_pose agilex_msgs/srv/GetChassisPose "{}"
