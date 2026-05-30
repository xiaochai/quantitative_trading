from typing import Any, Dict, List, Optional

from models.stock_data import DailyQuote


def to_lot_shares(budget: float, price: float) -> int:
    if not price or price <= 0:
        return 0
    raw_shares = int(budget / price)
    return raw_shares - raw_shares % 100


def record_trade(
    trades: List[Dict[str, Any]],
    trade_date: str,
    trade_type: str,
    price: float,
    shares: int,
    reason: str,
    profit: Optional[float] = None,
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


def build_price_data(quotes: List[DailyQuote]) -> List[Dict[str, Any]]:
    price_data = []
    for quote in quotes:
        if quote.close is None:
            continue
        price_data.append({
            "date": quote.trade_date.isoformat(),
            "open": quote.open,
            "high": quote.high,
            "low": quote.low,
            "close": quote.close,
            "volume": quote.volume,
            "ma5": quote.ma5,
            "ma20": quote.ma20,
            "ma60": quote.ma60,
            "rsi": quote.rsi,
            "macd": quote.macd,
            "macd_signal": quote.macd_signal,
            "macd_hist": quote.macd_hist,
            "boll_upper": quote.boll_upper,
            "boll_middle": quote.boll_middle,
            "boll_lower": quote.boll_lower,
        })
    return price_data


def calculate_metrics(
    initial_capital: float,
    final_capital: float,
    trades: List[Dict[str, Any]],
    max_drawdown: float,
) -> Dict[str, Any]:
    sell_trades = [t for t in trades if t["type"] == "SELL"]
    win_trades = [t for t in sell_trades if t.get("profit", 0) > 0]
    win_rate = (len(win_trades) / len(sell_trades) * 100) if sell_trades else 0
    return {
        "initial_capital": initial_capital,
        "final_capital": final_capital,
        "total_return": final_capital - initial_capital,
        "return_pct": ((final_capital - initial_capital) / initial_capital) * 100 if initial_capital else 0,
        "max_drawdown_pct": max_drawdown * 100,
        "win_rate": win_rate,
        "total_trades": len(sell_trades),
        "buy_count": len([t for t in trades if t["type"] == "BUY"]),
        "sell_count": len(sell_trades),
    }
