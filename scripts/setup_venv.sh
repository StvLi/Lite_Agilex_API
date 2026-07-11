#!/usr/bin/env bash
# 已弃用：请使用 setup_conda_env.sh
set -euo pipefail
echo "setup_venv.sh 已弃用，改为使用独立 conda 环境。" >&2
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/setup_conda_env.sh"
