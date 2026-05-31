import sys
import os
from datetime import datetime, timedelta
import time

import pandas as pd
import akshare as ak

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import SessionLocal, init_db
from models.stock_data import IndexDailyQuote


def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return datetime.strptime(value, '%Y-%m-%d').date()
    return value


def _index_symbol(index_code: str) -> str:
    code = str(index_code).strip()
    if code.startswith('399'):
        return f"sz{code}"
    return f"sh{code}"


def fetch_index_daily(index_code: str, start_date: str, end_date: str):
    symbol = _index_symbol(index_code)
    return ak.stock_zh_index_daily_em(symbol=symbol, start_date=start_date, end_date=end_date)


def fetch_index_via_stock_hist(index_code: str, start_date: str, end_date: str):
    df = ak.stock_zh_a_hist(
        symbol=_index_symbol(index_code),
        period='daily',
        start_date=start_date,
        end_date=end_date,
        adjust='',
    )
    if df is None or df.empty:
        return pd.DataFrame()

    col_map = {
        '日期': 'date',
        '开盘': 'open',
        '收盘': 'close',
        '最高': 'high',
        '最低': 'low',
        '成交量': 'volume',
        '成交额': 'amount',
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    if 'date' not in df.columns:
        return pd.DataFrame()

    keep_cols = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount']
    for col in keep_cols:
        if col not in df.columns:
            df[col] = None
    df = df[keep_cols].copy()
    df = df.sort_values('date')
    df['date'] = df['date'].astype(str)
    return df


def fetch_index_fallback(index_code: str, start_date: str, end_date: str):
    start_dt = datetime.strptime(start_date, '%Y%m%d').date()
    end_dt = datetime.strptime(end_date, '%Y%m%d').date()

    df = None
    last_error = None
    for fn in ['stock_zh_index_daily_tx', 'stock_zh_index_daily']:
        try:
            df = getattr(ak, fn)(symbol=_index_symbol(index_code))
            last_error = None
            break
        except Exception as ex:
            last_error = ex

    if df is None:
        raise last_error or RuntimeError('Failed to fetch index data')

    df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)].copy()
    if 'close' not in df.columns and '收盘' in df.columns:
        df = df.rename(columns={'收盘': 'close'})
    if 'open' not in df.columns and '开盘' in df.columns:
        df = df.rename(columns={'开盘': 'open'})
    if 'high' not in df.columns and '最高' in df.columns:
        df = df.rename(columns={'最高': 'high'})
    if 'low' not in df.columns and '最低' in df.columns:
        df = df.rename(columns={'最低': 'low'})

    if 'volume' not in df.columns and 'amount' in df.columns:
        df['volume'] = df['amount']
        df['amount'] = None
    elif 'amount' not in df.columns:
        df['amount'] = None

    df = df[['date', 'open', 'close', 'high', 'low', 'volume', 'amount']].copy()
    df = df.sort_values('date')
    df['date'] = df['date'].astype(str)
    return df


def fetch_index_range(index_code: str, start_date: str, end_date: str, chunk_days: int = 180, retries: int = 3):
    start_dt = datetime.strptime(start_date, '%Y%m%d')
    end_dt = datetime.strptime(end_date, '%Y%m%d')
    all_frames = []

    cursor = start_dt
    while cursor <= end_dt:
        chunk_end = min(cursor + timedelta(days=chunk_days), end_dt)
        s = cursor.strftime('%Y%m%d')
        e = chunk_end.strftime('%Y%m%d')

        last_error = None
        for i in range(retries):
            try:
                df = fetch_index_daily(index_code, s, e)
                if df is not None and not df.empty:
                    all_frames.append(df)
                last_error = None
                break
            except Exception as ex:
                last_error = ex
                time.sleep(1 + i)

        if last_error is not None:
            raise last_error

        cursor = chunk_end + timedelta(days=1)

    if not all_frames:
        return pd.DataFrame()

    merged = pd.concat(all_frames, ignore_index=True)
    merged = merged.drop_duplicates(subset=['date']).sort_values('date')
    return merged


def fetch_hs300_index_range(start_date: str, end_date: str, chunk_days: int = 180, retries: int = 3):
    return fetch_index_range('000300', start_date, end_date, chunk_days=chunk_days, retries=retries)


def save_to_db(db, df: pd.DataFrame, index_code: str = '000300'):
    if df is None or df.empty:
        return 0, 0

    inserted = 0
    updated = 0
    df = df.sort_values('date')
    prev_close = None
    index_code = str(index_code).strip()

    for _, row in df.iterrows():
        trade_date = _parse_date(row['date'])
        open_ = float(row['open']) if pd.notna(row['open']) else None
        close_ = float(row['close']) if pd.notna(row['close']) else None
        high_ = float(row['high']) if pd.notna(row['high']) else None
        low_ = float(row['low']) if pd.notna(row['low']) else None
        volume_ = int(row['volume']) if pd.notna(row['volume']) else 0
        amount_ = float(row['amount']) if pd.notna(row['amount']) else None

        change_pct = None
        if close_ is not None and prev_close is not None and prev_close != 0:
            change_pct = (close_ / prev_close - 1) * 100
        if close_ is not None:
            prev_close = close_

        existing = db.query(IndexDailyQuote).filter(
            IndexDailyQuote.index_code == index_code,
            IndexDailyQuote.trade_date == trade_date
        ).first()

        if existing:
            existing.open = open_
            existing.close = close_
            existing.high = high_
            existing.low = low_
            existing.volume = volume_
            existing.amount = amount_
            existing.change_pct = change_pct
            updated += 1
        else:
            item = IndexDailyQuote(
                index_code=index_code,
                trade_date=trade_date,
                open=open_,
                close=close_,
                high=high_,
                low=low_,
                volume=volume_,
                amount=amount_,
                change_pct=change_pct,
            )
            db.add(item)
            inserted += 1

    db.commit()
    return inserted, updated


def main():
    end = datetime.today().strftime('%Y%m%d')
    start = (datetime.today() - timedelta(days=365 * 5)).strftime('%Y%m%d')
    index_codes = ['000300', '000905'] # 沪深300指数和中证500指数

    if len(sys.argv) >= 2:
        start = sys.argv[1]
    if len(sys.argv) >= 3:
        end = sys.argv[2]
    if len(sys.argv) >= 4:
        index_codes = [item.strip() for item in sys.argv[3].split(',') if item.strip()]

    init_db()
    db = SessionLocal()
    try:
        for index_code in index_codes:
            try:
                df = fetch_index_range(index_code, start, end, chunk_days=180, retries=3)
            except Exception as ex:
                print(f'东方财富抓取失败({index_code})，切换备用源: {type(ex).__name__}: {ex}')
                try:
                    df = fetch_index_via_stock_hist(index_code, start, end)
                    if df is None or df.empty:
                        raise RuntimeError('stock_zh_a_hist returned empty')
                except Exception as ex2:
                    print(f'个股历史接口抓取失败({index_code})，切换备用源: {type(ex2).__name__}: {ex2}')
                    df = fetch_index_fallback(index_code, start, end)
            inserted, updated = save_to_db(db, df, index_code=index_code)
            print(f'指数抓取完成({index_code}): inserted={inserted}, updated={updated}, rows={0 if df is None else len(df)}')
    finally:
        db.close()


if __name__ == '__main__':
    main()
