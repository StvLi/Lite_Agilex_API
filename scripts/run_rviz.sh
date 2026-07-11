#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-15}"

# 按地图尺寸生成全图俯视配置（Scale 越小越能看全图）
if [[ -f "${ROOT_DIR}/scripts/env.sh" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/scripts/env.sh"
fi
python3 "${SCRIPT_DIR}/gen_rviz_config.py"

RVIZ_CFG="${ROOT_DIR}/ros2_ws/src/agilex_chassis_bridge/rviz/chassis_map.rviz"
exec "${SCRIPT_DIR}/run_ros2.sh" rviz2 -d "${RVIZ_CFG}"
