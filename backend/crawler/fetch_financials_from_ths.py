#!/usr/bin/env python3
"""
从同花顺获取财务基本信息
使用 stock_financial_abstract_ths 接口
"""
import sys
import os
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import SessionLocal, init_db
from models.stock_data import StockFundamental
import akshare as ak


def get_data_dir():
    """获取数据存储目录"""
    crawler_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(crawler_dir, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir


def get_financial_file_path(stock_code):
    """获取财务数据文件路径"""
    data_dir = get_data_dir()
    today_str = datetime.now().strftime('%Y%m%d')
    return os.path.join(data_dir, f'financial_{stock_code}_{today_str}.json')


def load_financial_from_file(stock_code):
    """从文件加载财务数据"""
    file_path = get_financial_file_path(stock_code)
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"加载财务数据文件失败: {e}")
        return None


def save_financial_to_file(stock_code, data):
    """保存财务数据到文件"""
    file_path = get_financial_file_path(stock_code)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"财务数据已保存到: {file_path}")
        return True
    except Exception as e:
        print(f"保存财务数据文件失败: {e}")
        return False


def fetch_financial_data(stock_code):
    """从同花顺获取财务数据"""
    print(f"正在获取 {stock_code} 的财务数据...")
    try:
        # 去掉后缀 .SH / .SZ
        code = stock_code.split('.')[0]
        df = ak.stock_financial_abstract_ths(symbol=code)
        print(f"获取到 {len(df)} 条财务数据")
        # 转换为字典列表
        return df.to_dict('records')
    except Exception as e:
        print(f"获取财务数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_financial_to_db(db, stock_code, financial_data):
    """保存财务数据到数据库"""
    if not financial_data:
        return False
    
    saved_count = 0
    
    for data in financial_data:
        try:
            # 尝试解析报告日期
            report_date_str = data.get('报告期', '')
            if not report_date_str:
                continue
                
            # 转换日期格式 (2022年报 → 2022-12-31)
            report_date = parse_report_date(report_date_str)
            if not report_date:
                continue
            
            # 检查是否已存在
            existing = db.query(StockFundamental).filter(
                StockFundamental.stock_code == stock_code,
                StockFundamental.report_date == report_date
            ).first()
            
            if existing:
                continue
            
            # 构建新记录
            pb = None  # 该接口没有市净率
            roe = parse_percent(data.get('净资产收益率'))
            eps = parse_financial_float(data.get('基本每股收益'))
            eps_ttm = None  # 该接口没有
            net_profit_growth = parse_percent(data.get('净利润同比增长率'))
            revenue_growth = parse_percent(data.get('营业总收入同比增长率'))
            dividend_yield = None  # 该接口没有
            
            record = StockFundamental(
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
            
            db.add(record)
            saved_count += 1
            
        except Exception as e:
            print(f"处理财务数据记录失败: {e}")
            continue
    
    if saved_count > 0:
        db.commit()
        print(f"保存了 {saved_count} 条财务数据")
        return True
    return False


def parse_report_date(date_str):
    """解析报告日期"""
    date_str = date_str.strip()
    try:
        if '年报' in date_str:
            year = date_str[:4]
            return datetime.strptime(f"{year}-12-31", "%Y-%m-%d").date()
        elif '中报' in date_str:
            year = date_str[:4]
            return datetime.strptime(f"{year}-06-30", "%Y-%m-%d").date()
        elif '三季' in date_str:
            year = date_str[:4]
            return datetime.strptime(f"{year}-09-30", "%Y-%m-%d").date()
        elif '一季' in date_str:
            year = date_str[:4]
            return datetime.strptime(f"{year}-03-31", "%Y-%m-%d").date()
        else:
            # 尝试直接解析
            return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return None


def parse_float(value):
    """解析浮点数"""
    if value is None or value == '' or value is False:
        return None
    try:
        return float(value)
    except:
        return None


def parse_percent(value):
    """解析百分比数据（去掉%符号）"""
    if value is None or value == '' or value is False:
        return None
    try:
        s = str(value)
        if '%' in s:
            s = s.replace('%', '')
        return float(s)
    except:
        return None


def parse_financial_float(value):
    """解析财务浮点数（处理亿、万、false等情况）"""
    if value is None or value == '' or value is False:
        return None
    try:
        s = str(value)
        if '亿' in s:
            # 暂时不处理单位，直接提取数字
            s = s.replace('亿', '')
        if '万' in s:
            s = s.replace('万', '')
        return float(s)
    except:
        return None


def fetch_and_save_financial(stock_code):
    """获取并保存财务数据"""
    init_db()
    db = SessionLocal()
    
    try:
        # 1. 先尝试从文件加载
        financial_data = load_financial_from_file(stock_code)
        
        if financial_data:
            print(f"从文件加载到财务数据: {stock_code}")
        else:
            # 2. 文件不存在，从接口获取
            financial_data = fetch_financial_data(stock_code)
            if financial_data:
                save_financial_to_file(stock_code, financial_data)
        
        # 3. 保存到数据库
        if financial_data:
            save_financial_to_db(db, stock_code, financial_data)
        
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("从同花顺获取财务数据")
    print("=" * 60)
    
    # 默认抓取招商银行
    default_code = "600036.SH"
    
    if len(sys.argv) > 1:
        stock_code = sys.argv[1]
    else:
        stock_code = default_code
    
    print(f"股票代码: {stock_code}")
    fetch_and_save_financial(stock_code)
