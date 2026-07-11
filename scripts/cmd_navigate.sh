#!/usr/bin/env bash
# 用法: ./scripts/cmd_navigate.sh [x] [y] [theta_deg]
# 不传参数时：先读当前位姿，再导航到同一点（朝向改为 0°，用于冒烟测试）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ $# -ge 3 ]]; then
  X="$1"
  Y="$2"
  THETA="$3"
else
  # shellcheck disable=SC1091
  source "${SCRIPT_DIR}/env.sh"
  read -r X Y THETA < <(
    python - <<'PY'
from agilex_client import AgilexClient, load_config
cfg = load_config()
c = AgilexClient(
    cfg["chassis"]["http_base"],
    cfg["chassis"]["ws_base"],
    cfg["auth"]["username"],
    cfg["auth"]["password"],
)
c.login()
p = c.fetch_pose_once()
print(p.x, p.y, 0.0)
PY
  )
  echo "未指定目标，使用当前位姿像素: x=${X} y=${Y} theta_deg=${THETA}"
fi

exec "${SCRIPT_DIR}/run_ros2.sh" ros2 service call /agilex/navigate_to_pose agilex_msgs/srv/NavigateToPose \
  "{x: ${X}, y: ${Y}, theta_deg: ${THETA}, follow_road_net: false}"
