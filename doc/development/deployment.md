# 部署说明

## 目标

- 后端 FastAPI 通过 supervisor 常驻运行
- 数据抓取定时任务通过 supervisor 常驻运行（APScheduler 两个 cron）
- 前端静态文件通过 nginx 提供
- 整站使用路径前缀：`/quantitative_trading/`

## 目录约定（服务器）

- 项目目录：`/root/quantitative_trading`
- Python venv：`/root/quantitative_trading/venv`
- 数据库文件（SQLite）：`/root/quantitative_trading/data/quantitative_trading.db`
- 前端静态文件：`/var/www/quantitative_trading`
- 日志目录：`/var/log/quantitative_trading`

## 一键部署（本地执行）

```bash
export SERVER_HOST=1.2.3.4
export SERVER_USER=root
export SSH_PORT=22
export REMOTE_ROOT=/root/quantitative_trading
export BASE_PATH=/quantitative_trading/
export REMOTE_WEB_ROOT=/var/www/quantitative_trading

bash scripts/deploy_to_server.sh
```

脚本会在本地构建前端，并把 `backend/`、`frontend/dist/`、`deploy/`、`scripts/` 上传到服务器。

## 服务器配置（必须）

在服务器创建配置文件：

```bash
cp /root/quantitative_trading/deploy/.env.example /root/quantitative_trading/deploy/.env
vim /root/quantitative_trading/deploy/.env
```

关键配置项：

- `QUANT_DB_PATH`：SQLite 路径（建议放到 `data/`，避免代码更新覆盖）
- `BACKEND_HOST`/`BACKEND_PORT`：后端监听地址与端口
- `DAILY_JOB_*`、`WEEKLY_JOB_*`：定时任务时间

然后执行：

```bash
cd /root/quantitative_trading
bash scripts/server_apply.sh
```

## nginx

部署脚本会把 nginx 片段复制到：

`/etc/nginx/snippets/quantitative_trading.locations.conf`

要求你的 nginx 主站点配置中已包含类似：

```nginx
include /etc/nginx/snippets/*.locations.conf;
```

## 进程查看

```bash
sudo supervisorctl status
sudo tail -f /var/log/quantitative_trading/backend.log
sudo tail -f /var/log/quantitative_trading/scheduler.log
```

