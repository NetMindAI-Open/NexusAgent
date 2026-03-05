#!/usr/bin/env bash
# ============================================================================
# NarraNexus Desktop App Build Script
#
# Usage:
#   bash build-desktop.sh          # Auto-detect platform
#   bash build-desktop.sh mac      # Build macOS DMG
#   bash build-desktop.sh linux    # Build Linux AppImage/deb
#   bash build-desktop.sh all      # Build all platforms (must run on Mac)
#
# Output: desktop/dist/
# ============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_DIR="${PROJECT_ROOT}/desktop"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

# ─── Prerequisites ─────────────────────────────────

check_prerequisites() {
  info "Checking prerequisites..."

  if ! command -v node &>/dev/null; then
    fail "Node.js not found. Please install Node.js >= 20"
  fi

  NODE_MAJOR=$(node -v | sed 's/v//' | cut -d. -f1)
  if [ "$NODE_MAJOR" -lt 20 ]; then
    fail "Node.js version too old ($(node -v)), requires >= 20"
  fi

  if ! command -v npm &>/dev/null; then
    fail "npm not found"
  fi

  ok "Node.js $(node -v) / npm $(npm -v)"
}

# ─── Install Dependencies ──────────────────────────

install_deps() {
  info "Installing desktop dependencies..."
  cd "$DESKTOP_DIR"

  if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules/.package-lock.json" ]; then
    npm install --no-audit --no-fund
    ok "Dependencies installed"
  else
    ok "Dependencies up to date"
  fi
}

# ─── Build Frontend ────────────────────────────────

build_frontend() {
  info "Building project frontend (frontend/)..."
  cd "$PROJECT_ROOT/frontend"

  if [ ! -d "node_modules" ]; then
    npm install --no-audit --no-fund
  fi

  npm run build
  ok "Frontend built -> frontend/dist/"
}

# ─── Compile Electron ──────────────────────────────

compile_electron() {
  info "Compiling Electron source..."
  cd "$DESKTOP_DIR"
  npx electron-vite build
  ok "Electron compiled -> desktop/out/"
}

# ─── Package ───────────────────────────────────────

package_app() {
  local target="$1"
  cd "$DESKTOP_DIR"

  case "$target" in
    mac)
      info "Packaging macOS DMG..."
      npx electron-builder --mac
      ;;
    linux)
      info "Packaging Linux AppImage/deb..."
      npx electron-builder --linux
      ;;
    all)
      info "Packaging all platforms..."
      npx electron-builder --mac --linux
      ;;
    *)
      fail "Unknown build target: $target"
      ;;
  esac

  ok "Packaging complete!"
  echo ""
  info "Output:"
  ls -lh "$DESKTOP_DIR/dist/"*.{dmg,AppImage,deb,snap} 2>/dev/null || true
  echo ""
}

# ─── Clean ─────────────────────────────────────────

clean() {
  info "Cleaning old build artifacts..."
  rm -rf "$DESKTOP_DIR/dist" "$DESKTOP_DIR/out"
  ok "Clean complete"
}

# ─── Detect Platform ──────────────────────────────

detect_platform() {
  case "$(uname -s)" in
    Darwin) echo "mac" ;;
    Linux)  echo "linux" ;;
    *)      fail "Unsupported OS: $(uname -s)" ;;
  esac
}

# ─── Main ──────────────────────────────────────────

main() {
  local target="${1:-}"

  echo ""
  echo "============================================"
  echo "  NarraNexus Desktop App Build"
  echo "============================================"
  echo ""

  if [ -z "$target" ]; then
    target=$(detect_platform)
    info "Auto-detected platform: $target"
  fi

  check_prerequisites
  clean
  install_deps
  build_frontend
  compile_electron
  package_app "$target"

  echo "============================================"
  ok "All done! Distribute the installer from dist/"
  echo "============================================"
}

main "$@"
