#!/usr/bin/env python3
"""
交易日历管理
"""
import sys
import os
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak


def get_data_dir():
    """获取数据存储目录"""
    crawler_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(crawler_dir, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir


def get_calendar_file_path():
    """获取日历文件路径"""
    data_dir = get_data_dir()
    return os.path.join(data_dir, 'trading_calendar.json')


def load_calendar_from_file():
    """从文件加载交易日历"""
    file_path = get_calendar_file_path()
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            dates = data.get('dates', [])
            # 规范化日期格式，去掉横杠
            dates = [d.replace('-', '') for d in dates]
            dates.sort()
            return dates
    except Exception as e:
        print(f"加载日历文件失败: {e}")
        return None


def save_calendar_to_file(dates):
    """保存交易日历到文件"""
    file_path = get_calendar_file_path()
    try:
        data = {
            'dates': dates,
            'updated_at': datetime.now().isoformat()
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"交易日历已保存到: {file_path}")
        return True
    except Exception as e:
        print(f"保存日历文件失败: {e}")
        return False


def fetch_trading_calendar():
    """从新浪接口获取交易日历"""
    print("正在从新浪获取交易日历...")
    try:
        df = ak.tool_trade_date_hist_sina()
        # 接口返回的格式是 YYYY-MM-DD，统一转换成 YYYYMMDD
        dates = df['trade_date'].astype(str).str.replace('-', '').tolist()
        dates.sort()
        print(f"获取到 {len(dates)} 个交易日")
        return dates
    except Exception as e:
        print(f"获取交易日历失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def update_trading_calendar():
    """更新交易日历（如果需要）"""
    today_str = datetime.now().strftime('%Y%m%d')
    
    # 先尝试加载
    dates = load_calendar_from_file()
    
    if dates:
        max_date = dates[-1]
        # 确保日期格式一致，去掉可能存在的横杠
        max_date_normalized = max_date.replace('-', '')
        if today_str <= max_date_normalized:
            print(f"日历数据已足够，最新交易日: {max_date}")
            return dates
        else:
            print(f"当前日期 {today_str} > 最新交易日 {max_date}，需要更新")
    
    # 获取新数据
    dates = fetch_trading_calendar()
    if dates:
        save_calendar_to_file(dates)
    return dates


def is_trading_day(check_date=None):
    """
    判断指定日期是否是交易日
    
    Args:
        check_date: 要检查的日期 (datetime对象或日期字符串)，默认今天
    
    Returns:
        bool
    """
    if check_date is None:
        check_date = datetime.now()
    
    if isinstance(check_date, str):
        check_date = datetime.strptime(check_date, '%Y%m%d')
    
    check_str = check_date.strftime('%Y%m%d')
    
    dates = load_calendar_from_file()
    if not dates:
        # 没有文件，先更新
        dates = update_trading_calendar()
        if not dates:
            print("无法获取交易日历，按周末/工作日粗略判断")
            return check_date.weekday() < 5  # 0-4 是周一到周五
    
    return check_str in dates


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("交易日历管理")
    print("=" * 60)
    
    dates = update_trading_calendar()
    
    if dates:
        today = datetime.now()
        today_str = today.strftime('%Y%m%d')
        is_today = is_trading_day()
        
        print(f"\n今天是: {today_str} ({['周一', '周二', '周三', '周四', '周五', '周六', '周日'][today.weekday()]})")
        print(f"今天是交易日: {is_today}")
        
        print(f"\n交易日范围: {dates[0]} ~ {dates[-1]}")
