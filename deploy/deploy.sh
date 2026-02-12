#!/bin/bash

set -e  # Exit immediately on error

echo "========================================="
echo "XYZ Agent One-Click Deploy Script"
echo "========================================="

# Auto-detect project root directory (parent of deploy.sh's directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_DIR/frontend"
DEPLOY_DIR="$PROJECT_DIR/deploy"
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
    echo "Usage: sudo bash deploy/deploy.sh"
    exit 1
fi

echo "Project directory: $PROJECT_DIR"
echo "Deploy user: $DEPLOY_USER"

# 1. Build frontend
echo ""
echo "Step 1: Building frontend application..."
cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    print_warning "Frontend dependencies not installed, installing..."
    sudo -u "$DEPLOY_USER" npm install
fi

print_status "Starting frontend build..."
sudo -u "$DEPLOY_USER" npm run build

if [ -d "dist" ]; then
    print_status "Frontend build complete"
else
    print_error "Frontend build failed"
    exit 1
fi

# 2. Generate and install systemd services
echo ""
echo "Step 2: Configuring backend services..."

# Replace placeholders in templates with actual paths to generate .service files
for tpl in "$DEPLOY_DIR"/systemd/*.service; do
    filename=$(basename "$tpl")
    sed -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" \
        -e "s|__DEPLOY_USER__|$DEPLOY_USER|g" \
        "$tpl" > "/etc/systemd/system/$filename"
done

# Replace placeholders in nginx config template
sed -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" \
    "$DEPLOY_DIR/nginx/xyz-agent.conf" > /etc/nginx/sites-available/xyz-agent.conf

print_status "Service files generated and installed"

# Reload systemd
systemctl daemon-reload

# Enable services (auto-start on boot)
systemctl enable xyz-mysql
systemctl enable xyz-agent-mcp
systemctl enable xyz-agent-api
systemctl enable xyz-agent-poller
systemctl enable xyz-agent-job-trigger

print_status "Services set to auto-start on boot"

# Start MySQL (must start before other services)
echo "Starting MySQL..."
systemctl restart xyz-mysql
sleep 5  # Wait for MySQL container to start

# Wait for MySQL to be ready
MYSQL_WAIT=0
while ! docker exec xyz-mysql mysqladmin ping -h localhost -u root -pxyz_root_pass &>/dev/null 2>&1; do
    if [ $MYSQL_WAIT -ge 30 ]; then
        print_warning "MySQL startup timed out, continuing deployment..."
        break
    fi
    sleep 2
    MYSQL_WAIT=$((MYSQL_WAIT + 2))
done
print_status "MySQL is ready"

# Create database tables
echo "Initializing database tables..."
cd "$PROJECT_DIR"
sudo -u "$DEPLOY_USER" "$PROJECT_DIR/.venv/bin/python" src/xyz_agent_context/utils/database_table_management/create_all_tables.py 2>&1 | tail -5
print_status "Database tables initialized"

# Start services
echo "Starting application services..."
systemctl restart xyz-agent-mcp
sleep 3  # Wait for MCP server to start

systemctl restart xyz-agent-api
sleep 2  # Wait for API server to start

systemctl restart xyz-agent-poller
systemctl restart xyz-agent-job-trigger

print_status "Backend services started"

# 3. Configure Nginx
echo ""
echo "Step 3: Configuring Nginx..."

# Backup existing config
if [ -f /etc/nginx/sites-enabled/default ]; then
    if [ ! -f /etc/nginx/sites-enabled/default.backup ]; then
        mv /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default.backup
        print_warning "Backed up existing Nginx config to default.backup"
    else
        rm /etc/nginx/sites-enabled/default
        print_warning "Removed existing Nginx default config"
    fi
fi

# Enable config
ln -sf /etc/nginx/sites-available/xyz-agent.conf /etc/nginx/sites-enabled/

# Test Nginx config
if nginx -t 2>&1 | grep -q "successful"; then
    print_status "Nginx config test passed"
    systemctl restart nginx
    print_status "Nginx restarted"
else
    print_error "Nginx config test failed"
    nginx -t
    exit 1
fi

# 4. Check service status
echo ""
echo "Step 4: Checking service status..."
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
check_service "xyz-mysql" || ALL_OK=false
check_service "xyz-agent-mcp" || ALL_OK=false
check_service "xyz-agent-api" || ALL_OK=false
check_service "xyz-agent-poller" || ALL_OK=false
check_service "xyz-agent-job-trigger" || ALL_OK=false
check_service "nginx" || ALL_OK=false

# 5. Print access info
echo ""
echo "========================================="
echo "Deployment complete!"
echo "========================================="
echo ""

PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "unavailable")

if [ "$PUBLIC_IP" != "unavailable" ]; then
    echo "Access URL: http://$PUBLIC_IP"
else
    echo "Could not auto-detect public IP. Check your AWS console."
fi

echo ""
echo "⚠️  Important: Make sure AWS Security Group has the following ports open:"
echo "   - Port 80 (HTTP) - Source: 0.0.0.0/0"
echo ""
echo "Common management commands:"
echo "  View all service status:"
echo "    sudo systemctl status xyz-mysql xyz-agent-mcp xyz-agent-api xyz-agent-poller xyz-agent-job-trigger nginx"
echo ""
echo "  View live logs:"
echo "    sudo journalctl -u xyz-agent-api -f"
echo ""
echo "  Restart all services:"
echo "    sudo bash $DEPLOY_DIR/restart.sh"
echo ""
echo "  Update code and restart:"
echo "    sudo bash $DEPLOY_DIR/update.sh"
echo ""

if [ "$ALL_OK" = true ]; then
    print_status "All services running. Ready to use!"
else
    print_warning "Some services failed to start. Please check the logs."
fi
