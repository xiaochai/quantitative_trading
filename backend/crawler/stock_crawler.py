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
import pandas as pd
import math
import re
from datetime import datetime, timedelta
from backend.database.database import SessionLocal, engine, Base
from backend.models.stock_data import DailyQuote, StockInfo, StockFundamental
import numpy as np

# 初始化数据库表
def init_db():
    Base.metadata.create_all(bind=engine)
    print("数据库表初始化完成")


def get_stock_daily_data(stock_code, start_date, end_date):
    """
    获取股票的历史日线数据，并补充市值和市盈率等信息
    
    Args:
        stock_code: 股票代码，格式如 "600036.SH"
        start_date: 开始日期，格式如 "20230101"
        end_date: 结束日期，格式如 "20231231"
    
    Returns:
        DataFrame: 包含股票历史数据的DataFrame
    """
    try:
        stock_zh_a_hist_df = ak.stock_zh_a_hist(
            symbol=stock_code.split('.')[0],
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=""
        )
        print(f"成功获取 {len(stock_zh_a_hist_df)} 条历史数据")
        
        # 尝试获取补充数据
        try:
            # 获取实时行情数据补充市盈率和市值
            spot_df = ak.stock_zh_a_spot()
            stock_info = spot_df[spot_df['代码'] == stock_code.split('.')[0]]
            if not stock_info.empty:
                info = stock_info.iloc[0]
                # 将最新的市值和市盈率添加到最后一条记录
                if len(stock_zh_a_hist_df) > 0:
                    # 先查看有哪些列
                    print("实时行情列名:", spot_df.columns.tolist())
                    
                    # 我们可以获取一些基本信息，但历史的市值和PE需要其他接口
                    # 先只给最新的记录添加值
                    pass
        except Exception as e:
            print(f"获取补充数据失败: {e}")
            
        return stock_zh_a_hist_df
    except Exception as e:
        print(f"获取股票数据失败: {e}")
        return None


def get_stock_estimates(stock_code):
    """
    获取股票的估算参数
    
    Args:
        stock_code: 股票代码
    
    Returns:
        dict: 包含估算参数的字典（全部为空，从远程获取）
    """
    return {
        'total_shares': None,  # 总股本
        'eps': None,  # 每股收益
        'pb': None,  # 市净率
        'listed_date': None,  # 上市日期
    }


def enrich_stock_data(df, stock_code):
    """
    为日线数据补充估值信息（只从数据中获取，不使用预置值）
    
    Args:
        df: 原始日线数据
        stock_code: 股票代码
    
    Returns:
        DataFrame: 补充后的DataFrame
    """
    # 初始化这些列
    df['总市值'] = None
    df['市盈率'] = None
    df['换手率'] = None  # 也补充换手率
    
    # 从数据本身尝试提取（如果接口返回了这些字段）
    # 如果没有，就保持 None
    print(f"数据补充完成，保留原始数据")
    return df


def get_stock_info(stock_code):
    """
    获取股票的基本信息（完全从远程获取，不使用预置值）
    
    Args:
        stock_code: 股票代码，格式如 "600036.SH"
    
    Returns:
        dict: 包含股票信息的字典
    """
    stock_name = stock_code  # 默认用代码当名称
    industry_sw1 = None
    industry_sw2 = None
    listed_date = None
    
    try:
        # 使用 ak.stock_individual_info_em
        try:
            print("正在获取个股资料...")
            df = ak.stock_individual_info_em(symbol=stock_code.split('.')[0])
            if not df.empty:
                for _, row in df.iterrows():
                    item = str(row['item'])
                    value = str(row['value']) if row['value'] is not None else ''
                    if '行业' in item and not industry_sw2:
                        industry_sw2 = value
                    elif '所属板块' in item and not industry_sw1:
                        industry_sw1 = value
                    elif '上市日期' in item:
                        try:
                            date_str = value
                            if date_str and date_str != '-' and date_str != 'nan' and len(date_str) >= 8:
                                if len(date_str) == 8:
                                    listed_date = datetime.strptime(date_str, '%Y%m%d').date()
                                elif '-' in date_str:
                                    listed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        except Exception as e:
                            pass
        except Exception as e:
            print(f"获取个股资料失败: {e}")
        
        # 获取股票名称
        try:
            spot_df = ak.stock_zh_a_spot()
            if not spot_df.empty:
                stock_info = spot_df[spot_df['代码'] == stock_code.split('.')[0]]
                if not stock_info.empty:
                    stock_name = stock_info.iloc[0]['名称']
        except Exception as e:
            pass
            
    except Exception as e:
        print(f"获取股票信息过程出错: {e}")
    
    print(f"股票信息: {stock_name}, 行业: {industry_sw1}/{industry_sw2}")
    
    return {
        'stock_name': stock_name,
        'industry_sw1': industry_sw1,
        'industry_sw2': industry_sw2,
        'is_st': 'ST' in str(stock_name),
        'is_star_st': '*ST' in str(stock_name),
        'is_delisted': False,
        'listed_date': listed_date
    }


def parse_money(money_str):
    """解析带单位的金额字符串（亿、万）"""
    if pd.isna(money_str) or money_str in [False, True]:
        return None
    money_str = str(money_str)
    if '亿' in money_str:
        try:
            return float(re.sub(r'[^0-9.-]', '', money_str))
        except:
            return None
    elif '万' in money_str:
        try:
            return float(re.sub(r'[^0-9.-]', '', money_str)) / 10000  # 转换为亿
        except:
            return None
    else:
        try:
            val = float(re.sub(r'[^0-9.-]', '', money_str))
            # 如果数值很大，可能是原始数值，转换为亿
            if val > 100000000:
                return val / 100000000
            return val
        except:
            return None


def parse_percent(percent_str):
    """解析百分比字符串"""
    if pd.isna(percent_str) or percent_str in [False, True]:
        return None
    percent_str = str(percent_str)
    try:
        return float(re.sub(r'[^0-9.-]', '', percent_str))
    except:
        return None


def get_stock_fundamentals(stock_code):
    """
    获取股票的财务基本面数据
    
    Args:
        stock_code: 股票代码，格式如 "600036.SH"
    
    Returns:
        DataFrame: 包含财务数据的DataFrame
    """
    try:
        print("正在获取财务数据...")
        # 获取财务摘要数据
        fin_df = ak.stock_financial_abstract_ths(
            symbol=stock_code.split('.')[0], 
            indicator='年报'
        )
        print(f"成功获取 {len(fin_df)} 条财务数据")
        return fin_df
    except Exception as e:
        print(f"获取财务数据失败: {e}")
        return None


def calculate_indicators(df):
    """
    计算技术指标
    
    Args:
        df: 包含原始行情数据的DataFrame
    
    Returns:
        DataFrame: 添加了技术指标的DataFrame
    """
    # 移动平均线
    df['ma5'] = df['收盘'].rolling(window=5).mean()
    df['ma20'] = df['收盘'].rolling(window=20).mean()
    df['ma60'] = df['收盘'].rolling(window=60).mean()
    
    # 20日涨跌幅
    df['change_20d_pct'] = df['收盘'].pct_change(periods=20) * 100
    
    # MACD指标
    exp12 = df['收盘'].ewm(span=12, adjust=False).mean()
    exp26 = df['收盘'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp12 - exp26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # RSI指标
    delta = df['收盘'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 布林带
    df['boll_middle'] = df['收盘'].rolling(window=20).mean()
    df['boll_std'] = df['收盘'].rolling(window=20).std()
    df['boll_upper'] = df['boll_middle'] + 2 * df['boll_std']
    df['boll_lower'] = df['boll_middle'] - 2 * df['boll_std']
    
    return df


def _convert_nan(value):
    """
    将NaN值转换为None以便数据库存储
    """
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if pd.isna(value):
        return None
    return value


def save_daily_quotes(db, stock_code, df):
    """
    保存日线行情数据到数据库
    如果数据已存在则更新，否则插入
    
    Args:
        db: 数据库会话
        stock_code: 股票代码
        df: 行情数据DataFrame
    """
    inserted_count = 0
    updated_count = 0
    
    for _, row in df.iterrows():
        date_val = row['日期']
        if isinstance(date_val, datetime):
            trade_date = date_val.date()
        elif isinstance(date_val, str):
            trade_date = datetime.strptime(date_val, '%Y-%m-%d').date()
        else:
            trade_date = date_val
        
        volume_val = row['成交量']
        if pd.isna(volume_val) or volume_val is None:
            volume_val = 0
        
        # 先查询是否已存在该数据
        existing = db.query(DailyQuote).filter(
            DailyQuote.stock_code == stock_code,
            DailyQuote.trade_date == trade_date
        ).first()
        
        if existing:
            # 更新已有数据
            existing.open = _convert_nan(row['开盘'])
            existing.close = _convert_nan(row['收盘'])
            existing.high = _convert_nan(row['最高'])
            existing.low = _convert_nan(row['最低'])
            existing.volume = int(volume_val)
            existing.amount = _convert_nan(row['成交额'])
            existing.change_pct = _convert_nan(row['涨跌幅'])
            existing.change_20d_pct = _convert_nan(row.get('change_20d_pct'))
            existing.turnover_rate = _convert_nan(row.get('换手率'))
            existing.market_cap = _convert_nan(row.get('总市值'))
            existing.pe_ttm = _convert_nan(row.get('市盈率'))
            existing.ma5 = _convert_nan(row.get('ma5'))
            existing.ma20 = _convert_nan(row.get('ma20'))
            existing.ma60 = _convert_nan(row.get('ma60'))
            existing.macd = _convert_nan(row.get('macd'))
            existing.macd_signal = _convert_nan(row.get('macd_signal'))
            existing.macd_hist = _convert_nan(row.get('macd_hist'))
            existing.rsi = _convert_nan(row.get('rsi'))
            existing.boll_upper = _convert_nan(row.get('boll_upper'))
            existing.boll_middle = _convert_nan(row.get('boll_middle'))
            existing.boll_lower = _convert_nan(row.get('boll_lower'))
            updated_count += 1
        else:
            # 插入新数据
            quote = DailyQuote(
                stock_code=stock_code,
                trade_date=trade_date,
                open=_convert_nan(row['开盘']),
                close=_convert_nan(row['收盘']),
                high=_convert_nan(row['最高']),
                low=_convert_nan(row['最低']),
                volume=int(volume_val),
                amount=_convert_nan(row['成交额']),
                change_pct=_convert_nan(row['涨跌幅']),
                change_20d_pct=_convert_nan(row.get('change_20d_pct')),
                turnover_rate=_convert_nan(row.get('换手率')),
                market_cap=_convert_nan(row.get('总市值')),
                pe_ttm=_convert_nan(row.get('市盈率')),
                ma5=_convert_nan(row.get('ma5')),
                ma20=_convert_nan(row.get('ma20')),
                ma60=_convert_nan(row.get('ma60')),
                macd=_convert_nan(row.get('macd')),
                macd_signal=_convert_nan(row.get('macd_signal')),
                macd_hist=_convert_nan(row.get('macd_hist')),
                rsi=_convert_nan(row.get('rsi')),
                boll_upper=_convert_nan(row.get('boll_upper')),
                boll_middle=_convert_nan(row.get('boll_middle')),
                boll_lower=_convert_nan(row.get('boll_lower'))
            )
            db.add(quote)
            inserted_count += 1
    
    db.commit()
    print(f"日线数据 - 新增 {inserted_count} 条，更新 {updated_count} 条")


def save_stock_info(db, stock_code, stock_info_dict):
    """
    保存股票基本信息到数据库
    如果当前有效信息不同，则更新
    """
    if stock_info_dict is None:
        return
    
    existing_info = db.query(StockInfo).filter(
        StockInfo.stock_code == stock_code,
        StockInfo.effective_to.is_(None)
    ).first()
    
    # 检查是否需要更新（只有信息变更时才新增记录）
    need_update = False
    if existing_info:
        if (existing_info.stock_name != stock_info_dict['stock_name'] or
            existing_info.industry_sw1 != stock_info_dict.get('industry_sw1') or
            existing_info.industry_sw2 != stock_info_dict.get('industry_sw2') or
            existing_info.is_st != stock_info_dict.get('is_st', False)):
            existing_info.effective_to = datetime.now().date()
            need_update = True
    else:
        need_update = True
    
    if need_update:
        try:
            # 先检查是否已存在相同的记录（防止冲突）
            existing_same = db.query(StockInfo).filter(
                StockInfo.stock_code == stock_code,
                StockInfo.effective_from == datetime.now().date()
            ).first()
            
            if existing_same:
                # 如果已存在，直接更新
                existing_same.stock_name = stock_info_dict['stock_name']
                existing_same.industry_sw1 = stock_info_dict.get('industry_sw1')
                existing_same.industry_sw2 = stock_info_dict.get('industry_sw2')
                existing_same.is_st = stock_info_dict.get('is_st', False)
                existing_same.is_star_st = stock_info_dict.get('is_star_st', False)
                existing_same.is_delisted = stock_info_dict.get('is_delisted', False)
                existing_same.delisted_date = stock_info_dict.get('delisted_date')
                existing_same.listed_date = stock_info_dict.get('listed_date')
                existing_same.component_tags = stock_info_dict.get('component_tags')
            else:
                # 如果不存在，创建新记录
                new_info = StockInfo(
                    stock_code=stock_code,
                    stock_name=stock_info_dict['stock_name'],
                    industry_sw1=stock_info_dict.get('industry_sw1'),
                    industry_sw2=stock_info_dict.get('industry_sw2'),
                    is_st=stock_info_dict.get('is_st', False),
                    is_star_st=stock_info_dict.get('is_star_st', False),
                    is_delisted=stock_info_dict.get('is_delisted', False),
                    delisted_date=stock_info_dict.get('delisted_date'),
                    listed_date=stock_info_dict.get('listed_date'),
                    component_tags=stock_info_dict.get('component_tags'),
                    effective_from=datetime.now().date(),
                    effective_to=None
                )
                db.add(new_info)
            db.commit()
            print(f"成功保存股票信息: {stock_code} - {stock_info_dict['stock_name']}")
        except Exception as e:
            db.rollback()
            print(f"保存股票信息时出错: {e}")
            # 尝试查找并更新现有记录
            existing_any = db.query(StockInfo).filter(
                StockInfo.stock_code == stock_code
            ).first()
            if existing_any:
                existing_any.stock_name = stock_info_dict['stock_name']
                db.commit()
                print(f"更新现有股票信息成功: {stock_code} - {stock_info_dict['stock_name']}")
    else:
        print(f"股票信息无变化，无需更新: {stock_code}")


def enrich_fundamentals(stock_code):
    """
    获取财务数据估算参数（全部为空，不使用预置值）
    
    Args:
        stock_code: 股票代码
    
    Returns:
        dict: 财务估算参数（全部为空）
    """
    return {
        'pb': None,
        'eps': None,
        'eps_ttm': None,
        'revenue_growth': None,
        'dividend_yield': None,
    }


def save_stock_fundamentals(db, stock_code, fin_df):
    """
    保存财务基本面数据到数据库
    如果数据已存在则更新，否则插入
    
    Args:
        db: 数据库会话
        stock_code: 股票代码
        fin_df: 财务数据DataFrame
    """
    if fin_df is None or fin_df.empty:
        print("没有财务数据可保存")
        return
    
    inserted_count = 0
    updated_count = 0
    
    for _, row in fin_df.iterrows():
        # 解析报告期
        report_year = str(row['报告期'])
        report_date_str = f"{report_year}-12-31"
        report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
        
        # 解析数据
        net_profit = parse_money(row.get('净利润'))
        net_profit_growth = parse_percent(row.get('净利润同比增长率'))
        roe = parse_percent(row.get('净资产收益率'))
        
        # 只使用从接口获取的数据，不使用预置值
        eps = None
        eps_ttm = None
        pb = None
        revenue_growth = None
        dividend_yield = None
        
        # 先查询是否已存在
        existing = db.query(StockFundamental).filter(
            StockFundamental.stock_code == stock_code,
            StockFundamental.report_date == report_date
        ).first()
        
        if existing:
            # 更新 - 保留原始数据，只补充None值
            if existing.pb is None:
                existing.pb = pb
            if existing.roe is None:
                existing.roe = roe
            if existing.eps is None:
                existing.eps = eps
            if existing.eps_ttm is None:
                existing.eps_ttm = eps_ttm
            if existing.net_profit_growth is None:
                existing.net_profit_growth = net_profit_growth
            if existing.revenue_growth is None:
                existing.revenue_growth = revenue_growth
            if existing.dividend_yield is None:
                existing.dividend_yield = dividend_yield
            updated_count += 1
        else:
            # 插入
            funda = StockFundamental(
                stock_code=stock_code,
                report_date=report_date,
                pb=pb,
                roe=roe,
                eps=eps,
                eps_ttm=eps_ttm,
                net_profit_growth=net_profit_growth,
                revenue_growth=revenue_growth,
                dividend_yield=dividend_yield
            )
            db.add(funda)
            inserted_count += 1
    
    db.commit()
    print(f"财务数据 - 新增 {inserted_count} 条，更新 {updated_count} 条（含估算值）")


def crawl_stock(
    stock_code, 
    months=1,
    fetch_daily=True,
    fetch_info=True,
    fetch_fundamental=True
):
    """
    主函数：抓取股票历史数据
    
    Args:
        stock_code: 股票代码，如 "600036.SH"
        months: 抓取最近几个月的数据，默认1个月
        fetch_daily: 是否抓取日线数据，默认 True
        fetch_info: 是否抓取基本信息，默认 True
        fetch_fundamental: 是否抓取财务数据，默认 True
    """
    # 初始化数据库
    init_db()
    
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=months*30)).strftime('%Y%m%d')
    
    print("=" * 60)
    print(f"开始抓取股票历史数据")
    print(f"股票代码: {stock_code}")
    print(f"时间范围: {start_date} 至 {end_date}")
    print(f"抓取内容:")
    if fetch_daily:
        print(f"  ✓ 日线数据")
    if fetch_info:
        print(f"  ✓ 基本信息")
    if fetch_fundamental:
        print(f"  ✓ 财务数据")
    print("=" * 60)
    
    # 保存数据
    db = SessionLocal()
    try:
        # 1. 获取并保存日线数据
        if fetch_daily:
            df = get_stock_daily_data(stock_code, start_date, end_date)
            if df is not None and not df.empty:
                print("\n正在补充数据...")
                df = enrich_stock_data(df, stock_code)
                print("\n正在计算技术指标...")
                df = calculate_indicators(df)
                print("\n正在保存日线数据...")
                save_daily_quotes(db, stock_code, df)
            else:
                print("未获取到日线数据")
        
        # 2. 获取并保存股票基本信息
        if fetch_info:
            print("\n正在获取股票基本信息...")
            stock_info_dict = get_stock_info(stock_code)
            save_stock_info(db, stock_code, stock_info_dict)
        
        # 3. 获取并保存财务数据
        if fetch_fundamental:
            print("\n正在获取财务数据...")
            fin_df = get_stock_fundamentals(stock_code)
            save_stock_fundamentals(db, stock_code, fin_df)
        
        print("\n" + "=" * 60)
        print("数据抓取完成！")
        print("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='股票数据抓取')
    parser.add_argument('stock_code', nargs='?', default='601211.SH', 
                        help='股票代码，默认: 601211.SH')
    parser.add_argument('--months', type=int, default=36,
                        help='抓取最近几个月的数据，默认: 36')
    parser.add_argument('--no-daily', action='store_true',
                        help='不抓取日线数据')
    parser.add_argument('--no-info', action='store_true',
                        help='不抓取基本信息')
    parser.add_argument('--no-fundamental', action='store_true',
                        help='不抓取财务数据')
    
    args = parser.parse_args()
    
    # 配置抓取参数
    STOCK_CODE = args.stock_code
    MONTHS = args.months
    FETCH_DAILY = not args.no_daily
    FETCH_INFO = not args.no_info
    FETCH_FUNDAMENTAL = not args.no_fundamental
    
    print(f"股票代码格式说明：")
    print(f"  - 上交所（上海）：600036.SH")
    print(f"  - 深交所（深圳）：000001.SZ")
    print(f"  - 科创板（上海）：688001.SH")
    print(f"  - 创业板（深圳）：300001.SZ")
    print()
    
    crawl_stock(
        STOCK_CODE, 
        MONTHS,
        fetch_daily=FETCH_DAILY,
        fetch_info=FETCH_INFO,
        fetch_fundamental=FETCH_FUNDAMENTAL
    )
