#!/usr/bin/env bash
# =============================================================================
# CNIS Parser — First-time server setup
# Run as root (or with sudo) on the Hostinger VPS
#
# Usage:
#   git clone <repo> /opt/cnis_parser   (or git pull if already there)
#   cd /opt/cnis_parser
#   sudo bash deploy/setup.sh
# =============================================================================
set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
APP_NAME="cnis_parser"
APP_DIR="/opt/cnis_parser"
APP_USER="cnis"
APP_GROUP="cnis"
VENV_DIR="${APP_DIR}/venv"
ENV_FILE="${APP_DIR}/.env"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
NGINX_CONF="/etc/nginx/sites-enabled/legal_data_api.conf"
NGINX_SNIPPET="/etc/nginx/snippets/cnis_parser.conf"
BIND_HOST="127.0.0.1"
BIND_PORT="8001"
PYTHON_BIN="python3"

# ── Colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# ── Pre-flight checks ───────────────────────────────────────────────────────
echo ""
echo "========================================="
echo "  CNIS Parser — Server Setup"
echo "========================================="
echo ""

[[ $EUID -ne 0 ]] && error "Run this script as root: sudo bash deploy/setup.sh"

# Check Python 3.11+
if ! command -v ${PYTHON_BIN} &>/dev/null; then
    error "Python 3 not found. Install it first: apt install python3 python3-venv python3-pip"
fi

PY_VERSION=$(${PYTHON_BIN} -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
info "Python version: ${PY_VERSION}"

# Check Nginx is installed
command -v nginx &>/dev/null || error "Nginx not found"
info "Nginx found"

# Check the Nginx config exists
[[ -f "${NGINX_CONF}" ]] || error "Nginx config not found at ${NGINX_CONF}"
info "Nginx config found at ${NGINX_CONF}"

# ── Step 1: Create system user ──────────────────────────────────────────────
echo ""
info "Step 1: System user"

if id "${APP_USER}" &>/dev/null; then
    info "User '${APP_USER}' already exists"
else
    useradd --system --no-create-home --shell /usr/sbin/nologin "${APP_USER}"
    info "Created system user '${APP_USER}'"
fi

# ── Step 2: Set directory ownership ─────────────────────────────────────────
info "Step 2: Directory permissions"

chown -R "${APP_USER}:${APP_GROUP}" "${APP_DIR}"
info "Ownership set to ${APP_USER}:${APP_GROUP}"

# ── Step 3: Python virtualenv ───────────────────────────────────────────────
echo ""
info "Step 3: Python virtualenv"

if [[ ! -d "${VENV_DIR}" ]]; then
    ${PYTHON_BIN} -m venv "${VENV_DIR}"
    info "Created virtualenv at ${VENV_DIR}"
else
    info "Virtualenv already exists"
fi

"${VENV_DIR}/bin/pip" install --upgrade pip --quiet
"${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt" --quiet
info "Dependencies installed"

chown -R "${APP_USER}:${APP_GROUP}" "${VENV_DIR}"

# ── Step 4: Environment file ────────────────────────────────────────────────
echo ""
info "Step 4: Environment file"

if [[ -f "${ENV_FILE}" ]]; then
    warn ".env already exists — skipping creation. Review it manually if needed."
else
    read -rp "Enter CNIS_API_KEY (leave empty for random): " INPUT_API_KEY
    if [[ -z "${INPUT_API_KEY}" ]]; then
        INPUT_API_KEY=$(openssl rand -hex 24)
        info "Generated random API key"
    fi

    cat > "${ENV_FILE}" <<EOF
CNIS_API_KEY=${INPUT_API_KEY}
CNIS_MAX_UPLOAD_SIZE_MB=16
CNIS_LOG_LEVEL=INFO
CNIS_CORS_ORIGINS=https://procstudio.api.br,http://localhost:3000
CNIS_DEBUG=false
EOF

    chown "${APP_USER}:${APP_GROUP}" "${ENV_FILE}"
    chmod 600 "${ENV_FILE}"
    info ".env created (permissions: 600)"
    echo ""
    warn "API KEY: ${INPUT_API_KEY}"
    warn "Save this key — you'll need it for client requests (X-API-Key header)"
    echo ""
fi

# ── Step 5: Systemd service ─────────────────────────────────────────────────
echo ""
info "Step 5: Systemd service"

cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=CNIS Parser API (FastAPI/Uvicorn)
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/uvicorn app.main:app --host ${BIND_HOST} --port ${BIND_PORT}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${APP_NAME}

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${APP_DIR}
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${APP_NAME}"
systemctl restart "${APP_NAME}"

# Wait a moment and check status
sleep 2
if systemctl is-active --quiet "${APP_NAME}"; then
    info "Service '${APP_NAME}' is running on ${BIND_HOST}:${BIND_PORT}"
else
    error "Service failed to start. Check: journalctl -u ${APP_NAME} -n 30"
fi

# ── Step 6: Nginx configuration ─────────────────────────────────────────────
echo ""
info "Step 6: Nginx configuration"

cat > "${NGINX_SNIPPET}" <<'EOF'
# CNIS Parser API — reverse proxy
# Included from legal_data_api.conf

location /cnis/ {
    # Strip /cnis prefix, forward to uvicorn
    rewrite ^/cnis/(.*) /$1 break;

    proxy_pass http://127.0.0.1:8001;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # File upload: match app max (16MB)
    client_max_body_size 16M;

    # Timeouts for PDF parsing (can take a few seconds)
    proxy_read_timeout 60s;
    proxy_send_timeout 60s;
}
EOF

info "Created Nginx snippet at ${NGINX_SNIPPET}"

# Check if snippet is already included in the main Nginx config
if grep -q "cnis_parser.conf" "${NGINX_CONF}"; then
    info "Nginx snippet already included in ${NGINX_CONF}"
else
    echo ""
    warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    warn "  MANUAL STEP REQUIRED: Add this line to your Nginx config"
    warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  Edit: ${NGINX_CONF}"
    echo ""
    echo "  Inside the server { ... } block for port 443, add:"
    echo ""
    echo "      include snippets/cnis_parser.conf;"
    echo ""
    echo "  Place it BEFORE the 'location / { return 404; }' block."
    echo ""
    warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    read -rp "Press Enter after you've added the include line (or Ctrl+C to do it later)..."
fi

# Test Nginx config
nginx -t 2>/dev/null && {
    systemctl reload nginx
    info "Nginx reloaded successfully"
} || {
    error "Nginx config test failed! Fix it before continuing: nginx -t"
}

# ── Step 7: Smoke test ──────────────────────────────────────────────────────
echo ""
info "Step 7: Smoke test"

HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "http://${BIND_HOST}:${BIND_PORT}/health" 2>/dev/null || true)
if [[ "${HEALTH}" == "200" ]]; then
    info "Direct health check passed (http://${BIND_HOST}:${BIND_PORT}/health → 200)"
else
    warn "Direct health check returned ${HEALTH} — check: journalctl -u ${APP_NAME} -n 30"
fi

NGINX_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "https://procstudio.api.br/cnis/health" 2>/dev/null || true)
if [[ "${NGINX_HEALTH}" == "200" ]]; then
    info "Nginx proxy check passed (https://procstudio.api.br/cnis/health → 200)"
else
    warn "Nginx proxy returned ${NGINX_HEALTH} — make sure the include line was added to Nginx"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "========================================="
echo "  Setup complete!"
echo "========================================="
echo ""
echo "  Service:   systemctl status ${APP_NAME}"
echo "  Logs:      journalctl -u ${APP_NAME} -f"
echo "  Restart:   systemctl restart ${APP_NAME}"
echo "  Endpoint:  https://procstudio.api.br/cnis/api/v1/parse"
echo "  Health:    https://procstudio.api.br/cnis/health"
echo ""
echo "  Next: set up GitHub Actions for automated deploys"
echo ""
