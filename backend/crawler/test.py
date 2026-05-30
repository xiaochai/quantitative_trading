"""
股票历史数据抓取脚本

功能：
1. 抓取指定A股股票的历史日线行情数据
2. 自动计算常用技术指标（MA5/MA20/MA60、MACD、RSI、布林带）
3. 保存数据到三张表：
   - daily_quotes: 日线行情数据
   - stock_info: 股票基本信息
   - stock_fundamentals: 基本面数据
4. 支持数据去重，重复数据会自动更新而不会重复插入

运行方式：
    cd /Users/bytedance/go/src/github.com/xiaochai/quantitative_trading
    PYTHONPATH=. backend/.venv/bin/python backend/crawler/stock_crawler.py
"""

import akshare as ak
stock_individual_basic_info_xq_df = ak.tool_trade_date_hist_sina()
print(stock_individual_basic_info_xq_df)