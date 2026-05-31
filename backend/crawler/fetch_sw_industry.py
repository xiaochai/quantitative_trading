#!/usr/bin/env python3
"""
从 akshare 获取最新申万行业分类并更新到 stock_info 表
"""
import sys
import os
import json
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import SessionLocal, init_db
from models.stock_data import StockInfo
import akshare as ak

def get_data_dir():
    """获取数据存储目录"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir

def fetch_sw_industry_data():
    """
    获取所有申万行业分类的成分股
    """
    print("=" * 60)
    print("从 akshare 获取最新申万行业分类数据")
    print("=" * 60)
    
    stock_industry_map = {}  # {stock_code: {'first': xx, 'second': xx}}
    
    try:
        # 1. 获取所有一级行业
        print("\n--- 步骤1: 获取一级行业 ---")
        df_first = ak.sw_index_first_info()
        print(f"找到 {len(df_first)} 个一级行业")
        
        for idx, row_first in df_first.iterrows():
            first_code = row_first['行业代码'].split('.')[0]  # 去掉 .SI
            first_name = row_first['行业名称']
            print(f"\n[{idx+1}/{len(df_first)}] 处理一级行业: {first_name} ({first_code})")
            
            try:
                # 获取该一级行业的所有成分股
                df_comp = ak.index_component_sw(symbol=first_code)
                print(f"  成分股数量: {len(df_comp)}")
                
                for _, comp_row in df_comp.iterrows():
                    stock_code = comp_row['证券代码']
                    stock_name = comp_row['证券名称']
                    
                    # 补全后缀
                    if stock_code.startswith('6'):
                        full_code = f"{stock_code}.SH"
                    elif stock_code.startswith('0') or stock_code.startswith('3'):
                        full_code = f"{stock_code}.SZ"
                    else:
                        continue
                    
                    # 存储一级行业信息
                    if full_code not in stock_industry_map:
                        stock_industry_map[full_code] = {
                            'first': first_name,
                            'second': None,
                            'name': stock_name
                        }
                    else:
                        # 如果已有记录，只更新一级行业（防止重复）
                        stock_industry_map[full_code]['first'] = first_name
                        stock_industry_map[full_code]['name'] = stock_name
            
            except Exception as e:
                print(f"  获取成分股失败: {e}")
                continue
        
        # 2. 获取所有二级行业并更新
        print("\n--- 步骤2: 获取二级行业 ---")
        df_second = ak.sw_index_second_info()
        print(f"找到 {len(df_second)} 个二级行业")
        
        for idx, row_second in df_second.iterrows():
            second_code = row_second['行业代码'].split('.')[0]
            second_name = row_second['行业名称']
            print(f"\r处理二级行业: [{idx+1}/{len(df_second)}] {second_name}", end='')
            
            try:
                df_comp = ak.index_component_sw(symbol=second_code)
                for _, comp_row in df_comp.iterrows():
                    stock_code = comp_row['证券代码']
                    
                    if stock_code.startswith('6'):
                        full_code = f"{stock_code}.SH"
                    elif stock_code.startswith('0') or stock_code.startswith('3'):
                        full_code = f"{stock_code}.SZ"
                    else:
                        continue
                    
                    # 更新二级行业
                    if full_code in stock_industry_map:
                        stock_industry_map[full_code]['second'] = second_name
            
            except Exception as e:
                continue
        
        print(f"\n\n总计收集到 {len(stock_industry_map)} 只股票的行业信息")
        
        # 保存到文件
        data_dir = get_data_dir()
        today = datetime.now().strftime('%Y%m%d')
        save_file = os.path.join(data_dir, f'sw_industry_akshare_{today}.json')
        
        with open(save_file, 'w', encoding='utf-8') as f:
            json.dump(stock_industry_map, f, ensure_ascii=False, indent=2)
        
        print(f"数据已保存到: {save_file}")
        
        return stock_industry_map
    
    except Exception as e:
        print(f"获取数据失败: {e}")
        import traceback
        traceback.print_exc()
        return {}

def update_stock_info(stock_industry_map):
    """
    更新 stock_info 表
    """
    print("\n" + "=" * 60)
    print("更新 stock_info 表")
    print("=" * 60)
    
    init_db()
    db = SessionLocal()
    
    today = date.today()
    updated_count = 0
    inserted_count = 0
    skipped_count = 0
    not_found_count = 0
    
    try:
        total = len(stock_industry_map)
        for idx, (stock_code, industry_info) in enumerate(stock_industry_map.items(), 1):
            if idx % 100 == 0:
                print(f"进度: {idx}/{total} ({idx/total*100:.1f}%)")
            
            # 查询最新记录
            latest_record = db.query(StockInfo).filter(
                StockInfo.stock_code == stock_code
            ).order_by(StockInfo.report_date.desc()).first()
            
            if latest_record:
                new_sw1 = industry_info.get('first')
                new_sw2 = industry_info.get('second')
                
                need_update = False
                if new_sw1 != latest_record.industry_sw1:
                    need_update = True
                if new_sw2 != latest_record.industry_sw2:
                    need_update = True
                
                if need_update:
                    # 检查今天是否已有记录
                    today_record = db.query(StockInfo).filter(
                        StockInfo.stock_code == stock_code,
                        StockInfo.report_date == today
                    ).first()
                    
                    if today_record:
                        today_record.industry_sw1 = new_sw1
                        today_record.industry_sw2 = new_sw2
                        updated_count += 1
                    else:
                        new_record = StockInfo(
                            stock_code=stock_code,
                            stock_name=industry_info.get('name', latest_record.stock_name),
                            industry_sw1=new_sw1,
                            industry_sw2=new_sw2,
                            is_st=latest_record.is_st,
                            is_star_st=latest_record.is_star_st,
                            is_delisted=latest_record.is_delisted,
                            listed_date=latest_record.listed_date,
                            delisted_date=latest_record.delisted_date,
                            component_tags=latest_record.component_tags,
                            report_date=today
                        )
                        db.add(new_record)
                        inserted_count += 1
                else:
                    skipped_count += 1
            else:
                not_found_count += 1
        
        db.commit()
        print("\n" + "=" * 60)
        print("更新完成!")
        print(f"  更新: {updated_count} 条")
        print(f"  插入: {inserted_count} 条")
        print(f"  跳过: {skipped_count} 条")
        print(f"  未找到: {not_found_count} 条")
        print("=" * 60)
    
    except Exception as e:
        db.rollback()
        print(f"更新失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def main():
    stock_industry_map = fetch_sw_industry_data()
    
    if stock_industry_map:
        update_stock_info(stock_industry_map)
    else:
        print("没有获取到数据")

if __name__ == "__main__":
    main()
