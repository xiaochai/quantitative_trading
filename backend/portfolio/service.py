from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.stock_data import DailyQuote, StockInfo
from portfolio.registry import (
    DEFAULT_STRATEGY_ID,
    DEFAULT_UNIVERSE_ID,
    PERIOD_OPTIONS,
    PERIOD_OPTION_LIST,
    PORTFOLIO_STRATEGIES,
    UNIVERSE_OPTIONS,
    build_strategy_meta,
    get_strategy_defaults,
)
from portfolio.utils import next_business_day


class HoldingInput(BaseModel):
    stock_code: str
    shares: int
    cost_price: float = 0.0


class PortfolioBacktestRequest(BaseModel):
    universe_id: str = DEFAULT_UNIVERSE_ID
    strategy_id: str = DEFAULT_STRATEGY_ID
    period: str = '2y'
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    initial_capital: float = 100000.0
    max_positions: int = 3
    cash_reserve_ratio: float = 0.1
    strategy_params: Dict[str, Any] = Field(default_factory=dict)


class PortfolioPlanRequest(BaseModel):
    universe_id: str = DEFAULT_UNIVERSE_ID
    strategy_id: str = DEFAULT_STRATEGY_ID
    max_positions: int = 3
    cash_reserve_ratio: float = 0.1
    current_cash: float = 0.0
    holdings: List[HoldingInput] = Field(default_factory=list)
    strategy_params: Dict[str, Any] = Field(default_factory=dict)


def _latest_stock_info_query(db: Session):
    from sqlalchemy import func

    subquery = db.query(
        StockInfo.stock_code,
        func.max(StockInfo.report_date).label('latest_report_date')
    ).group_by(StockInfo.stock_code).subquery()

    return db.query(StockInfo).join(
        subquery,
        (StockInfo.stock_code == subquery.c.stock_code) &
        (StockInfo.report_date == subquery.c.latest_report_date)
    )


def get_universe_members(universe_id: str, db: Session) -> Dict[str, Dict[str, Any]]:
    if universe_id != 'hs300':
        raise HTTPException(status_code=400, detail=f'Unsupported universe: {universe_id}')

    rows = _latest_stock_info_query(db).filter(StockInfo.component_tags.like('%"沪深300"%')).all()
    members = {}
    for row in rows:
        members[row.stock_code] = {
            'stock_code': row.stock_code,
            'stock_name': row.stock_name,
            'is_st': bool(row.is_st),
            'is_delisted': bool(row.is_delisted),
            'listed_date': row.listed_date,
        }
    return members


def load_universe_quotes(request: PortfolioBacktestRequest, universe_members: Dict[str, Dict[str, Any]], db: Session):
    if request.period not in PERIOD_OPTIONS:
        raise HTTPException(status_code=400, detail=f'Unsupported period: {request.period}')

    codes = list(universe_members.keys())
    if not codes:
        raise HTTPException(status_code=404, detail='Universe has no members')

    query = db.query(DailyQuote).filter(DailyQuote.stock_code.in_(codes))
    if request.end_date:
        query = query.filter(DailyQuote.trade_date <= request.end_date)
    quotes = query.order_by(DailyQuote.trade_date, DailyQuote.stock_code).all()
    if not quotes:
        raise HTTPException(status_code=404, detail='No quote data found for the requested universe')

    actual_end_date = request.end_date or quotes[-1].trade_date
    actual_start_date = request.start_date
    if actual_start_date is None:
        actual_start_date = actual_end_date - timedelta(days=PERIOD_OPTIONS[request.period])

    filtered = [item for item in quotes if item.trade_date >= actual_start_date]
    return filtered


def build_market_context(quotes: List[DailyQuote], universe_members: Dict[str, Dict[str, Any]], max_positions: int, cash_reserve_ratio: float, initial_capital: float = 0.0) -> Dict[str, Any]:
    quotes_by_date: Dict[str, Dict[str, Dict[str, Any]]] = {}
    dates = []
    seen_dates = set()

    for quote in quotes:
        trade_date = quote.trade_date.isoformat()
        if trade_date not in seen_dates:
            dates.append(trade_date)
            seen_dates.add(trade_date)
        listed_days = None
        meta = universe_members.get(quote.stock_code)
        if meta and meta.get('listed_date'):
            listed_days = (quote.trade_date - meta['listed_date']).days
        quotes_by_date.setdefault(trade_date, {})[quote.stock_code] = {
            'stock_code': quote.stock_code,
            'date': trade_date,
            'open': quote.open,
            'close': quote.close,
            'high': quote.high,
            'low': quote.low,
            'volume': quote.volume,
            'amount': quote.amount,
            'change_pct': quote.change_pct,
            'change_20d_pct': quote.change_20d_pct,
            'turnover_rate': quote.turnover_rate,
            'market_cap': quote.market_cap,
            'pe_ttm': quote.pe_ttm,
            'ma5': quote.ma5,
            'ma20': quote.ma20,
            'ma60': quote.ma60,
            'macd': quote.macd,
            'macd_signal': quote.macd_signal,
            'macd_hist': quote.macd_hist,
            'rsi': quote.rsi,
            'boll_upper': quote.boll_upper,
            'boll_middle': quote.boll_middle,
            'boll_lower': quote.boll_lower,
            'listed_days': listed_days,
        }

    enriched_meta = {}
    for stock_code, meta in universe_members.items():
        enriched_meta[stock_code] = dict(meta)
    return {
        'dates': dates,
        'quotes_by_date': quotes_by_date,
        'universe_meta': enriched_meta,
        'max_positions': max_positions,
        'cash_reserve_ratio': cash_reserve_ratio,
        'initial_capital': initial_capital,
        'next_plan_date': next_business_day(date.fromisoformat(dates[-1])).isoformat(),
    }


def get_portfolio_strategy_catalog() -> Dict[str, Any]:
    return {
        'default_strategy_id': DEFAULT_STRATEGY_ID,
        'default_universe_id': DEFAULT_UNIVERSE_ID,
        'period_options': PERIOD_OPTION_LIST,
        'universe_options': UNIVERSE_OPTIONS,
        'strategies': [build_strategy_meta(strategy_id) for strategy_id in PORTFOLIO_STRATEGIES.keys()],
    }


def execute_portfolio_backtest(request: PortfolioBacktestRequest, db: Session) -> Dict[str, Any]:
    if request.strategy_id not in PORTFOLIO_STRATEGIES:
        raise HTTPException(status_code=404, detail=f'Unknown strategy: {request.strategy_id}')
    universe_members = get_universe_members(request.universe_id, db)
    quotes = load_universe_quotes(request, universe_members, db)
    context = build_market_context(quotes, universe_members, request.max_positions, request.cash_reserve_ratio, request.initial_capital)
    strategy = PORTFOLIO_STRATEGIES[request.strategy_id]
    params = {**get_strategy_defaults(request.strategy_id), **request.strategy_params}
    result = strategy['runner'](context, params)
    return {
        'universe': {
            'id': request.universe_id,
            'label': '沪深300',
            'size': len(universe_members),
        },
        'strategy': {
            **build_strategy_meta(request.strategy_id),
            'params': params,
        },
        'period': request.period,
        'start_date': context['dates'][0],
        'end_date': context['dates'][-1],
        **result,
    }


def generate_portfolio_plan(request: PortfolioPlanRequest, db: Session) -> Dict[str, Any]:
    if request.strategy_id not in PORTFOLIO_STRATEGIES:
        raise HTTPException(status_code=404, detail=f'Unknown strategy: {request.strategy_id}')
    universe_members = get_universe_members(request.universe_id, db)
    codes = list(universe_members.keys())
    quotes = db.query(DailyQuote).filter(DailyQuote.stock_code.in_(codes)).order_by(DailyQuote.trade_date, DailyQuote.stock_code).all()
    if not quotes:
        raise HTTPException(status_code=404, detail='No quote data found for the requested universe')
    latest_date = quotes[-1].trade_date
    recent_quotes = [item for item in quotes if item.trade_date >= latest_date - timedelta(days=370)]
    context = build_market_context(recent_quotes, universe_members, request.max_positions, request.cash_reserve_ratio, 0.0)
    strategy = PORTFOLIO_STRATEGIES[request.strategy_id]
    params = {**get_strategy_defaults(request.strategy_id), **request.strategy_params}
    plan = strategy['planner'](context, params, [item.model_dump() for item in request.holdings], request.current_cash)
    return {
        'universe': {'id': request.universe_id, 'label': '沪深300', 'size': len(universe_members)},
        'strategy': {**build_strategy_meta(request.strategy_id), 'params': params},
        **plan,
    }
