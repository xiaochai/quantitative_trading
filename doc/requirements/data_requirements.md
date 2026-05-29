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
| stock\_code      | string | 股票代码（如 600000.SH） | 首次抓取 |
| trade\_date      | date   | 交易日期              | 每日盘后 |
| open             | float  | 开盘价               | 每日盘后 |
| close            | float  | 收盘价               | 每日盘后 |
| high             | float  | 最高价               | 每日盘后 |
| low              | float  | 最低价               | 每日盘后 |
| volume           | int    | 成交量（股）            | 每日盘后 |
| amount           | float  | 成交额（元）            | 每日盘后 |
| change\_pct      | float  | 当日涨跌幅（%）          | 每日盘后 |
| change\_20d\_pct | float  | 近20日涨跌幅（%）        | 每日盘后 |
| turnover\_rate   | float  | 换手率（%）            | 每日盘后 |
| market\_cap      | float  | 总市值（亿元）          | 每日盘后 |
| pe\_ttm          | float  | 滚动市盈率（TTM）        | 每日盘后 |

### 3.2 技术指标数据

| 字段名称         | 数据类型  | 说明        | 更新频率 |
| ------------ | ----- | --------- | ---- |
| ma5          | float | 5日均线      | 每日盘后 |
| ma20         | float | 20日均线     | 每日盘后 |
| ma60         | float | 60日均线     | 每日盘后 |
| macd         | float | MACD值     | 每日盘后 |
| macd\_signal | float | MACD信号线   | 每日盘后 |
| macd\_hist   | float | MACD柱状图   | 每日盘后 |
| rsi          | float | RSI相对强弱指标 | 每日盘后 |
| boll\_upper  | float | 布林带上轨     | 每日盘后 |
| boll\_middle | float | 布林带中轨     | 每日盘后 |
| boll\_lower  | float | 布林带下轨     | 每日盘后 |

### 3.3 基本面数据

| 字段名称                | 数据类型  | 说明        | 更新频率 |
| ------------------- | ----- | --------- | ---- |
| market\_cap         | float | 总市值（亿元）   | 每日盘后 |
| pe\_ttm             | float | 市盈率（TTM）  | 季度更新 |
| pb                  | float | 市净率       | 季度更新 |
| roe                 | float | 净资产收益率（%） | 季度更新 |
| eps                 | float | 每股收益（元）   | 季度更新 |
| net\_profit\_growth | float | 净利润增速（%）  | 季度更新 |
| revenue\_growth     | float | 营业收入增速（%） | 季度更新 |
| dividend\_yield     | float | 股息率（%）    | 年度更新 |

### 3.4 分类标签数据

| 字段名称            | 数据类型      | 说明                  | 更新频率  |
| --------------- | --------- | ------------------- | ----- |
| stock\_name     | string    | 股票名称                | 首次抓取  |
| industry\_sw1   | string    | 申万一级行业              | 每周检查  |
| industry\_sw2   | string    | 申万二级行业              | 每周检查  |
| is\_st          | boolean   | 是否ST                | 每周检查  |
| is\_star\_st    | boolean   | 是否\*ST              | 每周检查  |
| is\_delisted    | boolean   | 是否已退市               | 每周检查  |
| delisted\_date  | date      | 退市日期                | 退市时更新  |
| listed\_date    | date      | 上市日期                | 首次抓取  |
| component\_tags | string\[] | 成分股标签（如沪深300、创业板指等） | 指数调整后 |
| effective\_from | date      | 生效日期                | 首次抓取  |
| effective\_to   | date      | 失效日期（NULL表示当前有效）    | 状态变更时更新 |

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

#### 表1: daily\_quotes（日线行情表）

| 字段                                    | 类型     | 约束                          |
| ------------------------------------- | ------ | --------------------------- |
| id                                    | int    | PRIMARY KEY AUTO\_INCREMENT |
| stock\_code                           | string | NOT NULL                    |
| trade\_date                           | date   | NOT NULL                    |
| open                                  | float  | <br />                      |
| close                                 | float  | <br />                      |
| high                                  | float  | <br />                      |
| low                                   | float  | <br />                      |
| volume                                | bigint | <br />                      |
| amount                                | float  | <br />                      |
| change\_pct                           | float  | <br />                      |
| change\_20d\_pct                      | float  | <br />                      |
| turnover\_rate                        | float  | <br />                      |
| market\_cap                           | float  | 总市值（亿元）                |
| pe\_ttm                               | float  | 滚动市盈率（TTM）              |
| ma5                                   | float  | <br />                      |
| ma20                                  | float  | <br />                      |
| ma60                                  | float  | <br />                      |
| macd                                  | float  | <br />                      |
| macd\_signal                          | float  | <br />                      |
| macd\_hist                            | float  | <br />                      |
| rsi                                   | float  | <br />                      |
| boll\_upper                           | float  | <br />                      |
| boll\_middle                          | float  | <br />                      |
| boll\_lower                           | float  | <br />                      |
| UNIQUE KEY (stock\_code, trade\_date) | <br /> | <br />                      |

#### 表2: stock\_fundamentals（基本面数据表）

| 字段                                     | 类型     | 约束                          |
| -------------------------------------- | ------ | --------------------------- |
| id                                     | int    | PRIMARY KEY AUTO\_INCREMENT |
| stock\_code                            | string | NOT NULL                    |
| report\_date                           | date   | NOT NULL                    |
| pb                                     | float  | 市净率                       |
| roe                                    | float  | 净资产收益率（%）              |
| eps                                    | float  | 每股收益（元）                |
| eps\_ttm                               | float  | 滚动每股收益（TTM）            |
| net\_profit\_growth                    | float  | 净利润增速（%）                |
| revenue\_growth                        | float  | 营业收入增速（%）              |
| dividend\_yield                        | float  | 股息率（%）                  |
| UNIQUE KEY (stock\_code, report\_date) | <br /> | <br />                      |

**说明**：PE(TTM)和总市值存储在daily_quotes表中，本表格存储季度财报原始数据。

#### 表3: stock\_info（股票基础信息表）

| 字段              | 类型       | 约束            |
| --------------- | -------- | ------------- |
| id              | int      | PRIMARY KEY AUTO_INCREMENT |
| stock\_code     | string   | NOT NULL      |
| stock\_name     | string   | NOT NULL      |
| industry\_sw1   | string   | <br />        |
| industry\_sw2   | string   | <br />        |
| is\_st          | boolean  | DEFAULT FALSE |
| is\_star\_st    | boolean  | DEFAULT FALSE |
| is\_delisted    | boolean  | DEFAULT FALSE |
| delisted\_date  | date     | <br />        |
| listed\_date    | date     | <br />        |
| component\_tags | text     | JSON格式存储      |
| effective\_from | date     | NOT NULL      |
| effective\_to   | date     | <br />        |
| UNIQUE KEY (stock\_code, effective\_from) | <br /> | <br /> |

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

