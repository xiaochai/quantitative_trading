from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database.database import get_db
from models.stock_data import DailyQuote, StockInfo, StockFundamental
from datetime import date
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/stock/{stock_code}/quotes")
def get_stock_quotes(stock_code: str, db: Session = Depends(get_db)):
    quotes = db.query(DailyQuote).filter(
        DailyQuote.stock_code == stock_code
    ).order_by(DailyQuote.trade_date).all()
    
    result = []
    for q in quotes:
        result.append({
            "trade_date": q.trade_date.isoformat(),
            "open": q.open,
            "close": q.close,
            "high": q.high,
            "low": q.low,
            "volume": q.volume,
            "amount": q.amount,
            "change_pct": q.change_pct,
            "change_20d_pct": q.change_20d_pct,
            "turnover_rate": q.turnover_rate,
            "market_cap": q.market_cap,
            "pe_ttm": q.pe_ttm,
            "ma5": q.ma5,
            "ma20": q.ma20,
            "ma60": q.ma60,
            "macd": q.macd,
            "macd_signal": q.macd_signal,
            "macd_hist": q.macd_hist,
            "rsi": q.rsi,
            "boll_upper": q.boll_upper,
            "boll_middle": q.boll_middle,
            "boll_lower": q.boll_lower
        })
    return result

@app.get("/api/stock/{stock_code}/fundamentals")
def get_stock_fundamentals(stock_code: str, db: Session = Depends(get_db)):
    fundamentals = db.query(StockFundamental).filter(
        StockFundamental.stock_code == stock_code
    ).order_by(StockFundamental.report_date.desc()).all()
    
    result = []
    for f in fundamentals:
        result.append({
            "report_date": f.report_date.isoformat(),
            "pb": f.pb,
            "roe": f.roe,
            "eps": f.eps,
            "eps_ttm": f.eps_ttm,
            "net_profit_growth": f.net_profit_growth,
            "revenue_growth": f.revenue_growth,
            "dividend_yield": f.dividend_yield
        })
    return result

@app.get("/api/stock/{stock_code}/info")
def get_stock_info(stock_code: str, db: Session = Depends(get_db)):
    # 获取最新的记录，按 report_date 倒序
    info = db.query(StockInfo).filter(
        StockInfo.stock_code == stock_code
    ).order_by(StockInfo.report_date.desc()).first()
    
    if info:
        return {
            "stock_code": info.stock_code,
            "stock_name": info.stock_name,
            "industry_sw1": info.industry_sw1,
            "industry_sw2": info.industry_sw2,
            "is_st": info.is_st,
            "is_star_st": info.is_star_st,
            "is_delisted": info.is_delisted,
            "listed_date": info.listed_date.isoformat() if info.listed_date else None,
            "component_tags": json.loads(info.component_tags) if info.component_tags else []
        }
    return None

@app.get("/api/stocks")
def get_all_stocks(
    index: str = None,
    search: str = None,
    db: Session = Depends(get_db)
):
    """
    获取股票列表
    
    Args:
        index: 指数名称，如 '沪深300'，不传则返回所有股票
        search: 搜索关键词，支持股票代码或名称模糊搜索
    """
    from sqlalchemy import distinct, func, or_
    
    # 先获取所有股票的最新信息（以 stock_info 表为准）
    # 获取每个股票最新的 report_date
    subquery_info = db.query(
        StockInfo.stock_code,
        func.max(StockInfo.report_date).label('latest_report_date')
    ).group_by(StockInfo.stock_code).subquery()
    
    # 获取每个股票最新的 stock_info
    query = db.query(StockInfo).join(
        subquery_info,
        (StockInfo.stock_code == subquery_info.c.stock_code) &
        (StockInfo.report_date == subquery_info.c.latest_report_date)
    )
    
    # 如果指定了指数，筛选成分股
    if index:
        # component_tags 是 JSON 格式的数组，需要解析
        # 这里我们使用 like 查询来匹配
        query = query.filter(StockInfo.component_tags.like(f'%"{index}"%'))
    
    # 如果有搜索关键词，模糊匹配股票代码或名称
    if search:
        search = search.strip()
        query = query.filter(
            or_(
                StockInfo.stock_code.like(f'%{search}%'),
                StockInfo.stock_name.like(f'%{search}%')
            )
        )
    
    stock_info_list = query.all()
    
    result = []
    for stock_info in stock_info_list:
        # 获取该股票的最新行情数据
        latest_quote = db.query(DailyQuote).filter(
            DailyQuote.stock_code == stock_info.stock_code
        ).order_by(DailyQuote.trade_date.desc()).first()
        
        result.append({
            "stock_code": stock_info.stock_code,
            "stock_name": stock_info.stock_name,
            "industry_sw1": stock_info.industry_sw1,
            "industry_sw2": stock_info.industry_sw2,
            "is_st": stock_info.is_st,
            "is_star_st": stock_info.is_star_st,
            "component_tags": json.loads(stock_info.component_tags) if stock_info.component_tags else [],
            "latest_close": latest_quote.close if latest_quote else None,
            "change_pct": latest_quote.change_pct if latest_quote else None,
            "latest_date": latest_quote.trade_date.isoformat() if latest_quote and latest_quote.trade_date else None
        })
    
    return result

@app.get("/api/stocks/summary")
def get_stocks_summary(db: Session = Depends(get_db)):
    # 获取股票总数（以 stock_info 表为准）
    from sqlalchemy import distinct, func
    
    # 获取股票总数（每个股票只算一次，取最新的）
    stock_count = db.query(func.count(distinct(StockInfo.stock_code))).scalar()
    
    # 获取最新数据日期
    latest_date = db.query(func.max(DailyQuote.trade_date)).scalar()
    
    return {
        "total_stocks": stock_count or 0,
        "latest_date": latest_date.isoformat() if latest_date else None
    }


@app.get("/api/data/daily_quotes")
def get_daily_quotes(page: int = 1, page_size: int = 1000, stock_code: str = None, db: Session = Depends(get_db)):
    """获取日线行情数据，按id逆序排列，分页，支持按股票代码筛选"""
    from sqlalchemy import func
    
    query = db.query(DailyQuote)
    if stock_code:
        query = query.filter(DailyQuote.stock_code == stock_code)
    
    offset = (page - 1) * page_size
    total = query.with_entities(func.count(DailyQuote.id)).scalar()
    items = query.order_by(DailyQuote.id.desc()).offset(offset).limit(page_size).all()
    
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "stock_code": item.stock_code,
            "trade_date": item.trade_date.isoformat() if item.trade_date else None,
            "open": item.open,
            "close": item.close,
            "high": item.high,
            "low": item.low,
            "volume": item.volume,
            "amount": item.amount,
            "change_pct": item.change_pct,
            "change_20d_pct": item.change_20d_pct,
            "turnover_rate": item.turnover_rate,
            "market_cap": item.market_cap,
            "pe_ttm": item.pe_ttm,
            "ma5": item.ma5,
            "ma20": item.ma20,
            "ma60": item.ma60,
            "macd": item.macd,
            "macd_signal": item.macd_signal,
            "macd_hist": item.macd_hist,
            "rsi": item.rsi,
            "boll_upper": item.boll_upper,
            "boll_middle": item.boll_middle,
            "boll_lower": item.boll_lower
        })
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": result
    }


@app.get("/api/data/stock_fundamentals")
def get_stock_fundamentals(page: int = 1, page_size: int = 1000, stock_code: str = None, db: Session = Depends(get_db)):
    """获取股票基本面数据，按id逆序排列，分页，支持按股票代码筛选"""
    from sqlalchemy import func
    
    query = db.query(StockFundamental)
    if stock_code:
        query = query.filter(StockFundamental.stock_code == stock_code)
    
    offset = (page - 1) * page_size
    total = query.with_entities(func.count(StockFundamental.id)).scalar()
    items = query.order_by(StockFundamental.id.desc()).offset(offset).limit(page_size).all()
    
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "stock_code": item.stock_code,
            "report_date": item.report_date.isoformat() if item.report_date else None,
            "pb": item.pb,
            "roe": item.roe,
            "eps": item.eps,
            "eps_ttm": item.eps_ttm,
            "net_profit_growth": item.net_profit_growth,
            "revenue_growth": item.revenue_growth,
            "dividend_yield": item.dividend_yield
        })
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": result
    }


@app.get("/api/data/stock_info")
def get_stock_info(page: int = 1, page_size: int = 1000, stock_code: str = None, db: Session = Depends(get_db)):
    """获取股票信息数据，按id逆序排列，分页，支持按股票代码筛选"""
    from sqlalchemy import func
    
    query = db.query(StockInfo)
    if stock_code:
        query = query.filter(StockInfo.stock_code == stock_code)
    
    offset = (page - 1) * page_size
    total = query.with_entities(func.count(StockInfo.id)).scalar()
    items = query.order_by(StockInfo.id.desc()).offset(offset).limit(page_size).all()
    
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "stock_code": item.stock_code,
            "stock_name": item.stock_name,
            "industry_sw1": item.industry_sw1,
            "industry_sw2": item.industry_sw2,
            "is_st": item.is_st,
            "is_star_st": item.is_star_st,
            "is_delisted": item.is_delisted,
            "delisted_date": item.delisted_date.isoformat() if item.delisted_date else None,
            "listed_date": item.listed_date.isoformat() if item.listed_date else None,
            "component_tags": item.component_tags,
            "report_date": item.report_date.isoformat() if item.report_date else None
        })
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": result
    }

@app.get("/api/backtest/bollinger")
def get_bollinger_backtest(
    stock_code: str = "600036.SH",
    period: int = 20,  # 布林带周期
    std_dev: float = 2.0,  # 标准差倍数
    db: Session = Depends(get_db)
):
    """
    招商银行增强布林带回测

    策略逻辑：
    - 触及下轨分批建仓
    - 回到中轨先减仓
    - 触及上轨止盈
    - 跌破成本止损
    """
    from datetime import date, timedelta

    initial_capital = 100000.0
    first_entry_ratio = 0.25
    second_entry_ratio = 0.20
    third_entry_ratio = 0.35
    trend_tolerance = 0.98
    stop_loss_pct = 0.05
    partial_take_profit_pct = 0.01
    third_entry_discount = 0.01

    def to_lot_shares(budget: float, price: float) -> int:
        if not price or price <= 0:
            return 0
        raw_shares = int(budget / price)
        return raw_shares - raw_shares % 100

    def record_trade(
        trades: list,
        trade_date: str,
        trade_type: str,
        price: float,
        shares: int,
        reason: str,
        profit: float = None,
    ):
        item = {
            "date": trade_date,
            "type": trade_type,
            "price": price,
            "shares": shares,
            "reason": reason,
        }
        if profit is not None:
            item["profit"] = profit
        trades.append(item)

    one_year_ago = date.today() - timedelta(days=365)

    quotes = db.query(DailyQuote).filter(
        DailyQuote.stock_code == stock_code,
        DailyQuote.trade_date >= one_year_ago
    ).order_by(DailyQuote.trade_date).all()

    if not quotes:
        return {"error": "No data found for the given stock code"}

    bollinger_data = []
    for i, quote in enumerate(quotes):
        if i < period - 1:
            continue

        window_quotes = quotes[i-period+1:i+1]
        close_prices = [q.close for q in window_quotes if q.close is not None]

        if len(close_prices) < period:
            continue

        sma = sum(close_prices) / period
        variance = sum((p - sma) ** 2 for p in close_prices) / period
        std = variance ** 0.5
        upper = sma + std_dev * std
        lower = sma - std_dev * std

        bollinger_data.append({
            "date": quote.trade_date.isoformat(),
            "open": quote.open,
            "high": quote.high,
            "low": quote.low,
            "close": quote.close,
            "volume": quote.volume,
            "sma": sma,
            "upper": upper,
            "lower": lower,
            "ma60": quote.ma60,
        })

    trades = []
    equity_curve = []
    cash = initial_capital
    shares = 0
    avg_cost = 0.0
    position_layers = 0
    peak_equity = initial_capital
    max_drawdown = 0.0

    for data in bollinger_data:
        close = data["close"]
        if close is None:
            continue

        mid = data["sma"]
        upper = data["upper"]
        lower = data["lower"]
        ma60 = data["ma60"]
        trend_ok = ma60 is None or close >= ma60 * trend_tolerance

        if shares > 0 and close <= avg_cost * (1 - stop_loss_pct):
            sell_shares = shares
            cash += sell_shares * close
            profit = (close - avg_cost) * sell_shares
            record_trade(trades, data["date"], "SELL", close, sell_shares, "跌破持仓成本 5% 止损", profit)
            shares = 0
            avg_cost = 0.0
            position_layers = 0

        elif shares > 0 and close >= upper:
            sell_shares = shares
            cash += sell_shares * close
            profit = (close - avg_cost) * sell_shares
            record_trade(trades, data["date"], "SELL", close, sell_shares, "触及布林带上轨全部止盈", profit)
            shares = 0
            avg_cost = 0.0
            position_layers = 0

        elif shares > 0 and close >= mid and close >= avg_cost * (1 + partial_take_profit_pct):
            sell_shares = int(shares * 0.5)
            sell_shares -= sell_shares % 100
            if sell_shares <= 0 and shares >= 100:
                sell_shares = min(100, shares)

            if sell_shares > 0:
                cash += sell_shares * close
                profit = (close - avg_cost) * sell_shares
                record_trade(trades, data["date"], "SELL", close, sell_shares, "回到中轨先减仓一半", profit)
                shares -= sell_shares
                if shares == 0:
                    avg_cost = 0.0
                    position_layers = 0

        buy_reason = None
        entry_ratio = 0.0
        if shares == 0 and close <= lower and trend_ok:
            buy_reason = "触及下轨首笔建仓 25%"
            entry_ratio = first_entry_ratio
        elif shares > 0 and position_layers == 1 and close <= lower:
            buy_reason = "再次回踩下轨加仓 20%"
            entry_ratio = second_entry_ratio
        elif shares > 0 and position_layers == 2 and close <= lower * (1 - third_entry_discount):
            buy_reason = "较下轨再低 1% 时加仓 35%"
            entry_ratio = third_entry_ratio

        if buy_reason:
            buy_shares = to_lot_shares(cash * entry_ratio, close)
            if buy_shares >= 100:
                cost = buy_shares * close
                total_cost = avg_cost * shares + cost
                shares += buy_shares
                cash -= cost
                avg_cost = total_cost / shares
                position_layers += 1
                record_trade(trades, data["date"], "BUY", close, buy_shares, buy_reason)

        current_equity = cash + shares * close
        equity_curve.append({
            "date": data["date"],
            "equity": current_equity
        })
        peak_equity = max(peak_equity, current_equity)
        drawdown = (peak_equity - current_equity) / peak_equity if peak_equity > 0 else 0
        max_drawdown = max(max_drawdown, drawdown)

    if shares > 0 and bollinger_data:
        last_close = bollinger_data[-1]["close"]
        if last_close:
            sell_shares = shares
            cash += sell_shares * last_close
            profit = (last_close - avg_cost) * sell_shares
            record_trade(
                trades,
                bollinger_data[-1]["date"],
                "SELL",
                last_close,
                sell_shares,
                "样本结束平仓",
                profit,
            )
            shares = 0

    final_capital = cash
    final_return_pct = ((final_capital - initial_capital) / initial_capital) * 100
    win_trades = [t for t in trades if t["type"] == "SELL" and t["profit"] > 0]
    sell_trades = [t for t in trades if t["type"] == "SELL"]
    win_rate = (len(win_trades) / len(sell_trades) * 100) if sell_trades else 0

    return {
        "stock_code": stock_code,
        "strategy": {
            "name": "招商银行增强布林带分批策略",
            "rules": [
                "触及下轨且价格不低于 MA60 的 98% 时，首笔建仓 25%",
                "再次回踩下轨时加仓 20%",
                "较下轨再低 1% 时加仓 35%",
                "回到中轨且浮盈超过 1% 时，减仓一半",
                "触及上轨全部止盈，跌破持仓成本 5% 时止损",
            ],
            "params": {
                "period": period,
                "std_dev": std_dev,
                "first_entry_ratio": first_entry_ratio,
                "second_entry_ratio": second_entry_ratio,
                "third_entry_ratio": third_entry_ratio,
                "stop_loss_pct": stop_loss_pct,
                "partial_take_profit_pct": partial_take_profit_pct,
                "trend_tolerance": trend_tolerance,
            }
        },
        "bollinger_data": bollinger_data,
        "trades": trades,
        "equity_curve": equity_curve,
        "metrics": {
            "initial_capital": initial_capital,
            "final_capital": final_capital,
            "total_return": final_capital - initial_capital,
            "return_pct": final_return_pct,
            "max_drawdown_pct": max_drawdown * 100,
            "win_rate": win_rate,
            "total_trades": len(sell_trades),
            "buy_count": len([t for t in trades if t["type"] == "BUY"]),
            "sell_count": len(sell_trades),
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
