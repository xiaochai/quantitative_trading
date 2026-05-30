from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database.database import get_db
from models.stock_data import DailyQuote, StockInfo, StockFundamental
from strategies import BacktestRunRequest, execute_backtest, get_strategy_catalog
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
    from sqlalchemy import func, or_
    
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


@app.get("/api/backtest/strategies")
def get_backtest_strategies():
    return get_strategy_catalog()


@app.post("/api/backtest/run")
def run_backtest(request: BacktestRunRequest, db: Session = Depends(get_db)):
    return execute_backtest(request, db)


@app.get("/api/backtest/bollinger")
def get_bollinger_backtest(stock_code: str = "600036.SH", db: Session = Depends(get_db)):
    # 兼容旧页面入口，内部走新的通用回测框架
    request = BacktestRunRequest(stock_code=stock_code, strategy_id="short_trend", period="1y")
    return execute_backtest(request, db)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
