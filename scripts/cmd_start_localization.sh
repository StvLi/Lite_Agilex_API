#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

USE_PENDING=true
WAIT=true
TIMEOUT=60.0
X=0.0
Y=0.0
THETA=0.0

usage() {
  cat <<EOF
用法:
  $0                         # 使用 RViz/服务已记录的初始位姿，并等待定位完成
  $0 --no-wait               # 下发后立即返回，不等待定位完成
  $0 <x> <y> [theta_deg]     # 直接指定像素初值并等待定位完成
  $0 <x> <y> [theta_deg] --no-wait
EOF
}

ARGS=()
for arg in "$@"; do
  case "${arg}" in
    --no-wait) WAIT=false ;;
    -h|--help) usage; exit 0 ;;
    *) ARGS+=("${arg}") ;;
  esac
done

if ((${#ARGS[@]} >= 2)); then
  USE_PENDING=false
  X="${ARGS[0]}"
  Y="${ARGS[1]}"
  THETA="${ARGS[2]:-0}"
fi

exec "${SCRIPT_DIR}/run_ros2.sh" ros2 service call /agilex/start_localization agilex_msgs/srv/StartLocalization \
  "{use_pending_pose: ${USE_PENDING}, x: ${X}, y: ${Y}, theta_deg: ${THETA}, wait_for_ready: ${WAIT}, timeout_sec: ${TIMEOUT}}"
