#!/bin/bash

set -e

echo "========================================="
echo "XYZ Agent Code Update Script"
echo "========================================="

# Auto-detect project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_DIR/frontend"
DEPLOY_USER="${SUDO_USER:-$(whoami)}"

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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run this script with sudo"
    echo "Usage: sudo bash deploy/update.sh [--frontend] [--backend] [--all]"
    exit 1
fi

echo "Project directory: $PROJECT_DIR"
echo "Deploy user: $DEPLOY_USER"

# Parse arguments
UPDATE_FRONTEND=false
UPDATE_BACKEND=false

if [ $# -eq 0 ]; then
    # No arguments: update everything by default
    UPDATE_FRONTEND=true
    UPDATE_BACKEND=true
else
    while [[ $# -gt 0 ]]; do
        case $1 in
            --frontend)
                UPDATE_FRONTEND=true
                shift
                ;;
            --backend)
                UPDATE_BACKEND=true
                shift
                ;;
            --all)
                UPDATE_FRONTEND=true
                UPDATE_BACKEND=true
                shift
                ;;
            *)
                print_error "Unknown argument: $1"
                echo "Usage: sudo bash deploy/update.sh [--frontend] [--backend] [--all]"
                exit 1
                ;;
        esac
    done
fi

cd "$PROJECT_DIR"

# 1. Update frontend
if [ "$UPDATE_FRONTEND" = true ]; then
    echo ""
    echo "Step 1: Updating frontend..."
    cd "$FRONTEND_DIR"

    # Check for new dependencies
    if [ -f "package.json" ]; then
        print_status "Checking frontend dependencies..."
        sudo -u "$DEPLOY_USER" npm install
    fi

    # Rebuild
    print_status "Rebuilding frontend..."
    sudo -u "$DEPLOY_USER" npm run build

    if [ -d "dist" ]; then
        print_status "Frontend update complete"
    else
        print_error "Frontend build failed"
        exit 1
    fi

    cd "$PROJECT_DIR"
fi

# 2. Update backend
if [ "$UPDATE_BACKEND" = true ]; then
    echo ""
    echo "Step 2: Updating backend..."

    # Check for new dependencies
    print_status "Checking backend dependencies..."
    sudo -u "$DEPLOY_USER" "$PROJECT_DIR/.venv/bin/uv" sync

    # Sync database table schema
    print_status "Syncing database tables..."
    sudo -u "$DEPLOY_USER" "$PROJECT_DIR/.venv/bin/python" src/xyz_agent_context/utils/database_table_management/create_all_tables.py 2>&1 | tail -5
    print_status "Database table sync complete"

    # Restart backend services
    print_status "Restarting backend services..."

    # Restart in correct order
    systemctl restart xyz-agent-mcp
    sleep 2
    print_status "xyz-agent-mcp restarted"

    systemctl restart xyz-agent-api
    sleep 1
    print_status "xyz-agent-api restarted"

    systemctl restart xyz-agent-poller
    print_status "xyz-agent-poller restarted"

    systemctl restart xyz-agent-job-trigger
    print_status "xyz-agent-job-trigger restarted"
fi

# 3. Check service status
echo ""
echo "Step 3: Checking service status..."
echo ""

check_service() {
    if systemctl is-active --quiet "$1"; then
        print_status "$1 is running"
        return 0
    else
        print_error "$1 is not running"
        echo "  View logs: sudo journalctl -u $1 -n 50"
        return 1
    fi
}

ALL_OK=true
if [ "$UPDATE_BACKEND" = true ]; then
    check_service "xyz-agent-mcp" || ALL_OK=false
    check_service "xyz-agent-api" || ALL_OK=false
    check_service "xyz-agent-poller" || ALL_OK=false
    check_service "xyz-agent-job-trigger" || ALL_OK=false
fi

# 4. Done
echo ""
echo "========================================="
if [ "$ALL_OK" = true ]; then
    print_status "Update complete! All services running."
else
    print_warning "Update complete, but some services may have issues. Check the logs."
fi
echo "========================================="
echo ""

if [ "$UPDATE_BACKEND" = true ]; then
    echo "Tip: If a service fails to start, view its logs:"
    echo "  sudo journalctl -u xyz-agent-api -f"
    echo ""
fi
