#!/usr/bin/env bash
set -euo pipefail

SERVER_HOST="${SERVER_HOST:-}"
SERVER_USER="${SERVER_USER:-root}"
SSH_PORT="${SSH_PORT:-22}"
REMOTE_ROOT="${REMOTE_ROOT:-/root/quantitative_trading}"
BASE_PATH="${BASE_PATH:-/quantitative_trading/}"
REMOTE_WEB_ROOT="${REMOTE_WEB_ROOT:-/var/www/quantitative_trading}"

if [[ -z "$SERVER_HOST" ]]; then
  echo "SERVER_HOST is required (e.g. xiaochai.tech or 1.2.3.4)" >&2
  exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"
DEPLOY_DIR="$PROJECT_ROOT/deploy"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"

TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

export COPYFILE_DISABLE=1

TAR_OPTS=()
if tar --help 2>&1 | grep -q -- '--no-xattrs'; then
  TAR_OPTS+=(--no-xattrs)
fi
if tar --help 2>&1 | grep -q -- '--no-mac-metadata'; then
  TAR_OPTS+=(--no-mac-metadata)
fi

tar_pack() {
  local out="$1"
  shift

  if ((${#TAR_OPTS[@]})); then
    tar "${TAR_OPTS[@]}" -czf "$out" "$@"
  else
    tar -czf "$out" "$@"
  fi
}

echo "======================================"
echo "🚀 Quantitative Trading 部署脚本"
echo "======================================"
echo ""

if [[ -f "$PROJECT_ROOT/.env" || -f "$PROJECT_ROOT/deploy/.env" ]]; then
  echo "⚠️  警告: 检测到本地 .env 文件"
  echo "   这些文件不会被上传到服务器"
  echo "   请在服务器上单独配置 $REMOTE_ROOT/deploy/.env"
  echo ""
fi

echo "📦 [1/5] 构建前端 (BASE_PATH=$BASE_PATH)..."
(cd "$FRONTEND_DIR" && VITE_BASE_PATH="$BASE_PATH" VITE_API_BASE_PATH="${BASE_PATH%/}/api" npm run build)

echo "📦 [2/5] 打包项目文件..."
FRONT_TGZ="$TMP_DIR/frontend-dist.tgz"
BACK_TGZ="$TMP_DIR/backend.tgz"
DEPLOY_TGZ="$TMP_DIR/deploy.tgz"
SCRIPTS_TGZ="$TMP_DIR/scripts.tgz"

tar_pack "$FRONT_TGZ" -C "$FRONTEND_DIR/dist" .
tar_pack "$BACK_TGZ" -C "$BACKEND_DIR" \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.db' \
  --exclude='crawler/data' \
  --exclude='.DS_Store' \
  --exclude='._*' \
  .

tar_pack "$DEPLOY_TGZ" -C "$DEPLOY_DIR" \
  --exclude='.env' \
  --exclude='.DS_Store' \
  --exclude='._*' \
  .

tar_pack "$SCRIPTS_TGZ" -C "$SCRIPTS_DIR" \
  --exclude='.DS_Store' \
  --exclude='._*' \
  .

echo "   ✅ 打包完成"

echo "🚀 [3/5] 上传到服务器 $SERVER_HOST..."
REMOTE_TMP="/tmp/quantitative_trading_deploy"
REMOTE="$SERVER_USER@$SERVER_HOST"

ssh -p "$SSH_PORT" "$REMOTE" "mkdir -p '$REMOTE_TMP' '$REMOTE_ROOT'" 2>/dev/null

scp -P "$SSH_PORT" "$FRONT_TGZ" "$REMOTE:$REMOTE_TMP/frontend-dist.tgz"
scp -P "$SSH_PORT" "$BACK_TGZ" "$REMOTE:$REMOTE_TMP/backend.tgz"
scp -P "$SSH_PORT" "$DEPLOY_TGZ" "$REMOTE:$REMOTE_TMP/deploy.tgz"
scp -P "$SSH_PORT" "$SCRIPTS_TGZ" "$REMOTE:$REMOTE_TMP/scripts.tgz"

echo "   ✅ 上传完成"

echo "⚙️  [4/5] 在服务器上解压文件..."
ssh -p "$SSH_PORT" "$REMOTE" "set -euo pipefail; \
  mkdir -p '$REMOTE_ROOT/backend' '$REMOTE_ROOT/deploy' '$REMOTE_ROOT/frontend/dist'; \
  mkdir -p '$REMOTE_ROOT/scripts'; \
  mkdir -p '$REMOTE_WEB_ROOT'; \
  \
  echo '   解压前端到项目目录...'; \
  rm -rf '$REMOTE_ROOT/frontend/dist'/*; \
  tar -xzf '$REMOTE_TMP/frontend-dist.tgz' -C '$REMOTE_ROOT/frontend/dist'; \
  \
  echo '   解压前端到web目录...'; \
  rm -rf '$REMOTE_WEB_ROOT'/*; \
  tar -xzf '$REMOTE_TMP/frontend-dist.tgz' -C '$REMOTE_WEB_ROOT'; \
  \
  echo '   解压后端...'; \
  rm -rf '$REMOTE_ROOT/backend'/*; \
  tar -xzf '$REMOTE_TMP/backend.tgz' -C '$REMOTE_ROOT/backend'; \
  \
  echo '   解压部署配置...'; \
  rm -rf '$REMOTE_ROOT/deploy'/*; \
  tar -xzf '$REMOTE_TMP/deploy.tgz' -C '$REMOTE_ROOT/deploy'; \
  \
  echo '   解压脚本...'; \
  tar -xzf '$REMOTE_TMP/scripts.tgz' -C '$REMOTE_ROOT/scripts'; \
  \
  echo '   清理临时文件...'; \
  rm -rf '$REMOTE_TMP'; \
  \
  echo '   ✅ 解压完成'"

echo "⚙️  [5/5] 执行服务器部署..."
echo ""
echo "   请确保服务器上已配置 $REMOTE_ROOT/deploy/.env"
echo "   参考模板: $REMOTE_ROOT/deploy/.env.example"
echo ""

read -p "   配置完成了吗？继续执行 server_apply.sh？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo ""
  echo "ℹ️  部署暂停，请在服务器上完成配置后手动执行："
  echo "   cd $REMOTE_ROOT && bash scripts/server_apply.sh"
  exit 0
fi

echo ""
ssh -p "$SSH_PORT" "$REMOTE" "cd '$REMOTE_ROOT' && bash scripts/server_apply.sh"

echo ""
echo "======================================"
echo "✅ 部署成功完成！"
echo "======================================"
echo "访问地址: https://$SERVER_HOST$BASE_PATH"
echo ""

