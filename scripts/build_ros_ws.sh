#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WS_DIR="${ROOT_DIR}/ros2_ws"

# ROS2 编译使用系统 Python（conda 环境缺少 empy/rosidl 构建依赖）
if command -v conda >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh"
  if [[ -n "${CONDA_DEFAULT_ENV:-}" ]]; then
    conda deactivate
  fi
fi
set +u
source /opt/ros/jazzy/setup.bash
set -u
cd "${WS_DIR}"
colcon build --symlink-install "$@"
echo ""
echo "编译完成。在其他终端调用 ros2 前请执行："
echo "  source ${ROOT_DIR}/scripts/ros2_env.sh"
