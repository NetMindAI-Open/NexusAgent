#!/usr/bin/env bash
# ============================================================================
# EverMemOS 一键启动脚本
#
# 自动完成全部流程：
#   clone 源码 → 安装 Python 依赖 → 启动基础设施 → 等待就绪 → 启动 Web 服务
#
# 用法：
#   bash scripts/start_evermemos.sh            # 一键全部启动
#   bash scripts/start_evermemos.sh --update   # 拉取最新代码后重新安装并启动
#   bash scripts/start_evermemos.sh --stop     # 停止所有服务（含基础设施）
#   bash scripts/start_evermemos.sh --status   # 查看服务状态
# ============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EVERMEMOS_DIR="${PROJECT_ROOT}/.evermemos"
REPO_URL="https://github.com/NetMindAI-Open/EverMemOS.git"
BRANCH="main"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[EverMemOS]${NC} $*"; }
warn()  { echo -e "${YELLOW}[EverMemOS]${NC} $*"; }
ok()    { echo -e "${GREEN}[EverMemOS]${NC} $*"; }
err()   { echo -e "${RED}[EverMemOS]${NC} $*"; }

# ============================================================================
# 前置检查
# ============================================================================
check_prerequisites() {
    local missing=()

    if ! command -v git &>/dev/null; then missing+=("git"); fi
    if ! command -v uv &>/dev/null; then missing+=("uv (https://docs.astral.sh/uv/)"); fi
    if ! command -v docker &>/dev/null; then missing+=("docker"); fi

    # Docker 权限检测（安装后未重新登录时需要 sudo）
    DOCKER_CMD="docker"
    if command -v docker &>/dev/null; then
        if docker info &>/dev/null 2>&1; then
            DOCKER_CMD="docker"
        elif sudo docker info &>/dev/null 2>&1; then
            DOCKER_CMD="sudo docker"
        fi
    fi

    # docker compose (v2 plugin 或 docker-compose 独立命令)
    if $DOCKER_CMD compose version &>/dev/null; then
        COMPOSE_CMD="$DOCKER_CMD compose"
    elif command -v docker-compose &>/dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        missing+=("docker-compose")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        err "缺少必要工具："
        for tool in "${missing[@]}"; do
            err "  - $tool"
        done
        exit 1
    fi
}

# ============================================================================
# --stop：停止所有服务
# ============================================================================
if [[ "${1:-}" == "--stop" ]]; then
    check_prerequisites
    info "停止 EverMemOS Web 服务..."
    pkill -f "uvicorn.*1995" 2>/dev/null && ok "Web 服务已停止" || info "Web 服务未在运行"
    if [ -d "${EVERMEMOS_DIR}" ]; then
        info "停止基础设施容器..."
        cd "${EVERMEMOS_DIR}" && $COMPOSE_CMD down
        ok "全部已停止"
    fi
    exit 0
fi

# ============================================================================
# --status：查看服务状态
# ============================================================================
if [[ "${1:-}" == "--status" ]]; then
    check_prerequisites
    echo ""
    info "=== 基础设施状态 ==="
    if [ -d "${EVERMEMOS_DIR}" ]; then
        cd "${EVERMEMOS_DIR}" && $COMPOSE_CMD ps
    else
        warn "EverMemOS 尚未初始化（运行 bash scripts/start_evermemos.sh）"
    fi
    echo ""
    info "=== Web 服务状态 ==="
    if pgrep -f "uvicorn.*1995" &>/dev/null; then
        ok "Web 服务运行中 (http://localhost:1995)"
    else
        warn "Web 服务未运行"
    fi
    exit 0
fi

# ============================================================================
# 主流程
# ============================================================================
check_prerequisites

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       EverMemOS 一键启动                 ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ---- Step 1: Clone 源码 ----
if [ ! -d "${EVERMEMOS_DIR}" ]; then
    info "[1/5] 首次运行，clone EverMemOS 源码..."
    git clone "${REPO_URL}" -b "${BRANCH}" "${EVERMEMOS_DIR}"
    ok "[1/5] Clone 完成"
elif [[ "${1:-}" == "--update" ]]; then
    info "[1/5] 更新 EverMemOS 代码..."
    cd "${EVERMEMOS_DIR}" && git pull origin "${BRANCH}"
    ok "[1/5] 更新完成"
else
    ok "[1/5] 源码已存在，跳过 clone"
fi

cd "${EVERMEMOS_DIR}"

# ---- Step 2: 创建独立 venv + 安装依赖 ----
if [ ! -d "${EVERMEMOS_DIR}/.venv" ]; then
    info "[2/5] 创建独立虚拟环境 (Python 3.12)..."
    uv venv --python 3.12
    ok "[2/5] 虚拟环境已创建"
    info "[2/5] 安装 Python 依赖（首次安装较慢）..."
    uv sync
    ok "[2/5] 依赖安装完成"
elif [[ "${1:-}" == "--update" ]]; then
    info "[2/5] 重新安装依赖..."
    uv sync
    ok "[2/5] 依赖更新完成"
else
    ok "[2/5] 依赖已安装，跳过"
fi

# ---- Step 3: 生成 .env（首次） ----
if [ ! -f "${EVERMEMOS_DIR}/.env" ]; then
    info "[3/5] 生成默认 .env 配置..."
    cp "${EVERMEMOS_DIR}/env.template" "${EVERMEMOS_DIR}/.env"
    warn "[3/5] 已生成 .env，请编辑 ${EVERMEMOS_DIR}/.env 填写 API Key 等配置"
    warn "      至少需要配置：LLM_API_KEY, VECTORIZE_API_KEY"
    echo ""
    read -p "      按 Enter 继续启动（稍后也可以修改）..."
else
    ok "[3/5] .env 配置已存在"
fi

# ---- Step 4: 启动基础设施（Docker） ----
info "[4/5] 启动基础设施（MongoDB, Elasticsearch, Milvus, Redis）..."

# 先启动不会端口冲突的核心服务
$COMPOSE_CMD up -d mongodb elasticsearch milvus-etcd milvus-minio 2>&1 | grep -v "is obsolete"

# 单独处理 Redis：如果系统已有 Redis 在 6379，跳过 Docker Redis
# 跨平台端口检测
_is_port_up() {
    local port="$1"
    if [ "$(uname -s)" = "Darwin" ]; then
        lsof -iTCP:"$port" -sTCP:LISTEN -P -n &>/dev/null
    else
        ss -tlnp 2>/dev/null | grep -q ":${port} "
    fi
}
if _is_port_up 6379; then
    warn "[4/5] 端口 6379 已被占用，跳过 Docker Redis，使用系统已有的 Redis"
else
    $COMPOSE_CMD up -d redis 2>&1 | grep -v "is obsolete"
fi

# Milvus standalone 依赖 etcd + minio，等它们健康后再启动
sleep 3
$COMPOSE_CMD up -d milvus-standalone 2>&1 | grep -v "is obsolete"

# 等待各服务健康
info "[4/5] 等待服务就绪..."

wait_for_service() {
    local name="$1" check_cmd="$2" max_wait="${3:-60}"
    local elapsed=0
    while ! eval "$check_cmd" &>/dev/null; do
        if [ $elapsed -ge $max_wait ]; then
            warn "      $name 启动超时（${max_wait}s），继续..."
            return 1
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    ok "      $name 就绪"
}

wait_for_service "MongoDB"      "$DOCKER_CMD exec memsys-mongodb mongosh --eval 'db.runCommand({ping:1})'" 60
wait_for_service "Redis"        "redis-cli ping" 30  # 用 redis-cli 检查（无论 Docker 还是系统 Redis）
wait_for_service "Elasticsearch" "curl -sf http://localhost:19200/_cluster/health" 90
wait_for_service "Milvus"       "curl -sf http://localhost:9091/healthz" 120

ok "[4/5] 基础设施已就绪"
$COMPOSE_CMD ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || $COMPOSE_CMD ps
echo ""

# ---- Step 5: 启动 Web 服务 ----
ok "[5/5] 启动 EverMemOS Web 服务..."
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  EverMemOS 服务地址: http://localhost:1995 ║${NC}"
echo -e "${GREEN}║  按 Ctrl+C 停止 Web 服务                 ║${NC}"
echo -e "${GREEN}║  bash scripts/start_evermemos.sh --stop   ║${NC}"
echo -e "${GREEN}║  可停止全部服务（含 Docker）               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""

uv run web
