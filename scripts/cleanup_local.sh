#!/bin/bash
# 本地缓存清理脚本
# Usage: bash scripts/cleanup_local.sh

set -e

echo "=================================================="
echo "本地缓存清理脚本"
echo "=================================================="

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "项目目录: $PROJECT_ROOT"
echo ""

# 1. 清理 __pycache__ 目录
echo "[1/4] 清理 __pycache__ 目录..."
pycache_count=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
echo "      找到 $pycache_count 个 __pycache__ 目录"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo "      已清理"

# 2. 清理 .pyc 文件
echo "[2/4] 清理 .pyc 文件..."
pyc_count=$(find . -type f -name "*.pyc" 2>/dev/null | wc -l)
echo "      找到 $pyc_count 个 .pyc 文件"
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "      已清理"

# 3. 清理 .pytest_cache
echo "[3/4] 清理 .pytest_cache..."
if [ -d ".pytest_cache" ]; then
    rm -rf .pytest_cache
    echo "      已删除 .pytest_cache"
else
    echo "      .pytest_cache 不存在"
fi

# 4. 清理 agent_workspace（保留 .gitkeep）
echo "[4/4] 清理 agent_workspace..."
if [ -d "agent_workspace" ]; then
    # 统计文件夹数量
    ws_count=$(ls -d agent_workspace/*/ 2>/dev/null | wc -l || echo 0)
    echo "      找到 $ws_count 个工作区目录"

    # 删除所有子目录（不删除 .gitkeep）
    find agent_workspace -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} + 2>/dev/null || true
    echo "      已清理 agent_workspace"
else
    echo "      agent_workspace 不存在"
fi

echo ""
echo "=================================================="
echo "清理完成!"
echo "=================================================="
