#!/usr/bin/env python3
"""
探索 stock_individual_info_em 接口的结构
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak

print("=" * 60)
print("探索 stock_individual_info_em 接口")
print("=" * 60)

try:
    df = ak.stock_individual_info_em(symbol="600036")
    print("列名:", df.columns.tolist())
    print("\n数据:")
    print(df.to_string())
    
    print("\n\n查找包含上市时间...")
    for _, row in df.iterrows():
        item = str(row.get('item', ''))
        value = row.get('value', '')
        if '上市' in item or 'date' in item.lower():
            print(f"  {item}: {value}")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
