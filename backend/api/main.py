from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database.database import get_db
from models.stock_data import DailyQuote, StockInfo, StockFundamental
from datetime import date

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
            "listed_date": info.listed_date.isoformat() if info.listed_date else None
        }
    return None

@app.get("/api/stocks")
def get_all_stocks(db: Session = Depends(get_db)):
    # 从 daily_quotes 表获取所有有数据的股票
    from sqlalchemy import distinct, func, or_
    
    # 获取每个股票的最新数据日期
    subquery = db.query(
        DailyQuote.stock_code,
        func.max(DailyQuote.trade_date).label('latest_date')
    ).group_by(DailyQuote.stock_code).subquery()
    
    # 关联查询获取最新数据
    # 使用 distinct 去重，或者先获取去重的 stock_code
    stock_codes = db.query(distinct(DailyQuote.stock_code)).all()
    result = []
    
    for (code,) in stock_codes:
        # 获取每个股票的最新数据
        latest_quote = db.query(DailyQuote).filter(
            DailyQuote.stock_code == code
        ).order_by(DailyQuote.trade_date.desc()).first()
        
        # 获取股票信息（按 report_date 倒序取最新）
        stock_info = db.query(StockInfo).filter(
            StockInfo.stock_code == code
        ).order_by(StockInfo.report_date.desc()).first()
        
        if latest_quote:
            result.append({
                "stock_code": latest_quote.stock_code,
                "stock_name": stock_info.stock_name if stock_info else latest_quote.stock_code,
                "latest_close": latest_quote.close,
                "change_pct": latest_quote.change_pct,
                "latest_date": latest_quote.trade_date.isoformat() if latest_quote.trade_date else None
            })
    
    return result

@app.get("/api/stocks/summary")
def get_stocks_summary(db: Session = Depends(get_db)):
    # 获取股票总数和最近数据日期
    from sqlalchemy import distinct, func
    
    stock_count = db.query(func.count(distinct(DailyQuote.stock_code))).scalar()
    latest_date = db.query(func.max(DailyQuote.trade_date)).scalar()
    
    return {
        "total_stocks": stock_count or 0,
        "latest_date": latest_date.isoformat() if latest_date else None
    }


@app.get("/api/data/daily_quotes")
def get_daily_quotes(page: int = 1, page_size: int = 1000, db: Session = Depends(get_db)):
    """获取日线行情数据，按id逆序排列，分页"""
    from sqlalchemy import func
    
    offset = (page - 1) * page_size
    total = db.query(func.count(DailyQuote.id)).scalar()
    items = db.query(DailyQuote).order_by(DailyQuote.id.desc()).offset(offset).limit(page_size).all()
    
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
def get_stock_fundamentals(page: int = 1, page_size: int = 1000, db: Session = Depends(get_db)):
    """获取股票基本面数据，按id逆序排列，分页"""
    from sqlalchemy import func
    
    offset = (page - 1) * page_size
    total = db.query(func.count(StockFundamental.id)).scalar()
    items = db.query(StockFundamental).order_by(StockFundamental.id.desc()).offset(offset).limit(page_size).all()
    
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
def get_stock_info(page: int = 1, page_size: int = 1000, db: Session = Depends(get_db)):
    """获取股票信息数据，按id逆序排列，分页"""
    from sqlalchemy import func
    
    offset = (page - 1) * page_size
    total = db.query(func.count(StockInfo.id)).scalar()
    items = db.query(StockInfo).order_by(StockInfo.id.desc()).offset(offset).limit(page_size).all()
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)