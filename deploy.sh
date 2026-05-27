#!/bin/bash
set -e

echo "================================================"
echo "  PF Intelligence Hub — DigitalOcean Deploy"
echo "================================================"
echo ""

# ── 1. Install Docker ────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "[1/4] Installing Docker..."
  apt-get update -qq
  apt-get install -y docker.io docker-compose-plugin curl
  systemctl enable --now docker
  echo "      Docker installed."
else
  echo "[1/4] Docker already installed — skipping."
fi

# ── 2. Clone or update repo ──────────────────────────
echo "[2/4] Fetching latest code..."
if [ ! -d "/opt/pf-intelligence/.git" ]; then
  git clone https://github.com/Knox8907/pf-intelligence.git /opt/pf-intelligence
else
  git -C /opt/pf-intelligence pull --ff-only
fi
cd /opt/pf-intelligence

# ── 3. Check .env ────────────────────────────────────
echo "[3/4] Checking environment config..."
if [ ! -f "backend/.env" ]; then
  cp backend/.env.example backend/.env
  echo ""
  echo "  ┌─────────────────────────────────────────────────────┐"
  echo "  │  ACTION REQUIRED — fill in backend/.env             │"
  echo "  │                                                     │"
  echo "  │  nano backend/.env                                  │"
  echo "  │                                                     │"
  echo "  │  Required values:                                   │"
  echo "  │    POSTGRES_PASSWORD  — strong random password      │"
  echo "  │    DATABASE_URL       — use same password above     │"
  echo "  │    SECRET_KEY         — min 32 random chars         │"
  echo "  │    ANTHROPIC_API_KEY  — from console.anthropic.com  │"
  echo "  │    ADMIN_EMAIL        — your login email            │"
  echo "  │    ADMIN_PASSWORD     — your login password         │"
  echo "  │                                                     │"
  echo "  │  Then re-run:  bash deploy.sh                       │"
  echo "  └─────────────────────────────────────────────────────┘"
  echo ""
  exit 0
fi

# ── 4. Build and start ───────────────────────────────
echo "[4/4] Building and starting services..."
docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "================================================"
echo "  Deploy complete!"
echo ""
SERVER_IP=$(curl -sf https://ifconfig.me || echo "<your-droplet-ip>")
echo "  App:   http://${SERVER_IP}"
echo ""
echo "  Useful commands:"
echo "    Logs:     docker compose -f docker-compose.prod.yml logs -f"
echo "    Restart:  docker compose -f docker-compose.prod.yml restart"
echo "    Stop:     docker compose -f docker-compose.prod.yml down"
echo "================================================"
