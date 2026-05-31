from datetime import datetime, timedelta

from crawler.trading_calendar import is_trading_day, update_trading_calendar
from crawler import fetch_all_from_sina, fetch_constituents, fetch_sw_industry, fetch_hs300_index


def _fetch_hs300_index_recent(days: int = 14):
    end = datetime.today().strftime('%Y%m%d')
    start = (datetime.today() - timedelta(days=days)).strftime('%Y%m%d')

    try:
        df = fetch_hs300_index.fetch_hs300_index_range(start, end, chunk_days=180, retries=3)
    except Exception as ex:
        print(f'东方财富抓取失败，切换备用源: {type(ex).__name__}: {ex}')
        try:
            df = fetch_hs300_index.fetch_hs300_index_via_stock_hist(start, end)
            if df is None or df.empty:
                raise RuntimeError('stock_zh_a_hist returned empty')
        except Exception as ex2:
            print(f'个股历史接口抓取失败，切换备用源: {type(ex2).__name__}: {ex2}')
            df = fetch_hs300_index.fetch_hs300_index_fallback(start, end)

    fetch_hs300_index.init_db()
    db = fetch_hs300_index.SessionLocal()
    try:
        inserted, updated = fetch_hs300_index.save_to_db(db, df)
        print(f'沪深300指数抓取完成: inserted={inserted}, updated={updated}, rows={0 if df is None else len(df)}')
    finally:
        db.close()


def run_daily_job():
    now = datetime.now()
    print(f'[daily] start: {now.isoformat(timespec="seconds")}')

    update_trading_calendar()
    if not is_trading_day(now):
        print('[daily] skip: not a trading day')
        return

    fetch_all_from_sina.main()
    _fetch_hs300_index_recent(days=14)

    print(f'[daily] done: {datetime.now().isoformat(timespec="seconds")}')


def run_weekly_job():
    now = datetime.now()
    print(f'[weekly] start: {now.isoformat(timespec="seconds")}')

    update_trading_calendar()
    fetch_sw_industry.main()
    fetch_constituents.main()

    print(f'[weekly] done: {datetime.now().isoformat(timespec="seconds")}')

