#!/bin/bash

set -e

echo "========================================="
echo "XYZ Agent One-Click Restart Script"
echo "========================================="

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# All backend services (in startup order, MySQL first)
SERVICES=(xyz-mysql xyz-agent-mcp xyz-agent-api xyz-agent-poller xyz-agent-job-trigger)

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run this script with sudo"
    echo "Usage: sudo bash deploy/restart.sh [--all | --backend | service_name...]"
    echo ""
    echo "Examples:"
    echo "  sudo bash deploy/restart.sh               # Restart all backend services"
    echo "  sudo bash deploy/restart.sh --all          # Restart backend + nginx"
    echo "  sudo bash deploy/restart.sh xyz-agent-api  # Restart API service only"
    exit 1
fi

# Parse arguments
INCLUDE_NGINX=false
TARGET_SERVICES=()

if [ $# -eq 0 ] || [ "$1" = "--backend" ]; then
    TARGET_SERVICES=("${SERVICES[@]}")
elif [ "$1" = "--all" ]; then
    TARGET_SERVICES=("${SERVICES[@]}")
    INCLUDE_NGINX=true
else
    # User specified specific service names
    TARGET_SERVICES=("$@")
fi

# 1. Stop services (reverse order: stop downstream before upstream)
echo ""
echo "Step 1: Stopping services..."
for (( i=${#TARGET_SERVICES[@]}-1; i>=0; i-- )); do
    svc="${TARGET_SERVICES[$i]}"
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        systemctl stop "$svc"
        print_status "Stopped $svc"
    else
        print_warning "$svc is not running"
    fi
done

# 2. Reload systemd (in case .service files changed)
systemctl daemon-reload

# 3. Start services in correct order
echo ""
echo "Step 2: Starting services..."
for svc in "${TARGET_SERVICES[@]}"; do
    systemctl start "$svc"

    # MySQL and MCP need extra wait time
    if [ "$svc" = "xyz-mysql" ]; then
        sleep 5
    elif [ "$svc" = "xyz-agent-mcp" ]; then
        sleep 3
    else
        sleep 1
    fi

    if systemctl is-active --quiet "$svc"; then
        print_status "$svc started successfully"
    else
        print_error "$svc failed to start"
        echo "  View logs: sudo journalctl -u $svc -n 50"
    fi
done

# 4. Restart nginx (if requested)
if [ "$INCLUDE_NGINX" = true ]; then
    echo ""
    echo "Step 3: Restarting Nginx..."
    systemctl restart nginx
    if systemctl is-active --quiet nginx; then
        print_status "nginx started successfully"
    else
        print_error "nginx failed to start"
    fi
fi

# 5. Status summary
echo ""
echo "========================================="
echo "Service Status Summary"
echo "========================================="

ALL_OK=true
for svc in "${TARGET_SERVICES[@]}"; do
    if systemctl is-active --quiet "$svc"; then
        print_status "$svc is running"
    else
        print_error "$svc is not running"
        ALL_OK=false
    fi
done

if [ "$INCLUDE_NGINX" = true ]; then
    if systemctl is-active --quiet nginx; then
        print_status "nginx is running"
    else
        print_error "nginx is not running"
        ALL_OK=false
    fi
fi

echo ""
if [ "$ALL_OK" = true ]; then
    print_status "All services restarted successfully!"
else
    print_warning "Some services failed to start. Please check the logs."
fi
