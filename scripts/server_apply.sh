#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/root/quantitative_trading}"
BACKEND_DIR="$PROJECT_ROOT/backend"
DEPLOY_DIR="$PROJECT_ROOT/deploy"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/venv}"
ENV_FILE="$DEPLOY_DIR/.env"

if [[ ! -d "$BACKEND_DIR" ]]; then
  echo "Backend directory not found: $BACKEND_DIR" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "⚠️  警告: $ENV_FILE 不存在，请先创建配置文件！" >&2
  echo "   参考模板: $DEPLOY_DIR/.env.example" >&2
  echo "" >&2
fi

if [[ -f "$ENV_FILE" ]]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

WEB_ROOT="${WEB_ROOT:-/var/www/quantitative_trading}"
QUANT_DB_PATH="${QUANT_DB_PATH:-$PROJECT_ROOT/data/quantitative_trading.db}"

sudo mkdir -p /var/log/quantitative_trading
mkdir -p "$(dirname "$QUANT_DB_PATH")"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

chmod +x "$DEPLOY_DIR/start_backend.sh"
chmod +x "$DEPLOY_DIR/start_scheduler.sh"

sudo cp "$DEPLOY_DIR/supervisor/quantitative-trading-backend.conf" /etc/supervisor/conf.d/quantitative-trading-backend.conf
sudo cp "$DEPLOY_DIR/supervisor/quantitative-trading-scheduler.conf" /etc/supervisor/conf.d/quantitative-trading-scheduler.conf
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart quantitative-trading-backend || sudo supervisorctl start quantitative-trading-backend
sudo supervisorctl restart quantitative-trading-scheduler || sudo supervisorctl start quantitative-trading-scheduler

if [[ -d "$PROJECT_ROOT/frontend/dist" ]]; then
  sudo mkdir -p "$WEB_ROOT"
  sudo rm -rf "$WEB_ROOT"/*
  sudo cp -a "$PROJECT_ROOT/frontend/dist/." "$WEB_ROOT/"
  sudo chmod -R a+rX "$WEB_ROOT"
fi

sudo mkdir -p /etc/nginx/snippets
sudo cp "$DEPLOY_DIR/nginx/quantitative_trading.conf" /etc/nginx/snippets/quantitative_trading.locations.conf

sudo nginx -t
sudo nginx -s reload

echo ""
echo "✅ 部署成功！"
echo ""

