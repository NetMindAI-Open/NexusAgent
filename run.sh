#!/usr/bin/env bash
# ============================================================================
# NexusAgent Unified Entry Script
#
# One-click: Environment Install → Service Startup → Status Monitor → Stop
#
# Usage:
#   bash run.sh              # Interactive menu
#   bash run.sh install      # Run installation directly
#   bash run.sh run          # Start all services directly
#   bash run.sh status       # View service status
#   bash run.sh stop         # Stop all services
#   bash run.sh update       # Pull latest code & update deps (DB untouched)
# ============================================================================

set -uo pipefail

# ============================================================================
# Global Variables
# ============================================================================
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
EVERMEMOS_DIR="${PROJECT_ROOT}/.evermemos"
EVERMEMOS_REPO="git@github.com:NetMindAI-Open/EverMemOS.git"
EVERMEMOS_BRANCH="main"
TMUX_SESSION="xyz-dev"

# OS Detection
OS_TYPE="$(uname -s)"  # Darwin = macOS, Linux = Linux

# ============================================================================
# Cross-platform port detection (macOS lacks ss, use lsof instead)
# ============================================================================
is_port_up() {
    local port="$1"
    if [ "$OS_TYPE" = "Darwin" ]; then
        lsof -iTCP:"$port" -sTCP:LISTEN -P -n &>/dev/null
    else
        ss -tlnp 2>/dev/null | grep -q ":${port} "
    fi
}

# ============================================================================
# Get process occupying a port (cross-platform)
# ============================================================================
get_port_occupant() {
    local port="$1"
    local occupant=""
    if [ "$OS_TYPE" = "Darwin" ]; then
        occupant=$(lsof -iTCP:"$port" -sTCP:LISTEN -P -n 2>/dev/null | awk 'NR==2{print $1 " (PID: " $2 ")"}')
    else
        occupant=$(ss -tlnp 2>/dev/null | grep ":${port} " | sed 's/.*users:(("//' | sed 's/".*//' | head -1)
    fi
    echo "${occupant:-unknown process}"
}

# ============================================================================
# Color Definitions
# ============================================================================
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'

# Gradient colors (for Banner)
G1='\033[38;5;39m'   # Bright blue
G2='\033[38;5;38m'   # Blue-cyan
G3='\033[38;5;44m'   # Cyan
G4='\033[38;5;43m'   # Cyan-green
G5='\033[38;5;49m'   # Green-cyan
G6='\033[38;5;48m'   # Bright green

# ============================================================================
# Logging Functions
# ============================================================================
info()    { echo -e "${CYAN}  ▸${RESET} $*"; }
success() { echo -e "${GREEN}  ✓${RESET} $*"; }
warn()    { echo -e "${YELLOW}  ⚠${RESET} $*"; }
fail()    { echo -e "${RED}  ✗${RESET} $*"; }
step()    { echo -e "\n${BOLD}${WHITE}  [$1]${RESET} $2"; }

# ============================================================================
# Banner
# ============================================================================
show_banner() {
    clear
    echo ""
    echo -e "${G1}    ███╗   ██╗${G2}███████╗${G3}██╗  ██╗${G4}██╗   ██╗${G5}███████╗${RESET}"
    echo -e "${G1}    ████╗  ██║${G2}██╔════╝${G3}╚██╗██╔╝${G4}██║   ██║${G5}██╔════╝${RESET}"
    echo -e "${G1}    ██╔██╗ ██║${G2}█████╗  ${G3} ╚███╔╝ ${G4}██║   ██║${G5}███████╗${RESET}"
    echo -e "${G1}    ██║╚██╗██║${G2}██╔══╝  ${G3} ██╔██╗ ${G4}██║   ██║${G5}╚════██║${RESET}"
    echo -e "${G1}    ██║ ╚████║${G2}███████╗${G3}██╔╝ ██╗${G4}╚██████╔╝${G5}███████║${RESET}"
    echo -e "${G1}    ╚═╝  ╚═══╝${G2}╚══════╝${G3}╚═╝  ╚═╝${G4} ╚═════╝ ${G5}╚══════╝${RESET}"
    echo ""
    echo -e "${G3}       █████╗  ${G4} ██████╗ ${G5}███████╗${G6}███╗   ██╗████████╗${RESET}"
    echo -e "${G3}      ██╔══██╗ ${G4}██╔════╝ ${G5}██╔════╝${G6}████╗  ██║╚══██╔══╝${RESET}"
    echo -e "${G3}      ███████║ ${G4}██║  ███╗${G5}█████╗  ${G6}██╔██╗ ██║   ██║   ${RESET}"
    echo -e "${G3}      ██╔══██║ ${G4}██║   ██║${G5}██╔══╝  ${G6}██║╚██╗██║   ██║   ${RESET}"
    echo -e "${G3}      ██║  ██║ ${G4}╚██████╔╝${G5}███████╗${G6}██║ ╚████║   ██║   ${RESET}"
    echo -e "${G3}      ╚═╝  ╚═╝ ${G4} ╚═════╝ ${G5}╚══════╝${G6}╚═╝  ╚═══╝   ╚═╝   ${RESET}"
    echo ""
    echo -e "${DIM}    ─────────────────────────────────────────────────${RESET}"
    echo -e "${DIM}      Modular Agent Framework with Long-term Memory${RESET}"
    echo -e "${DIM}    ─────────────────────────────────────────────────${RESET}"
    echo ""
}

# ============================================================================
# Interactive Menu
# ============================================================================
show_menu() {
    echo -e "    ${BOLD}${WHITE}Select an action:${RESET}"
    echo ""
    echo -e "    ${G1}[1]${RESET}  ${BOLD}Install${RESET}   Install all dependencies and environment"
    echo -e "    ${G3}[2]${RESET}  ${BOLD}Run${RESET}       Start all services"
    echo -e "    ${G5}[3]${RESET}  ${BOLD}Status${RESET}    View service status"
    echo -e "    ${YELLOW}[4]${RESET}  ${BOLD}Stop${RESET}      Stop all services"
    echo -e "    ${CYAN}[5]${RESET}  ${BOLD}Update${RESET}    Pull latest code and update dependencies"
    echo -e "    ${DIM}[q]${RESET}  ${DIM}Quit${RESET}      ${DIM}Exit${RESET}"
    echo ""
    read -rp "    > " choice
    echo ""

    case "$choice" in
        1|install)  do_install ;;
        2|run)      do_run ;;
        3|status)   do_status ;;
        4|stop)     do_stop ;;
        5|update)   do_update ;;
        q|Q|quit)   echo -e "    ${DIM}Bye!${RESET}"; exit 0 ;;
        *)          warn "Invalid option: $choice"; show_menu ;;
    esac
}

# ============================================================================
# Docker permission detection: may need sudo if not re-logged after install
# ============================================================================
DOCKER_CMD="docker"

detect_docker_permission() {
    if ! command -v docker &>/dev/null; then
        return
    fi
    # Try running docker without sudo; if it fails, add sudo
    if docker info &>/dev/null 2>&1; then
        DOCKER_CMD="docker"
    elif sudo docker info &>/dev/null 2>&1; then
        DOCKER_CMD="sudo docker"
        warn "Docker requires sudo (re-login to use without sudo)"
    fi
}

# ============================================================================
# Docker Compose command detection (auto-adapts sudo)
# ============================================================================
detect_compose_cmd() {
    detect_docker_permission
    if $DOCKER_CMD compose version &>/dev/null 2>&1; then
        COMPOSE_CMD="$DOCKER_CMD compose"
    elif command -v docker-compose &>/dev/null; then
        # Standalone docker-compose binary doesn't need sudo
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD=""
    fi
}

# ============================================================================
# Docker Health Check: Validate daemon, version, and compose availability
#
# Returns: 0=healthy  1=warnings  2=critical failure
# ============================================================================
check_docker_health() {
    local has_warning=false
    local has_critical=false

    # 1. Check if Docker is installed
    if ! command -v docker &>/dev/null; then
        fail "Docker is not installed"
        info "  Install: https://docs.docker.com/engine/install/"
        return 2
    fi

    # 2. Check if Docker daemon is running
    if ! docker info &>/dev/null 2>&1 && ! sudo docker info &>/dev/null 2>&1; then
        fail "Docker daemon is not running"
        if [ "$OS_TYPE" = "Darwin" ]; then
            info "  Please start Docker Desktop"
        else
            info "  Try: sudo systemctl start docker"
        fi
        return 2
    fi

    detect_docker_permission
    success "Docker daemon is running"

    # 3. Check Docker version (minimum 20.10 for compose v2 support)
    local docker_version
    docker_version=$($DOCKER_CMD version --format '{{.Server.Version}}' 2>/dev/null || echo "unknown")

    if [ "$docker_version" != "unknown" ]; then
        local major minor
        major=$(echo "$docker_version" | cut -d. -f1)
        minor=$(echo "$docker_version" | cut -d. -f2)
        if [ "${major:-0}" -lt 20 ] || { [ "${major:-0}" -eq 20 ] && [ "${minor:-0}" -lt 10 ]; }; then
            warn "Docker version $docker_version is outdated (minimum recommended: 20.10)"
            info "  Some features may not work correctly. Please upgrade Docker."
            has_warning=true
        else
            success "Docker version: $docker_version"
        fi
    else
        warn "Could not determine Docker version"
        has_warning=true
    fi

    # 4. Check Docker Compose
    detect_compose_cmd
    if [ -n "${COMPOSE_CMD:-}" ]; then
        local compose_version
        compose_version=$($COMPOSE_CMD version --short 2>/dev/null || $COMPOSE_CMD version 2>/dev/null | head -1 || echo "unknown")
        success "Docker Compose available: $compose_version"
    else
        fail "Docker Compose is not available"
        info "  'docker compose' (plugin) or 'docker-compose' (standalone) is required"
        has_critical=true
    fi

    # 5. Check Docker disk space
    local docker_root
    docker_root=$($DOCKER_CMD info --format '{{.DockerRootDir}}' 2>/dev/null || echo "")
    if [ -n "$docker_root" ] && command -v df &>/dev/null; then
        local avail_kb
        avail_kb=$(df -k "$docker_root" 2>/dev/null | awk 'NR==2{print $4}')
        if [ -n "$avail_kb" ] && [ "$avail_kb" -lt 1048576 ]; then  # < 1GB
            warn "Low disk space in Docker storage ($docker_root): $(( avail_kb / 1024 )) MB free"
            info "  Docker containers may fail to start. Free up disk space."
            has_warning=true
        fi
    fi

    if [ "$has_critical" = true ]; then
        return 2
    elif [ "$has_warning" = true ]; then
        return 1
    fi
    return 0
}

# ============================================================================
# Port Conflict Pre-check
#
# Args: pairs of "port:service_name" ...
# Returns: 0=all clear  1=conflicts found
# ============================================================================
check_port_conflicts() {
    local has_conflict=false

    for pair in "$@"; do
        local port="${pair%%:*}"
        local service="${pair#*:}"

        if is_port_up "$port"; then
            local occupant
            occupant=$(get_port_occupant "$port")
            warn "Port $port ($service) is already in use by: $occupant"
            has_conflict=true
        fi
    done

    if [ "$has_conflict" = true ]; then
        return 1
    fi
    return 0
}

# ============================================================================
# HTTP Health Check: Verify a service responds to HTTP requests
#
# Args: url [timeout_seconds]
# Returns: 0=healthy  1=unhealthy
# ============================================================================
http_health_check() {
    local url="$1"
    local timeout="${2:-5}"
    curl -sf --max-time "$timeout" "$url" &>/dev/null
}

# ============================================================================
# Post-startup Service Health Verification
# ============================================================================
verify_services_health() {
    echo ""
    echo -e "  ${BOLD}Service Health Verification:${RESET}"
    echo -e "  ${DIM}  ──────────────────────────────────────────${RESET}"

    local all_healthy=true
    local warnings=""

    # FastAPI Backend - HTTP health check
    if is_port_up 8000; then
        if http_health_check "http://localhost:8000/docs" 5; then
            echo -e "    ${GREEN}●${RESET}  FastAPI Backend        ${GREEN}Healthy${RESET}  (HTTP OK on /docs)"
        else
            echo -e "    ${YELLOW}●${RESET}  FastAPI Backend        ${YELLOW}Port open but not responding to HTTP${RESET}"
            warnings="${warnings}\n    - FastAPI: Port 8000 is open but HTTP requests fail."
            warnings="${warnings}\n      Check logs: tmux attach -t ${TMUX_SESSION} then Ctrl-b 2"
            all_healthy=false
        fi
    else
        echo -e "    ${RED}○${RESET}  FastAPI Backend        ${RED}Not running${RESET}  (port 8000)"
        warnings="${warnings}\n    - FastAPI backend failed to start on port 8000."
        warnings="${warnings}\n      Check logs: tmux attach -t ${TMUX_SESSION} then Ctrl-b 2"
        all_healthy=false
    fi

    # MCP Server
    if is_port_up 7801; then
        echo -e "    ${GREEN}●${RESET}  MCP Server             ${GREEN}Running${RESET}  (port 7801)"
    else
        echo -e "    ${RED}○${RESET}  MCP Server             ${RED}Not running${RESET}  (port 7801)"
        warnings="${warnings}\n    - MCP Server failed to start on port 7801."
        warnings="${warnings}\n      Check logs: tmux attach -t ${TMUX_SESSION} then Ctrl-b 5"
        all_healthy=false
    fi

    # Frontend - HTTP health check
    if is_port_up 5173; then
        if http_health_check "http://localhost:5173" 5; then
            echo -e "    ${GREEN}●${RESET}  Frontend               ${GREEN}Healthy${RESET}  (HTTP OK)"
        else
            echo -e "    ${YELLOW}●${RESET}  Frontend               ${YELLOW}Port open but not responding to HTTP${RESET}"
            warnings="${warnings}\n    - Frontend: Port 5173 is open but not serving pages."
            warnings="${warnings}\n      Check logs: tmux attach -t ${TMUX_SESSION} then Ctrl-b 1"
            all_healthy=false
        fi
    else
        echo -e "    ${RED}○${RESET}  Frontend               ${RED}Not running${RESET}  (port 5173)"
        warnings="${warnings}\n    - Frontend failed to start on port 5173."
        warnings="${warnings}\n      Check logs: tmux attach -t ${TMUX_SESSION} then Ctrl-b 1"
        all_healthy=false
    fi

    # MySQL connectivity
    if is_port_up 3306; then
        echo -e "    ${GREEN}●${RESET}  MySQL                  ${GREEN}Running${RESET}  (port 3306)"
    else
        echo -e "    ${YELLOW}○${RESET}  MySQL                  ${YELLOW}Not running${RESET}  (port 3306)"
        warnings="${warnings}\n    - MySQL is not running. Backend services may fail to connect to the database."
        all_healthy=false
    fi

    # Docker container health (check for unhealthy containers)
    if command -v docker &>/dev/null && $DOCKER_CMD info &>/dev/null 2>&1; then
        local unhealthy_containers
        unhealthy_containers=$($DOCKER_CMD ps --filter "health=unhealthy" --format "{{.Names}}" 2>/dev/null)
        if [ -n "$unhealthy_containers" ]; then
            echo ""
            warn "Unhealthy Docker containers detected:"
            while IFS= read -r name; do
                echo -e "    ${RED}●${RESET}  Container: $name"
            done <<< "$unhealthy_containers"
            warnings="${warnings}\n    - Some Docker containers are unhealthy. Run '$DOCKER_CMD ps' to inspect."
            all_healthy=false
        fi

        # Check for containers that exited with errors
        local exited_containers
        exited_containers=$($DOCKER_CMD ps -a --filter "status=exited" --filter "label=com.docker.compose.project" --format "{{.Names}}: exit {{.Status}}" 2>/dev/null | head -5)
        if [ -n "$exited_containers" ]; then
            echo ""
            warn "Docker containers that exited unexpectedly:"
            while IFS= read -r line; do
                echo -e "    ${YELLOW}●${RESET}  $line"
            done <<< "$exited_containers"
            warnings="${warnings}\n    - Some Docker containers have exited. Run '$DOCKER_CMD logs <container>' to check."
            all_healthy=false
        fi
    fi

    echo -e "  ${DIM}  ──────────────────────────────────────────${RESET}"

    # Summary
    if [ "$all_healthy" = true ]; then
        echo ""
        echo -e "  ${GREEN}${BOLD}All services are healthy!${RESET}"
    else
        echo ""
        echo -e "  ${YELLOW}${BOLD}╔══════════════════════════════════════════════════╗${RESET}"
        echo -e "  ${YELLOW}${BOLD}║  ⚠  Some services have issues                   ║${RESET}"
        echo -e "  ${YELLOW}${BOLD}╚══════════════════════════════════════════════════╝${RESET}"
        echo -e "$warnings"
        echo ""
        echo -e "    ${DIM}Tip: Attach to tmux to view service logs:${RESET}"
        echo -e "    ${WHITE}tmux attach -t ${TMUX_SESSION}${RESET}"
        echo -e "    ${DIM}Switch windows with Ctrl-b + n/p${RESET}"
    fi
}

# ============================================================================
# Cross-platform sed -i (macOS needs sed -i '', Linux uses sed -i directly)
# ============================================================================
sed_inplace() {
    if [ "$OS_TYPE" = "Darwin" ]; then
        sed -i '' "$@"
    else
        sed -i "$@"
    fi
}

# ============================================================================
# Start MySQL Docker container and wait until ready
# ============================================================================
start_mysql_docker() {
    detect_compose_cmd
    if [ -z "${COMPOSE_CMD:-}" ]; then
        fail "Docker Compose is not available"
        return 1
    fi

    cd "$PROJECT_ROOT"
    info "Starting MySQL Docker container..."
    $COMPOSE_CMD up -d mysql 2>&1 | grep -v "is obsolete" || true

    # Wait for MySQL to be ready
    local elapsed=0
    local max_wait=60
    printf "    Waiting for MySQL "
    while ! $DOCKER_CMD exec xyz-mysql mysqladmin ping -h localhost -u root -pxyz_root_pass &>/dev/null 2>&1; do
        if [ $elapsed -ge $max_wait ]; then
            echo -e " ${YELLOW}Timeout${RESET}"
            warn "MySQL startup timed out. Check Docker logs: $DOCKER_CMD logs xyz-mysql"
            return 1
        fi
        printf "."
        sleep 2
        elapsed=$((elapsed + 2))
    done
    echo -e " ${GREEN}Ready${RESET}"
    success "MySQL Docker is ready (127.0.0.1:3306)"
}

# ============================================================================
# Ensure MySQL is available (detect port conflicts + interactive handling)
#
# Returns: 0=MySQL ready  1=user skipped or failed
# ============================================================================
ensure_mysql() {
    detect_compose_cmd
    if [ -z "${COMPOSE_CMD:-}" ] || ! command -v docker &>/dev/null; then
        warn "Docker is not available, skipping MySQL Docker startup"
        info "Please ensure you have a MySQL service running"
        return 1
    fi

    # Port not occupied → normal startup
    if ! is_port_up 3306; then
        start_mysql_docker
        return $?
    fi

    # Port occupied → check if it's our own container
    if $DOCKER_CMD ps --format '{{.Names}}' 2>/dev/null | grep -q '^xyz-mysql$'; then
        success "xyz-mysql is already running (port 3306)"
        return 0
    fi

    # ---- Port occupied by another process/container ----
    local occupant=""

    # Try to find the occupant from Docker containers
    occupant=$($DOCKER_CMD ps --filter "publish=3306" --format "{{.Names}}  ({{.Image}})" 2>/dev/null | head -1)
    if [ -z "$occupant" ]; then
        # Non-Docker process occupying the port (system MySQL, etc.)
        occupant=$(get_port_occupant 3306)
        [ -n "$occupant" ] && occupant="System process: $occupant"
    else
        occupant="Docker container: $occupant"
    fi
    [ -z "$occupant" ] && occupant="Unknown process"

    echo ""
    echo -e "  ${BOLD}${YELLOW}╔══════════════════════════════════════════════════╗${RESET}"
    echo -e "  ${BOLD}${YELLOW}║  ⚠  MySQL port 3306 is occupied by another service ║${RESET}"
    echo -e "  ${BOLD}${YELLOW}╚══════════════════════════════════════════════════╝${RESET}"
    echo ""
    echo -e "    Occupant: ${BOLD}${occupant}${RESET}"
    echo -e "    This project requires: ${BOLD}xyz-mysql${RESET} (password: xyz_root_pass)"
    echo ""
    echo -e "    ${DIM}If you use the existing MySQL directly, the password/database${RESET}"
    echo -e "    ${DIM}may not match, causing backend services (FastAPI, MCP) to fail.${RESET}"
    echo ""
    echo -e "    ${G1}[1]${RESET}  ${BOLD}Stop the occupant and start xyz-mysql${RESET}  ${DIM}(Recommended)${RESET}"
    echo -e "    ${G3}[2]${RESET}  ${BOLD}I confirm the existing MySQL config is compatible${RESET}"
    echo -e "    ${YELLOW}[3]${RESET}  ${BOLD}Skip, I will handle it manually later${RESET}"
    echo ""
    read -rp "    > " mysql_choice
    echo ""

    case "$mysql_choice" in
        1)
            info "Stopping the service occupying port 3306..."
            # Stop the Docker container occupying the port
            local container_name
            container_name=$($DOCKER_CMD ps --filter "publish=3306" --format "{{.Names}}" 2>/dev/null | head -1)
            if [ -n "$container_name" ]; then
                $DOCKER_CMD stop "$container_name" 2>/dev/null
                success "Stopped container: $container_name"
            else
                # Non-Docker process, prompt user to handle manually
                fail "The port is not occupied by a Docker container. Please stop it manually."
                echo -e "    ${DIM}Example: sudo systemctl stop mysql${RESET}"
                return 1
            fi
            # Wait for port to be released
            sleep 2
            if is_port_up 3306; then
                fail "Port 3306 is still occupied. Please check manually."
                return 1
            fi
            start_mysql_docker
            return $?
            ;;
        2)
            warn "Using existing MySQL instance. Please ensure .env database config is correct."
            info "If services fail to start later, check DB_HOST / DB_PASSWORD in .env"
            return 0
            ;;
        3|*)
            info "Skipping MySQL startup. Please handle it manually later."
            return 1
            ;;
    esac
}

# ============================================================================
# Install: Guided installation of all dependencies
# ============================================================================
do_install() {
    echo -e "  ${BOLD}${G1}╔══════════════════════════════════════════════════╗${RESET}"
    echo -e "  ${BOLD}${G1}║           Installation Wizard                    ║${RESET}"
    echo -e "  ${BOLD}${G1}╚══════════════════════════════════════════════════╝${RESET}"
    echo ""

    # ---- OS Selection ----
    echo -e "    ${BOLD}${WHITE}Select your operating system:${RESET}"
    echo ""
    echo -e "    ${G1}[1]${RESET}  ${BOLD}Linux${RESET}     Ubuntu / Debian / CentOS etc."
    echo -e "    ${G3}[2]${RESET}  ${BOLD}macOS${RESET}     Intel / Apple Silicon"
    echo -e "    ${G5}[3]${RESET}  ${BOLD}Windows${RESET}   Via WSL2"
    echo ""
    read -rp "    > " os_choice
    echo ""

    case "$os_choice" in
        1) INSTALL_OS="linux" ;;
        2) INSTALL_OS="macos" ;;
        3)
            INSTALL_OS="windows"
            echo -e "  ${BOLD}${YELLOW}╔══════════════════════════════════════════════════╗${RESET}"
            echo -e "  ${BOLD}${YELLOW}║           Windows Users Notice                   ║${RESET}"
            echo -e "  ${BOLD}${YELLOW}╚══════════════════════════════════════════════════╝${RESET}"
            echo ""
            echo -e "    This project needs to run inside ${BOLD}WSL2${RESET} (Windows Subsystem for Linux)."
            echo ""
            echo -e "    If WSL2 is not installed yet, run in PowerShell (Admin):"
            echo -e "    ${WHITE}wsl --install${RESET}"
            echo ""
            echo -e "    After installation, re-run this script in the WSL2 terminal:"
            echo -e "    ${WHITE}bash run.sh install${RESET}"
            echo ""
            echo -e "    ${DIM}Docker Desktop requires WSL2 backend integration:${RESET}"
            echo -e "    ${DIM}Settings → Resources → WSL Integration → Enable your distro${RESET}"
            echo ""
            # Check if actually running in WSL
            if grep -qi microsoft /proc/version 2>/dev/null; then
                success "WSL environment detected, continuing installation..."
                INSTALL_OS="linux"  # WSL follows the Linux flow
            else
                warn "Not currently in a WSL environment. Installation may be incomplete."
                read -rp "    Continue anyway? [y/N] " wsl_continue
                if [[ "$wsl_continue" != "y" && "$wsl_continue" != "Y" ]]; then
                    echo -e "    ${DIM}Please re-run in a WSL2 terminal${RESET}"
                    return 0
                fi
                INSTALL_OS="linux"  # User insists, follow Linux flow
            fi
            ;;
        *)
            warn "Invalid option, defaulting to Linux"
            INSTALL_OS="linux"
            ;;
    esac

    local total_steps=9
    local current=0

    # --- Step 1: uv ---
    current=$((current + 1))
    step "${current}/${total_steps}" "Checking uv (Python package manager)"
    if command -v uv &>/dev/null; then
        success "uv is installed: $(uv --version 2>/dev/null || echo 'unknown')"
    else
        info "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Add uv to the current session PATH
        export PATH="$HOME/.local/bin:$PATH"
        if command -v uv &>/dev/null; then
            success "uv installed successfully"
        else
            fail "uv installation failed. Please install manually: https://docs.astral.sh/uv/"
            return 1
        fi
    fi

    # --- Step 2: Docker ---
    current=$((current + 1))
    step "${current}/${total_steps}" "Checking Docker"

    if command -v docker &>/dev/null; then
        # Docker is installed, run comprehensive health check
        check_docker_health
        local docker_status=$?
        if [ $docker_status -eq 2 ]; then
            fail "Docker has critical issues (see above). Some features will not work."
            echo ""
            read -rp "    Continue anyway? [y/N] " docker_continue
            if [[ "$docker_continue" != "y" && "$docker_continue" != "Y" ]]; then
                return 1
            fi
        elif [ $docker_status -eq 1 ]; then
            warn "Docker has warnings (see above). Continuing with installation..."
        fi
    else
        case "$INSTALL_OS" in
            linux)
                info "Installing Docker (Linux)..."
                if curl -fsSL https://get.docker.com | sh; then
                    sudo usermod -aG docker "$USER" 2>/dev/null || true
                    success "Docker installed successfully"
                    warn "Current user added to docker group. You may need to re-login for it to take effect."
                    # Verify after install
                    check_docker_health || true
                else
                    fail "Docker automatic installation failed"
                    echo -e "    ${DIM}Please install manually: https://docs.docker.com/engine/install/${RESET}"
                    read -rp "    Press Enter to continue (skipping Docker)..."
                fi
                ;;
            macos)
                fail "Docker is not installed"
                echo ""
                echo -e "    macOS: Please install ${BOLD}Docker Desktop${RESET}:"
                echo -e "    ${WHITE}https://www.docker.com/products/docker-desktop/${RESET}"
                echo ""
                echo -e "    ${DIM}Or via Homebrew:${RESET}"
                echo -e "    ${WHITE}brew install --cask docker${RESET}"
                echo ""
                read -rp "    Press Enter after installing Docker..."
                if command -v docker &>/dev/null; then
                    check_docker_health || true
                else
                    warn "Docker still not detected. Docker-related steps may fail."
                fi
                ;;
        esac
    fi

    # --- Step 3: Node.js ---
    current=$((current + 1))
    step "${current}/${total_steps}" "Checking Node.js"
    if command -v node &>/dev/null; then
        success "Node.js is installed: $(node --version)"
    else
        case "$INSTALL_OS" in
            linux)
                info "Installing Node.js 20.x (apt)..."
                if command -v apt-get &>/dev/null; then
                    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
                    sudo apt-get install -y nodejs
                elif command -v yum &>/dev/null; then
                    curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
                    sudo yum install -y nodejs
                else
                    warn "Cannot auto-install Node.js. Please install manually: https://nodejs.org/"
                    read -rp "    Press Enter to continue..."
                fi
                ;;
            macos)
                if command -v brew &>/dev/null; then
                    info "Installing Node.js 20 (Homebrew)..."
                    brew install node@20
                    # Ensure node@20 is in PATH
                    brew link --overwrite node@20 2>/dev/null || true
                else
                    warn "Homebrew not detected. Please install Homebrew or Node.js manually."
                    echo -e "    ${DIM}Install Homebrew:${RESET} ${WHITE}/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"${RESET}"
                    echo -e "    ${DIM}Or install Node.js directly:${RESET} ${WHITE}https://nodejs.org/${RESET}"
                    read -rp "    Press Enter to continue..."
                fi
                ;;
        esac
        if command -v node &>/dev/null; then
            success "Node.js installed successfully: $(node --version)"
        fi
    fi

    # --- Step 4: tmux ---
    current=$((current + 1))
    step "${current}/${total_steps}" "Checking tmux"
    if command -v tmux &>/dev/null; then
        success "tmux is installed: $(tmux -V 2>/dev/null)"
    else
        case "$INSTALL_OS" in
            linux)
                info "Installing tmux (apt)..."
                if command -v apt-get &>/dev/null; then
                    sudo apt-get install -y tmux
                elif command -v yum &>/dev/null; then
                    sudo yum install -y tmux
                else
                    warn "Cannot auto-install tmux. Please install manually."
                fi
                ;;
            macos)
                if command -v brew &>/dev/null; then
                    info "Installing tmux (Homebrew)..."
                    brew install tmux
                else
                    warn "Homebrew not detected. Please install tmux manually."
                    echo -e "    ${WHITE}brew install tmux${RESET}"
                    read -rp "    Press Enter to continue..."
                fi
                ;;
        esac
        if command -v tmux &>/dev/null; then
            success "tmux installed successfully"
        fi
    fi

    # --- Step 5: Claude CLI (required) ---
    current=$((current + 1))
    step "${current}/${total_steps}" "Checking Claude CLI (core dependency)"
    if command -v claude &>/dev/null; then
        success "Claude CLI is installed ($(claude -v 2>/dev/null || echo 'unknown version'))"
    else
        if command -v npm &>/dev/null; then
            info "Installing Claude CLI..."
            npm install -g @anthropic-ai/claude-code
            if command -v claude &>/dev/null; then
                success "Claude CLI installed successfully"
            else
                fail "Claude CLI installation failed"
                echo ""
                echo "    Claude Code is the core Agent runtime for this project."
                echo "    Without it, the system cannot function. Please install manually:"
                echo ""
                echo "      npm install -g @anthropic-ai/claude-code"
                echo ""
                echo "    If npm global install has permission issues, try:"
                echo "      sudo npm install -g @anthropic-ai/claude-code"
                echo "      # Or configure npm prefix:"
                echo "      npm config set prefix ~/.npm-global"
                echo "      export PATH=\$HOME/.npm-global/bin:\$PATH"
                echo ""
                read -rp "    Press Enter to continue (but subsequent runs may fail)..."
            fi
        else
            fail "npm is not available, cannot install Claude CLI"
            echo ""
            echo "    Claude Code is the core Agent runtime for this project."
            echo "    Without it, the system cannot function."
            echo "    Please install Node.js (>= 18) and npm first, then run:"
            echo ""
            echo "      npm install -g @anthropic-ai/claude-code"
            echo ""
            read -rp "    Press Enter to continue (but subsequent runs may fail)..."
        fi
    fi

    # --- Step 6: Python dependencies ---
    current=$((current + 1))
    step "${current}/${total_steps}" "Installing Python dependencies"
    if command -v uv &>/dev/null; then
        info "Running uv sync..."
        cd "$PROJECT_ROOT"
        uv sync
        success "Python dependencies installed"
    else
        fail "uv is not available, cannot install Python dependencies"
    fi

    # --- Step 7: Frontend dependencies ---
    current=$((current + 1))
    step "${current}/${total_steps}" "Installing frontend dependencies"
    if [ -d "${PROJECT_ROOT}/frontend" ] && command -v npm &>/dev/null; then
        info "Running npm install..."
        cd "${PROJECT_ROOT}/frontend"
        npm install --silent
        success "Frontend dependencies installed"
        cd "$PROJECT_ROOT"
    else
        warn "Frontend directory not found or npm not available, skipping"
    fi

    # --- Step 8: MySQL Docker ---
    current=$((current + 1))
    step "${current}/${total_steps}" "Starting MySQL database (Docker)"
    ensure_mysql

    # --- Step 9: .env configuration ---
    current=$((current + 1))
    step "${current}/${total_steps}" "Configuring environment variables (.env)"
    if [ -f "${PROJECT_ROOT}/.env" ]; then
        success ".env already exists"
        read -rp "    Reconfigure .env? [y/N] " reconfigure
        if [[ "$reconfigure" == "y" || "$reconfigure" == "Y" ]]; then
            configure_env
        else
            info "Keeping existing .env, skipping"
        fi
    else
        # Auto-generate .env: copy from .env.example, then ask about API keys
        auto_generate_env
    fi

    # --- Done ---
    echo ""
    echo -e "  ${BOLD}${GREEN}╔══════════════════════════════════════════════════╗${RESET}"
    echo -e "  ${BOLD}${GREEN}║           Installation Complete!                 ║${RESET}"
    echo -e "  ${BOLD}${GREEN}╚══════════════════════════════════════════════════╝${RESET}"
    echo ""
    echo -e "    ${DIM}Next step: Select [2] Run to start all services${RESET}"
    echo ""

    read -rp "    Press Enter to return to menu..."
    show_banner
    show_menu
}

# ============================================================================
# .env interactive configuration
# ============================================================================
configure_env() {
    info "Generating .env configuration file"
    echo ""

    local env_file="${PROJECT_ROOT}/.env"

    # Check if Docker MySQL is running, provide defaults
    local mysql_docker_running=false
    detect_docker_permission
    if $DOCKER_CMD exec xyz-mysql mysqladmin ping -h localhost -u root -pxyz_root_pass &>/dev/null 2>&1; then
        mysql_docker_running=true
        success "Docker MySQL detected running, using default database config"
        echo -e "    ${DIM}(DB: 127.0.0.1:3306/xyz_agent_context, User: root)${RESET}"
        echo ""
    fi

    read -rp "    OPENAI_API_KEY: " val_openai
    read -rp "    GOOGLE_API_KEY: " val_google
    read -rp "    NETMIND_API_KEY (optional, for EverMemOS, press Enter to skip): " val_netmind
    echo ""

    # If Docker MySQL is available, use Docker config by default
    if [ "$mysql_docker_running" = true ]; then
        local val_db_host="127.0.0.1"
        local val_db_port="3306"
        local val_db_name="xyz_agent_context"
        local val_db_user="root"
        local val_db_pass="xyz_root_pass"

        echo -e "    ${DIM}Database config auto-filled (Docker MySQL)${RESET}"
        read -rp "    Customize database config? [y/N] " customize_db
        if [[ "$customize_db" == "y" || "$customize_db" == "Y" ]]; then
            info "Database configuration (MySQL):"
            read -rp "    DB_HOST [127.0.0.1]: " input_host
            read -rp "    DB_PORT [3306]: " input_port
            read -rp "    DB_NAME [xyz_agent_context]: " input_name
            read -rp "    DB_USER [root]: " input_user
            read -rsp "    DB_PASSWORD [xyz_root_pass]: " input_pass
            echo ""
            [ -n "$input_host" ] && val_db_host="$input_host"
            [ -n "$input_port" ] && val_db_port="$input_port"
            [ -n "$input_name" ] && val_db_name="$input_name"
            [ -n "$input_user" ] && val_db_user="$input_user"
            [ -n "$input_pass" ] && val_db_pass="$input_pass"
        fi
    else
        info "Database configuration (MySQL):"
        read -rp "    DB_HOST [localhost]: " val_db_host
        read -rp "    DB_PORT [3306]: " val_db_port
        read -rp "    DB_NAME: " val_db_name
        read -rp "    DB_USER: " val_db_user
        read -rsp "    DB_PASSWORD: " val_db_pass
        echo ""
        val_db_host="${val_db_host:-localhost}"
        val_db_port="${val_db_port:-3306}"
    fi
    echo ""
    read -rp "    ADMIN_SECRET_KEY: " val_admin_key

    cat > "$env_file" << EOF
# =============================================================================
# LLM API Keys
# =============================================================================
OPENAI_API_KEY="${val_openai}"
GOOGLE_API_KEY="${val_google}"
NETMIND_API_KEY="${val_netmind}"

# =============================================================================
# Database (MySQL)
# =============================================================================
DB_HOST="${val_db_host}"
DB_PORT=${val_db_port}
DB_NAME="${val_db_name}"
DB_USER="${val_db_user}"
DB_PASSWORD="${val_db_pass}"

# =============================================================================
# Auth
# =============================================================================
ADMIN_SECRET_KEY="${val_admin_key}"

# =============================================================================
# Workspace (optional)
# =============================================================================
# BASE_WORKING_PATH="./agent_workspace"
EOF

    success ".env generated: ${env_file}"
}

# ============================================================================
# .env auto-generation (zero interaction, use defaults)
# ============================================================================
auto_generate_env() {
    local env_file="${PROJECT_ROOT}/.env"

    # Auto-generate .env with Docker MySQL defaults, API keys left blank
    cat > "$env_file" << 'EOF'
# =============================================================================
# LLM API Keys (please fill in manually after installation)
# =============================================================================
OPENAI_API_KEY=""
GOOGLE_API_KEY=""
NETMIND_API_KEY=""

# =============================================================================
# Database (MySQL) — Docker default config, no changes needed
# =============================================================================
DB_HOST="127.0.0.1"
DB_PORT=3306
DB_NAME="xyz_agent_context"
DB_USER="root"
DB_PASSWORD="xyz_root_pass"

# =============================================================================
# Auth
# =============================================================================
ADMIN_SECRET_KEY="nexus-admin-secret"

# =============================================================================
# Workspace (optional)
# =============================================================================
# BASE_WORKING_PATH="./agent_workspace"
EOF

    success ".env auto-generated (Docker MySQL default config)"

    # Ask whether to fill in API keys now
    echo ""
    read -rp "    Configure API keys now? [y/N] " fill_keys
    if [[ "$fill_keys" == "y" || "$fill_keys" == "Y" ]]; then
        read -rp "    OPENAI_API_KEY: " val_openai
        read -rp "    GOOGLE_API_KEY: " val_google
        read -rp "    NETMIND_API_KEY (optional, for EverMemOS, press Enter to skip): " val_netmind
        if [ -n "$val_openai" ]; then
            sed_inplace "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=\"${val_openai}\"|" "$env_file"
        fi
        if [ -n "$val_google" ]; then
            sed_inplace "s|^GOOGLE_API_KEY=.*|GOOGLE_API_KEY=\"${val_google}\"|" "$env_file"
        fi
        if [ -n "$val_netmind" ]; then
            sed_inplace "s|^NETMIND_API_KEY=.*|NETMIND_API_KEY=\"${val_netmind}\"|" "$env_file"
        fi
        success "API keys updated"
    else
        info "Skipping API key config. You can edit the .env file later."
    fi
}

# ============================================================================
# EverMemOS .env interactive configuration
# ============================================================================
configure_evermemos_env() {
    local env_file="${EVERMEMOS_DIR}/.env"

    # Try to read NETMIND_API_KEY from project .env (set during install)
    local netmind_api_key=""
    if [ -f "${PROJECT_ROOT}/.env" ]; then
        netmind_api_key=$(grep '^NETMIND_API_KEY=' "${PROJECT_ROOT}/.env" 2>/dev/null | sed 's/^NETMIND_API_KEY=//' | tr -d '"' || true)
    fi

    echo ""
    echo -e "  ${BOLD}${G3}╔══════════════════════════════════════════════════╗${RESET}"
    echo -e "  ${BOLD}${G3}║           EverMemOS Configuration Wizard         ║${RESET}"
    echo -e "  ${BOLD}${G3}╚══════════════════════════════════════════════════╝${RESET}"
    echo ""
    echo -e "    ${DIM}EverMemOS provides long-term memory for Agents (conversation${RESET}"
    echo -e "    ${DIM}boundary detection, memory extraction & semantic retrieval).${RESET}"
    echo -e "    ${DIM}All options below can be skipped by pressing Enter.${RESET}"
    echo ""

    # If NETMIND_API_KEY is available, offer one-click auto-config
    if [ -n "$netmind_api_key" ]; then
        echo -e "    ${GREEN}✓ NetMind API Key detected from .env${RESET}"
        echo ""
        echo -e "    ${G1}[1]${RESET}  ${BOLD}Auto-configure with NetMind${RESET}  ${DIM}(Recommended, one-click setup)${RESET}"
        echo -e "         ${DIM}LLM: DeepSeek-V3.2 | Embedding: bge-m3 | Rerank: Disabled${RESET}"
        echo -e "    ${G3}[2]${RESET}  ${BOLD}Manual configuration${RESET}  ${DIM}(Choose providers individually)${RESET}"
        echo ""
        read -rp "    > " auto_choice
        echo ""

        if [[ "$auto_choice" != "2" ]]; then
            # Auto-configure: NetMind LLM + Embedding, Rerank disabled
            sed_inplace "s|^LLM_MODEL=.*|LLM_MODEL=deepseek-ai/DeepSeek-V3.2|" "$env_file"
            sed_inplace "s|^LLM_BASE_URL=.*|LLM_BASE_URL=https://api.netmind.ai/inference-api/openai/v1|" "$env_file"
            sed_inplace "s|^LLM_API_KEY=.*|LLM_API_KEY=${netmind_api_key}|" "$env_file"

            sed_inplace "s|^VECTORIZE_PROVIDER=.*|VECTORIZE_PROVIDER=deepinfra|" "$env_file"
            sed_inplace "s|^VECTORIZE_MODEL=.*|VECTORIZE_MODEL=BAAI/bge-m3|" "$env_file"
            sed_inplace "s|^VECTORIZE_BASE_URL=.*|VECTORIZE_BASE_URL=https://api.netmind.ai/inference-api/openai/v1|" "$env_file"
            sed_inplace "s|^VECTORIZE_API_KEY=.*|VECTORIZE_API_KEY=${netmind_api_key}|" "$env_file"

            sed_inplace "s|^RERANK_PROVIDER=.*|RERANK_PROVIDER=none|" "$env_file"
            sed_inplace "s|^RERANK_API_KEY=.*|RERANK_API_KEY=EMPTY|" "$env_file"
            sed_inplace "s|^RERANK_BASE_URL=.*|RERANK_BASE_URL=|" "$env_file"
            sed_inplace "s|^RERANK_MODEL=.*|RERANK_MODEL=|" "$env_file"
            sed_inplace "s|^RERANK_FALLBACK_PROVIDER=.*|RERANK_FALLBACK_PROVIDER=none|" "$env_file"
            sed_inplace "s|^RERANK_FALLBACK_API_KEY=.*|RERANK_FALLBACK_API_KEY=EMPTY|" "$env_file"
            sed_inplace "s|^RERANK_FALLBACK_BASE_URL=.*|RERANK_FALLBACK_BASE_URL=|" "$env_file"

            echo ""
            success "EverMemOS auto-configured with NetMind (LLM + Embedding + Rerank disabled)"
            echo -e "    ${DIM}Config file: ${env_file}${RESET}"
            return
        fi
    else
        echo -e "    ${BOLD}Skip all${RESET}  → Keep template defaults (vLLM local mode),"
        echo -e "               requires self-hosted vLLM inference service"
        echo -e "    ${BOLD}Fill keys${RESET} → Use cloud API (NetMind / OpenRouter / DeepInfra),"
        echo -e "               no GPU needed, memory features available immediately"
        echo ""
    fi

    echo -e "    ${DIM}Config file: ${EVERMEMOS_DIR}/.env (can be edited manually anytime)${RESET}"
    echo ""

    # ---- 1) LLM service selection ----
    echo -e "    ${BOLD}${WHITE}[1/3] LLM Service${RESET}"
    echo -e "    ${DIM}Used for conversation boundary detection & memory extraction${RESET}"
    echo ""
    echo -e "    ${G1}[1]${RESET}  ${BOLD}NetMind${RESET}       ${DIM}(Recommended, DeepSeek-V3.2, \$0.27/\$0.4 per MToken)${RESET}"
    echo -e "    ${G3}[2]${RESET}  ${BOLD}OpenRouter${RESET}    ${DIM}(grok-4-fast, requires OpenRouter key)${RESET}"
    echo -e "    ${DIM}    Skip → Keep defaults (requires manual config)${RESET}"
    echo ""
    read -rp "    > " llm_choice
    echo ""

    case "$llm_choice" in
        1)
            # NetMind: DeepSeek-V3.2
            sed_inplace "s|^LLM_MODEL=.*|LLM_MODEL=deepseek-ai/DeepSeek-V3.2|" "$env_file"
            sed_inplace "s|^LLM_BASE_URL=.*|LLM_BASE_URL=https://api.netmind.ai/inference-api/openai/v1|" "$env_file"

            if [ -n "$netmind_api_key" ]; then
                sed_inplace "s|^LLM_API_KEY=.*|LLM_API_KEY=${netmind_api_key}|" "$env_file"
                success "Reusing NetMind API Key from .env"
            else
                read -rp "    NetMind API Key (get from netmind.ai): " val_llm_key
                if [ -n "$val_llm_key" ]; then
                    sed_inplace "s|^LLM_API_KEY=.*|LLM_API_KEY=${val_llm_key}|" "$env_file"
                    netmind_api_key="$val_llm_key"
                fi
            fi
            ;;
        2)
            # OpenRouter: keep default model (grok-4-fast)
            read -rp "    LLM_API_KEY (OpenRouter Key): " val_llm_key
            if [ -n "$val_llm_key" ]; then
                sed_inplace "s|^LLM_API_KEY=.*|LLM_API_KEY=${val_llm_key}|" "$env_file"
            fi
            ;;
        *)
            # Skip: if NetMind key available, auto-apply NetMind config
            if [ -n "$netmind_api_key" ]; then
                sed_inplace "s|^LLM_MODEL=.*|LLM_MODEL=deepseek-ai/DeepSeek-V3.2|" "$env_file"
                sed_inplace "s|^LLM_BASE_URL=.*|LLM_BASE_URL=https://api.netmind.ai/inference-api/openai/v1|" "$env_file"
                sed_inplace "s|^LLM_API_KEY=.*|LLM_API_KEY=${netmind_api_key}|" "$env_file"
                info "Skipped — auto-applied NetMind config (DeepSeek-V3.2)"
            else
                info "Keeping LLM default config"
            fi
            ;;
    esac
    echo ""

    # ---- 2) Embedding service selection ----
    echo -e "    ${BOLD}${WHITE}[2/3] Embedding (Vectorization) Service${RESET}"
    echo -e "    ${DIM}Converts memory text into vectors for semantic search${RESET}"
    echo ""
    echo -e "    ${G1}[1]${RESET}  ${BOLD}NetMind${RESET}       ${DIM}(Recommended, bge-m3, no GPU needed)${RESET}"
    echo -e "    ${G3}[2]${RESET}  ${BOLD}DeepInfra${RESET}     ${DIM}(Qwen3-Embedding-4B, requires DeepInfra key)${RESET}"
    echo -e "    ${G3}[3]${RESET}  ${BOLD}vLLM${RESET}          ${DIM}(Self-hosted, requires local GPU)${RESET}"
    echo -e "    ${DIM}    Skip → Keep defaults (vLLM local mode)${RESET}"
    echo ""
    read -rp "    > " embed_choice
    echo ""

    case "$embed_choice" in
        1)
            # NetMind: bge-m3
            sed_inplace "s|^VECTORIZE_PROVIDER=.*|VECTORIZE_PROVIDER=deepinfra|" "$env_file"
            sed_inplace "s|^VECTORIZE_MODEL=.*|VECTORIZE_MODEL=BAAI/bge-m3|" "$env_file"
            sed_inplace "s|^VECTORIZE_BASE_URL=.*|VECTORIZE_BASE_URL=https://api.netmind.ai/inference-api/openai/v1|" "$env_file"
            sed_inplace "s|^VECTORIZE_FALLBACK_PROVIDER=.*|VECTORIZE_FALLBACK_PROVIDER=none|" "$env_file"

            if [ -n "$netmind_api_key" ]; then
                sed_inplace "s|^VECTORIZE_API_KEY=.*|VECTORIZE_API_KEY=${netmind_api_key}|" "$env_file"
                success "Reusing NetMind API Key"
            else
                read -rp "    NetMind API Key (get from netmind.ai): " val_vec_key
                if [ -n "$val_vec_key" ]; then
                    sed_inplace "s|^VECTORIZE_API_KEY=.*|VECTORIZE_API_KEY=${val_vec_key}|" "$env_file"
                fi
            fi
            ;;
        2)
            # DeepInfra: Qwen3-Embedding-4B (original option 1)
            sed_inplace "s|^VECTORIZE_PROVIDER=.*|VECTORIZE_PROVIDER=deepinfra|" "$env_file"
            sed_inplace "s|^VECTORIZE_BASE_URL=.*|VECTORIZE_BASE_URL=https://api.deepinfra.com/v1/openai|" "$env_file"
            sed_inplace "s|^VECTORIZE_FALLBACK_PROVIDER=.*|VECTORIZE_FALLBACK_PROVIDER=vllm|" "$env_file"

            read -rp "    VECTORIZE_API_KEY (DeepInfra Key): " val_vec_key
            if [ -n "$val_vec_key" ]; then
                sed_inplace "s|^VECTORIZE_API_KEY=.*|VECTORIZE_API_KEY=${val_vec_key}|" "$env_file"
            fi

            read -rp "    Fallback vLLM URL [http://localhost:8000/v1]: " val_vec_fb_url
            val_vec_fb_url="${val_vec_fb_url:-http://localhost:8000/v1}"
            sed_inplace "s|^VECTORIZE_FALLBACK_BASE_URL=.*|VECTORIZE_FALLBACK_BASE_URL=${val_vec_fb_url}|" "$env_file"
            sed_inplace "s|^VECTORIZE_FALLBACK_API_KEY=.*|VECTORIZE_FALLBACK_API_KEY=EMPTY|" "$env_file"
            ;;
        3)
            # vLLM self-hosted (original option 2)
            sed_inplace "s|^VECTORIZE_PROVIDER=.*|VECTORIZE_PROVIDER=vllm|" "$env_file"
            sed_inplace "s|^VECTORIZE_API_KEY=.*|VECTORIZE_API_KEY=EMPTY|" "$env_file"
            sed_inplace "s|^VECTORIZE_FALLBACK_PROVIDER=.*|VECTORIZE_FALLBACK_PROVIDER=deepinfra|" "$env_file"

            read -rp "    VECTORIZE_BASE_URL [http://localhost:8000/v1]: " val_vec_url
            val_vec_url="${val_vec_url:-http://localhost:8000/v1}"
            sed_inplace "s|^VECTORIZE_BASE_URL=.*|VECTORIZE_BASE_URL=${val_vec_url}|" "$env_file"

            read -rp "    Fallback DeepInfra API Key (optional, press Enter to skip): " val_vec_fb_key
            if [ -n "$val_vec_fb_key" ]; then
                sed_inplace "s|^VECTORIZE_FALLBACK_API_KEY=.*|VECTORIZE_FALLBACK_API_KEY=${val_vec_fb_key}|" "$env_file"
            fi
            sed_inplace "s|^VECTORIZE_FALLBACK_BASE_URL=.*|VECTORIZE_FALLBACK_BASE_URL=https://api.deepinfra.com/v1/openai|" "$env_file"
            ;;
        *)
            # Skip: if NetMind key available, auto-apply NetMind config
            if [ -n "$netmind_api_key" ]; then
                sed_inplace "s|^VECTORIZE_PROVIDER=.*|VECTORIZE_PROVIDER=deepinfra|" "$env_file"
                sed_inplace "s|^VECTORIZE_MODEL=.*|VECTORIZE_MODEL=BAAI/bge-m3|" "$env_file"
                sed_inplace "s|^VECTORIZE_BASE_URL=.*|VECTORIZE_BASE_URL=https://api.netmind.ai/inference-api/openai/v1|" "$env_file"
                sed_inplace "s|^VECTORIZE_API_KEY=.*|VECTORIZE_API_KEY=${netmind_api_key}|" "$env_file"
                sed_inplace "s|^VECTORIZE_FALLBACK_PROVIDER=.*|VECTORIZE_FALLBACK_PROVIDER=none|" "$env_file"
                info "Skipped — auto-applied NetMind config (bge-m3)"
            else
                info "Keeping Embedding default config (vLLM local, requires self-hosted deployment)"
            fi
            ;;
    esac
    echo ""

    # ---- 3) Rerank service selection (optional) ----
    echo -e "    ${BOLD}${WHITE}[3/3] Rerank Service (Optional)${RESET}"
    echo -e "    ${DIM}Re-ranks retrieved memory fragments by relevance.${RESET}"
    echo -e "    ${DIM}Not required — system uses RRF ranking without it.${RESET}"
    echo ""
    echo -e "    ${G1}[1]${RESET}  ${BOLD}Disable${RESET}       ${DIM}(Recommended, uses RRF ranking only — no extra cost)${RESET}"
    echo -e "    ${G3}[2]${RESET}  ${BOLD}DeepInfra${RESET}     ${DIM}(Improves accuracy, requires DeepInfra key)${RESET}"
    echo -e "    ${G3}[3]${RESET}  ${BOLD}vLLM${RESET}          ${DIM}(Self-hosted, requires local GPU)${RESET}"
    echo -e "    ${DIM}    Skip → Disable rerank (recommended)${RESET}"
    echo ""
    read -rp "    > " rerank_choice
    echo ""

    case "$rerank_choice" in
        2)
            # DeepInfra (original option 1)
            sed_inplace "s|^RERANK_PROVIDER=.*|RERANK_PROVIDER=deepinfra|" "$env_file"
            sed_inplace "s|^RERANK_BASE_URL=.*|RERANK_BASE_URL=https://api.deepinfra.com/v1/inference|" "$env_file"
            sed_inplace "s|^RERANK_FALLBACK_PROVIDER=.*|RERANK_FALLBACK_PROVIDER=vllm|" "$env_file"

            read -rp "    RERANK_API_KEY (DeepInfra Key): " val_rr_key
            if [ -n "$val_rr_key" ]; then
                sed_inplace "s|^RERANK_API_KEY=.*|RERANK_API_KEY=${val_rr_key}|" "$env_file"
            fi

            read -rp "    Fallback vLLM Rerank URL [http://localhost:12000/v1/rerank]: " val_rr_fb_url
            val_rr_fb_url="${val_rr_fb_url:-http://localhost:12000/v1/rerank}"
            sed_inplace "s|^RERANK_FALLBACK_BASE_URL=.*|RERANK_FALLBACK_BASE_URL=${val_rr_fb_url}|" "$env_file"
            sed_inplace "s|^RERANK_FALLBACK_API_KEY=.*|RERANK_FALLBACK_API_KEY=EMPTY|" "$env_file"
            ;;
        3)
            # vLLM self-hosted (original option 2)
            sed_inplace "s|^RERANK_PROVIDER=.*|RERANK_PROVIDER=vllm|" "$env_file"
            sed_inplace "s|^RERANK_API_KEY=.*|RERANK_API_KEY=EMPTY|" "$env_file"
            sed_inplace "s|^RERANK_FALLBACK_PROVIDER=.*|RERANK_FALLBACK_PROVIDER=deepinfra|" "$env_file"

            read -rp "    RERANK_BASE_URL [http://localhost:12000/v1/rerank]: " val_rr_url
            val_rr_url="${val_rr_url:-http://localhost:12000/v1/rerank}"
            sed_inplace "s|^RERANK_BASE_URL=.*|RERANK_BASE_URL=${val_rr_url}|" "$env_file"

            read -rp "    Fallback DeepInfra API Key (optional, press Enter to skip): " val_rr_fb_key
            if [ -n "$val_rr_fb_key" ]; then
                sed_inplace "s|^RERANK_FALLBACK_API_KEY=.*|RERANK_FALLBACK_API_KEY=${val_rr_fb_key}|" "$env_file"
            fi
            sed_inplace "s|^RERANK_FALLBACK_BASE_URL=.*|RERANK_FALLBACK_BASE_URL=https://api.deepinfra.com/v1/inference|" "$env_file"
            ;;
        *)
            # Disable rerank (option 1, skip, or any other input)
            sed_inplace "s|^RERANK_PROVIDER=.*|RERANK_PROVIDER=none|" "$env_file"
            sed_inplace "s|^RERANK_API_KEY=.*|RERANK_API_KEY=EMPTY|" "$env_file"
            sed_inplace "s|^RERANK_BASE_URL=.*|RERANK_BASE_URL=|" "$env_file"
            sed_inplace "s|^RERANK_MODEL=.*|RERANK_MODEL=|" "$env_file"
            sed_inplace "s|^RERANK_FALLBACK_PROVIDER=.*|RERANK_FALLBACK_PROVIDER=none|" "$env_file"
            sed_inplace "s|^RERANK_FALLBACK_API_KEY=.*|RERANK_FALLBACK_API_KEY=EMPTY|" "$env_file"
            sed_inplace "s|^RERANK_FALLBACK_BASE_URL=.*|RERANK_FALLBACK_BASE_URL=|" "$env_file"
            info "Rerank disabled (using RRF ranking only)"
            ;;
    esac

    echo ""
    success "EverMemOS configuration complete: ${env_file}"
}

# ============================================================================
# Run: Start all services
# ============================================================================
do_run() {
    echo -e "  ${BOLD}${G3}╔══════════════════════════════════════════════════╗${RESET}"
    echo -e "  ${BOLD}${G3}║           Starting All Services                  ║${RESET}"
    echo -e "  ${BOLD}${G3}╚══════════════════════════════════════════════════╝${RESET}"
    echo ""

    cd "$PROJECT_ROOT"

    # --- Pre-flight checks ---
    step "0" "Pre-flight checks"
    local has_error=false

    if ! command -v uv &>/dev/null; then
        fail "uv is not installed (please run Install first)"
        has_error=true
    fi
    if ! command -v tmux &>/dev/null; then
        fail "tmux is not installed (please run Install first)"
        has_error=true
    fi
    if ! command -v claude &>/dev/null; then
        fail "Claude CLI is not installed — core Agent runtime missing, cannot process user messages"
        info "  Install: npm install -g @anthropic-ai/claude-code"
        has_error=true
    fi
    if [ ! -f "${PROJECT_ROOT}/.env" ]; then
        fail ".env does not exist (please run Install first)"
        has_error=true
    fi

    # Docker health check
    if command -v docker &>/dev/null; then
        echo ""
        info "Checking Docker health..."
        check_docker_health
        local docker_health=$?
        if [ $docker_health -eq 2 ]; then
            warn "Docker has critical issues. Docker-dependent services will not start."
            warn "You can continue, but MySQL and EverMemOS will be unavailable."
        fi
    else
        warn "Docker is not installed. MySQL and EverMemOS infrastructure will be unavailable."
    fi

    if [ "$has_error" = true ]; then
        echo ""
        fail "Pre-flight checks failed. Please run Install first."
        read -rp "    Press Enter to return to menu..."
        show_banner
        show_menu
        return
    fi
    success "Pre-flight checks passed"

    # --- Port conflict pre-check ---
    step "0.3" "Checking for port conflicts"
    local port_warnings=false
    local conflict_ports=()
    if ! check_port_conflicts \
        "8000:FastAPI Backend" \
        "5173:Frontend Dev" \
        "7801:MCP Server"; then
        port_warnings=true
        # Collect conflicting port PIDs for potential kill
        for pair in "8000:FastAPI Backend" "5173:Frontend Dev" "7801:MCP Server"; do
            local _port="${pair%%:*}"
            if is_port_up "$_port"; then
                conflict_ports+=("$_port")
            fi
        done
        echo ""
        warn "Some required ports are already in use (see above)."
        echo -e "    ${DIM}Services may fail to start if ports are occupied.${RESET}"
        echo ""
        echo -e "    ${G1}[1]${RESET}  ${BOLD}Kill & Continue${RESET}  ${DIM}(kill occupying processes, then start)${RESET}"
        echo -e "    ${G3}[2]${RESET}  ${BOLD}Continue anyway${RESET}  ${DIM}(may conflict with existing services)${RESET}"
        echo -e "    ${G5}[3]${RESET}  ${BOLD}Abort${RESET}           ${DIM}(return to menu)${RESET}"
        echo ""
        read -rp "    > " port_choice
        case "$port_choice" in
            1)
                # Kill processes on conflicting ports
                for _port in "${conflict_ports[@]}"; do
                    local _pid=""
                    if [ "$OS_TYPE" = "Darwin" ]; then
                        _pid=$(lsof -iTCP:"$_port" -sTCP:LISTEN -P -n 2>/dev/null | awk 'NR==2{print $2}')
                    else
                        _pid=$(ss -tlnp 2>/dev/null | grep ":${_port} " | sed 's/.*pid=//' | sed 's/,.*//' | head -1)
                    fi
                    if [ -n "$_pid" ]; then
                        kill "$_pid" 2>/dev/null && info "Killed PID $_pid on port $_port" || warn "Failed to kill PID $_pid on port $_port"
                    fi
                done
                sleep 1
                success "Conflicting processes cleared"
                ;;
            3)
                info "Aborted. Returning to menu."
                echo ""
                read -rp "    Press Enter to return to menu..."
                show_banner
                show_menu
                return
                ;;
            *)
                info "Continuing with existing port conflicts..."
                ;;
        esac
    else
        success "No port conflicts detected (8000, 5173, 7801)"
    fi

    # --- Step 0.5: MySQL Docker ---
    detect_compose_cmd
    if [ -n "${COMPOSE_CMD:-}" ] && command -v docker &>/dev/null; then
        step "0.5" "Starting MySQL database (Docker)"
        ensure_mysql

        # Create database tables (if they don't exist)
        step "0.6" "Initializing database tables"
        if command -v uv &>/dev/null && [ -f "${PROJECT_ROOT}/.env" ]; then
            cd "$PROJECT_ROOT"
            uv run python src/xyz_agent_context/utils/database_table_management/create_all_tables.py 2>&1 | tail -5
            success "Database tables initialized"
        else
            warn "Skipping database table initialization (uv or .env not available)"
        fi
    fi

    # --- Step 1: EverMemOS infrastructure ---
    if [ -n "${COMPOSE_CMD:-}" ] && command -v docker &>/dev/null; then
        step "1" "Starting EverMemOS infrastructure (Docker)"

        # If EverMemOS hasn't been initialized, do it now
        if [ ! -d "${EVERMEMOS_DIR}" ]; then
            info "First run, cloning EverMemOS source..."
            git clone "${EVERMEMOS_REPO}" -b "${EVERMEMOS_BRANCH}" "${EVERMEMOS_DIR}"
            success "Clone complete"
        fi

        # Create venv + install dependencies
        cd "${EVERMEMOS_DIR}"
        if [ ! -d "${EVERMEMOS_DIR}/.venv" ]; then
            info "Creating EverMemOS virtual environment..."
            uv venv --python 3.12
            uv sync
            success "EverMemOS dependencies installed"
        fi

        # Generate .env (if it doesn't exist) and guide configuration
        if [ ! -f "${EVERMEMOS_DIR}/.env" ] && [ -f "${EVERMEMOS_DIR}/env.template" ]; then
            cp "${EVERMEMOS_DIR}/env.template" "${EVERMEMOS_DIR}/.env"
            configure_evermemos_env
        elif [ -f "${EVERMEMOS_DIR}/.env" ]; then
            # If already exists, check if key is still default placeholder
            if grep -q 'LLM_API_KEY=sk-or-v1-xxxx' "${EVERMEMOS_DIR}/.env"; then
                warn "EverMemOS API Key is not configured yet"
                read -rp "    Configure now? [y/N] " configure_em
                if [[ "$configure_em" == "y" || "$configure_em" == "Y" ]]; then
                    configure_evermemos_env
                fi
            fi
        fi

        # Start Docker containers
        info "Starting Docker containers..."
        $COMPOSE_CMD up -d mongodb elasticsearch milvus-etcd milvus-minio 2>&1 | grep -v "is obsolete" || true

        # Redis: skip if system already has one
        if is_port_up 6379; then
            info "Port 6379 already in use, using system Redis"
        else
            $COMPOSE_CMD up -d redis 2>&1 | grep -v "is obsolete" || true
        fi

        sleep 3
        $COMPOSE_CMD up -d milvus-standalone 2>&1 | grep -v "is obsolete" || true

        # --- Step 2: Wait for infrastructure ---
        step "2" "Waiting for infrastructure to be ready"

        wait_for_service() {
            local name="$1" check_cmd="$2" max_wait="${3:-60}"
            local elapsed=0
            printf "    %-20s " "$name"
            while ! eval "$check_cmd" &>/dev/null; do
                if [ $elapsed -ge $max_wait ]; then
                    echo -e "${YELLOW}Timeout${RESET}"
                    return 1
                fi
                printf "."
                sleep 2
                elapsed=$((elapsed + 2))
            done
            echo -e " ${GREEN}Ready${RESET}"
        }

        wait_for_service "MongoDB"       "$DOCKER_CMD exec memsys-mongodb mongosh --eval 'db.runCommand({ping:1})'" 60
        wait_for_service "Redis"         "redis-cli ping" 10
        wait_for_service "Elasticsearch" "curl -sf http://localhost:19200/_cluster/health" 90
        wait_for_service "Milvus"        "curl -sf http://localhost:9091/healthz" 120

        success "Infrastructure is ready"

        # --- Step 3: Start EverMemOS Web ---
        step "3" "Starting EverMemOS Web service (port 1995)"
        if pgrep -f "uvicorn.*1995" &>/dev/null; then
            info "EverMemOS Web is already running"
        else
            cd "${EVERMEMOS_DIR}"
            nohup uv run web > "${EVERMEMOS_DIR}/web.log" 2>&1 &
            # Wait for port 1995 (EverMemOS needs a few seconds to init ES indexes)
            local web_elapsed=0
            printf "    Waiting for port 1995 "
            while ! is_port_up 1995; do
                if [ $web_elapsed -ge 30 ]; then
                    echo -e " ${YELLOW}Timeout${RESET}"
                    warn "EverMemOS Web startup timed out. Check logs: ${EVERMEMOS_DIR}/web.log"
                    break
                fi
                printf "."
                sleep 1
                web_elapsed=$((web_elapsed + 1))
            done
            if is_port_up 1995; then
                echo -e " ${GREEN}Ready${RESET}"
                success "EverMemOS Web started (http://localhost:1995)"
            fi
        fi
        cd "$PROJECT_ROOT"
    else
        warn "Docker not available, skipping EverMemOS infrastructure (steps 1-3)"
    fi

    # --- Step 4: Start tmux session ---
    step "4" "Starting application services (tmux: ${TMUX_SESSION})"

    # Kill existing session if present
    tmux has-session -t "$TMUX_SESSION" 2>/dev/null && tmux kill-session -t "$TMUX_SESSION"

    # Window 0: Control Panel (press q to stop all)
    tmux new-session -d -s "$TMUX_SESSION" -n control -c "$PROJECT_ROOT"
    tmux send-keys -t "$TMUX_SESSION":control "bash start/control.sh" C-m
    info "Control Panel     → tmux window 0 [control]     Press q to exit"

    # Window 1: Frontend
    tmux new-window -t "$TMUX_SESSION" -n frontend -c "$PROJECT_ROOT"
    tmux send-keys -t "$TMUX_SESSION":frontend "bash start/frontend.sh" C-m
    info "Frontend          → tmux window 1 [frontend]    Port 5173"

    # Window 2: FastAPI
    tmux new-window -t "$TMUX_SESSION" -n backend -c "$PROJECT_ROOT"
    tmux send-keys -t "$TMUX_SESSION":backend "bash start/backend.sh" C-m
    info "FastAPI Backend   → tmux window 2 [backend]     Port 8000"

    # Window 3: JobTrigger
    tmux new-window -t "$TMUX_SESSION" -n job-trigger -c "$PROJECT_ROOT"
    tmux send-keys -t "$TMUX_SESSION":job-trigger "bash start/job-trigger.sh" C-m
    info "Job Trigger       → tmux window 3 [job-trigger]"

    # Window 4: ModulePoller
    tmux new-window -t "$TMUX_SESSION" -n poller -c "$PROJECT_ROOT"
    tmux send-keys -t "$TMUX_SESSION":poller "bash start/poller.sh" C-m
    info "Module Poller     → tmux window 4 [poller]"

    # Window 5: MCP
    tmux new-window -t "$TMUX_SESSION" -n mcp -c "$PROJECT_ROOT"
    tmux send-keys -t "$TMUX_SESSION":mcp "bash start/mcp.sh" C-m
    info "MCP Server        → tmux window 5 [mcp]         Ports 7801-7805"

    tmux select-window -t "$TMUX_SESSION":control

    # --- Step 5: Wait for services and verify health ---
    step "5" "Waiting for application services"
    local svc_elapsed=0
    local max_svc_wait=45
    printf "    Waiting for service ports "
    while [ $svc_elapsed -lt $max_svc_wait ]; do
        # Check key ports: MCP(7801) + FastAPI(8000) + Frontend(5173)
        local ready=0
        is_port_up 7801 && ready=$((ready + 1))
        is_port_up 8000 && ready=$((ready + 1))
        is_port_up 5173 && ready=$((ready + 1))
        if [ $ready -ge 3 ]; then
            break
        fi
        printf "."
        sleep 2
        svc_elapsed=$((svc_elapsed + 2))
    done
    echo -e " ${GREEN}Done${RESET}"

    # Give services a moment to fully initialize after ports are open
    sleep 2

    # --- Step 6: Health verification ---
    step "6" "Verifying service health"
    verify_services_health

    # --- Status panel ---
    echo ""
    show_status_panel

    echo ""
    echo -e "  ${BOLD}${GREEN}All services have been started!${RESET}"
    echo ""
    echo -e "    ${DIM}Enter tmux:            ${RESET}${WHITE}tmux attach -t ${TMUX_SESSION}${RESET}"
    echo -e "    ${DIM}Switch windows:        ${RESET}${WHITE}Ctrl-b + n / p${RESET}"
    echo -e "    ${DIM}Stop all:              ${RESET}${WHITE}Switch to [control] window and press q${RESET}"
    echo ""

    read -rp "    Enter tmux? [Y/n] " attach_choice
    if [[ "$attach_choice" != "n" && "$attach_choice" != "N" ]]; then
        tmux attach -t "$TMUX_SESSION"
    fi
}

# ============================================================================
# Status: View all service status
# ============================================================================
do_status() {
    echo -e "  ${BOLD}${G5}╔══════════════════════════════════════════════════╗${RESET}"
    echo -e "  ${BOLD}${G5}║           Service Status                         ║${RESET}"
    echo -e "  ${BOLD}${G5}╚══════════════════════════════════════════════════╝${RESET}"
    echo ""

    show_status_panel

    # Docker container details
    detect_compose_cmd
    if [ -n "${COMPOSE_CMD:-}" ]; then
        echo ""
        echo -e "  ${BOLD}Docker Containers:${RESET}"
        # Project MySQL
        if [ -f "${PROJECT_ROOT}/docker-compose.yaml" ]; then
            cd "${PROJECT_ROOT}"
            $COMPOSE_CMD ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || $COMPOSE_CMD ps 2>/dev/null
        fi
        # EverMemOS
        if [ -d "${EVERMEMOS_DIR}" ]; then
            cd "${EVERMEMOS_DIR}"
            $COMPOSE_CMD ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || $COMPOSE_CMD ps 2>/dev/null
        fi
        cd "$PROJECT_ROOT"
    fi

    # tmux session
    echo ""
    echo -e "  ${BOLD}tmux Session:${RESET}"
    if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
        tmux list-windows -t "$TMUX_SESSION" -F "    #{window_name}: #{pane_current_command}" 2>/dev/null
    else
        echo -e "    ${DIM}tmux session '${TMUX_SESSION}' does not exist${RESET}"
    fi

    # Health verification
    verify_services_health

    echo ""
    read -rp "    Press Enter to return to menu..."
    show_banner
    show_menu
}

# ============================================================================
# Status Panel (port detection)
# ============================================================================
show_status_panel() {
    echo -e "  ${BOLD}Service Port Status:${RESET}"
    echo -e "  ${DIM}  ──────────────────────────────────────────${RESET}"

    check_port() {
        local name="$1" port="$2" url="${3:-}"
        if is_port_up "$port"; then
            printf "    ${GREEN}●${RESET}  %-22s Port %-5s ${GREEN}Running${RESET}" "$name" "$port"
            [ -n "$url" ] && printf "  ${DIM}%s${RESET}" "$url"
            echo ""
        else
            printf "    ${RED}○${RESET}  %-22s Port %-5s ${DIM}Not running${RESET}\n" "$name" "$port"
        fi
    }

    check_port "MySQL"              "3306"
    check_port "EverMemOS Web"     "1995"  "http://localhost:1995"
    check_port "MongoDB"           "27017"
    check_port "Elasticsearch"     "19200"
    check_port "Redis"             "6379"
    check_port "Milvus"            "19530"
    check_port "MCP Server"        "7801"
    check_port "FastAPI Backend"   "8000"  "http://localhost:8000"
    check_port "Frontend Dev"      "5173"  "http://localhost:5173"

    echo -e "  ${DIM}  ──────────────────────────────────────────${RESET}"
}

# ============================================================================
# Update: Pull latest code and re-sync dependencies (DB untouched)
# ============================================================================
do_update() {
    echo -e "  ${BOLD}${CYAN}╔══════════════════════════════════════════════════╗${RESET}"
    echo -e "  ${BOLD}${CYAN}║           Update & Reinstall                     ║${RESET}"
    echo -e "  ${BOLD}${CYAN}╚══════════════════════════════════════════════════╝${RESET}"
    echo ""
    echo -e "    ${DIM}This will pull the latest code and update dependencies.${RESET}"
    echo -e "    ${DIM}Database, .env, and Docker volumes will NOT be touched.${RESET}"
    echo ""

    local total_steps=5
    local current=0

    # --- Step 1: Stop running services ---
    current=$((current + 1))
    step "${current}/${total_steps}" "Stopping running services"

    local services_were_running=false

    if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
        services_were_running=true
        tmux kill-session -t "$TMUX_SESSION"
        success "tmux session '${TMUX_SESSION}' stopped"
    else
        info "No running services detected, skipping"
    fi

    if pgrep -f "uvicorn.*1995" &>/dev/null; then
        pkill -f "uvicorn.*1995" 2>/dev/null
        success "EverMemOS Web stopped"
    fi

    # --- Step 2: Pull latest code ---
    current=$((current + 1))
    step "${current}/${total_steps}" "Pulling latest code (git pull)"
    cd "$PROJECT_ROOT"

    # Check for uncommitted changes
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        warn "You have uncommitted changes in the working directory."
        echo ""
        echo -e "    ${G1}[1]${RESET}  ${BOLD}Stash changes and pull${RESET}  ${DIM}(git stash → pull → stash pop)${RESET}"
        echo -e "    ${G3}[2]${RESET}  ${BOLD}Pull anyway${RESET}             ${DIM}(may cause merge conflicts)${RESET}"
        echo -e "    ${YELLOW}[3]${RESET}  ${BOLD}Skip git pull${RESET}          ${DIM}(only update dependencies)${RESET}"
        echo ""
        read -rp "    > " git_choice
        echo ""

        case "$git_choice" in
            1)
                info "Stashing local changes..."
                git stash
                success "Changes stashed"
                if git pull; then
                    success "Code updated"
                else
                    fail "git pull failed"
                    warn "Your stashed changes are preserved. Run 'git stash pop' to restore."
                fi
                info "Restoring stashed changes..."
                if git stash pop 2>/dev/null; then
                    success "Stashed changes restored"
                else
                    warn "Could not auto-restore stashed changes (possible conflict)."
                    info "Run 'git stash pop' manually to resolve."
                fi
                ;;
            2)
                if git pull; then
                    success "Code updated"
                else
                    fail "git pull failed (likely merge conflicts). Please resolve manually."
                fi
                ;;
            3)
                info "Skipping git pull"
                ;;
            *)
                info "Skipping git pull"
                ;;
        esac
    else
        if git pull; then
            success "Code updated"
        else
            fail "git pull failed. Please check your git remote settings."
        fi
    fi

    # --- Step 3: Update Python dependencies ---
    current=$((current + 1))
    step "${current}/${total_steps}" "Updating Python dependencies (uv sync)"
    if command -v uv &>/dev/null; then
        cd "$PROJECT_ROOT"
        if uv sync; then
            success "Python dependencies updated"
        else
            fail "uv sync failed. Check pyproject.toml for errors."
        fi
    else
        fail "uv is not installed. Run Install first."
    fi

    # --- Step 4: Update frontend dependencies ---
    current=$((current + 1))
    step "${current}/${total_steps}" "Updating frontend dependencies (npm install)"
    if [ -d "${PROJECT_ROOT}/frontend" ] && command -v npm &>/dev/null; then
        cd "${PROJECT_ROOT}/frontend"
        if npm install --silent; then
            success "Frontend dependencies updated"
        else
            fail "npm install failed. Check frontend/package.json for errors."
        fi
        cd "$PROJECT_ROOT"
    else
        warn "Frontend directory not found or npm not available, skipping"
    fi

    # --- Step 5: Update EverMemOS (if initialized) ---
    current=$((current + 1))
    step "${current}/${total_steps}" "Updating EverMemOS"
    if [ -d "${EVERMEMOS_DIR}" ]; then
        cd "${EVERMEMOS_DIR}"
        if git pull 2>/dev/null; then
            success "EverMemOS code updated"
        else
            warn "EverMemOS git pull failed (may not be a git repo or has conflicts)"
        fi
        if command -v uv &>/dev/null && [ -f "${EVERMEMOS_DIR}/pyproject.toml" ]; then
            uv sync 2>/dev/null && success "EverMemOS dependencies updated" || warn "EverMemOS uv sync failed"
        fi
        cd "$PROJECT_ROOT"
    else
        info "EverMemOS not initialized, skipping"
    fi

    # --- Done ---
    echo ""
    echo -e "  ${BOLD}${GREEN}╔══════════════════════════════════════════════════╗${RESET}"
    echo -e "  ${BOLD}${GREEN}║           Update Complete!                        ║${RESET}"
    echo -e "  ${BOLD}${GREEN}╚══════════════════════════════════════════════════╝${RESET}"
    echo ""
    echo -e "    ${DIM}Database and .env were not modified.${RESET}"

    if [ "$services_were_running" = true ]; then
        echo ""
        read -rp "    Services were running before update. Restart now? [Y/n] " restart_choice
        if [[ "$restart_choice" != "n" && "$restart_choice" != "N" ]]; then
            do_run
            return
        fi
    fi

    echo ""
    echo -e "    ${DIM}Next step: Select [2] Run to start all services${RESET}"
    echo ""

    read -rp "    Press Enter to return to menu..."
    show_banner
    show_menu
}

# ============================================================================
# Stop: Stop all services
# ============================================================================
do_stop() {
    echo -e "  ${BOLD}${YELLOW}╔══════════════════════════════════════════════════╗${RESET}"
    echo -e "  ${BOLD}${YELLOW}║           Stopping All Services                  ║${RESET}"
    echo -e "  ${BOLD}${YELLOW}╚══════════════════════════════════════════════════╝${RESET}"
    echo ""

    # --- Stop tmux session ---
    step "1" "Stopping tmux session"
    if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
        tmux kill-session -t "$TMUX_SESSION"
        success "tmux session '${TMUX_SESSION}' stopped"
    else
        info "tmux session does not exist, skipping"
    fi

    # --- Stop EverMemOS Web ---
    step "2" "Stopping EverMemOS Web service"
    if pgrep -f "uvicorn.*1995" &>/dev/null; then
        pkill -f "uvicorn.*1995" 2>/dev/null
        success "EverMemOS Web stopped"
    else
        info "EverMemOS Web is not running"
    fi

    # --- Stop Docker containers ---
    step "3" "Stopping Docker containers"
    detect_compose_cmd
    if [ -n "${COMPOSE_CMD:-}" ]; then
        # Stop project MySQL
        if [ -f "${PROJECT_ROOT}/docker-compose.yaml" ]; then
            cd "${PROJECT_ROOT}"
            $COMPOSE_CMD down 2>/dev/null
            success "MySQL Docker stopped"
        fi
        # Stop EverMemOS infrastructure
        if [ -d "${EVERMEMOS_DIR}" ]; then
            cd "${EVERMEMOS_DIR}"
            $COMPOSE_CMD down 2>/dev/null
            success "EverMemOS Docker containers stopped"
        fi
        cd "$PROJECT_ROOT"
    else
        info "Docker Compose not available, skipping"
    fi

    echo ""
    success "All services stopped"
    echo ""

    read -rp "    Press Enter to return to menu..."
    show_banner
    show_menu
}

# ============================================================================
# Main Entry
# ============================================================================
main() {
    # Support direct command-line arguments
    case "${1:-}" in
        install)  show_banner; do_install ;;
        run)      show_banner; do_run ;;
        status)   show_banner; do_status ;;
        stop)     show_banner; do_stop ;;
        update)   show_banner; do_update ;;
        -h|--help)
            echo "Usage: bash run.sh [install|run|status|stop|update]"
            echo ""
            echo "  install   Install all dependencies and environment"
            echo "  run       Start all services"
            echo "  status    View service status"
            echo "  stop      Stop all services"
            echo "  update    Pull latest code and update dependencies (DB untouched)"
            echo ""
            echo "Run without arguments for an interactive menu."
            exit 0
            ;;
        "")       show_banner; show_menu ;;
        *)        echo "Unknown command: $1"; echo "Usage: bash run.sh [install|run|status|stop|update]"; exit 1 ;;
    esac
}

main "$@"
