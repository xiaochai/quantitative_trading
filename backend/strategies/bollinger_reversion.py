from typing import Any, Dict, List

from strategies.utils import calculate_metrics, record_trade, to_lot_shares


def run(price_data: List[Dict[str, Any]], params: Dict[str, Any], initial_capital: float) -> Dict[str, Any]:
    buy_below_lower_pct = float(params["buy_below_lower_pct"])
    take_profit_on_middle = bool(params["take_profit_on_middle"])
    stop_loss_pct = float(params["stop_loss_pct"])
    max_holding_days = int(params["max_holding_days"])

    trades = []
    equity_curve = []
    cash = initial_capital
    shares = 0
    entry_price = 0.0
    holding_days = 0
    peak_equity = initial_capital
    max_drawdown = 0.0

    for data in price_data:
        close = data["close"]
        lower = data["boll_lower"]
        middle = data["boll_middle"]
        upper = data["boll_upper"]
        if close is None:
            continue

        if shares > 0:
            holding_days += 1
            sell_reason = None
            if close <= entry_price * (1 - stop_loss_pct):
                sell_reason = f"跌破入场价 {stop_loss_pct * 100:.1f}% 止损"
            elif take_profit_on_middle and middle is not None and close >= middle:
                sell_reason = "回到布林带中轨止盈"
            elif not take_profit_on_middle and upper is not None and close >= upper:
                sell_reason = "触及布林带上轨止盈"
            elif holding_days >= max_holding_days:
                sell_reason = f"达到 {max_holding_days} 个交易日持有上限"

            if sell_reason:
                cash += shares * close
                profit = (close - entry_price) * shares
                record_trade(trades, data["date"], "SELL", close, shares, sell_reason, profit)
                shares = 0
                entry_price = 0.0
                holding_days = 0

        if shares == 0 and lower is not None and close <= lower * (1 - buy_below_lower_pct):
            buy_shares = to_lot_shares(cash, close)
            if buy_shares >= 100:
                cash -= buy_shares * close
                shares = buy_shares
                entry_price = close
                holding_days = 0
                record_trade(trades, data["date"], "BUY", close, buy_shares, "跌破布林带下轨后做均值回归")

        current_equity = cash + shares * close
        equity_curve.append({"date": data["date"], "equity": current_equity})
        peak_equity = max(peak_equity, current_equity)
        drawdown = (peak_equity - current_equity) / peak_equity if peak_equity > 0 else 0
        max_drawdown = max(max_drawdown, drawdown)

    if shares > 0 and price_data:
        last_close = price_data[-1]["close"]
        cash += shares * last_close
        profit = (last_close - entry_price) * shares
        record_trade(trades, price_data[-1]["date"], "SELL", last_close, shares, "样本结束平仓", profit)

    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "metrics": calculate_metrics(initial_capital, cash, trades, max_drawdown),
    }


STRATEGY = {
    "id": "bollinger_reversion",
    "name": "布林带均值回归策略",
    "description": "当价格跌破布林带下轨后尝试做反弹，适合震荡行情。",
    "rules": [
        "价格跌破布林带下轨后买入",
        "优先回到中轨止盈，也可切换为上轨止盈",
        "加入止损和最大持有天数，避免长期套牢",
    ],
    "chart_overlays": [
        {"key": "boll_upper", "label": "布林上轨", "color": "#ff6b6b", "lineStyle": "dashed"},
        {"key": "boll_middle", "label": "布林中轨", "color": "#ffd93d", "lineStyle": "solid"},
        {"key": "boll_lower", "label": "布林下轨", "color": "#00ff88", "lineStyle": "dashed"},
    ],
    "param_schema": [
        {"key": "buy_below_lower_pct", "label": "下轨下穿比例", "type": "number", "default": 0.0, "min": 0.0, "max": 0.05, "step": 0.005},
        {"key": "take_profit_on_middle", "label": "中轨止盈", "type": "boolean", "default": True},
        {"key": "stop_loss_pct", "label": "止损比例", "type": "number", "default": 0.03, "min": 0.005, "max": 0.1, "step": 0.005},
        {"key": "max_holding_days", "label": "最大持有天数", "type": "number", "default": 10, "min": 1, "max": 60, "step": 1},
    ],
    "runner": run,
}
