#!/usr/bin/env bash
# 创建项目 Python 虚拟环境并安装依赖
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$ROOT_DIR"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  echo "已创建 .venv"
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "虚拟环境就绪: source ${ROOT_DIR}/.venv/bin/activate"
