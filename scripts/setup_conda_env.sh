#!/usr/bin/env bash
# 创建/更新本项目专用 conda 环境（不污染 base 或 lite_ros2_env）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_NAME="${LITE_AGILEX_CONDA_ENV:-lite_agilex_api}"

cd "${ROOT_DIR}"

if ! command -v conda >/dev/null 2>&1; then
  echo "未找到 conda，请先安装 Miniconda/Anaconda。" >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$(conda info --base)/etc/profile.d/conda.sh"

if conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  echo "更新已有 conda 环境: ${ENV_NAME}"
  conda env update -f environment.yml --prune
else
  echo "创建 conda 环境: ${ENV_NAME}"
  conda env create -f environment.yml
fi

echo
echo "环境就绪:"
echo "  conda activate ${ENV_NAME}"
echo "或:"
echo "  source ${ROOT_DIR}/scripts/env.sh"
