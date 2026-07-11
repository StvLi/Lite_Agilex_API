#!/usr/bin/env bash
# 创建/更新本项目专用 conda 环境（不污染 base 或 lite_ros2_env）
#
# 镜像策略（国内网络优先）：
#   Conda  - 首选 USTC，失败回退 Aliyun
#   Pip    - 首选清华 TUNA，失败回退 Aliyun
#
# 快速路径：环境已存在时仅 pip install，不执行 conda env update。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_NAME="${LITE_AGILEX_CONDA_ENV:-lite_agilex_api}"

# Conda 镜像（USTC → Aliyun）
CONDA_CHANNELS_USTC=(
  "https://mirrors.ustc.edu.cn/anaconda/pkgs/main"
  "https://mirrors.ustc.edu.cn/anaconda/cloud/conda-forge"
)
CONDA_CHANNELS_ALIYUN=(
  "https://mirrors.aliyun.com/anaconda/pkgs/main"
  "https://mirrors.aliyun.com/anaconda/cloud/conda-forge"
)

# Pip 镜像（清华 TUNA → Aliyun）
PIP_INDEX_USTC="https://pypi.tuna.tsinghua.edu.cn/simple"
PIP_INDEX_ALIYUN="https://mirrors.aliyun.com/pypi/simple/"

cd "${ROOT_DIR}"

if ! command -v conda >/dev/null 2>&1; then
  echo "未找到 conda，请先安装 Miniconda/Anaconda。" >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$(conda info --base)/etc/profile.d/conda.sh"

pip_install_with_mirror() {
  local mirror_used=""
  pip install --upgrade pip -i "${PIP_INDEX_USTC}" --trusted-host pypi.tuna.tsinghua.edu.cn \
    && mirror_used="${PIP_INDEX_USTC}" \
    || {
      echo "Pip 清华镜像失败，回退 Aliyun ..."
      pip install --upgrade pip -i "${PIP_INDEX_ALIYUN}" --trusted-host mirrors.aliyun.com
      mirror_used="${PIP_INDEX_ALIYUN}"
    }

  pip install -r "${ROOT_DIR}/requirements.txt" -i "${PIP_INDEX_USTC}" --trusted-host pypi.tuna.tsinghua.edu.cn \
    && mirror_used="${PIP_INDEX_USTC}" \
    || {
      echo "Pip 清华镜像失败，回退 Aliyun ..."
      pip install -r "${ROOT_DIR}/requirements.txt" -i "${PIP_INDEX_ALIYUN}" --trusted-host mirrors.aliyun.com
      mirror_used="${PIP_INDEX_ALIYUN}"
    }

  echo "Pip 镜像: ${mirror_used}"
}

conda_create_with_mirror() {
  local channels=("$@")
  local channel_args=()
  for ch in "${channels[@]}"; do
    channel_args+=(-c "${ch}")
  done

  # 仅安装 python+pip，其余走 pip（避免 conda 解析慢）
  conda create -y -n "${ENV_NAME}" "${channel_args[@]}" python=3.12 pip
}

if conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  echo "环境已存在: ${ENV_NAME}，仅安装/更新 pip 依赖（快速路径）"
  conda activate "${ENV_NAME}"
  pip_install_with_mirror
else
  echo "创建 conda 环境: ${ENV_NAME}"
  if conda_create_with_mirror "${CONDA_CHANNELS_USTC[@]}"; then
    echo "Conda 镜像: USTC"
  else
    echo "Conda USTC 失败，回退 Aliyun ..."
    conda env remove -n "${ENV_NAME}" -y 2>/dev/null || true
    conda_create_with_mirror "${CONDA_CHANNELS_ALIYUN[@]}"
    echo "Conda 镜像: Aliyun"
  fi
  conda activate "${ENV_NAME}"
  pip_install_with_mirror
fi

echo
echo "环境就绪:"
echo "  conda activate ${ENV_NAME}"
echo "或:"
echo "  source ${ROOT_DIR}/scripts/env.sh"
