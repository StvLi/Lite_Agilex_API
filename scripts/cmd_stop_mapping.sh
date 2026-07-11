#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/run_ros2.sh" ros2 service call /agilex/stop_mapping agilex_msgs/srv/StopMapping \
  "{save_map: true, remark: 'debug update'}"
