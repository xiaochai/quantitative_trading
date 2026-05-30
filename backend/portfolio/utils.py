from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def to_lot_shares(budget: float, price: Optional[float]) -> int:
    if not price or price <= 0:
        return 0
    raw_shares = int(budget / price)
    return raw_shares - raw_shares % 100


def next_business_day(value: date) -> date:
    current = value + timedelta(days=1)
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current


def safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def annualized_return_pct(initial_capital: float, final_capital: float, trading_days: int) -> float:
    if initial_capital <= 0 or final_capital <= 0 or trading_days <= 0:
        return 0.0
    years = trading_days / 252
    if years <= 0:
        return 0.0
    return ((final_capital / initial_capital) ** (1 / years) - 1) * 100


def build_analysis_lines(metrics: Dict[str, Any], latest_candidates: List[Dict[str, Any]]) -> List[str]:
    lines = [
        f"组合总收益 {metrics['return_pct']:.2f}%，年化收益 {metrics['annualized_return_pct']:.2f}%，最大回撤 {metrics['max_drawdown_pct']:.2f}%。",
        f"共执行 {metrics['buy_count']} 次买入、{metrics['sell_count']} 次卖出，调仓日 {metrics['rebalance_count']} 个，胜率 {metrics['win_rate']:.2f}%。",
    ]
    if latest_candidates:
        top = latest_candidates[0]
        lines.append(f"最新候选榜首是 {top['stock_name']}({top['stock_code']})，综合得分 {top['score']:.2f}。")
    return lines
