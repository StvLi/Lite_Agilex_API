#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WS_DIR="${ROOT_DIR}/ros2_ws"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/env.sh"
source /opt/ros/jazzy/setup.bash
cd "${WS_DIR}"
colcon build --symlink-install "$@"
echo "source ${WS_DIR}/install/setup.bash"
