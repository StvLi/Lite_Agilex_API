#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/run_ros2.sh" ros2 service call /agilex/save_debug_map agilex_msgs/srv/SaveDebugMap "{}"
