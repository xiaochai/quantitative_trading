# A股量化交易系统 —— 项目介绍文档

> 版本：v1.0\
> 更新日期：2026-05-31\
> 仓库地址：<https://github.com/xiaochai/quantitative_trading>

***

## 目录

1. [概述](#1-概述)
2. [代码结构](#2-代码结构)
3. [后端代码详解](#3-后端代码详解)
4. [前端代码详解](#4-前端代码详解)
5. [策略框架与内置策略](#5-策略框架与内置策略)
6. [部署发布](#6-部署发布)
7. [免责声明](#7-免责声明)

***

## 1. 概述

### 1.1 系统定位

**A股量化交易系统**是一套面向个人投资者的全栈量化研究工具，覆盖从数据采集、技术指标计算、策略回测到前端可视化、自动调度的完整链路。系统设计目标是为A股投资决策提供数据驱动、可回测、可复现的量化支撑。

### 1.2 解决的核心问题

| 问题             | 解决方案                            |
| -------------- | ------------------------------- |
| 金融数据获取分散、格式不统一 | 通过 akshare 统一抓取，存入 SQLite 标准化存储 |
| 缺乏可复现的回测环境     | 提供单股策略回测 + 组合轮动回测两套框架           |
| 策略参数调优无据可依     | 策略参数全部可配置，前端实时调整，即时看结果          |
| 每日盯盘选股效率低      | 组合策略支持"收盘后自动选股 → 次日开盘计划"模式      |
| 数据更新依赖手工       | APScheduler 定时任务盘后自动抓取最新行情      |

### 1.3 整体架构

```
+---------------------------------------------------------------+
|                   前端 (Vue 3 + Vite)                          |
|  +--------+  +------------+  +---------+  +------------+       |
|  | 首页   |  | 股票详情    |  | 回测     |  | 组合轮动    |      |
|  +--------+  +------------+  +---------+  +------------+       |
|             ECharts 5 图表 · 可视化收益曲线                     |
+-------------------------------+-------------------------------+
                                | REST API (FastAPI)
+-------------------------------+-------------------------------+
|                   后端 (Python 3.9)                             |
|  +---------------------------------------------------------+  |
|  |              API 层 (FastAPI)                            |  |
|  |  /api/stock/*    /api/backtest/*                         |  |
|  |  /api/portfolio/*    /api/data/*                         |  |
|  +---------------------------------------------------------+  |
|  +----------------------+  +---------------------------+      |
|  |  strategies/         |  |  portfolio/                |      |
|  |  单股策略框架         |  |  组合轮动框架               |      |
|  |  · 布林带回归         |  |  · 沪深300日频轮动          |      |
|  |  · 高频短趋势         |  |                            |      |
|  +----------------------+  +---------------------------+      |
|  +-------------------+     +-----------------------------+     |
|  |  crawler/          |     |  scheduler/                  |     |
|  |  数据抓取脚本       |     |  APScheduler 定时调度         |     |
|  +-------------------+     +-----------------------------+     |
|  +---------------------------------------------------------+  |
|  |         SQLAlchemy ORM → SQLite DB                       |  |
|  +---------------------------------------------------------+  |
+---------------------------------------------------------------+
                                |
+-------------------------------+-------------------------------+
|              外部数据源 (akshare)                               |
|   新浪行情 · 同花顺财务 · 申万行业 · 指数成分股                  |
+---------------------------------------------------------------+
```

### 1.4 技术栈

| 层    | 技术                      | 说明                             |
| ---- | ----------------------- | ------------------------------ |
| 后端框架 | FastAPI (Python)        | 高性能异步 REST API，自动生成 OpenAPI 文档 |
| ORM  | SQLAlchemy              | 数据库抽象层，支持声明式模型定义               |
| 数据库  | SQLite                  | 轻量级文件数据库，部署零依赖，适合个人研究场景        |
| 数据源  | akshare                 | 开源免费的A股金融数据 SDK                |
| 定时任务 | APScheduler             | 进程内 cron 调度器                   |
| 前端框架 | Vue 3 (Composition API) | 现代响应式前端框架                      |
| 构建工具 | Vite 5                  | 极速开发服务器与生产构建                   |
| 图表库  | ECharts 5               | K线图、收益曲线、技术指标叠加                |
| 路由   | Vue Router 4            | 前端 SPA 路由                      |
| 部署   | supervisor + nginx      | 进程守护 + 反向代理                    |

***

## 2. 代码结构

### 2.1 顶层目录

```
quantitative_trading/
├── backend/           # Python 后端（核心业务逻辑）
├── frontend/          # Vue 3 前端（用户界面）
├── deploy/            # 部署配置（supervisor、nginx、环境变量）
├── doc/               # 项目文档（需求、设计、开发指南）
├── scripts/           # 运维脚本（一键开发启动、服务器部署）
└── .gitignore
```

### 2.2 backend/ 目录详解

```
backend/
├── api/
│   └── main.py                    # FastAPI 主应用，定义所有 REST 接口
├── database/
│   ├── database.py                # 数据库连接与初始化
│   └── create_tables.py           # 独立的建表脚本
├── models/
│   ├── __init__.py
│   └── stock_data.py              # 4 张核心数据表的 ORM 模型定义
├── crawler/                       # 数据抓取脚本集
│   ├── README.md                  # 抓取脚本使用说明
│   ├── fetch_all_from_sina.py     # 新浪行情抓取（日线 + 基本信息）
│   ├── fetch_historical_data.py   # 历史日线数据 + 技术指标计算
│   ├── batch_fetch_history_data.py# 批量抓取所有股票历史数据
│   ├── fetch_financials_from_ths.py# 同花顺财务基本面抓取
│   ├── fetch_constituents.py      # 指数成分股列表抓取
│   ├── fetch_sw_industry.py       # 申万行业分类解析
│   ├── fetch_hs300_index.py       # 沪深300指数日线抓取
│   ├── trading_calendar.py        # 交易日历管理
│   ├── explore_listed_date.py     # 上市日期探索工具
│   └── data/                      # 抓取数据本地缓存（JSON 文件）
├── strategies/                    # 单只股票策略框架
│   ├── __init__.py
│   ├── registry.py                # 策略注册表（注册 + 元数据 + 参数默认值）
│   ├── service.py                 # 策略服务层（回测调度、数据加载）
│   ├── utils.py                   # 公共工具（整手计算、指标计算、交易记录）
│   ├── bollinger_reversion.py     # 策略1：布林带均值回归
│   └── short_trend.py             # 策略2：高频短趋势
├── portfolio/                     # 组合轮动策略框架
│   ├── __init__.py
│   ├── README.md                  # 组合框架设计文档
│   ├── registry.py                # 组合策略注册表
│   ├── service.py                 # 组合服务层（回测调度、市场上下文构建）
│   ├── utils.py                   # 组合工具（年化收益、安全转换、下一工作日）
│   └── strategies/
│       ├── __init__.py
│       └── hs300_rotation.py      # 策略3：沪深300日频趋势轮动
└── scheduler/
    ├── jobs.py                    # 定时任务定义（每日盘后 + 每周）
    └── run_scheduler.py           # APScheduler 调度器主进程
```

### 2.3 frontend/ 目录详解

```
frontend/
├── package.json                   # 项目依赖与脚本
├── vite.config.js                 # Vite 构建配置
├── index.html                     # HTML 入口
└── src/
    ├── main.js                    # Vue 应用入口
    ├── App.vue                    # 根组件（全局布局 + 背景）
    ├── api.js                     # API 请求封装
    ├── router/
    │   └── index.js               # 前端路由配置（5 个页面）
    └── views/
        ├── Home.vue              # 首页：股票搜索、列表、快捷入口
        ├── StockDetail.vue       # 股票详情：K线图 + 技术指标 + 基本面
        ├── DataViewer.vue        # 数据浏览：4 张数据表分页查看
        ├── Backtest.vue          # 单股回测：策略配置 + 收益曲线 + 交易明细
        └── PortfolioBacktest.vue # 组合回测：轮动配置 + 组合曲线 + 调仓计划
```

### 2.4 deploy/ 目录详解

```
deploy/
├── .env.example                          # 环境变量模板
├── start_backend.sh                      # supervisor 调用的后端启动脚本
├── start_scheduler.sh                    # supervisor 调用的定时任务启动脚本
├── quantitative_trading_backend.conf      # supervisor 配置：后端进程
├── quantitative_trading_scheduler.conf    # supervisor 配置：定时任务进程
└── quantitative_trading.locations.conf    # nginx location 片段
```

### 2.5 scripts/ 目录详解

```
scripts/
├── run_dev.sh                    # 一键启动开发环境（前后端同时启动）
├── deploy_to_server.sh           # 一键部署到服务器（构建前端 → 打包 → 上传 → 解压）
└── server_apply.sh               # 服务器端配置应用（创建 venv、安装依赖、配置 supervisor）
```

***

## 3. 后端代码详解

### 3.1 数据库设计

系统使用 **SQLite** 作为存储引擎，通过 **SQLAlchemy ORM** 进行数据访问。数据库文件默认路径为项目根目录下的 `quantitative_trading.db`，可通过环境变量 `QUANT_DB_PATH` 自定义。

#### 3.1.1 数据库连接 (`database/database.py`)

采用 FastAPI 标准的依赖注入模式管理数据库会话：

- 连接创建：`engine = create_engine(f"sqlite:///{db_path}")`
- 会话工厂：`SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)`
- 依赖注入：`get_db()` 函数为每个请求创建会话，请求完成后自动关闭

#### 3.1.2 数据表结构 (`models/stock_data.py`)

系统共设计 **4 张核心数据表**：

**表 1：`daily_quotes`（日线行情 + 技术指标）**

| 字段                                       | 类型         | 说明                |
| ---------------------------------------- | ---------- | ----------------- |
| id                                       | INTEGER PK | 自增主键              |
| stock\_code                              | VARCHAR    | 股票代码（如 600036.SH） |
| trade\_date                              | DATE       | 交易日期              |
| open / close / high / low                | FLOAT      | OHLC 价格           |
| volume                                   | INTEGER    | 成交量（股）            |
| amount                                   | FLOAT      | 成交额（元）            |
| change\_pct                              | FLOAT      | 当日涨跌幅（%）          |
| change\_20d\_pct                         | FLOAT      | 近20日涨跌幅（%）        |
| turnover\_rate                           | FLOAT      | 换手率（%）            |
| market\_cap                              | FLOAT      | 总市值（亿元）           |
| pe\_ttm                                  | FLOAT      | 滚动市盈率             |
| ma5 / ma20 / ma60                        | FLOAT      | 移动均线（5/20/60日）    |
| macd / macd\_signal / macd\_hist         | FLOAT      | MACD 指标三件套        |
| rsi                                      | FLOAT      | RSI 相对强弱指标（14日）   |
| boll\_upper / boll\_middle / boll\_lower | FLOAT      | 布林带三轨（20日，2倍标准差）  |

> **唯一约束**：`(stock_code, trade_date)` 组合唯一，保证数据不重复。
>
> **技术指标计算**：MA、MACD、RSI、布林带均由抓取脚本在入库时自动计算并存储，回测时直接读取，避免重复计算。

**表 2：`index_daily_quotes`（指数日线行情）**

| 字段                        | 类型         | 说明                     |
| ------------------------- | ---------- | ---------------------- |
| id                        | INTEGER PK | 自增主键                   |
| index\_code               | VARCHAR    | 指数代码（如 000300 代表沪深300） |
| trade\_date               | DATE       | 交易日期                   |
| open / close / high / low | FLOAT      | OHLC 价格                |
| volume                    | INTEGER    | 成交量                    |
| amount                    | FLOAT      | 成交额                    |
| change\_pct               | FLOAT      | 涨跌幅                    |

> **用途**：组合回测中作为基准（benchmark），对比策略收益与指数表现；市场风控中判断指数是否跌破均线。

**表 3：`stock_fundamentals`（基本面数据）**

| 字段                  | 类型         | 说明        |
| ------------------- | ---------- | --------- |
| id                  | INTEGER PK | 自增主键      |
| stock\_code         | VARCHAR    | 股票代码      |
| report\_date        | DATE       | 报告期日期     |
| pb                  | FLOAT      | 市净率       |
| roe                 | FLOAT      | 净资产收益率（%） |
| eps                 | FLOAT      | 每股收益（元）   |
| eps\_ttm            | FLOAT      | 每股收益（TTM） |
| net\_profit\_growth | FLOAT      | 净利润增速（%）  |
| revenue\_growth     | FLOAT      | 营业收入增速（%） |
| dividend\_yield     | FLOAT      | 股息率（%）    |

> **数据来源**：同花顺 `ak.stock_financial_abstract_ths()`，按季报节点更新。

**表 4：`stock_info`（股票元信息）**

| 字段              | 类型         | 说明                                   |
| --------------- | ---------- | ------------------------------------ |
| id              | INTEGER PK | 自增主键                                 |
| stock\_code     | VARCHAR    | 股票代码                                 |
| stock\_name     | VARCHAR    | 股票名称                                 |
| industry\_sw1   | VARCHAR    | 申万一级行业                               |
| industry\_sw2   | VARCHAR    | 申万二级行业                               |
| is\_st          | BOOLEAN    | 是否 ST                                |
| is\_star\_st    | BOOLEAN    | 是否 \*ST                              |
| is\_delisted    | BOOLEAN    | 是否已退市                                |
| delisted\_date  | DATE       | 退市日期                                 |
| listed\_date    | DATE       | 上市日期                                 |
| component\_tags | TEXT       | 成分股标签（JSON 数组，如 `["沪深300", "创业板指"]`） |
| report\_date    | DATE       | 报告日期（标记状态快照时间）                       |

> **设计特点**：`stock_info` 表按 `(stock_code, report_date)` 保留历史快照。当股票状态发生变化（ST、退市、名称变更等）时，插入新记录而非覆盖旧记录。查询最新状态时按 `report_date` 倒序取第一条。

#### 3.1.3 表关系概览

```
stock_info (元信息)          stock_fundamentals (基本面)
   stock_code ◄────────────── stock_code
   stock_name                 report_date
   industry_sw1/sw2           pb / roe / eps
   component_tags             net_profit_growth

daily_quotes (日线行情)       index_daily_quotes (指数行情)
   stock_code                   index_code
   trade_date                   trade_date
   价格 + 技术指标               价格数据
```

### 3.2 API 接口一览

所有接口由 `backend/api/main.py` 定义。

| 方法   | 路径                                    | 功能       | 关键参数                        |
| ---- | ------------------------------------- | -------- | --------------------------- |
| GET  | /api/stock/{stock\_code}/quotes       | 单股历史行情   | stock\_code（路径参数）           |
| GET  | /api/stock/{stock\_code}/fundamentals | 单股基本面    | stock\_code                 |
| GET  | /api/stock/{stock\_code}/info         | 单股元信息    | stock\_code                 |
| GET  | /api/stocks                           | 股票列表     | index（指数筛选）、search（模糊搜索）    |
| GET  | /api/stocks/summary                   | 系统概览统计   | 无                           |
| GET  | /api/data/daily\_quotes               | 日线数据分页   | page、page\_size、stock\_code |
| GET  | /api/data/index\_daily\_quotes        | 指数数据分页   | page、page\_size、index\_code |
| GET  | /api/data/stock\_fundamentals         | 基本面数据分页  | page、page\_size、stock\_code |
| GET  | /api/data/stock\_info                 | 元信息数据分页  | page、page\_size、stock\_code |
| POST | /api/backtest/run                     | 执行单股回测   | BacktestRunRequest 模型       |
| GET  | /api/backtest/strategies              | 获取策略目录   | 无                           |
| POST | /api/portfolio/backtest               | 执行组合回测   | PortfolioBacktestRequest 模型 |
| POST | /api/portfolio/plan                   | 生成次日调仓计划 | PortfolioPlanRequest 模型     |
| GET  | /api/portfolio/strategies             | 获取组合策略目录 | 无                           |

### 3.3 数据抓取模块 (`crawler/`)

数据抓取是系统的基础设施层，负责从 akshare 等外部数据源获取数据，计算技术指标，并写入数据库。

#### 3.3.1 抓取脚本职责矩阵

| 脚本                             | 职责              | 数据源                                 | 写入表                                 |
| ------------------------------ | --------------- | ----------------------------------- | ----------------------------------- |
| `fetch_all_from_sina.py`       | 每日盘后行情 + 基本信息   | `ak.stock_zh_a_spot_em()`           | `daily_quotes`、`stock_info`         |
| `fetch_historical_data.py`     | 历史日线 + 计算所有技术指标 | `ak.stock_zh_a_hist()`              | `daily_quotes`                      |
| `batch_fetch_history_data.py`  | 批量遍历所有股票        | 调用上述脚本                              | `daily_quotes`、`stock_fundamentals` |
| `fetch_financials_from_ths.py` | 财务基本面           | `ak.stock_financial_abstract_ths()` | `stock_fundamentals`                |
| `fetch_constituents.py`        | 指数成分股列表         | `ak.index_stock_cons()`             | `stock_info.component_tags`         |
| `fetch_sw_industry.py`         | 申万行业分类          | Excel 文件解析                          | `stock_info.industry_sw1/sw2`       |
| `fetch_hs300_index.py`         | 沪深300指数日线       | `ak.stock_zh_index_daily_em()`      | `index_daily_quotes`                |
| `trading_calendar.py`          | 交易日历缓存          | 新浪接口                                | 本地文件缓存                              |
| `explore_listed_date.py`       | 上市日期探索补全        | 多数据源尝试                              | `stock_info.listed_date`            |

#### 3.3.2 数据流设计

抓取脚本遵循统一的数据流模式：

```
外部数据源 (akshare)
       │
       ▼
获取原始 DataFrame
       │
       ▼
本地 JSON 文件缓存 (crawler/data/)
       │  （避免重复请求，失败时可重试）
       ▼
数据清洗与字段映射
       │
       ▼
技术指标计算（仅 fetch_historical_data.py）
┌───────┬────────┬────────┬───────────┐
│  MA   │  MACD  │  RSI   │ 布林带     │
│ 5/20/60│ 12/26/9│ 14日  │ 20日/2σ   │
└───────┴────────┴────────┴───────────┘
       │
       ▼
Upsert 写入 SQLite
(INSERT OR REPLACE via unique constraint)
```

#### 3.3.3 关键设计决策

- **本地文件缓存**：每个脚本在调用 API 前先检查本地 JSON 文件是否存在（按日期/参数命名），避免重复请求和 API 限流。
- **增量更新**：每日盘后脚本只抓取当日数据，通过唯一约束自动去重。
- **技术指标预计算**：在入库时一次性计算好 MA/MACD/RSI/布林带，回测时直接读取，避免每次回测重复计算。
- **stock\_info 历史快照**：状态变更时插入新记录而非 UPDATE，保留完整的状态变更历史。

### 3.4 定时调度模块 (`scheduler/`)

基于 **APScheduler** 实现两个定时任务，通过 supervisor 常驻运行。

#### 调度架构

```
run_scheduler.py (APScheduler BlockingScheduler)
    │
    ├── 每日盘后任务 (Cron: 默认 18:30)
    │   ├── 更新交易日历
    │   ├── 检查是否交易日（非交易日跳过）
    │   ├── 新浪行情抓取 (fetch_all_from_sina.py)
    │   └── 沪深300指数抓取 (fetch_hs300_index.py)
    │
    └── 每周任务 (Cron: 默认 周六 06:30)
        ├── 更新交易日历
        ├── 申万行业分类更新 (fetch_sw_industry.py)
        └── 成分股标签更新 (fetch_constituents.py)
```

#### 配置方式

通过环境变量自定义执行时间：

| 环境变量                | 默认值           | 说明     |
| ------------------- | ------------- | ------ |
| `DAILY_JOB_HOUR`    | 18            | 每日任务小时 |
| `DAILY_JOB_MINUTE`  | 30            | 每日任务分钟 |
| `WEEKLY_JOB_DAY`    | sat           | 每周任务星期 |
| `WEEKLY_JOB_HOUR`   | 6             | 每周任务小时 |
| `WEEKLY_JOB_MINUTE` | 30            | 每周任务分钟 |
| `SCHED_TZ`          | Asia/Shanghai | 时区     |

***

## 4. 前端代码详解

### 4.1 技术栈与设计风格

前端采用 **Vue 3 Composition API + Vite 5** 构建，图表使用 **ECharts 5**。整体 UI 采用深色科幻风格（Dark Tech），以深蓝/青配色为主，搭配网格背景和渐变光晕动画。

### 4.2 路由设计

| 路径                    | 组件                      | 页面功能                      |
| --------------------- | ----------------------- | ------------------------- |
| `/`                   | `Home.vue`              | 首页：系统概览统计、股票搜索、股票列表、快捷入口  |
| `/stock/:code`        | `StockDetail.vue`       | 股票详情：K线图 + 技术指标叠加 + 基本面数据 |
| `/data-viewer`        | `DataViewer.vue`        | 数据浏览：4 张表的 Tab 切换分页查看     |
| `/backtest`           | `Backtest.vue`          | 单股回测：策略配置 + 收益曲线 + 交易明细   |
| `/portfolio-backtest` | `PortfolioBacktest.vue` | 组合回测：轮动配置 + 组合曲线 + 调仓计划   |

### 4.3 各页面功能详解

#### 4.3.1 首页 (`Home.vue`)

- **系统概览**：显示股票总数 + 最新数据日期
- **股票搜索**：输入代码或名称模糊搜索
- **股票列表**：网格卡片展示，包含股票名、代码、最新价、涨跌幅、行业标签
- **快捷入口**：三个大按钮直达「组合轮动」「策略回测」「数据浏览」

#### 4.3.2 股票详情 (`StockDetail.vue`)

- **基本信息卡片**：代码、名称、申万行业、ST 状态、上市日期、成分股标签
- **K线图**（ECharts）：支持缩放、拖拽，叠加 MA5/MA20/MA60 + 布林带三轨
- **成交量柱状图**：与 K 线图联动
- **MACD 指标图**：MACD 线 + 信号线 + 柱状图
- **RSI 指标图**：RSI 线 + 超买超卖参考线（70/30）
- **基本面表格**：PB、ROE、EPS、净利润增速、营收增速等历史数据

#### 4.3.3 数据浏览 (`DataViewer.vue`)

- **4 个 Tab 切换**：日线行情、指数行情、股票基本面、股票信息
- **分页浏览**：每个 Tab 独立分页控制
- **股票代码筛选**：支持按代码过滤

#### 4.3.4 单股回测 (`Backtest.vue`)

**配置区**：

- 股票选择（模糊搜索下拉）
- 回测周期（3个月/6个月/1年/2年/3年/全部）
- 策略选择（下拉显示策略名称和描述）
- 初始资金（可调）
- 动态策略参数面板（根据所选策略自动渲染参数控件）

**结果展示区**：

- **指标卡片**：总收益率、最终资金、交易次数、胜率、最大回撤、买入/卖出次数
- **收益曲线图**（ECharts）：账户净值曲线 + 买入/卖出标记点
- **策略叠加线**：根据策略定义的 chart\_overlays 在 K 线图上叠加指标线
- **交易明细表**：每笔交易的日期、方向、价格、股数、盈亏、原因

#### 4.3.5 组合回测 (`PortfolioBacktest.vue`)

**配置区**：

- 股票池选择（当前仅沪深300）
- 策略选择、回测周期、初始资金、最大持仓数、现金保留比例
- 动态策略参数面板
- 当前持仓编辑（用于生成明日计划场景）

**结果展示区**：

- **指标卡片**：总收益率、年化收益、最终资金、最大回撤、调仓日数量、胜率、平均持仓数
- **策略分析摘要**：组合收益 + 年化 + 回撤的文字说明，最新候选榜首信息
- **组合收益曲线**：策略净值 vs 沪深300基准对比
- **调仓事件表**：每笔买入/卖出的日期、标的、价格、股数、原因
- **最新候选排名表**：最新选股日的候选股票及其综合得分和排名理由
- **明日计划**（仅 plan 模式）：明日买入建议、明日卖出建议的详细列表

***

## 5. 策略框架与内置策略

系统设计了两套独立的策略框架，对应两种不同的投资决策模式。

### 5.1 策略框架对比

| 维度   | `strategies/` 单股框架 | `portfolio/` 组合框架    |
| ---- | ------------------ | -------------------- |
| 决策对象 | 单只股票               | 股票池（如沪深300全体成分股）     |
| 决策逻辑 | 技术指标触发买卖信号         | 每日排名打分 + 调仓          |
| 持仓方式 | 单只股票，做完一笔再下一笔      | 同时持有 N 只，按日轮动        |
| 典型场景 | "这只股票适合做短线吗？"      | "沪深300里现在应该买哪几只？"    |
| 策略数  | 2 个                | 1 个                  |
| 回测输出 | 单股收益曲线 + 逐笔交易      | 组合净值曲线 + 基准对比 + 调仓事件 |
| 计划输出 | 无                  | 明日买入/卖出建议            |

### 5.2 单股回测框架 (`strategies/`)

#### 5.2.1 框架架构

```
service.py（调度层）
    │ 1. 接收 BacktestRunRequest（股票代码 + 周期 + 策略ID + 参数）
    │ 2. load_backtest_quotes()：从 daily_quotes 表加载行情
    │ 3. build_price_data()：ORM 对象 → 策略可消费的 Dict 数组
    │ 4. get_strategy_defaults()：获取策略参数默认值
    │ 5. 合并用户参数：{**defaults, **user_params}
    │ 6. strategy["runner"](price_data, merged_params, initial_capital)
    │ 7. 拼装返回结果（stock info + price_data + trades + equity + metrics）
    ▼
策略 runner 函数（纯函数）
    │ 输入：price_data、params、initial_capital
    │ 输出：trades、equity_curve、metrics
    ▼
registry.py（注册表）
    注册所有策略，提供元数据查询（名称、描述、规则、参数schema、图表叠加线）
```

#### 5.2.2 策略开发模式

每个策略是独立的 Python 模块，实现一个 `run()` 函数和一个 `STRATEGY` 字典：

```python
# 策略模块标准结构
def run(price_data, params, initial_capital):
    """纯函数：根据行情数据和参数执行回测"""
    trades = []
    equity_curve = []
    # ... 交易逻辑 ...
    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "metrics": calculate_metrics(initial_capital, cash, trades, max_drawdown),
    }

STRATEGY = {
    "id": "strategy_id",          # 唯一标识
    "name": "策略中文名",           # 前端显示
    "description": "策略描述",     # 前端 tooltip
    "rules": ["规则1", "规则2"],   # 前端展示
    "chart_overlays": [...],      # ECharts 叠加线配置
    "param_schema": [...],        # 参数定义（key/label/type/default/min/max/step）
    "runner": run,                # 回测入口函数
}
```

新增策略只需在 `registry.py` 中注册：

```python
from strategies.new_strategy import STRATEGY as NEW_STRATEGY
BACKTEST_STRATEGIES[NEW_STRATEGY["id"]] = NEW_STRATEGY
```

前端会自动通过 `GET /api/backtest/strategies` 发现新策略并渲染对应的配置面板。

#### 5.2.3 通用工具 (`utils.py`)

| 函数                             | 功能                    |
| ------------------------------ | --------------------- |
| `to_lot_shares(budget, price)` | 计算可买整手股数（A股 100 股=1手） |
| `record_trade(trades, ...)`    | 标准化交易记录写入             |
| `build_price_data(quotes)`     | ORM 对象转为策略可消费的字典列表    |
| `calculate_metrics(...)`       | 计算总收益、收益率、最大回撤、胜率     |

### 5.3 策略1：布林带均值回归 (`bollinger_reversion`)

#### 策略思想

布林带中轨是 20 日均线，上下轨是中轨 ± 2 倍标准差。统计学上约 95% 的价格应落在带内。当价格跌破下轨时，短期超卖，统计上有均值回归倾向。策略在此时买入，等待价格回到中轨或上轨后卖出。

#### 交易规则

**买入条件**：股价 ≤ 布林带下轨 × (1 - buy\_below\_lower\_pct)

**卖出条件（任一触发）**：

1. 中轨止盈：股价 ≥ 布林带中轨（take\_profit\_on\_middle=True 时）
2. 上轨止盈：股价 ≥ 布林带上轨（take\_profit\_on\_middle=False 时）
3. 止损：股价 ≤ 入场价 × (1 - stop\_loss\_pct)
4. 超时：持仓天数 ≥ max\_holding\_days

#### 可调参数

| 参数                      | 默认值  | 范围         | 说明                   |
| ----------------------- | ---- | ---------- | -------------------- |
| `buy_below_lower_pct`   | 0.0  | 0\~0.05    | 下轨下穿比例，越大越保守         |
| `take_profit_on_middle` | True | bool       | True=中轨止盈，False=上轨止盈 |
| `stop_loss_pct`         | 0.03 | 0.005\~0.1 | 止损比例                 |
| `max_holding_days`      | 10   | 1\~60      | 最大持有天数               |

#### 适用场景

震荡市效果较好；单边下跌趋势中可能反复止损。适合波动率适中、无明显趋势的个股。

### 5.4 策略2：高频短趋势 (`short_trend`)

#### 策略思想

利用 MA5/MA20 判断短期趋势方向，RSI 和 MACD 确认动能强度，只在"趋势向上 + 动能充足"时入场，快速获利了结。RSI 到目标值即止盈，不贪长线。

#### 交易规则

**买入条件（同时满足）**：

1. 趋势确认：close > MA5 且 MA5 > MA20 × ma\_gap\_ratio
2. 动量确认：RSI ≥ buy\_rsi\_threshold
3. MACD 确认：macd\_hist > 0 且 macd\_hist ≥ prev\_macd\_hist（柱线未衰减）

**卖出条件（任一触发）**：

1. RSI 止盈：RSI ≥ sell\_rsi\_threshold
2. 止损：收盘价 ≤ 入场价 × (1 - stop\_loss\_pct)
3. 超时：持仓天数 ≥ max\_holding\_days
4. 趋势破坏：收盘价跌破 MA5

#### 可调参数

| 参数                   | 默认值   | 范围         | 说明              |
| -------------------- | ----- | ---------- | --------------- |
| `buy_rsi_threshold`  | 55    | 40\~80     | 买入所需的 RSI 最低值   |
| `sell_rsi_threshold` | 62    | 45\~90     | 触发止盈的 RSI 值     |
| `stop_loss_pct`      | 0.015 | 0.005\~0.1 | 止损比例（更紧）        |
| `max_holding_days`   | 3     | 1\~20      | 最大持有天数（短线特征）    |
| `ma_gap_ratio`       | 1.006 | 1.0\~1.03  | MA5/MA20 趋势强度系数 |

#### 适用场景

短线强势股追涨，持有时长 1\~3 天。默认止损仅 1.5%，适合波动率较高、趋势明确的个股。不适合横盘震荡阶段。

### 5.5 组合轮动框架 (`portfolio/`)

#### 5.5.1 设计理念

组合框架解决的不是"什么时候买卖某只股票"，而是"在给定的股票池里，每天应该持有哪几只"。

核心工作流：

```
收盘后 (T日)
    │
    ├── 1. 获取股票池（如沪深300成分股）
    ├── 2. 基础过滤（剔除 ST / 退市 / 上市不足 / 趋势向下）
    ├── 3. 多因子打分排序（动量 + 趋势 + 结构 + RSI + MACD + 流动性）
    ├── 4. 生成目标持仓列表（前 N 名 + 已有持仓缓冲区）
    └── 5. 生成调仓计划（买什么、卖什么、为什么）
           │
           ▼
次日开盘 (T+1日)
    │
    └── 按计划执行买卖（以开盘价成交）
```

**关键特征**：

- 信号在前一日收盘时产生，实际执行在次日开盘——避免未来函数
- 有持仓缓冲机制（keep\_buffer）：排名略有下滑但仍在前列的股票不会被立即卖出，减少不必要换手
- 支持市场风控：当沪深300指数跌破 MA60 时自动清仓

#### 5.5.2 框架架构

```
service.py（调度层）
    │ 1. get_universe_members()：从 stock_info 获取股票池成员
    │ 2. load_universe_quotes()：批量加载成分股行情
    │ 3. build_market_context()：构建按日期分组的数据字典
    │ 4. load_hs300_index_close_map()：加载基准指数数据
    │ 5. build_hs300_benchmark_curve()：构建基准收益曲线
    │ 6. 调用策略 runner() / planner()
    │ 7. 拼装返回结果
    ▼
策略模块 (hs300_rotation.py)
    │ runner()：历史回测
    │ planner()：生成明日计划
    ▼
registry.py（注册表）
    注册组合策略 + 股票池 + 周期选项
```

#### 5.5.3 策略开发模式

与单股策略类似，但接口更复杂：

```python
STRATEGY = {
    "id": "strategy_id",
    "name": "策略名称",
    "description": "...",
    "rules": [...],
    "param_schema": [...],
    "runner": run_backtest,    # 回测函数(context, params) → dict
    "planner": build_plan,     # 计划函数(context, params, holdings, cash) → dict
}
```

- `runner` 负责完整的逐年逐日回测逻辑
- `planner` 负责根据当前持仓和最新行情，生成明日买卖建议

### 5.6 策略3：沪深300日频趋势轮动 (`hs300_rotation`)

#### 策略思想

每天从沪深300成分股中，通过多因子打分选出趋势最强、动能最足的 N 只股票，持续持有。弱票淘汰，强票补入，让资金始终待在相对强势的标的上。

#### 选股过滤条件（硬性门槛）

一只股票必须同时满足以下所有条件，才有资格进入打分环节：

1. ✅ 非 ST、未退市
2. ✅ 上市天数 ≥ `min_listed_days`
3. ✅ 收盘价 > MA20（短期在均线上方）
4. ✅ MA20 > MA60（中期趋势向上）
5. ✅ 20日涨幅 > 0
6. ✅ MACD 柱线 > 0（动能为正）
7. ✅ RSI 在 \[`min_rsi`, `max_rsi`] 区间内

#### 多因子打分体系

通过过滤的股票进入综合打分，总分由 5 个维度构成：

| 维度           | 权重占比  | 核心指标          | 逻辑                              |
| ------------ | ----- | ------------- | ------------------------------- |
| **动量分**      | \~20% | 20日涨幅         | 涨得越多分越高，截断上限防极端值                |
| **趋势分**      | \~20% | close/MA20    | 站在 MA20 上方越远分越高                 |
| **结构分**      | \~26% | MA20/MA60     | MA20 比 MA60 高得越明显，中期结构越漂亮       |
| **RSI 分**    | \~23% | RSI           | 偏向 RSI≈60 时最优（不超买也不过弱）          |
| **MACD+流动性** | \~11% | MACD 金叉 + 换手率 | MACD > Signal 加分；0.5%\~5% 换手率最佳 |

#### 调仓与持仓缓冲机制

每日调仓逻辑：

1. **卖出**：触发以下任一条件则卖出
   - 市场风控触发（沪深300跌破 MA\_N）
   - 收盘跌破 MA20 × 0.98
   - MA20 跌破 MA60
   - MACD 柱线转负
   - 跌破成本价止损
   - 跌出目标组合且已持有超过 min\_holding\_days
2. **买入**：从高到低依次买入候选股票，直至持仓数达到 max\_positions
   - 资金在持仓间大致等权分配
   - 保留 cash\_reserve\_ratio 比例现金
3. **持仓缓冲（keep\_buffer）**：已持有但排名略超 max\_positions 的股票不会被立即踢出
   - 例：max\_positions=5, keep\_buffer=2 → 排名前 7 的已有持仓都可保留
   - 减少不必要换手，降低交易摩擦

#### 可调参数

| 参数                           | 默认值   | 说明             |
| ---------------------------- | ----- | -------------- |
| `score_threshold`            | 0     | 入围最低总分         |
| `min_listed_days`            | 60    | 最低上市天数         |
| `min_rsi`                    | 30    | RSI 下限         |
| `max_rsi`                    | 85    | RSI 上限         |
| `max_positions`              | 3     | 最大持仓数（由回测配置控制） |
| `keep_buffer`                | 2     | 持仓缓冲数          |
| `min_holding_days`           | 1     | 最短持有天数         |
| `stop_loss_pct`              | 0.08  | 止损比例           |
| `enable_intraday_stop`       | false | 是否启用日内止损       |
| `intraday_stop_loss_pct`     | 0.04  | 日内止损比例         |
| `enable_market_risk_control` | false | 是否启用市场风控       |
| `market_ma_window`           | 60    | 市场风控均线周期       |

#### 适用场景

趋势市（无论牛熊）效果较好；震荡市中频繁调仓可能增加摩擦成本。适合作为中长线"被动选股"策略，减少主观判断。

***

## 6. 部署发布

### 6.1 本地开发环境

**前置条件**：Python 3.9（含 venv）、Node.js v18+

**一键启动**：

```bash
cd quantitative_trading
bash scripts/run_dev.sh
```

脚本自动完成：

1. 检查端口占用（8001/8080）
2. 激活 Python venv，启动 FastAPI（uvicorn --reload，端口 8001）
3. 安装前端依赖（如需要），启动 Vite（端口 8080）
4. 展示日志并等待 Ctrl+C 优雅退出

访问地址：

- 前端：`http://localhost:8080`
- API 文档：`http://localhost:8001/docs`

### 6.2 服务器部署架构

```
                    ┌──────────────────┐
                    │     用户浏览器     │
                    └────────┬─────────┘
                             │ HTTPS
                    ┌────────▼─────────┐
                    │     nginx         │
                    │  /quantitative_trading/ ──► 前端静态文件
                    │  /quantitative_trading/api/ ──► proxy_pass :8001
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼                             ▼
    ┌─────────────────┐          ┌─────────────────┐
    │  supervisor      │          │  supervisor      │
    │  fastapi (8001)  │          │  scheduler       │
    └─────────────────┘          └─────────────────┘
              │                             │
              ▼                             ▼
    ┌─────────────────────────────────────────────┐
    │              SQLite Database                 │
    │     /root/quantitative_trading/data/*.db     │
    └─────────────────────────────────────────────┘
```

### 6.3 一键部署流程

```bash
# 本地执行
export SERVER_HOST=你的服务器IP
export SERVER_USER=root
export SSH_PORT=22
export BASE_PATH=/quantitative_trading/

bash scripts/deploy_to_server.sh
```

脚本自动执行：

1. 本地构建前端（`npm run build`）
2. 打包 backend / frontend-dist / deploy / scripts 为 tar.gz
3. SCP 上传至服务器临时目录
4. SSH 远程解压到目标目录
5. 提示配置 `.env`，确认后执行 `server_apply.sh`

### 6.4 服务器端配置 (`server_apply.sh`)

```bash
cd /root/quantitative_trading
bash scripts/server_apply.sh
```

自动完成：

- 创建 Python venv 并安装依赖
- 创建数据目录
- 配置 supervisor（复制 conf 到 `/etc/supervisor/conf.d/`）
- 重载 supervisor 使配置生效
- 提示配置 nginx

### 6.5 环境变量 (`.env`)

| 变量                  | 说明           | 默认值                              |
| ------------------- | ------------ | -------------------------------- |
| `QUANT_DB_PATH`     | SQLite 数据库路径 | 项目目录下的 `quantitative_trading.db` |
| `BACKEND_HOST`      | 后端监听地址       | 127.0.0.1                        |
| `BACKEND_PORT`      | 后端监听端口       | 8001                             |
| `DAILY_JOB_HOUR`    | 每日任务小时       | 18                               |
| `DAILY_JOB_MINUTE`  | 每日任务分钟       | 30                               |
| `WEEKLY_JOB_DAY`    | 每周任务星期       | sat                              |
| `WEEKLY_JOB_HOUR`   | 每周任务小时       | 6                                |
| `WEEKLY_JOB_MINUTE` | 每周任务分钟       | 30                               |
| `SCHED_TZ`          | 调度时区         | Asia/Shanghai                    |

### 6.6 进程管理

```bash
# 查看进程状态
sudo supervisorctl status

# 查看日志
sudo tail -f /var/log/quantitative_trading/backend.log
sudo tail -f /var/log/quantitative_trading/scheduler.log

# 重启服务
sudo supervisorctl restart quantitative_trading_backend
sudo supervisorctl restart quantitative_trading_scheduler
```

### 6.7 数据库初始化

首次部署后需要初始化数据：

```bash
# 1. 抓取交易日历
cd /root/quantitative_trading/backend
venv/bin/python crawler/trading_calendar.py

# 2. 批量抓取历史数据（时间范围可自定义）
PYTHONPATH=. venv/bin/python crawler/batch_fetch_history_data.py 20230101 20260530

# 3. 更新行业分类和成分股标签
PYTHONPATH=. venv/bin/python crawler/fetch_sw_industry.py
PYTHONPATH=. venv/bin/python crawler/fetch_constituents.py
```

***

## 7. 免责声明

> **⚠️ 重要提示：本系统仅供学习和研究目的使用，不构成任何投资建议。**

1. **非商业软件**：本项目为开源的个人量化研究工具，不提供任何形式的投资顾问服务。
2. **回测局限性**：所有回测结果均基于历史数据模拟，**历史表现不代表未来收益**。回测中可能存在幸存者偏差、过拟合、交易成本估算不足等问题。
3. **数据准确性**：系统数据来源于 akshare 等第三方免费接口，**不保证数据的实时性、完整性和准确性**。实际交易中的价格可能与系统数据存在差异。
4. **技术指标局限性**：MA、MACD、RSI、布林带等指标均为滞后指标，在极端行情下可能失效。
5. **策略风险**：
   - 布林带均值回归策略在单边下跌市场中可能连续止损
   - 高频短趋势策略对市场噪声敏感，在横盘震荡中容易反复亏损
   - 沪深300轮动策略在风格突变时可能落后于指数
6. **使用者责任**：使用者应自行承担使用本系统进行实际交易的全部风险。作者不对因使用本系统而产生的任何直接或间接损失承担责任。
7. **合规提醒**：在中国境内使用本系统进行实盘交易前，请确保遵守相关证券法律法规，通过合法券商进行交易。
8. **数据版权**：系统中使用的金融数据版权归各数据源所有，请遵守相关数据使用协议。

***

> 项目 GitHub：<https://github.com/xiaochai/quantitative_trading>

