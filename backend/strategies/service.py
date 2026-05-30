from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.stock_data import DailyQuote, StockInfo
from strategies.registry import (
    BACKTEST_STRATEGIES,
    DEFAULT_STRATEGY_ID,
    PERIOD_OPTIONS,
    PERIOD_OPTION_LIST,
    build_strategy_meta,
    get_strategy_defaults,
)
from strategies.utils import build_price_data


class BacktestRunRequest(BaseModel):
    stock_code: str = "600036.SH"
    strategy_id: str = DEFAULT_STRATEGY_ID
    period: str = "1y"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    initial_capital: float = 100000.0
    strategy_params: Dict[str, Any] = Field(default_factory=dict)


def get_latest_stock_snapshot(stock_code: str, db: Session) -> Dict[str, Any]:
    info = db.query(StockInfo).filter(
        StockInfo.stock_code == stock_code
    ).order_by(StockInfo.report_date.desc()).first()
    latest_quote = db.query(DailyQuote).filter(
        DailyQuote.stock_code == stock_code
    ).order_by(DailyQuote.trade_date.desc()).first()
    return {
        "stock_code": stock_code,
        "stock_name": info.stock_name if info else stock_code,
        "latest_date": latest_quote.trade_date.isoformat() if latest_quote and latest_quote.trade_date else None,
    }


def load_backtest_quotes(request: BacktestRunRequest, db: Session) -> List[DailyQuote]:
    if request.period not in PERIOD_OPTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported period: {request.period}")

    query = db.query(DailyQuote).filter(DailyQuote.stock_code == request.stock_code)
    if request.end_date:
        query = query.filter(DailyQuote.trade_date <= request.end_date)
    quotes = query.order_by(DailyQuote.trade_date).all()

    if not quotes:
        return []

    actual_end_date = request.end_date or quotes[-1].trade_date
    actual_start_date = request.start_date
    if actual_start_date is None and PERIOD_OPTIONS[request.period] is not None:
        actual_start_date = actual_end_date - timedelta(days=PERIOD_OPTIONS[request.period])

    if actual_start_date is not None:
        quotes = [quote for quote in quotes if quote.trade_date >= actual_start_date]

    return quotes


def execute_backtest(request: BacktestRunRequest, db: Session) -> Dict[str, Any]:
    if request.strategy_id not in BACKTEST_STRATEGIES:
        raise HTTPException(status_code=404, detail=f"Unknown strategy: {request.strategy_id}")

    quotes = load_backtest_quotes(request, db)
    if not quotes:
        raise HTTPException(status_code=404, detail="No data found for the given stock code and period")

    price_data = build_price_data(quotes)
    strategy_defaults = get_strategy_defaults(request.strategy_id)
    merged_params = {**strategy_defaults, **request.strategy_params}
    strategy = BACKTEST_STRATEGIES[request.strategy_id]
    strategy_result = strategy["runner"](price_data, merged_params, request.initial_capital)

    stock_snapshot = get_latest_stock_snapshot(request.stock_code, db)
    return {
        "stock": stock_snapshot,
        "period": request.period,
        "start_date": quotes[0].trade_date.isoformat() if quotes and quotes[0].trade_date else None,
        "end_date": quotes[-1].trade_date.isoformat() if quotes and quotes[-1].trade_date else None,
        "strategy": {
            **build_strategy_meta(request.strategy_id),
            "params": merged_params,
        },
        "price_data": price_data,
        "trades": strategy_result["trades"],
        "equity_curve": strategy_result["equity_curve"],
        "metrics": strategy_result["metrics"],
    }


def get_strategy_catalog() -> Dict[str, Any]:
    return {
        "default_strategy_id": DEFAULT_STRATEGY_ID,
        "period_options": PERIOD_OPTION_LIST,
        "strategies": [build_strategy_meta(strategy_id) for strategy_id in BACKTEST_STRATEGIES.keys()],
    }
