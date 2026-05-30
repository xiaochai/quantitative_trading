# A股量化交易系统 - 数据需求文档

## 1. 文档说明

本文档定义了A股量化交易系统所需的全部数据项，用于指导数据抓取、存储和管理模块的开发。

***

## 2. 数据范围

### 2.1 时间范围

- **起始日期**：2023年1月1日
- **结束日期**：当前日期（动态更新）

### 2.2 股票范围

- A股市场所有正常交易的股票（含沪深主板、创业板、科创板）
- 排除已退市股票，但保留退市前数据用于回测

***

## 3. 数据分类及详细字段

### 3.1 核心行情数据

| 字段名称             | 数据类型   | 说明                | 更新频率 |
| ---------------- | ------ | ----------------- | ---- |
| stock_code      | string | 股票代码（如 600000.SH） | 首次抓取 |
| trade_date      | date   | 交易日期              | 每日盘后 |
| open             | float  | 开盘价               | 每日盘后 |
| close            | float  | 收盘价               | 每日盘后 |
| high             | float  | 最高价               | 每日盘后 |
| low              | float  | 最低价               | 每日盘后 |
| volume           | int    | 成交量（股）            | 每日盘后 |
| amount           | float  | 成交额（元）            | 每日盘后 |
| change_pct      | float  | 当日涨跌幅（%）          | 每日盘后 |
| change_20d_pct | float  | 近20日涨跌幅（%）        | 每日盘后 |
| turnover_rate   | float  | 换手率（%）            | 每日盘后 |
| market_cap      | float  | 总市值（亿元）          | 每日盘后 |
| pe_ttm          | float  | 滚动市盈率（TTM）        | 每日盘后 |

### 3.2 技术指标数据

| 字段名称         | 数据类型  | 说明        | 更新频率 |
| ------------ | ----- | --------- | ---- |
| ma5          | float | 5日均线      | 每日盘后 |
| ma20         | float | 20日均线     | 每日盘后 |
| ma60         | float | 60日均线     | 每日盘后 |
| macd         | float | MACD值     | 每日盘后 |
| macd_signal | float | MACD信号线   | 每日盘后 |
| macd_hist   | float | MACD柱状图   | 每日盘后 |
| rsi          | float | RSI相对强弱指标 | 每日盘后 |
| boll_upper  | float | 布林带上轨     | 每日盘后 |
| boll_middle | float | 布林带中轨     | 每日盘后 |
| boll_lower  | float | 布林带下轨     | 每日盘后 |

### 3.3 基本面数据

| 字段名称                | 数据类型  | 说明        | 更新频率 |
| ------------------- | ----- | --------- | ---- |
| market_cap         | float | 总市值（亿元）   | 每日盘后 |
| pe_ttm             | float | 市盈率（TTM）  | 季度更新 |
| pb                  | float | 市净率       | 季度更新 |
| roe                 | float | 净资产收益率（%） | 季度更新 |
| eps                 | float | 每股收益（元）   | 季度更新 |
| net_profit_growth | float | 净利润增速（%）  | 季度更新 |
| revenue_growth     | float | 营业收入增速（%） | 季度更新 |
| dividend_yield     | float | 股息率（%）    | 年度更新 |

### 3.4 分类标签数据

| 字段名称            | 数据类型      | 说明                  | 更新频率  |
| --------------- | --------- | ------------------- | ----- |
| stock_name     | string    | 股票名称                | 每日检查  |
| industry_sw1   | string    | 申万一级行业              | 每日检查  |
| industry_sw2   | string    | 申万二级行业              | 每日检查  |
| is_st          | boolean   | 是否ST                | 每日检查  |
| is_star_st    | boolean   | 是否*ST              | 每日检查  |
| is_delisted    | boolean   | 是否已退市               | 每日检查  |
| delisted_date  | date      | 退市日期                | 退市时更新  |
| listed_date    | date      | 上市日期                | 首次抓取  |
| component_tags | string[] | 成分股标签（如沪深300、创业板指等） | 指数调整后 |
| report_date  | date      | 报告日期                | 状态变更时更新 |

***

## 4. 数据更新策略

### 4.1 初始化抓取

- 首次运行时，抓取2023年1月1日至今的所有历史数据
- 按股票代码分批抓取，避免请求过于集中

### 4.2 日常更新

- **盘后更新**（15:30后）：当日行情数据
- **每周检查**：ST状态、行业分类、退市状态
- **季度更新**：财务数据（PE、PB、ROE等）
- **指数调整后**：成分股标签（通常每半年）

***

## 5. 数据来源

| 数据类型  | 推荐数据源         | 说明         |
| ----- | ------------- | ---------- |
| 行情数据  | akshare       | 免费、全面、更新及时 |
| 财务数据  | akshare       | 覆盖主要财务指标   |
| 行业分类  | akshare（申万分类） | 权威行业标准     |
| 成分股数据 | akshare       | 各指数成分股列表   |

***

## 6. 数据存储结构

### 6.1 数据表设计原则

- **行情表**：按日期+股票代码分区，便于查询
- **基本面表**：按股票代码存储，记录时间点
- **分类标签表**：单独存储，减少冗余

### 6.2 核心数据表

#### 表1: daily_quotes（日线行情表）

| 字段                                    | 类型     | 约束                          | 说明                      | 备注 |
| ------------------------------------- | ------ | --------------------------- | ----------------------- | --- |
| id                                    | int    | PRIMARY KEY AUTO_INCREMENT | 自增主键                    |  -   |
| stock_code                           | string | NOT NULL                    | 股票代码                    |   -  |
| trade_date                           | date   | NOT NULL                    | 交易日期                    |   -  |
| open                                  | float  | <br />                      | 开盘价                     |已拉取，已校验，不复权|
| close                                 | float  | <br />                      | 收盘价                     |已拉取，已校验，不复权|
| high                                  | float  | <br />                      | 最高价                     |已拉取，已校验，不复权|
| low                                   | float  | <br />                      | 最低价                     |已拉取，已校验，不复权|
| volume                                | bigint | <br />                      | 成交量（手）                 |已拉取，已校验|
| amount                                | float  | <br />                      | 成交额（元）                 |*计算估算|
| change_pct                           | float  | <br />                      | 当日涨跌幅（%）               |  已拉取   |
| change_20d_pct                      | float  | <br />                      | 近20日涨跌幅（%）             |   计算值  |
| turnover_rate                        | float  | <br />                      | 换手率（%）                 |  *未拉取   |
| market_cap                           | float  | 总市值（亿元）                | 总市值                     |   *未拉取    |
| pe_ttm                               | float  | 滚动市盈率（TTM）              | 滚动市盈率                   |   *未拉取    |
| ma5                                   | float  | <br />                      | 5日均线                    |  计算值  |
| ma20                                  | float  | <br />                      | 20日均线                   |  计算值   |
| ma60                                  | float  | <br />                      | 60日均线                   |  计算值   |
| macd                                  | float  | <br />                      | MACD值                   |  计算值   |
| macd_signal                          | float  | <br />                      | MACD信号线                 |  计算值   |
| macd_hist                            | float  | <br />                      | MACD柱状图                 |  计算值   |
| rsi                                   | float  | <br />                      | RSI相对强弱指标             |  计算值   |
| boll_upper                           | float  | <br />                      | 布林带上轨                  |  计算值   |
| boll_middle                          | float  | <br />                      | 布林带中轨                  |  计算值   |
| boll_lower                           | float  | <br />                      | 布林带下轨                  |  计算值   |
| UNIQUE KEY (stock_code, trade_date) | <br /> | <br />                      | 唯一约束                    |     |

#### 表2: stock_fundamentals（基本面数据表）

| 字段                                     | 类型     | 约束                          | 说明                 | 备注 |
| -------------------------------------- | ------ | --------------------------- | ------------------ | --- |
| id                                     | int    | PRIMARY KEY AUTO_INCREMENT | 自增主键             |  -   |
| stock_code                            | string | NOT NULL                    | 股票代码             |   -  |
| report_date                           | date   | NOT NULL                    | 报告日期             |   已抓取  |
| pb                                     | float  | 市净率                       | 市净率              |  *未抓取   |
| roe                                    | float  | 净资产收益率（%）              | 净资产收益率          |   已抓取   |
| eps                                    | float  | 每股收益（元）                | 每股收益            |   已抓取   |
| eps_ttm                               | float  | 滚动每股收益（TTM）            | 滚动每股收益          |   *未抓取   |
| net_profit_growth                    | float  | 净利润增速（%）                | 净利润增速           |  已抓取   |
| revenue_growth                        | float  | 营业收入增速（%）              | 营业收入增速          |  已抓取   |
| dividend_yield                        | float  | 股息率（%）                  | 股息率             |  *未抓取   |
| UNIQUE KEY (stock_code, report_date) | <br /> | <br />                      | 唯一约束             |     |

**说明**：PE(TTM)和总市值存储在daily_quotes表中，本表格存储季度财报原始数据。

#### 表3: stock_info（股票基础信息表）

| 字段              | 类型       | 约束            | 说明             | 备注 |
| --------------- | -------- | ------------- | -------------- | --- |
| id              | int      | PRIMARY KEY AUTO_INCREMENT | 自增主键          | -    |
| stock_code     | string   | NOT NULL      | 股票代码          |  -   |
| stock_name     | string   | NOT NULL      | 股票名称          |  已抓取   |
| industry_sw1   | string   | <br />        | 申万一级行业        |  *未抓取   |
| industry_sw2   | string   | <br />        | 申万二级行业        |  *未抓取   |
| is_st          | boolean  | DEFAULT FALSE | 是否ST          |   计算值  |
| is_star_st    | boolean  | DEFAULT FALSE | 是否*ST        |   计算值  |
| is_delisted    | boolean  | DEFAULT FALSE | 是否已退市         |  *未抓取   |
| delisted_date  | date     | <br />        | 退市日期          |  *未抓取   |
| listed_date    | date     | <br />        | 上市日期          |  *未抓取   |
| component_tags | text     | JSON格式存储      | 成分股标签         |  *未抓取   |
| report_date    | date     | NOT NULL      | 报告日期          |   -  |
| UNIQUE KEY (stock_code, report_date) | <br /> | <br /> | 唯一约束          |     |

**记录逻辑**：
- 每只股票可以有多条记录，按 report_date 区分不同时期的状态
- 当股票信息发生变化时（如变成ST、退市、名称变更等），插入一条新记录
- 同一天内多次更新时，直接更新当天的记录，而不是插入多条
- 查询最新信息时，按 report_date 倒序取第一条记录

***

## 7. 数据质量要求

### 7.1 准确性

- 确保行情数据与官方交易所数据一致
- 财务数据需核对财报发布日期

### 7.2 完整性

- 不遗漏任何交易日数据
- 新上市股票需及时纳入

### 7.3 及时性

- 盘后数据在当日18:00前完成更新
- 财务数据在财报发布后3个工作日内更新

***

## 8. 附录

### 8.1 股票代码格式

- 沪市：600xxx.SH、601xxx.SH、603xxx.SH、605xxx.SH
- 深市：000xxx.SZ、001xxx.SZ（深市主板）
- 创业板：300xxx.SZ
- 科创板：688xxx.SH

### 8.2 申万一级行业列表

1. 农林牧渔
2. 采掘
3. 化工
4. 钢铁
5. 有色金属
6. 建筑材料
7. 建筑装饰
8. 电气设备
9. 机械设备
10. 国防军工
11. 汽车
12. 家用电器
13. 食品饮料
14. 纺织服饰
15. 轻工制造
16. 医药生物
17. 公用事业
18. 交通运输
19. 房地产
20. 商贸零售
21. 社会服务
22. 综合
23. 电子
24. 计算机
25. 通信
26. 银行
27. 非银金融
28. 传媒
