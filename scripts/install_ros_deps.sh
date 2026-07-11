#!/usr/bin/env bash
# ROS2 桥接节点由系统 Python 运行（与 rclpy 同环境），需单独安装 HTTP/WS 依赖
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 退出 conda，避免 pip 装到 conda 环境
if command -v conda >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh"
  while [[ -n "${CONDA_DEFAULT_ENV:-}" ]]; do
    conda deactivate
  done
fi

SYS_PYTHON="/usr/bin/python3"
if [[ ! -x "${SYS_PYTHON}" ]]; then
  SYS_PYTHON="$(command -v python3)"
fi

"${SYS_PYTHON}" -m pip install --user --break-system-packages \
  -r "${ROOT_DIR}/requirements.txt"

echo "系统 Python (${SYS_PYTHON}) 依赖已安装，供 ros2 run 使用"
