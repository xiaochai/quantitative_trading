#!/usr/bin/env python3
"""
抓取指数成分股数据并更新到 stock_info 表
"""
import sys
import os
import json
from datetime import datetime, date

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import SessionLocal, init_db
from models.stock_data import StockInfo
import akshare as ak

# 定义需要抓取的常见指数
INDEX_LIST = [
    {'name': '沪深300', 'symbol': '000300'},
    {'name': '中证500', 'symbol': '000905'},
    {'name': '中证1000', 'symbol': '000852'},
    {'name': '创业板指', 'symbol': '399006'},
    {'name': '上证50', 'symbol': '000016'},
    {'name': '科创50', 'symbol': '000688'},
    {'name': '上证180', 'symbol': '000010'},
    {'name': '深证100', 'symbol': '399330'},
]

def get_data_dir():
    """获取数据存储目录"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir

def fetch_index_constituents(index_name, index_symbol):
    """
    获取单个指数的成分股
    
    Args:
        index_name: 指数名称
        index_symbol: 指数代码
    
    Returns:
        list: 股票代码列表
    """
    print(f"正在抓取 {index_name} ({index_symbol}) 成分股...")
    try:
        df = ak.index_stock_cons(symbol=index_symbol)
        stock_codes = df['品种代码'].tolist()
        print(f"  成功获取 {len(stock_codes)} 只成分股")
        return stock_codes
    except Exception as e:
        print(f"  抓取失败: {e}")
        return []

def fetch_all_constituents():
    """
    抓取所有指数的成分股并聚合
    
    Returns:
        dict: {stock_code: [index_names]}
    """
    print("=" * 60)
    print("开始抓取指数成分股数据")
    print("=" * 60)
    
    # 股票代码到指数标签的映射
    stock_tags = {}
    
    for index_info in INDEX_LIST:
        stock_codes = fetch_index_constituents(index_info['name'], index_info['symbol'])
        
        # 聚合到股票标签
        for stock_code in stock_codes:
            if stock_code not in stock_tags:
                stock_tags[stock_code] = []
            stock_tags[stock_code].append(index_info['name'])
    
    # 保存到文件
    data_dir = get_data_dir()
    today = datetime.now().strftime('%Y%m%d')
    file_path = os.path.join(data_dir, f'constituents_{today}.json')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(stock_tags, f, ensure_ascii=False, indent=2)
    
    print(f"\n成分股数据已保存到: {file_path}")
    print(f"共涉及 {len(stock_tags)} 只股票")
    
    return stock_tags

def update_stock_info(stock_tags):
    """
    更新 stock_info 表的 component_tags 字段
    
    Args:
        stock_tags: {stock_code: [index_names]}
    """
    print("\n" + "=" * 60)
    print("开始更新 stock_info 表")
    print("=" * 60)
    
    init_db()
    db = SessionLocal()
    
    today = date.today()
    updated_count = 0
    inserted_count = 0
    
    try:
        for stock_code_short, tags in stock_tags.items():
            # 补充完整的股票代码
            # 注意：这里假设6开头的是上海，0/3开头的是深圳
            if stock_code_short.startswith('6'):
                stock_code = f"{stock_code_short}.SH"
            elif stock_code_short.startswith('0') or stock_code_short.startswith('3'):
                stock_code = f"{stock_code_short}.SZ"
            else:
                # 不确定的跳过或根据实际情况处理
                print(f"  无法确定股票代码后缀: {stock_code_short}，跳过")
                continue
            
            # 查询该股票最新的记录
            latest_record = db.query(StockInfo).filter(
                StockInfo.stock_code == stock_code
            ).order_by(
                StockInfo.report_date.desc()
            ).first()
            
            if latest_record:
                # 检查是否需要更新
                new_tags_json = json.dumps(tags, ensure_ascii=False)
                old_tags_json = latest_record.component_tags or '[]'
                
                if new_tags_json != old_tags_json:
                    # 检查今天是否已经有记录
                    today_record = db.query(StockInfo).filter(
                        StockInfo.stock_code == stock_code,
                        StockInfo.report_date == today
                    ).first()
                    
                    if today_record:
                        # 更新今天的记录
                        today_record.component_tags = new_tags_json
                        today_record.stock_name = latest_record.stock_name
                        today_record.industry_sw1 = latest_record.industry_sw1
                        today_record.industry_sw2 = latest_record.industry_sw2
                        today_record.is_st = latest_record.is_st
                        today_record.is_star_st = latest_record.is_star_st
                        today_record.is_delisted = latest_record.is_delisted
                        today_record.listed_date = latest_record.listed_date
                        today_record.delisted_date = latest_record.delisted_date
                        updated_count += 1
                        print(f"  更新: {stock_code} {latest_record.stock_name or ''} - 标签: {tags}")
                    else:
                        # 插入新记录
                        new_record = StockInfo(
                            stock_code=stock_code,
                            stock_name=latest_record.stock_name,
                            industry_sw1=latest_record.industry_sw1,
                            industry_sw2=latest_record.industry_sw2,
                            is_st=latest_record.is_st,
                            is_star_st=latest_record.is_star_st,
                            is_delisted=latest_record.is_delisted,
                            listed_date=latest_record.listed_date,
                            delisted_date=latest_record.delisted_date,
                            component_tags=new_tags_json,
                            report_date=today
                        )
                        db.add(new_record)
                        inserted_count += 1
                        print(f"  插入: {stock_code} {latest_record.stock_name or ''} - 标签: {tags}")
            else:
                print(f"  股票不在 stock_info 表中: {stock_code}，跳过")
        
        db.commit()
        print("\n" + "=" * 60)
        print(f"更新完成! 更新: {updated_count} 条, 插入: {inserted_count} 条")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"更新失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def load_constituents_from_file():
    """
    从文件加载成分股数据（避免重复抓取）
    
    Returns:
        dict: {stock_code: [index_names]} 或 None
    """
    data_dir = get_data_dir()
    today = datetime.now().strftime('%Y%m%d')
    file_path = os.path.join(data_dir, f'constituents_{today}.json')
    
    if os.path.exists(file_path):
        print(f"从文件加载成分股数据: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return None

def main():
    # 先尝试从文件加载
    stock_tags = load_constituents_from_file()
    
    # 如果文件不存在或需要重新抓取
    if stock_tags is None:
        stock_tags = fetch_all_constituents()
    
    # 更新数据库
    if stock_tags:
        update_stock_info(stock_tags)
    else:
        print("没有获取到成分股数据")

if __name__ == "__main__":
    main()
