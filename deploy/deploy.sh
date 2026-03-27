#!/usr/bin/env bash
# =============================================================================
# CNIS Parser — Deploy script (called by GitHub Actions or manually)
#
# Usage:  sudo bash deploy/deploy.sh
# =============================================================================
set -euo pipefail

APP_NAME="cnis_parser"
APP_DIR="/opt/cnis_parser"
VENV_DIR="${APP_DIR}/venv"
APP_USER="cnis"
APP_GROUP="cnis"

GREEN='\033[0;32m'
NC='\033[0m'
info() { echo -e "${GREEN}[✓]${NC} $*"; }

echo ""
echo "── Deploying CNIS Parser ──"
echo ""

cd "${APP_DIR}"

# Pull latest code
info "Pulling latest code..."
git fetch origin
git reset --hard origin/main

# Update dependencies
info "Installing dependencies..."
"${VENV_DIR}/bin/pip" install -r requirements.txt --quiet

# Fix ownership (in case git pull changed things)
chown -R "${APP_USER}:${APP_GROUP}" "${APP_DIR}"

# Restart service
info "Restarting service..."
systemctl restart "${APP_NAME}"

sleep 2
if systemctl is-active --quiet "${APP_NAME}"; then
    info "Deploy complete — service is running"
else
    echo "[✗] Service failed to start"
    journalctl -u "${APP_NAME}" -n 15 --no-pager
    exit 1
fi

# Health check
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8001/health" 2>/dev/null || true)
if [[ "${HEALTH}" == "200" ]]; then
    info "Health check passed"
else
    echo "[!] Health check returned ${HEALTH}"
    exit 1
fi

echo ""
info "Deploy successful!"
echo ""
