#!/usr/bin/env python3
"""
批量获取所有股票的历史数据和财务数据
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import SessionLocal, init_db
from models.stock_data import StockInfo

# 导入两个抓取函数
from fetch_financials_from_ths import fetch_and_save_financial
from fetch_historical_data import fetch_and_save_historical


def get_active_stocks():
    """获取所有未退市的股票
    
    Returns:
        list: 股票代码列表
    """
    db = SessionLocal()
    try:
        # 获取最新的股票信息（按股票代码分组，取最新的 report_date）
        # 使用子查询获取每个股票的最新记录
        from sqlalchemy import func, desc
        
        # 先获取每个股票代码的最新 report_date
        subquery = db.query(
            StockInfo.stock_code,
            func.max(StockInfo.report_date).label('max_date')
        ).group_by(StockInfo.stock_code).subquery()
        
        # 再关联查询获取完整信息
        query = db.query(StockInfo).join(
            subquery,
            (StockInfo.stock_code == subquery.c.stock_code) & 
            (StockInfo.report_date == subquery.c.max_date)
        ).filter(StockInfo.is_delisted == False)
        
        stocks = query.all()
        stock_codes = [stock.stock_code for stock in stocks]
        
        print(f"找到 {len(stock_codes)} 只未退市的股票")
        return stock_codes
        
    finally:
        db.close()


def batch_fetch(start_date='20230531', end_date='20260530'):
    """批量抓取所有股票的数据
    
    Args:
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)
    """
    print("=" * 60)
    print("批量获取股票历史数据和财务数据")
    print("=" * 60)
    print(f"历史数据时间范围: {start_date} 至 {end_date}")
    print()
    
    # 初始化数据库
    init_db()
    
    # 获取股票列表
    stock_codes = get_active_stocks()
    
    if not stock_codes:
        print("没有找到可抓取的股票")
        return
    
    # 开始批量抓取
    success_count = 0
    fail_count = 0
    
    for i, stock_code in enumerate(stock_codes, 1):
        print()
        print("-" * 60)
        print(f"[{i}/{len(stock_codes)}] 处理: {stock_code}")
        print("-" * 60)
        
        try:
            # 1. 获取财务数据
            print("\n[1/2] 正在获取财务数据...")
            fetch_and_save_financial(stock_code)
            
            # 2. 获取历史数据
            print("\n[2/2] 正在获取历史数据...")
            fetch_and_save_historical(stock_code, start_date, end_date)
            
            success_count += 1
            print(f"\n✓ {stock_code} 处理成功")
            
        except Exception as e:
            fail_count += 1
            print(f"\n✗ {stock_code} 处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 输出统计信息
    print()
    print("=" * 60)
    print("批量抓取完成")
    print("=" * 60)
    print(f"总计: {len(stock_codes)} 只")
    print(f"成功: {success_count} 只")
    print(f"失败: {fail_count} 只")


if __name__ == "__main__":
    # 支持自定义日期范围
    start_date = '20230531'
    end_date = '20260530'
    
    if len(sys.argv) > 2:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
    
    batch_fetch(start_date, end_date)
