#!/usr/bin/env bash
# 一次性环境准备：凭据模板、conda、ROS2 编译
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

if [[ ! -f config/local.yaml ]]; then
  cp config/local.yaml.example config/local.yaml
  echo "已创建 config/local.yaml，请编辑填入 auth 用户名密码后重新运行本脚本。"
  exit 1
fi

./scripts/setup_conda_env.sh
./scripts/build_ros_ws.sh

echo ""
echo "一次性准备完成。接下来按 README 开终端 A/B/D 即可。"
