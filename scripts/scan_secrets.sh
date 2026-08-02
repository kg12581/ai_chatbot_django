#!/usr/bin/env bash
#
# 硬编码密钥扫描脚本（Gitleaks）
# 用法：
#   ./scripts/scan_secrets.sh            # 扫工作区 + git 历史
#   ./scripts/scan_secrets.sh --no-git   # 只扫当前工作区文件
#
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v gitleaks >/dev/null 2>&1; then
  echo "错误：未安装 gitleaks，请先运行：brew install gitleaks" >&2
  exit 1
fi

echo "==> Gitleaks 硬编码密钥扫描开始..."
gitleaks detect --source . --config .gitleaks.toml --redact --verbose "$@"
