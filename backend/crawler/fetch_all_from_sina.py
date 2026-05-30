#!/usr/bin/env python3
"""
从新浪接口获取今天所有股票数据
"""
import sys
import os
import json
from datetime import datetime, date
import pandas as pd

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import SessionLocal, init_db
from models.stock_data import DailyQuote, StockInfo
import akshare as ak


def get_data_dir():
    """获取数据存储目录"""
    crawler_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(crawler_dir, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir


def get_today_data_file_path():
    """获取今天的数据文件路径"""
    data_dir = get_data_dir()
    today_str = datetime.now().strftime('%Y%m%d')
    return os.path.join(data_dir, f'sina_stock_data_{today_str}.json')


def load_data_from_file():
    """从文件加载数据"""
    file_path = get_today_data_file_path()
    if os.path.exists(file_path):
        print(f"发现今天的数据文件: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return pd.read_json(file_path)
        except Exception as e:
            print(f"加载文件失败: {e}")
            return None
    return None


def save_data_to_file(df):
    """保存数据到文件"""
    file_path = get_today_data_file_path()
    try:
        df.to_json(file_path, orient='records', force_ascii=False, indent=2)
        print(f"数据已保存到: {file_path}")
        return True
    except Exception as e:
        print(f"保存文件失败: {e}")
        return False


def fetch_data_from_sina():
    """从新浪接口获取数据"""
    print("正在从新浪接口获取股票数据...")
    try:
        df = ak.stock_zh_a_spot()
        print(f"✓ 成功获取 {len(df)} 只股票数据")
        print(f"列名: {df.columns.tolist()}")
        print(f"\n前3条数据:")
        print(df.head(3).to_string())
        return df
    except Exception as e:
        print(f"获取数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def convert_stock_code(code):
    """转换股票代码格式"""
    # 确保转换为字符串
    code_str = str(code).strip().lower()
    
    # 格式是 bj920000, sz301348 这种
    if len(code_str) >= 8:
        prefix = code_str[:2]
        num = code_str[2:]
        if prefix == 'bj':
            return f"{num}.BJ"
        elif prefix == 'sz':
            return f"{num}.SZ"
        elif prefix == 'sh':
            return f"{num}.SH"
    
    # 如果是纯数字，判断市场
    if len(code_str) >= 6 and code_str.isdigit():
        if code_str.startswith('6'):
            return f"{code_str}.SH"
        else:
            return f"{code_str}.SZ"
    
    # 备用方案
    return code_str


def parse_bool(value):
    """解析布尔值"""
    if isinstance(value, bool):
        return value
    s = str(value).lower()
    return s in ['true', '1', 'yes', 'st']


def process_stock_info(db, row):
    """处理单只股票的信息更新"""
    # 解析数据
    code = row.get('代码', '')
    name = str(row.get('名称', ''))
    
    stock_code = convert_stock_code(code)
    
    # 跳过无效数据
    if not stock_code or len(stock_code) < 6 or name == 'nan':
        return False
    
    # 构建新的信息
    new_info = {
        'stock_code': stock_code,
        'stock_name': name,
        'industry_sw1': None,  # 新浪接口可能没有行业信息
        'industry_sw2': None,
        'is_st': 'ST' in name,
        'is_star_st': '*ST' in name,
        'is_delisted': '退' in name,
        'delisted_date': None,
        'listed_date': None,
        'component_tags': None,
        'report_date': date.today()
    }
    
    # 查找今天是否已有记录
    existing_today = db.query(StockInfo).filter(
        StockInfo.stock_code == stock_code,
        StockInfo.report_date == date.today()
    ).first()
    
    if existing_today:
        # 今天已有记录，更新就行
        existing_today.stock_name = name
        existing_today.is_st = 'ST' in name
        existing_today.is_star_st = '*ST' in name
        existing_today.is_delisted = '退' in name
        return True
    
    # 查找最新记录
    latest = db.query(StockInfo).filter(
        StockInfo.stock_code == stock_code
    ).order_by(StockInfo.report_date.desc()).first()
    
    # 比较是否有变化
    changed = False
    if not latest:
        changed = True  # 第一次插入
    else:
        # 检查关键字段是否有变化
        if (latest.stock_name != name or
            latest.is_st != ('ST' in name) or
            latest.is_star_st != ('*ST' in name) or
            latest.is_delisted != ('退' in name)):
            changed = True
    
    if changed:
        # 有变化，插入新记录
        record = StockInfo(**new_info)
        db.add(record)
        if not latest:
            print(f"[+] 新增股票: {stock_code} - {name}")
        else:
            print(f"[+] 股票信息变化: {stock_code} - {name}")
        return True
    else:
        return False


def process_daily_quotes(db, row):
    """处理日线数据"""
    # 解析数据
    code = row.get('代码', '')
    name = str(row.get('名称', ''))
    stock_code = convert_stock_code(code)
    trade_date = date.today()
    
    # 跳过无效数据
    if not stock_code or len(stock_code) < 6 or name == 'nan':
        return False
    
    # 解析行情数据
    try:
        open_price = float(row.get('今开')) if pd.notna(row.get('今开')) else None
        close_price = float(row.get('最新价')) if pd.notna(row.get('最新价')) else None
        high_price = float(row.get('最高')) if pd.notna(row.get('最高')) else None
        low_price = float(row.get('最低')) if pd.notna(row.get('最低')) else None
        volume = int(row.get('成交量')) if pd.notna(row.get('成交量')) else None
        amount = float(row.get('成交额')) if pd.notna(row.get('成交额')) else None
        change_pct = float(row.get('涨跌幅')) if pd.notna(row.get('涨跌幅')) else None
    except Exception as e:
        print(f"解析数据失败 {stock_code}: {e}")
        return False
    
    # 查找现有记录
    existing = db.query(DailyQuote).filter(
        DailyQuote.stock_code == stock_code,
        DailyQuote.trade_date == trade_date
    ).first()
    
    if not existing:
        # 新建记录
        quote = DailyQuote(
            stock_code=stock_code,
            trade_date=trade_date,
            open=open_price,
            close=close_price,
            high=high_price,
            low=low_price,
            volume=volume,
            amount=amount,
            change_pct=change_pct,
            change_20d_pct=None,
            turnover_rate=None,
            market_cap=None,
            pe_ttm=None,
            ma5=None,
            ma20=None,
            ma60=None,
            macd=None,
            macd_signal=None,
            macd_hist=None,
            rsi=None,
            boll_upper=None,
            boll_middle=None,
            boll_lower=None
        )
        db.add(quote)
        return True
    else:
        # 更新记录
        updated = False
        if open_price is not None and existing.open != open_price:
            existing.open = open_price
            updated = True
        if close_price is not None and existing.close != close_price:
            existing.close = close_price
            updated = True
        if high_price is not None and existing.high != high_price:
            existing.high = high_price
            updated = True
        if low_price is not None and existing.low != low_price:
            existing.low = low_price
            updated = True
        if volume is not None and existing.volume != volume:
            existing.volume = volume
            updated = True
        if amount is not None and existing.amount != amount:
            existing.amount = amount
            updated = True
        if change_pct is not None and existing.change_pct != change_pct:
            existing.change_pct = change_pct
            updated = True
        return updated


def main():
    """主函数"""
    # 初始化数据库
    init_db()
    db = SessionLocal()
    
    try:
        # 第1步: 检查是否有今天的文件
        df = load_data_from_file()
        
        if df is None:
            # 第2步: 从接口获取数据
            df = fetch_data_from_sina()
            if df is None or df.empty:
                print("获取数据失败，退出")
                return
            
            # 第3步: 保存到文件
            save_data_to_file(df)
        else:
            print(f"从文件加载了 {len(df)} 条数据")
        
        # 第4、5步: 处理stock_info
        print("\n" + "="*60)
        print("正在处理股票信息...")
        print("="*60)
        info_changes = 0
        for idx, row in df.iterrows():
            try:
                if process_stock_info(db, row):
                    info_changes += 1
                # 每10条提交一次
                if (idx + 1) % 10 == 0:
                    db.commit()
                    print(f"已处理 {idx + 1}/{len(df)} 只股票")
            except Exception as e:
                print(f"处理第{idx}条股票信息失败: {e}")
                db.rollback()
        
        db.commit()
        print(f"\n股票信息处理完成，变更数量: {info_changes}")
        
        # 第6步: 处理daily_quotes
        print("\n" + "="*60)
        print("正在处理日线数据...")
        print("="*60)
        quote_changes = 0
        for idx, row in df.iterrows():
            try:
                if process_daily_quotes(db, row):
                    quote_changes += 1
                # 每10条提交一次
                if (idx + 1) % 10 == 0:
                    db.commit()
                    print(f"已处理 {idx + 1}/{len(df)} 条行情数据")
            except Exception as e:
                print(f"处理第{idx}条行情数据失败: {e}")
                db.rollback()
        
        db.commit()
        print(f"\n日线数据处理完成，变更数量: {quote_changes}")
        
        print("\n" + "="*60)
        print("✓ 全部处理完成!")
        print("="*60)
        
    except Exception as e:
        print(f"处理失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
