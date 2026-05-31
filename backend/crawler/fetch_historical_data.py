#!/usr/bin/env python3
"""
从 akshare 获取股票历史日线数据
使用 get_stock_daily_data 方法
"""
import sys
import os
import json
import pandas as pd
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import SessionLocal, init_db
from models.stock_data import DailyQuote
import akshare as ak
import math


def _parse_trade_date(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, dict):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%Y%m%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        try:
            return pd.to_datetime(value).date()
        except Exception:
            return None
    if isinstance(value, (int, float)):
        if value <= 0:
            return None
        ts = float(value)
        if ts > 10_000_000_000:
            ts = ts / 1000.0
        try:
            return datetime.fromtimestamp(ts).date()
        except Exception:
            return None
    if hasattr(value, "to_pydatetime"):
        try:
            return value.to_pydatetime().date()
        except Exception:
            return None
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def get_data_dir():
    """获取数据存储目录"""
    crawler_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(crawler_dir, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir


def get_historical_file_path(stock_code, start_date, end_date):
    """获取历史数据文件路径"""
    data_dir = get_data_dir()
    return os.path.join(data_dir, f'historical_{stock_code}_{start_date}_{end_date}.json')


def load_historical_from_file(stock_code, start_date, end_date):
    """从文件加载历史数据"""
    file_path = get_historical_file_path(stock_code, start_date, end_date)
    if not os.path.exists(file_path):
        return None
    
    try:
        df = pd.read_json(file_path, orient='records')
        if df is None or df.empty:
            return None
        if '日期' not in df.columns:
            return None
        return df
    except Exception as e:
        print(f"加载历史数据文件失败: {e}")
        return None


def save_historical_to_file(stock_code, start_date, end_date, df):
    """保存历史数据到文件"""
    file_path = get_historical_file_path(stock_code, start_date, end_date)
    try:
        df.to_json(file_path, orient='records', force_ascii=False, indent=2)
        print(f"历史数据已保存到: {file_path}")
        return True
    except Exception as e:
        print(f"保存历史数据文件失败: {e}")
        return False


def get_stock_daily_data(stock_code, start_date, end_date):
    """获取股票的历史日线数据"""
    try:
        stock_zh_a_hist_df = ak.stock_zh_a_hist(
            symbol=stock_code.split('.')[0],
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=""
        )
        print(f"成功获取 {len(stock_zh_a_hist_df)} 条历史数据")
        return stock_zh_a_hist_df
    except Exception as e:
        print(f"获取股票数据失败: {e}")
        return None


def calculate_indicators(df):
    """计算技术指标并补充缺失数据"""
    # 补充估算成交额（如果缺失）：使用 (最高价+最低价)/2 * 成交量 估算
    if '成交额' in df.columns:
        mask = df['成交额'].isna()
        if mask.any():
            # 估算成交额 = 平均价 × 成交量
            # akshare 的成交量单位通常是手，1手=100股
            df.loc[mask, '成交额'] = (df.loc[mask, '最高'] + df.loc[mask, '最低']) / 2 * df.loc[mask, '成交量'] * 100
    
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
    """将NaN值转换为None以便数据库存储"""
    if isinstance(value, dict):
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if pd.isna(value):
        return None
    return value


def save_historical_to_db(db, stock_code, df):
    """保存历史数据到数据库"""
    if df is None or df.empty:
        return False
    
    inserted_count = 0
    updated_count = 0
    
    for _, row in df.iterrows():
        trade_date = _parse_trade_date(row.get('日期'))
        if trade_date is None:
            continue
        
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
    
    if inserted_count + updated_count > 0:
        db.commit()
        print(f"历史数据 - 新增 {inserted_count} 条，更新 {updated_count} 条")
        return True
    return False


def fetch_and_save_historical(stock_code, start_date=None, end_date=None):
    """获取并保存历史数据
    
    Args:
        stock_code: 股票代码
        start_date: 开始日期 (YYYYMMDD)，默认3年前
        end_date: 结束日期 (YYYYMMDD)，默认今天
    """
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=3*365)).strftime('%Y%m%d')
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    
    init_db()
    db = SessionLocal()
    
    try:
        # 1. 先尝试从文件加载
        df = load_historical_from_file(stock_code, start_date, end_date)
        
        if df is not None:
            print(f"从文件加载到历史数据: {stock_code}")
        else:
            # 2. 文件不存在，从接口获取
            df = get_stock_daily_data(stock_code, start_date, end_date)
            if df is not None and not df.empty:
                save_historical_to_file(stock_code, start_date, end_date, df)
        
        # 3. 计算技术指标
        if df is not None and not df.empty:
            print("正在计算技术指标...")
            df = calculate_indicators(df)
            
            # 4. 保存到数据库
            save_historical_to_db(db, stock_code, df)
        
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("从 akshare 获取股票历史日线数据")
    print("=" * 60)
    
    # 默认抓取招商银行
    default_code = "600036.SH"
    
    stock_code = default_code
    start_date = None
    end_date = None
    
    if len(sys.argv) > 1:
        stock_code = sys.argv[1]
    if len(sys.argv) > 3:
        start_date = sys.argv[2]
        end_date = sys.argv[3]
    
    print(f"股票代码: {stock_code}")
    if start_date and end_date:
        print(f"时间范围: {start_date} 至 {end_date}")
    else:
        print(f"时间范围: 默认最近3年")
    fetch_and_save_historical(stock_code, start_date, end_date)
