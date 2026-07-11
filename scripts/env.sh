#!/usr/bin/env bash
# 激活本项目专用 conda 环境（lite_agilex_api）
set -euo pipefail

ENV_NAME="${LITE_AGILEX_CONDA_ENV:-lite_agilex_api}"

if ! command -v conda >/dev/null 2>&1; then
  echo "未找到 conda，请先安装 Miniconda/Anaconda。" >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$(conda info --base)/etc/profile.d/conda.sh"

if ! conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  echo "conda 环境 ${ENV_NAME} 不存在，请先运行: ./scripts/setup_conda_env.sh" >&2
  exit 1
fi

conda activate "${ENV_NAME}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${ROOT_DIR}/python:${PYTHONPATH:-}"
