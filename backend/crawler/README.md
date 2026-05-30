# 数据抓取脚本说明

本目录包含量化交易系统的数据抓取相关脚本。

---

## 📋 脚本列表

| 脚本文件名 | 功能说明 |
|---------|------|
| `fetch_all_from_sina.py` | 从新浪获取每日股票数据（行情+基本信息） |
| `fetch_financials_from_ths.py` | 从同花顺获取财务基本信息 |
| `fetch_historical_data.py` | 获取股票历史日线数据 |
| `batch_fetch_history_data.py` | 批量获取所有股票的历史数据和财务数据 |
| `trading_calendar.py` | 交易日历管理 |

---

## 1. `trading_calendar.py` - 交易日历管理

### 功能说明
- 从新浪接口获取完整的A股交易日历
- 本地缓存日历数据，避免重复请求
- 提供判断任意日期是否是交易日的功能

### 可用函数

```python
from backend.crawler.trading_calendar import (
    is_trading_day,
    update_trading_calendar,
    load_calendar_from_file
)

# 1. 判断今天是否是交易日
if is_trading_day():
    print("今天开市")

# 2. 判断指定日期是否是交易日
is_trading_day('20260601')  # 支持日期字符串
is_trading_day(datetime_obj)  # 也支持 datetime 对象

# 3. 更新交易日历（如果需要）
dates = update_trading_calendar()

# 4. 加载本地缓存的日历
dates = load_calendar_from_file()
```

### 运行方式
```bash
PYTHONPATH=. backend/.venv/bin/python backend/crawler/trading_calendar.py
```

---

## 2. `fetch_all_from_sina.py` - 从新浪获取每日股票数据

### 功能说明
- 从新浪接口获取所有A股实时行情数据
- 更新股票基本信息（名称、ST状态、退市状态等）
- 保存行情数据到 `daily_quotes` 表
- 保存股票信息到 `stock_info` 表（有变化时插入新记录）
- 数据优先从本地文件加载，避免重复请求

### stock_info 记录逻辑
- 每只股票可以有多条记录，按 `report_date` 区分不同时期的状态
- 当股票信息发生变化时（如变成ST、退市、名称变更等），插入一条新记录
- 同一天内多次更新时，直接更新当天的记录，而不是插入多条
- 查询最新信息时，按 `report_date` 倒序取第一条记录

### 可用函数
脚本主要直接运行，不对外暴露函数。

### 运行方式
```bash
PYTHONPATH=. backend/.venv/bin/python backend/crawler/fetch_all_from_sina.py
```

---

## 3. `fetch_financials_from_ths.py` - 从同花顺获取财务基本信息

### 功能说明
- 使用 `ak.stock_financial_abstract_ths()` 接口获取财务数据
- 数据优先从本地文件加载，避免重复请求
- 保存财务数据到 `stock_fundamentals` 表
- 支持解析年报、中报、三季报、一季报等日期格式

### 可用函数
脚本主要直接运行，不对外暴露函数。

### 运行方式
```bash
# 默认抓取招商银行
PYTHONPATH=. backend/.venv/bin/python backend/crawler/fetch_financials_from_ths.py

# 指定股票代码
PYTHONPATH=. backend/.venv/bin/python backend/crawler/fetch_financials_from_ths.py 600036.SH
```

---

## 4. `fetch_historical_data.py` - 获取股票历史日线数据

### 功能说明
- 使用 `ak.stock_zh_a_hist()` 接口获取历史日线数据
- 数据优先从本地文件加载，避免重复请求
- 自动计算技术指标（MA5/MA20/MA60、MACD、RSI、布林带）
- 保存历史数据到 `daily_quotes` 表
- 支持数据去重和更新

### 可用函数
脚本主要直接运行，不对外暴露函数。

### 运行方式
```bash
# 使用默认参数（最近3年，600036.SH）
PYTHONPATH=. backend/.venv/bin/python backend/crawler/fetch_historical_data.py

# 指定股票代码
PYTHONPATH=. backend/.venv/bin/python backend/crawler/fetch_historical_data.py 000001.SZ

# 指定股票代码和时间范围
PYTHONPATH=. backend/.venv/bin/python backend/crawler/fetch_historical_data.py 600036.SH 20230101 20260530
```

---

## 5. `batch_fetch_history_data.py` - 批量获取所有股票数据

### 功能说明
- 从 `stock_info` 表获取所有未退市的股票
- 依次为每只股票调用 `fetch_and_save_financial()` 获取财务数据
- 依次为每只股票调用 `fetch_and_save_historical()` 获取历史数据
- 显示抓取进度和统计信息
- 默认时间范围：2023-05-31 至 2026-05-30

### 可用函数
脚本主要直接运行，不对外暴露函数。

### 运行方式
```bash
# 使用默认时间范围
PYTHONPATH=. backend/.venv/bin/python backend/crawler/batch_fetch_history_data.py

# 自定义时间范围
PYTHONPATH=. backend/.venv/bin/python backend/crawler/batch_fetch_history_data.py 20230101 20260530
```

---

## 📂 数据文件

所有数据文件都保存在 `data/` 子目录下：

| 文件名 | 说明 |
|------|------|
| `sina_stock_data_YYYYMMDD.json` | 每日从新浪获取的原始股票数据 |
| `financial_STOCKCODE_YYYYMMDD.json` | 单只股票的财务数据 |
| `historical_STOCKCODE_STARTDATE_ENDDATE.json` | 单只股票的历史日线数据 |
| `trading_calendar.json` | 交易日历缓存 |

---

## 🔄 推荐工作流程

1. **初始化数据（首次运行）**：
   ```bash
   # 获取所有股票的基本信息
   PYTHONPATH=. backend/.venv/bin/python backend/crawler/fetch_all_from_sina.py
   
   # 批量获取所有股票的历史数据和财务数据
   PYTHONPATH=. backend/.venv/bin/python backend/crawler/batch_fetch_history_data.py
   ```

2. **每天盘后运行**：
   ```bash
   # 先检查是否是交易日
   PYTHONPATH=. backend/.venv/bin/python backend/crawler/trading_calendar.py
   
   # 如果是交易日，获取数据
   PYTHONPATH=. backend/.venv/bin/python backend/crawler/fetch_all_from_sina.py
   ```

3. **按需抓取单只股票数据**：
   ```bash
   # 财务数据
   PYTHONPATH=. backend/.venv/bin/python backend/crawler/fetch_financials_from_ths.py 600036.SH
   
   # 历史数据
   PYTHONPATH=. backend/.venv/bin/python backend/crawler/fetch_historical_data.py 600036.SH 20230101 20260530
   ```

---

## 📊 数据库表结构

参考 `/doc/requirements/data_requirements.md` 中的详细说明。
