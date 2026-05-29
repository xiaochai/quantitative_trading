#!/usr/bin/env python3
"""
批量抓取股票历史数据
通过读取已保存的股票列表文件，调用 crawl_stock 逐个抓取
"""
import sys
import os
import time
import json
import glob

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from stock_crawler import crawl_stock
import pandas as pd


def find_latest_stock_list():
    """
    找到最新的股票列表文件
    
    Returns:
        str: 文件路径
    """
    # 在当前目录查找 all_a_stocks_*.json 或 *.csv 文件
    crawler_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 先找 json
    json_files = glob.glob(os.path.join(crawler_dir, 'all_a_stocks_*.json'))
    if json_files:
        # 按修改时间排序，取最新的
        json_files.sort(key=os.path.getmtime, reverse=True)
        return json_files[0]
    
    # 再找 csv
    csv_files = glob.glob(os.path.join(crawler_dir, 'all_a_stocks_*.csv'))
    if csv_files:
        csv_files.sort(key=os.path.getmtime, reverse=True)
        return csv_files[0]
    
    return None


def load_stock_list(file_path):
    """
    加载股票列表
    
    Args:
        file_path: 文件路径
    
    Returns:
        list: 股票列表，格式 [{'stock_code': '...', 'stock_name': '...'}, ...]
    """
    if not file_path or not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return []
    
    if file_path.endswith('.json'):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    elif file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
        return df.to_dict('records')
    else:
        print(f"不支持的文件格式: {file_path}")
        return []


def batch_crawl(
    stock_list, 
    months=36, 
    sleep_between=3,
    fetch_daily=True,
    fetch_info=True,
    fetch_fundamental=True
):
    """
    批量抓取股票数据
    
    Args:
        stock_list: 股票列表
        months: 抓取几个月的数据
        sleep_between: 每个股票之间的暂停时间（秒）
        fetch_daily: 是否抓取日线数据
        fetch_info: 是否抓取基本信息
        fetch_fundamental: 是否抓取财务数据
    """
    total = len(stock_list)
    success_count = 0
    fail_count = 0
    
    print("=" * 80)
    print(f"开始批量抓取")
    print(f"股票总数: {total}")
    print(f"抓取时间范围: 最近 {months} 个月")
    print(f"每个股票间隔: {sleep_between} 秒")
    print(f"抓取内容:")
    if fetch_daily:
        print(f"  ✓ 日线数据")
    if fetch_info:
        print(f"  ✓ 基本信息")
    if fetch_fundamental:
        print(f"  ✓ 财务数据")
    print("=" * 80)
    
    for idx, stock in enumerate(stock_list):
        stock_code = stock.get('stock_code', '')
        stock_name = stock.get('stock_name', '')
        
        print(f"\n[{idx+1}/{total}] 正在抓取: {stock_name} ({stock_code})")
        print("-" * 80)
        
        try:
            # 调用抓取函数
            crawl_stock(
                stock_code, 
                months=months,
                fetch_daily=fetch_daily,
                fetch_info=fetch_info,
                fetch_fundamental=fetch_fundamental
            )
            success_count += 1
            print(f"✓ {stock_name} ({stock_code}) 抓取成功")
            
        except Exception as e:
            fail_count += 1
            print(f"✗ {stock_name} ({stock_code}) 抓取失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 不是最后一个的话，sleep一下
        if idx < total - 1:
            print(f"\n等待 {sleep_between} 秒...")
            time.sleep(sleep_between)
    
    print("\n" + "=" * 80)
    print("批量抓取完成！")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"总计: {total}")
    print("=" * 80)


def main():
    """
    主函数
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='批量股票数据抓取')
    parser.add_argument('--file', type=str, default=None,
                        help='股票列表文件路径，默认自动查找最新的')
    parser.add_argument('--count', type=int, default=None,
                        help='要抓取的股票数量，默认全部')
    parser.add_argument('--months', type=int, default=36,
                        help='抓取最近几个月的数据，默认: 36')
    parser.add_argument('--sleep', type=int, default=3,
                        help='每个股票间隔几秒，默认: 3')
    parser.add_argument('--no-daily', action='store_true',
                        help='不抓取日线数据')
    parser.add_argument('--no-info', action='store_true',
                        help='不抓取基本信息')
    parser.add_argument('--no-fundamental', action='store_true',
                        help='不抓取财务数据')
    
    args = parser.parse_args()
    
    # 查找最新的股票列表文件
    if args.file:
        stock_file = args.file
    else:
        stock_file = find_latest_stock_list()
    
    if not stock_file or not os.path.exists(stock_file):
        print("未找到股票列表文件！请先运行 fetch_all_stocks.py")
        return
    
    print(f"找到股票列表文件: {stock_file}")
    
    # 加载股票列表
    stock_list = load_stock_list(stock_file)
    
    if not stock_list:
        print("股票列表为空！")
        return
    
    # 确定要抓取的数量
    num_to_crawl = len(stock_list)
    if args.count:
        num_to_crawl = min(args.count, len(stock_list))
    else:
        # 交互式询问
        print(f"\n总共 {len(stock_list)} 只股票")
        try:
            user_input = input(f"请输入要抓取的数量（直接回车抓取全部 {len(stock_list)} 只）: ").strip()
            if user_input:
                num_to_crawl = int(user_input)
                if num_to_crawl > len(stock_list):
                    num_to_crawl = len(stock_list)
                elif num_to_crawl <= 0:
                    print("数量必须大于0")
                    return
        except ValueError:
            pass
    
    # 截取指定数量
    stock_list = stock_list[:num_to_crawl]
    
    # 开始批量抓取
    batch_crawl(
        stock_list=stock_list,
        months=args.months,
        sleep_between=args.sleep,
        fetch_daily=not args.no_daily,
        fetch_info=not args.no_info,
        fetch_fundamental=not args.no_fundamental
    )


if __name__ == "__main__":
    main()
