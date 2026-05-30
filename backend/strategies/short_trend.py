from typing import Any, Dict, List

from strategies.utils import calculate_metrics, record_trade, to_lot_shares


def run(price_data: List[Dict[str, Any]], params: Dict[str, Any], initial_capital: float) -> Dict[str, Any]:
    buy_rsi_threshold = float(params["buy_rsi_threshold"])
    sell_rsi_threshold = float(params["sell_rsi_threshold"])
    stop_loss_pct = float(params["stop_loss_pct"])
    max_holding_days = int(params["max_holding_days"])
    ma_gap_ratio = float(params["ma_gap_ratio"])

    trades = []
    equity_curve = []
    cash = initial_capital
    shares = 0
    entry_price = 0.0
    holding_days = 0
    peak_equity = initial_capital
    max_drawdown = 0.0

    for idx, data in enumerate(price_data):
        close = data["close"]
        ma5 = data["ma5"]
        ma20 = data["ma20"]
        rsi = data["rsi"] if data["rsi"] is not None else 50
        macd_hist = data["macd_hist"] if data["macd_hist"] is not None else 0
        prev_macd_hist = 0
        if idx > 0 and price_data[idx - 1]["macd_hist"] is not None:
            prev_macd_hist = price_data[idx - 1]["macd_hist"]

        if shares > 0:
            holding_days += 1
            sell_reason = None

            if rsi >= sell_rsi_threshold:
                sell_reason = f"RSI 触及 {sell_rsi_threshold:g}，短线止盈"
            elif close <= entry_price * (1 - stop_loss_pct):
                sell_reason = f"跌破入场价 {stop_loss_pct * 100:.1f}% 止损"
            elif holding_days >= max_holding_days:
                sell_reason = f"达到 {max_holding_days} 个交易日持有上限"
            elif ma5 is not None and close < ma5:
                sell_reason = "收盘跌回 MA5 下方"

            if sell_reason:
                sell_shares = shares
                cash += sell_shares * close
                profit = (close - entry_price) * sell_shares
                record_trade(trades, data["date"], "SELL", close, sell_shares, sell_reason, profit)
                shares = 0
                entry_price = 0.0
                holding_days = 0
                current_equity = cash
                equity_curve.append({"date": data["date"], "equity": current_equity})
                peak_equity = max(peak_equity, current_equity)
                drawdown = (peak_equity - current_equity) / peak_equity if peak_equity > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
                continue

        if shares == 0 and ma5 is not None and ma20 is not None:
            trend_breakout = close > ma5 and ma5 > ma20 * ma_gap_ratio
            momentum_ok = rsi >= buy_rsi_threshold and macd_hist > 0 and prev_macd_hist <= macd_hist
            if trend_breakout and momentum_ok:
                buy_shares = to_lot_shares(cash, close)
                if buy_shares >= 100:
                    cash -= buy_shares * close
                    shares = buy_shares
                    entry_price = close
                    holding_days = 0
                    record_trade(
                        trades,
                        data["date"],
                        "BUY",
                        close,
                        buy_shares,
                        "MA5 强于 MA20 且 RSI/MACD 动能共振，顺势做多",
                    )

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
    "id": "short_trend",
    "name": "高频短趋势策略",
    "description": "基于 MA5/MA20、RSI 和 MACD 动能的顺势快进快出策略。",
    "rules": [
        "当收盘价站上 MA5，且 MA5 高于 MA20 一定比例时，认为短趋势成立",
        "同时要求 RSI 与 MACD 动能确认，再执行买入",
        "买入后若 RSI 到目标值、跌破入场价止损、持有超时，或跌回 MA5 下方，则卖出",
    ],
    "chart_overlays": [
        {"key": "ma5", "label": "MA5", "color": "#ffd93d", "lineStyle": "solid"},
        {"key": "ma20", "label": "MA20", "color": "#00d4ff", "lineStyle": "dashed"},
    ],
    "param_schema": [
        {"key": "buy_rsi_threshold", "label": "买入 RSI", "type": "number", "default": 55, "min": 40, "max": 80, "step": 1},
        {"key": "sell_rsi_threshold", "label": "卖出 RSI", "type": "number", "default": 62, "min": 45, "max": 90, "step": 1},
        {"key": "stop_loss_pct", "label": "止损比例", "type": "number", "default": 0.015, "min": 0.005, "max": 0.1, "step": 0.005},
        {"key": "max_holding_days", "label": "最大持有天数", "type": "number", "default": 3, "min": 1, "max": 20, "step": 1},
        {"key": "ma_gap_ratio", "label": "MA5/MA20 趋势系数", "type": "number", "default": 1.006, "min": 1.0, "max": 1.03, "step": 0.001},
    ],
    "runner": run,
}
