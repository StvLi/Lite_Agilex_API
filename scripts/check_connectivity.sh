#!/usr/bin/env bash
# 检查到各硬件节点的网络连通性
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

TIMEOUT="${PING_TIMEOUT:-2}"

declare -A HOSTS=(
  ["RDK_X5_运控"]="192.168.88.10"
  ["DGX_Spark_算力"]="192.168.88.11"
  ["桌面开发机_88网"]="192.168.88.12"
  ["松灵底盘_Jetson"]="10.7.5.99"
  ["桌面开发机_车网"]="10.7.5.100"
)

echo "=== Lite Agilex API 连通性检查 ==="
echo "时间: $(date -Iseconds)"
echo

fail=0
for name in "${!HOSTS[@]}"; do
  ip="${HOSTS[$name]}"
  printf "%-22s %-18s " "$name" "$ip"
  if ping -c 1 -W "$TIMEOUT" "$ip" &>/dev/null; then
    echo "OK"
  else
    echo "FAIL"
    fail=$((fail + 1))
  fi
done

echo
if [[ -n "${CHASSIS_HOST:-}" ]]; then
  host="${CHASSIS_HOST}"
else
  host="10.7.5.99"
fi

printf "HTTP 探测 (%s) ... " "$host"
if curl -s --connect-timeout 3 -o /dev/null -w "%{http_code}" "http://${host}/apiUrl" 2>/dev/null | grep -qE '^[0-9]+$'; then
  code=$(curl -s --connect-timeout 3 -o /dev/null -w "%{http_code}" "http://${host}/apiUrl" 2>/dev/null || echo "000")
  echo "响应 HTTP $code"
else
  echo "无响应（NAVIS HTTP 可能未启动或不可达）"
  fail=$((fail + 1))
fi

echo
if [[ $fail -eq 0 ]]; then
  echo "全部检查通过。"
  exit 0
else
  echo "$fail 项检查未通过，详见 docs/DEBUG_LOG.md 记录后重试。"
  exit 1
fi
