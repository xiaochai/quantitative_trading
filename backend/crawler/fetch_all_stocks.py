#!/usr/bin/env python3
"""
获取所有A股股票列表并保存到文件
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import akshare as ak
import pandas as pd


def get_all_a_stocks():
    """
    获取所有A股股票列表
    
    Returns:
        DataFrame: 包含所有股票信息的DataFrame
    """
    print("=" * 60)
    print("正在获取所有A股股票列表...")
    print("=" * 60)
    
    # 尝试多个接口
    interfaces = [
        ('stock_zh_a_spot_em', ak.stock_zh_a_spot_em, {}),
        ('stock_zh_a_spot', ak.stock_zh_a_spot, {}),
    ]
    
    for name, func, kwargs in interfaces:
        try:
            print(f"尝试接口: {name}")
            df = func(**kwargs)
            
            if df is not None and not df.empty:
                print(f"✓ 成功获取 {len(df)} 只股票")
                print("\n前5只股票:")
                if '代码' in df.columns and '名称' in df.columns:
                    print(df[['代码', '名称']].head().to_string(index=False))
                return df
        except Exception as e:
            print(f"  接口 {name} 失败: {e}")
            continue
    
    print("\n✗ 所有接口都失败了")
    return None


def save_stocks_to_file(df):
    """
    将股票列表保存到文件
    
    Args:
        df: 股票信息DataFrame
    """
    if df is None or df.empty:
        return
    
    print("\n" + "=" * 60)
    print("正在保存到文件...")
    print("=" * 60)
    
    # 生成文件名（带时间戳）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_csv = f'all_a_stocks_{timestamp}.csv'
    filename_json = f'all_a_stocks_{timestamp}.json'
    
    # 处理股票代码格式
    processed_data = []
    debug_printed = False
    
    for idx, row in df.iterrows():
        # 处理股票代码
        code = str(row['代码'])
        original_code = str(row['代码'])
        
        # 打印前几个例子看看
        if not debug_printed and idx < 3:
            print(f"示例股票代码: '{original_code}'")
            debug_printed = True
        
        # 尝试多种格式识别
        stock_code = None
        
        # 格式1: bj920000 → 920000.BJ
        code_lower = code.lower()
        if code_lower.startswith('bj'):
            numeric_part = code_lower[2:]
            stock_code = f"{numeric_part}.BJ"
        elif code_lower.startswith('sh'):
            numeric_part = code_lower[2:]
            stock_code = f"{numeric_part}.SH"
        elif code_lower.startswith('sz'):
            numeric_part = code_lower[2:]
            stock_code = f"{numeric_part}.SZ"
        else:
            # 格式2: 纯数字
            numeric_code = code
            if numeric_code.startswith('6'):
                stock_code = f"{numeric_code}.SH"
            elif numeric_code.startswith('0') or numeric_code.startswith('3'):
                stock_code = f"{numeric_code}.SZ"
            elif numeric_code.startswith('8') or numeric_code.startswith('4'):
                stock_code = f"{numeric_code}.BJ"
        
        if stock_code is None:
            print(f"跳过无法识别的股票: {original_code}")
            continue
        
        processed_row = {
            'stock_code': stock_code,
            'stock_name': str(row.get('名称', '')),
        }
        # 添加其他可能的列
        for col in df.columns:
            if col not in ['代码', '名称']:
                processed_row[col] = row[col]
        
        processed_data.append(processed_row)
    
    processed_df = pd.DataFrame(processed_data)
    
    # 保存为 CSV
    csv_path = os.path.join(os.path.dirname(__file__), filename_csv)
    processed_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"✓ 已保存到 CSV: {csv_path}")
    
    # 保存为 JSON
    json_path = os.path.join(os.path.dirname(__file__), filename_json)
    processed_df.to_json(json_path, orient='records', force_ascii=False, indent=2)
    print(f"✓ 已保存到 JSON: {json_path}")
    
    # 显示统计
    print("\n股票市场分布:")
    sh_count = len([d for d in processed_data if d['stock_code'].endswith('.SH')])
    sz_count = len([d for d in processed_data if d['stock_code'].endswith('.SZ')])
    bj_count = len([d for d in processed_data if d['stock_code'].endswith('.BJ')])
    print(f"  上交所: {sh_count} 只")
    print(f"  深交所: {sz_count} 只")
    if bj_count > 0:
        print(f"  北交所: {bj_count} 只")
    print(f"  总计: {sh_count + sz_count + bj_count} 只")
    
    print("\n" + "=" * 60)
    print("保存完成！")
    print("=" * 60)


def main():
    """
    主函数
    """
    # 获取所有A股
    df = get_all_a_stocks()
    
    if df is not None:
        # 保存到文件
        save_stocks_to_file(df)
        
        print(f"\n✓ 完成！文件保存在: {os.path.dirname(os.path.abspath(__file__))}")


if __name__ == "__main__":
    main()
