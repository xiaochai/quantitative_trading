from __future__ import annotations

from statistics import pstdev
from typing import Any, Dict, List, Optional, Tuple

from portfolio.utils import (
    annualized_return_pct,
    build_analysis_lines,
    clamp,
    safe_float,
    to_lot_shares,
)


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _recent_closes(
    dates: List[str],
    quotes_by_date: Dict[str, Dict[str, Dict[str, Any]]],
    date_index: int,
    stock_code: str,
    window: int,
) -> List[float]:
    start = max(0, date_index - window + 1)
    closes: List[float] = []
    for trade_date in dates[start:date_index + 1]:
        quote = quotes_by_date.get(trade_date, {}).get(stock_code)
        close = _optional_float(quote.get('close')) if quote else None
        if close and close > 0:
            closes.append(close)
    return closes


def _pct_change_from_series(values: List[float], periods: int) -> Optional[float]:
    if len(values) <= periods:
        return None
    base = values[-periods - 1]
    current = values[-1]
    if base <= 0:
        return None
    return (current / base - 1) * 100


def _volatility_from_closes(values: List[float], window: int) -> Optional[float]:
    if len(values) < window + 1:
        return None
    returns = []
    recent = values[-(window + 1):]
    for idx in range(1, len(recent)):
        prev_close = recent[idx - 1]
        current_close = recent[idx]
        if prev_close <= 0:
            return None
        returns.append((current_close / prev_close - 1) * 100)
    if len(returns) < 2:
        return None
    return pstdev(returns)


def _drawdown_from_closes(values: List[float], window: int) -> Optional[float]:
    if len(values) < window:
        return None
    recent = values[-window:]
    peak = max(recent) if recent else 0.0
    current = recent[-1] if recent else 0.0
    if peak <= 0:
        return None
    return (peak - current) / peak * 100


def _build_history_features(
    stock_code: str,
    quote: Dict[str, Any],
    dates: List[str],
    quotes_by_date: Dict[str, Dict[str, Dict[str, Any]]],
    date_index: int,
    params: Dict[str, Any],
) -> Dict[str, Optional[float]]:
    volatility_window = int(params.get('volatility_window') or 10)
    drawdown_window = int(params.get('drawdown_window') or 15)
    lookback = max(25, volatility_window + 1, drawdown_window)
    closes = _recent_closes(dates, quotes_by_date, date_index, stock_code, lookback)
    close = _optional_float(quote.get('close'))
    ma20 = _optional_float(quote.get('ma20'))

    momentum_20d = _optional_float(quote.get('change_20d_pct'))
    if momentum_20d is None:
        momentum_20d = _pct_change_from_series(closes, 20)

    close_ma20_gap_pct = None
    if close and ma20 and ma20 > 0:
        close_ma20_gap_pct = (close / ma20 - 1) * 100

    return {
        'momentum_20d_pct': momentum_20d,
        'gain_5d_pct': _pct_change_from_series(closes, 5),
        'close_ma20_gap_pct': close_ma20_gap_pct,
        'volatility_pct': _volatility_from_closes(closes, volatility_window),
        'drawdown_pct': _drawdown_from_closes(closes, drawdown_window),
    }


def _candidate_reason(
    quote: Dict[str, Any],
    score_parts: Dict[str, float],
    history_features: Dict[str, Optional[float]],
) -> str:
    extras = []
    if history_features.get('gain_5d_pct') is not None:
        extras.append(f"5日涨幅 {history_features['gain_5d_pct']:.2f}%")
    if history_features.get('volatility_pct') is not None:
        extras.append(f"10日波动 {history_features['volatility_pct']:.2f}%")
    if history_features.get('drawdown_pct') is not None:
        extras.append(f"近端回撤 {history_features['drawdown_pct']:.2f}%")
    extra_text = f"、{'、'.join(extras)}" if extras else ""
    return (
        f"20日涨幅 {safe_float(history_features.get('momentum_20d_pct')):.2f}%、"
        f"收盘/MA20 {safe_float(quote.get('close')) / max(safe_float(quote.get('ma20'), 1e-9), 1e-9):.3f}、"
        f"MA20/MA60 {safe_float(quote.get('ma20')) / max(safe_float(quote.get('ma60'), 1e-9), 1e-9):.3f}、"
        f"RSI {safe_float(quote.get('rsi')):.1f}、MACD柱 {safe_float(quote.get('macd_hist')):.4f}{extra_text}；"
        f"动量 {score_parts['momentum']:.1f} / 趋势 {score_parts['trend']:.1f} / 结构 {score_parts['structure']:.1f} / RSI {score_parts['rsi']:.1f} / MACD {score_parts['macd']:.1f}"
    )


def _is_eligible(
    quote: Dict[str, Any],
    meta: Dict[str, Any],
    params: Dict[str, Any],
    history_features: Dict[str, Optional[float]],
) -> bool:
    close = _optional_float(quote.get('close'))
    ma20 = _optional_float(quote.get('ma20'))
    ma60 = _optional_float(quote.get('ma60'))
    rsi = _optional_float(quote.get('rsi'))
    macd_hist = _optional_float(quote.get('macd_hist'))
    momentum_20d = history_features.get('momentum_20d_pct')

    if not close or not ma20 or not ma60:
        return False
    if meta.get('is_st') or meta.get('is_delisted'):
        return False
    listed_days = meta.get('listed_days')
    if listed_days is not None and listed_days < int(params['min_listed_days']):
        return False
    if close <= ma20 or ma20 <= ma60:
        return False
    if momentum_20d is not None and momentum_20d <= 0:
        return False
    if macd_hist is not None and macd_hist <= 0:
        return False
    if rsi is not None and (rsi < float(params['min_rsi']) or rsi > float(params['max_rsi'])):
        return False

    if bool(params.get('enable_overheat_filter')):
        gain_5d_pct = history_features.get('gain_5d_pct')
        if gain_5d_pct is not None and gain_5d_pct > float(params['max_5d_gain_pct']):
            return False
        close_ma20_gap_pct = history_features.get('close_ma20_gap_pct')
        if close_ma20_gap_pct is not None and close_ma20_gap_pct > float(params['max_close_ma20_gap_pct']):
            return False

    if bool(params.get('enable_volatility_filter')):
        volatility_pct = history_features.get('volatility_pct')
        if volatility_pct is not None and volatility_pct > float(params['max_volatility_pct']):
            return False

    if bool(params.get('enable_drawdown_filter')):
        drawdown_pct = history_features.get('drawdown_pct')
        if drawdown_pct is not None and drawdown_pct > float(params['max_drawdown_pct']):
            return False

    return True


def _score_universe(
    quotes_for_day: Dict[str, Dict[str, Any]],
    universe_meta: Dict[str, Dict[str, Any]],
    params: Dict[str, Any],
    dates: List[str],
    quotes_by_date: Dict[str, Dict[str, Dict[str, Any]]],
    date_index: int,
) -> List[Dict[str, Any]]:
    ranked = []
    for stock_code, quote in quotes_for_day.items():
        meta = universe_meta.get(stock_code)
        if not meta:
            continue

        history_features = _build_history_features(stock_code, quote, dates, quotes_by_date, date_index, params)
        if not _is_eligible(quote, meta, params, history_features):
            continue

        momentum_20d = history_features.get('momentum_20d_pct') or 0.0
        momentum = clamp(momentum_20d, 0, 25) * 1.4
        trend = clamp((safe_float(quote.get('close')) / max(safe_float(quote.get('ma20'), 1e-9), 1e-9) - 1) * 100, 0, 10) * 1.4
        structure = clamp((safe_float(quote.get('ma20')) / max(safe_float(quote.get('ma60'), 1e-9), 1e-9) - 1) * 100, 0, 10) * 1.8

        rsi = _optional_float(quote.get('rsi'))
        rsi_score = 8.0 if rsi is None else max(0.0, 16 - abs(rsi - 60) * 0.7)

        macd = _optional_float(quote.get('macd'))
        macd_signal = _optional_float(quote.get('macd_signal'))
        if macd is None or macd_signal is None:
            macd_score = 4.0
        else:
            macd_score = 8.0 + (4.0 if macd > macd_signal else 0.0)

        turnover = _optional_float(quote.get('turnover_rate'))
        liquidity_score = 5.0 if turnover is not None and 0.5 <= turnover <= 5.0 else 2.5 if turnover is not None and turnover > 0 else 0.0

        score_parts = {
            'momentum': momentum,
            'trend': trend,
            'structure': structure,
            'rsi': rsi_score,
            'macd': macd_score + liquidity_score,
        }
        total_score = sum(score_parts.values())
        if total_score < float(params['score_threshold']):
            continue

        ranked.append({
            'stock_code': stock_code,
            'stock_name': meta['stock_name'],
            'score': round(total_score, 4),
            'reason': _candidate_reason(quote, score_parts, history_features),
            'quote': quote,
            'history_features': history_features,
        })

    ranked.sort(key=lambda item: item['score'], reverse=True)
    for idx, item in enumerate(ranked, start=1):
        item['rank'] = idx
    return ranked


def _build_target_codes(
    rankings: List[Dict[str, Any]],
    current_holdings: Dict[str, Dict[str, Any]],
    max_positions: int,
    keep_buffer: int,
) -> List[str]:
    ranking_map = {item['stock_code']: item for item in rankings}
    keep_codes = []
    for stock_code in current_holdings.keys():
        ranked = ranking_map.get(stock_code)
        if ranked and ranked['rank'] <= max_positions + keep_buffer:
            keep_codes.append((ranked['rank'], stock_code))
    keep_codes.sort(key=lambda item: item[0])
    selected = [item[1] for item in keep_codes[:max_positions]]
    for item in rankings:
        if item['stock_code'] in selected:
            continue
        if len(selected) >= max_positions:
            break
        selected.append(item['stock_code'])
    return selected


def _portfolio_value(
    cash: float,
    holdings: Dict[str, Dict[str, Any]],
    quote_map: Dict[str, Dict[str, Any]],
    price_key: str,
) -> float:
    value = cash
    for stock_code, holding in holdings.items():
        quote = quote_map.get(stock_code)
        price = quote.get(price_key) if quote else None
        if price:
            value += holding['shares'] * price
    return value


def _exit_reason(
    stock_code: str,
    target_codes: List[str],
    ranking_map: Dict[str, Dict[str, Any]],
    signal_quote: Dict[str, Any],
) -> str:
    if stock_code not in target_codes:
        ranked = ranking_map.get(stock_code)
        if not ranked:
            return '不再满足增强版趋势/动量过滤，移出组合'
        return f"跌出目标组合，当前排名第 {ranked['rank']}"
    close = signal_quote.get('close')
    ma20 = signal_quote.get('ma20')
    ma60 = signal_quote.get('ma60')
    macd_hist = safe_float(signal_quote.get('macd_hist'))
    if close and ma20 and close <= ma20:
        return '收盘跌破 MA20，趋势走弱'
    if ma20 and ma60 and ma20 <= ma60:
        return 'MA20 下穿或贴近 MA60，中期结构转弱'
    if macd_hist <= 0:
        return 'MACD 柱线转负，动能衰减'
    return '组合优化调仓'


def _build_metrics(
    initial_capital: float,
    final_capital: float,
    equity_curve: List[Dict[str, Any]],
    trade_records: List[Dict[str, Any]],
    rebalance_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    max_drawdown = 0.0
    peak = 0.0
    average_positions = 0.0
    for item in equity_curve:
        equity = item['equity']
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
        average_positions += item.get('positions', 0)
    average_positions = average_positions / len(equity_curve) if equity_curve else 0.0
    sell_trades = [item for item in trade_records if item['action'] == 'SELL']
    win_trades = [item for item in sell_trades if item.get('profit', 0) > 0]
    total_fees = sum(safe_float(item.get('fees')) for item in trade_records)
    return {
        'initial_capital': initial_capital,
        'final_capital': round(final_capital, 2),
        'total_return': round(final_capital - initial_capital, 2),
        'return_pct': round((final_capital - initial_capital) / initial_capital * 100, 2) if initial_capital else 0.0,
        'annualized_return_pct': round(annualized_return_pct(initial_capital, final_capital, len(equity_curve)), 2),
        'max_drawdown_pct': round(max_drawdown * 100, 2),
        'buy_count': len([item for item in trade_records if item['action'] == 'BUY']),
        'sell_count': len(sell_trades),
        'total_trades': len(sell_trades),
        'win_rate': round(len(win_trades) / len(sell_trades) * 100, 2) if sell_trades else 0.0,
        'rebalance_count': len(rebalance_events),
        'average_positions': round(average_positions, 2),
        'total_fees': round(total_fees, 2),
    }


def _market_risk_off(signal_date: str, index_close_by_date: Dict[str, float], window: int) -> Optional[Dict[str, Any]]:
    if window <= 1:
        return None
    idx_close = index_close_by_date.get(signal_date)
    if idx_close is None:
        return None
    recent_dates = sorted([d for d in index_close_by_date.keys() if d <= signal_date])[-window:]
    if len(recent_dates) < window:
        return None
    ma = sum(index_close_by_date[d] for d in recent_dates) / window
    if idx_close <= ma:
        return {'close': idx_close, 'ma': ma, 'window': window}
    return None


def _price_limit_ratio(stock_code: str, meta: Dict[str, Any]) -> float:
    if meta.get('is_st'):
        return 0.05
    if stock_code.startswith(('300', '301', '688')):
        return 0.20
    return 0.10


def _open_execution_block_reason(
    side: str,
    stock_code: str,
    meta: Dict[str, Any],
    prev_close: Optional[float],
    execute_quote: Optional[Dict[str, Any]],
) -> Optional[str]:
    if not execute_quote:
        return '执行日无行情（可能停牌/数据缺失）'
    open_price = _optional_float(execute_quote.get('open'))
    high_price = _optional_float(execute_quote.get('high'))
    low_price = _optional_float(execute_quote.get('low'))
    if not open_price or open_price <= 0:
        return '执行日缺少开盘价（可能停牌/数据缺失）'
    if not prev_close or prev_close <= 0:
        return None

    limit_ratio = _price_limit_ratio(stock_code, meta)
    if side == 'BUY':
        limit_up = prev_close * (1 + limit_ratio)
        if open_price >= limit_up * 0.999 and (low_price is None or low_price >= limit_up * 0.999):
            return f'次日疑似封住涨停，无法按开盘价买入（涨跌幅限制 {limit_ratio * 100:.0f}%）'
    else:
        limit_down = prev_close * (1 - limit_ratio)
        if open_price <= limit_down * 1.001 and (high_price is None or high_price <= limit_down * 1.001):
            return f'次日疑似封住跌停，无法按开盘价卖出（涨跌幅限制 {limit_ratio * 100:.0f}%）'
    return None


def _intraday_stop_block_reason(
    stock_code: str,
    meta: Dict[str, Any],
    prev_close: Optional[float],
    execute_quote: Optional[Dict[str, Any]],
) -> Optional[str]:
    if not execute_quote or not prev_close or prev_close <= 0:
        return None
    high_price = _optional_float(execute_quote.get('high'))
    limit_ratio = _price_limit_ratio(stock_code, meta)
    limit_down = prev_close * (1 - limit_ratio)
    if high_price is not None and high_price <= limit_down * 1.001:
        return f'执行日全天接近跌停，盘中止损无法成交（涨跌幅限制 {limit_ratio * 100:.0f}%）'
    return None


def _commission(amount: float, rate: float, minimum: float) -> float:
    if amount <= 0 or rate <= 0:
        return 0.0
    return max(amount * rate, minimum)


def _estimate_buy_order(shares: int, reference_price: float, params: Dict[str, Any]) -> Dict[str, float]:
    slippage_rate = float(params.get('slippage_rate') or 0.0)
    buy_commission_rate = float(params.get('buy_commission_rate') or 0.0)
    min_commission = float(params.get('min_commission') or 0.0)
    executed_price = reference_price * (1 + slippage_rate)
    gross_amount = shares * executed_price
    commission = _commission(gross_amount, buy_commission_rate, min_commission)
    total_cost = gross_amount + commission
    return {
        'executed_price': executed_price,
        'gross_amount': gross_amount,
        'fees': commission,
        'total_cost': total_cost,
    }


def _estimate_sell_order(shares: int, reference_price: float, params: Dict[str, Any]) -> Dict[str, float]:
    slippage_rate = float(params.get('slippage_rate') or 0.0)
    sell_commission_rate = float(params.get('sell_commission_rate') or 0.0)
    sell_stamp_duty_rate = float(params.get('sell_stamp_duty_rate') or 0.0)
    min_commission = float(params.get('min_commission') or 0.0)
    executed_price = reference_price * (1 - slippage_rate)
    gross_amount = shares * executed_price
    commission = _commission(gross_amount, sell_commission_rate, min_commission)
    stamp_duty = gross_amount * sell_stamp_duty_rate
    fees = commission + stamp_duty
    net_amount = gross_amount - fees
    return {
        'executed_price': executed_price,
        'gross_amount': gross_amount,
        'fees': fees,
        'net_amount': net_amount,
    }


def _fit_buy_order(
    budget: float,
    reference_price: float,
    params: Dict[str, Any],
) -> Tuple[int, Optional[Dict[str, float]]]:
    if budget <= 0 or reference_price <= 0:
        return 0, None
    shares = to_lot_shares(budget, reference_price)
    while shares >= 100:
        order = _estimate_buy_order(shares, reference_price, params)
        if order['total_cost'] <= budget + 1e-9:
            return shares, order
        shares -= 100
    return 0, None


def run_backtest(context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    dates = context['dates']  # 回测交易日序列（信号日为 T，执行日使用 T+1）
    quotes_by_date = context['quotes_by_date']  # 行情数据：quotes_by_date[date][stock_code] -> 日线与指标字典
    universe_meta = context['universe_meta']  # 股票池元数据：ST/退市/上市日期/名称等
    index_close_by_date = context.get('hs300_index_close_by_date') or {}  # 沪深300指数收盘价映射（用于市场风控）
    initial_capital = float(context['initial_capital'])  # 初始资金
    max_positions = int(context['max_positions'])  # 最大持仓只数
    cash_reserve_ratio = float(context['cash_reserve_ratio'])  # 预留现金比例（不参与建仓）
    keep_buffer = int(params['keep_buffer'])  # 持仓缓冲名次：已有持仓排名略靠后时仍可继续持有以降低换手
    min_holding_days = int(params['min_holding_days'])  # 最短持有天数（未满则掉出目标组合也不立刻卖）
    stop_loss_pct = float(params['stop_loss_pct'])  # 收盘止损比例（基于成本价触发）
    enable_intraday_stop = bool(params.get('enable_intraday_stop'))  # 是否启用盘中止损（使用执行日 low 触发）
    intraday_stop_loss_pct = float(params.get('intraday_stop_loss_pct') or 0.0)  # 盘中止损比例（相对前收/锚定价）
    enable_market_risk = bool(params.get('enable_market_risk_control'))  # 是否启用市场风控（指数跌破均线则 risk-off）
    market_ma_window = int(params.get('market_ma_window') or 60)  # 市场风控均线窗口（默认 60 日）

    cash = initial_capital
    holdings: Dict[str, Dict[str, Any]] = {}
    trade_records: List[Dict[str, Any]] = []
    rebalance_events: List[Dict[str, Any]] = []
    equity_curve: List[Dict[str, Any]] = []
    latest_candidates: List[Dict[str, Any]] = []

    for idx, signal_date in enumerate(dates[:-1]):
        signal_quotes = quotes_by_date[signal_date]
        equity_curve.append({
            'date': signal_date,
            'equity': round(_portfolio_value(cash, holdings, signal_quotes, 'close'), 2),
            'positions': len(holdings),
        })

        rankings = _score_universe(signal_quotes, universe_meta, params, dates, quotes_by_date, idx)
        latest_candidates = rankings[:10]
        ranking_map = {item['stock_code']: item for item in rankings}
        market_risk = _market_risk_off(signal_date, index_close_by_date, market_ma_window) if enable_market_risk else None
        target_codes = [] if market_risk else _build_target_codes(rankings, holdings, max_positions, keep_buffer)
        execute_date = dates[idx + 1]
        execute_quotes = quotes_by_date[execute_date]

        sells = []
        sell_blocked = []
        estimated_cash = cash
        for stock_code, holding in list(holdings.items()):
            signal_quote = signal_quotes.get(stock_code, {})
            meta = universe_meta.get(stock_code, {})
            close = _optional_float(signal_quote.get('close'))
            ma20 = _optional_float(signal_quote.get('ma20'))
            ma60 = _optional_float(signal_quote.get('ma60'))
            macd_hist = _optional_float(signal_quote.get('macd_hist'))
            holding_days = idx - holding['entry_index']
            hard_exit = (
                (close and ma20 and close <= ma20 * 0.98) or
                (ma20 and ma60 and ma20 <= ma60) or
                (macd_hist is not None and macd_hist <= 0) or
                (close and close <= holding['cost_price'] * (1 - stop_loss_pct))
            )
            soft_exit = stock_code not in target_codes and holding_days >= min_holding_days
            should_exit = bool(market_risk) or hard_exit or soft_exit
            if not should_exit:
                continue
            execute_quote = execute_quotes.get(stock_code)
            blocked_reason = _open_execution_block_reason('SELL', stock_code, meta, close, execute_quote)
            if blocked_reason:
                sell_blocked.append({
                    'stock_code': stock_code,
                    'stock_name': holding['stock_name'],
                    'reason': blocked_reason,
                })
                continue

            open_price = float(execute_quote['open'])
            order = _estimate_sell_order(holding['shares'], open_price, params)
            proceeds = order['net_amount']
            profit = proceeds - holding['shares'] * holding['cost_price']
            estimated_cash += proceeds
            sells.append({
                'action': 'SELL',
                'signal_date': signal_date,
                'execute_date': execute_date,
                'stock_code': stock_code,
                'stock_name': holding['stock_name'],
                'shares': holding['shares'],
                'price': round(order['executed_price'], 2),
                'gross_amount': round(order['gross_amount'], 2),
                'fees': round(order['fees'], 2),
                'amount': round(proceeds, 2),
                'profit': round(profit, 2),
                'reason': (
                    f"市场风控触发：沪深300收盘 {market_risk['close']:.2f} 跌破 MA{market_risk['window']} {market_risk['ma']:.2f}，清仓防回撤"
                    if market_risk else _exit_reason(stock_code, target_codes, ranking_map, signal_quote)
                ),
            })

        for item in sells:
            cash += item['amount']
            holdings.pop(item['stock_code'], None)
            trade_records.append(item)

        available_slots = max_positions - len(holdings)
        buys = []
        buy_skipped = []
        if available_slots > 0 and not market_risk:
            portfolio_value = _portfolio_value(cash, holdings, signal_quotes, 'close')
            target_position_value = portfolio_value * (1 - cash_reserve_ratio) / max_positions if max_positions else 0
            for candidate in rankings:
                if candidate['stock_code'] in holdings or candidate['stock_code'] not in target_codes:
                    continue
                execute_quote = execute_quotes.get(candidate['stock_code'])
                prev_close = _optional_float(signal_quotes.get(candidate['stock_code'], {}).get('close'))
                blocked_reason = _open_execution_block_reason(
                    'BUY',
                    candidate['stock_code'],
                    universe_meta.get(candidate['stock_code'], {}),
                    prev_close,
                    execute_quote,
                )
                if blocked_reason:
                    buy_skipped.append({
                        'stock_code': candidate['stock_code'],
                        'stock_name': candidate['stock_name'],
                        'reason': blocked_reason,
                        'rank': candidate.get('rank'),
                    })
                    continue
                open_price = float(execute_quote['open'])
                budget = min(target_position_value, cash)
                shares, order = _fit_buy_order(budget, open_price, params)
                if shares < 100 or not order:
                    buy_skipped.append({
                        'stock_code': candidate['stock_code'],
                        'stock_name': candidate['stock_name'],
                        'reason': f'资金不足买入1手（预算 {budget:.2f}，参考开盘价 {open_price:.2f}）',
                        'rank': candidate.get('rank'),
                    })
                    continue
                cash -= order['total_cost']
                holdings[candidate['stock_code']] = {
                    'stock_code': candidate['stock_code'],
                    'stock_name': candidate['stock_name'],
                    'shares': shares,
                    'cost_price': order['executed_price'],
                    'entry_index': idx + 1,
                }
                buy_record = {
                    'action': 'BUY',
                    'signal_date': signal_date,
                    'execute_date': execute_date,
                    'stock_code': candidate['stock_code'],
                    'stock_name': candidate['stock_name'],
                    'shares': shares,
                    'price': round(order['executed_price'], 2),
                    'gross_amount': round(order['gross_amount'], 2),
                    'fees': round(order['fees'], 2),
                    'amount': round(order['total_cost'], 2),
                    'reason': f"入选第 {candidate['rank']} 名，得分 {candidate['score']:.2f}。{candidate['reason']}",
                    'score': round(candidate['score'], 2),
                    'rank': candidate['rank'],
                }
                trade_records.append(buy_record)
                buys.append(buy_record)
                if len(buys) >= available_slots:
                    break

        stop_sells = []
        stop_blocked = []
        if enable_intraday_stop and intraday_stop_loss_pct > 0:
            for stock_code, holding in list(holdings.items()):
                prev_quote = signal_quotes.get(stock_code)
                if not prev_quote or not prev_quote.get('close'):
                    continue
                execute_quote = execute_quotes.get(stock_code)
                if not execute_quote:
                    continue
                blocked_reason = _intraday_stop_block_reason(
                    stock_code,
                    universe_meta.get(stock_code, {}),
                    _optional_float(prev_quote.get('close')),
                    execute_quote,
                )
                if blocked_reason:
                    stop_blocked.append({
                        'stock_code': stock_code,
                        'stock_name': holding['stock_name'],
                        'reason': blocked_reason,
                    })
                    continue
                low_price = _optional_float(execute_quote.get('low'))
                open_price = _optional_float(execute_quote.get('open'))
                prev_close = float(prev_quote['close'])
                stop_price = prev_close * (1 - intraday_stop_loss_pct)
                if not low_price or stop_price <= 0:
                    continue
                if low_price > stop_price:
                    continue
                reference_price = open_price if open_price and open_price <= stop_price else stop_price
                order = _estimate_sell_order(holding['shares'], reference_price, params)
                proceeds = order['net_amount']
                profit = proceeds - holding['shares'] * holding['cost_price']
                cash += proceeds
                holdings.pop(stock_code, None)
                stop_sells.append({
                    'action': 'SELL',
                    'signal_date': signal_date,
                    'execute_date': execute_date,
                    'stock_code': stock_code,
                    'stock_name': holding['stock_name'],
                    'shares': holding['shares'],
                    'price': round(order['executed_price'], 2),
                    'gross_amount': round(order['gross_amount'], 2),
                    'fees': round(order['fees'], 2),
                    'amount': round(proceeds, 2),
                    'profit': round(profit, 2),
                    'reason': f"盘中止损触发：跌破前收 {prev_close:.2f} 的 {intraday_stop_loss_pct * 100:.2f}%（止损价 {stop_price:.2f}）",
                })

        trade_records.extend(stop_sells)

        target_stocks = []
        for code in target_codes:
            ranked = ranking_map.get(code)
            if ranked:
                target_stocks.append(f"{ranked['stock_name']}({code})")
            elif code in holdings:
                target_stocks.append(f"{holdings[code]['stock_name']}({code})")
            else:
                target_stocks.append(code)

        if buys or sells or stop_sells or buy_skipped or sell_blocked or stop_blocked:
            rebalance_events.append({
                'signal_date': signal_date,
                'execute_date': execute_date,
                'buy_count': len(buys),
                'sell_count': len(sells) + len(stop_sells),
                'buy_stocks': [f"{item['stock_name']}({item['stock_code']})" for item in buys],
                'sell_stocks': [f"{item['stock_name']}({item['stock_code']})" for item in sells + stop_sells],
                'target_stocks': target_stocks,
                'buy_skipped': buy_skipped[:10],
                'sell_blocked': sell_blocked[:10],
                'stop_blocked': stop_blocked[:10],
            })

    last_date = dates[-1]
    last_quotes = quotes_by_date[last_date]
    final_capital = _portfolio_value(cash, holdings, last_quotes, 'close')
    equity_curve.append({
        'date': last_date,
        'equity': round(final_capital, 2),
        'positions': len(holdings),
    })

    metrics = _build_metrics(initial_capital, final_capital, equity_curve, trade_records, rebalance_events)
    return {
        'metrics': metrics,
        'equity_curve': equity_curve,
        'trade_records': trade_records,
        'rebalance_events': rebalance_events,
        'latest_candidates': latest_candidates,
        'analysis': [
            f"市场风控：{'开启' if enable_market_risk else '关闭'}（沪深300 跌破 MA{market_ma_window} 时，下一交易日清仓并停止开新仓）。",
            f"增强过滤：过热 {'开启' if bool(params.get('enable_overheat_filter')) else '关闭'} / 波动率 {'开启' if bool(params.get('enable_volatility_filter')) else '关闭'} / 回撤 {'开启' if bool(params.get('enable_drawdown_filter')) else '关闭'}；若缺少所需指标则自动跳过对应过滤。",
            f"成交约束：模拟买卖双边滑点 {float(params.get('slippage_rate') or 0.0) * 100:.2f}% ，买入佣金 {float(params.get('buy_commission_rate') or 0.0) * 100:.3f}% ，卖出佣金 {float(params.get('sell_commission_rate') or 0.0) * 100:.3f}% ，印花税 {float(params.get('sell_stamp_duty_rate') or 0.0) * 100:.3f}% 。",
            *build_analysis_lines(metrics, latest_candidates),
        ],
        'final_holdings': list(holdings.values()),
    }


def build_plan(context: Dict[str, Any], params: Dict[str, Any], holdings_input: List[Dict[str, Any]], current_cash: float) -> Dict[str, Any]:
    dates = context['dates']
    signal_date = dates[-1]
    signal_index = len(dates) - 1
    quotes_by_date = context['quotes_by_date']
    signal_quotes = quotes_by_date[signal_date]
    universe_meta = context['universe_meta']
    index_close_by_date = context.get('hs300_index_close_by_date') or {}
    rankings = _score_universe(signal_quotes, universe_meta, params, dates, quotes_by_date, signal_index)
    ranking_map = {item['stock_code']: item for item in rankings}

    current_holdings = {}
    for item in holdings_input:
        stock_code = item['stock_code'].strip()
        if not stock_code:
            continue
        meta = universe_meta.get(stock_code, {'stock_name': item.get('stock_name') or stock_code})
        current_holdings[stock_code] = {
            'stock_code': stock_code,
            'stock_name': meta.get('stock_name', stock_code),
            'shares': int(item.get('shares') or 0),
            'cost_price': float(item.get('cost_price') or 0),
        }

    max_positions = int(context['max_positions'])
    cash_reserve_ratio = float(context['cash_reserve_ratio'])
    keep_buffer = int(params['keep_buffer'])
    enable_market_risk = bool(params.get('enable_market_risk_control'))
    market_ma_window = int(params.get('market_ma_window') or 60)
    market_risk = _market_risk_off(signal_date, index_close_by_date, market_ma_window) if enable_market_risk else None
    target_codes = [] if market_risk else _build_target_codes(rankings, current_holdings, max_positions, keep_buffer)

    latest_equity = _portfolio_value(current_cash, current_holdings, signal_quotes, 'close')
    target_position_value = latest_equity * (1 - cash_reserve_ratio) / max_positions if max_positions else 0
    sell_limit_buffer = float(params['sell_limit_buffer'])
    buy_limit_buffer = float(params['buy_limit_buffer'])
    enable_intraday_stop = bool(params.get('enable_intraday_stop'))
    intraday_stop_loss_pct = float(params.get('intraday_stop_loss_pct') or 0.0)

    next_day_actions = []
    estimated_cash = current_cash
    for stock_code, holding in current_holdings.items():
        signal_quote = signal_quotes.get(stock_code)
        if not signal_quote or not signal_quote.get('close'):
            continue
        close_price = float(signal_quote['close'])
        if stock_code not in target_codes:
            reference_price = close_price * (1 - sell_limit_buffer)
            order = _estimate_sell_order(holding['shares'], reference_price, params)
            estimated_cash += order['net_amount']
            next_day_actions.append({
                'action': 'SELL',
                'stock_code': stock_code,
                'stock_name': holding['stock_name'],
                'shares': holding['shares'],
                'reference_price': round(reference_price, 2),
                'estimated_price': round(order['executed_price'], 2),
                'reference_amount': round(order['net_amount'], 2),
                'fees': round(order['fees'], 2),
                'reason': (
                    f"市场风控触发：沪深300收盘 {market_risk['close']:.2f} 跌破 MA{market_risk['window']} {market_risk['ma']:.2f}，建议卖出规避回撤"
                    if market_risk else _exit_reason(stock_code, target_codes, ranking_map, signal_quote)
                ),
            })

    remaining_holdings = {code: data for code, data in current_holdings.items() if code in target_codes}
    open_slots = max_positions - len(remaining_holdings)
    if open_slots > 0 and not market_risk:
        for candidate in rankings:
            if candidate['stock_code'] in remaining_holdings or candidate['stock_code'] not in target_codes:
                continue
            signal_quote = signal_quotes.get(candidate['stock_code'])
            if not signal_quote or not signal_quote.get('close'):
                continue
            reference_price = float(signal_quote['close']) * (1 + buy_limit_buffer)
            budget = min(target_position_value, estimated_cash)
            shares, order = _fit_buy_order(budget, reference_price, params)
            if shares < 100 or not order:
                continue
            estimated_cash -= order['total_cost']
            next_day_actions.append({
                'action': 'BUY',
                'stock_code': candidate['stock_code'],
                'stock_name': candidate['stock_name'],
                'shares': shares,
                'reference_price': round(reference_price, 2),
                'estimated_price': round(order['executed_price'], 2),
                'reference_amount': round(order['total_cost'], 2),
                'fees': round(order['fees'], 2),
                'reason': f"入选第 {candidate['rank']} 名，得分 {candidate['score']:.2f}。{candidate['reason']}",
            })
            if len([item for item in next_day_actions if item['action'] == 'BUY']) >= open_slots:
                break

    keep_positions = []
    for stock_code in target_codes:
        if stock_code not in current_holdings:
            continue
        ranked = ranking_map.get(stock_code)
        keep_positions.append({
            'stock_code': stock_code,
            'stock_name': current_holdings[stock_code]['stock_name'],
            'shares': current_holdings[stock_code]['shares'],
            'score': round(ranked['score'], 2) if ranked else None,
            'reason': '继续保留在目标组合内',
        })

    risk_orders = []
    if enable_intraday_stop and intraday_stop_loss_pct > 0:
        planned_sell_codes = {item['stock_code'] for item in next_day_actions if item['action'] == 'SELL'}
        for stock_code, holding in current_holdings.items():
            if stock_code in planned_sell_codes:
                continue
            signal_quote = signal_quotes.get(stock_code)
            close_price = signal_quote.get('close') if signal_quote else None
            anchor_price = safe_float(close_price, 0.0) or float(holding.get('cost_price') or 0)
            if anchor_price <= 0 or holding['shares'] <= 0:
                continue
            stop_price = round(anchor_price * (1 - intraday_stop_loss_pct), 2)
            limit_price = round(stop_price * (1 - sell_limit_buffer), 2)
            if stop_price <= 0 or limit_price <= 0:
                continue
            risk_orders.append({
                'action': 'STOP_SELL',
                'stock_code': stock_code,
                'stock_name': holding['stock_name'],
                'shares': holding['shares'],
                'stop_price': stop_price,
                'limit_price': limit_price,
                'reason': f"盘中止损 {intraday_stop_loss_pct * 100:.2f}%（基于前收 {safe_float(close_price, 0.0):.2f}）",
            })

    return {
        'signal_date': signal_date,
        'plan_date': context['next_plan_date'],
        'latest_candidates': rankings[:10],
        'target_codes': target_codes,
        'keep_positions': keep_positions,
        'next_day_actions': next_day_actions,
        'risk_orders': risk_orders,
        'estimated_cash_after_orders': round(estimated_cash, 2),
        'analysis': [
            f"市场风控：{'开启' if enable_market_risk else '关闭'}（沪深300 跌破 MA{market_ma_window} 时，下一交易日优先卖出并暂停开新仓）。",
            f"增强过滤：过热/波动率/回撤过滤已纳入，若缺少所需字段则自动跳过对应条件。",
            f"收盘后候选前 {max_positions} 名将作为下一交易日的目标组合，并按费用模型估算资金占用。",
            f"盘中止损：{'已开启' if enable_intraday_stop else '未开启'}（比例 {intraday_stop_loss_pct * 100:.2f}%）。",
        ],
    }


STRATEGY = {
    'id': 'hs300_rotation_enhanced',
    'name': '沪深300增强趋势轮动',
    'description': '在原趋势轮动基础上加入过热约束、波动/回撤过滤、交易成本与涨跌停/停牌成交约束。',
    'rules': [
        '仅在沪深300成分股中选股，剔除 ST、退市风险和上市时间过短的股票。',
        '要求收盘价站上 MA20、MA20 高于 MA60，并优先选择动量、趋势结构、RSI 和 MACD 更健康的股票。',
        '新增短期过热过滤、波动率过滤和近期回撤过滤；如果数据库中缺少所需指标，则自动跳过对应过滤。',
        '回测执行引入滑点、佣金、印花税，并对停牌、疑似一字涨停/跌停场景不再假设能成交。',
    ],
    'param_schema': [
        {'key': 'enable_market_risk_control', 'label': '启用市场风控', 'type': 'boolean', 'default': True},
        {'key': 'market_ma_window', 'label': '市场风控均线', 'type': 'number', 'default': 60, 'min': 20, 'max': 250, 'step': 5},
        {'key': 'score_threshold', 'label': '最低得分', 'type': 'number', 'default': 55, 'min': 20, 'max': 100, 'step': 1},
        {'key': 'min_rsi', 'label': '最小 RSI', 'type': 'number', 'default': 48, 'min': 20, 'max': 80, 'step': 1},
        {'key': 'max_rsi', 'label': '最大 RSI', 'type': 'number', 'default': 75, 'min': 40, 'max': 95, 'step': 1},
        {'key': 'min_listed_days', 'label': '最短上市天数', 'type': 'number', 'default': 120, 'min': 30, 'max': 500, 'step': 10},
        {'key': 'keep_buffer', 'label': '持仓缓冲名次', 'type': 'number', 'default': 3, 'min': 0, 'max': 10, 'step': 1},
        {'key': 'min_holding_days', 'label': '最短持有天数', 'type': 'number', 'default': 10, 'min': 1, 'max': 30, 'step': 1},
        {'key': 'stop_loss_pct', 'label': '收盘止损比例', 'type': 'number', 'default': 0.08, 'min': 0.01, 'max': 0.2, 'step': 0.01},
        {'key': 'enable_intraday_stop', 'label': '启用盘中止损单', 'type': 'boolean', 'default': False},
        {'key': 'intraday_stop_loss_pct', 'label': '盘中止损比例', 'type': 'number', 'default': 0.06, 'min': 0.01, 'max': 0.2, 'step': 0.01},
        {'key': 'enable_overheat_filter', 'label': '启用过热过滤', 'type': 'boolean', 'default': True},
        {'key': 'max_5d_gain_pct', 'label': '最大5日涨幅', 'type': 'number', 'default': 15, 'min': 5, 'max': 40, 'step': 1},
        {'key': 'max_close_ma20_gap_pct', 'label': '收盘偏离MA20上限', 'type': 'number', 'default': 12, 'min': 3, 'max': 30, 'step': 1},
        {'key': 'enable_volatility_filter', 'label': '启用波动率过滤', 'type': 'boolean', 'default': True},
        {'key': 'volatility_window', 'label': '波动率窗口', 'type': 'number', 'default': 10, 'min': 5, 'max': 30, 'step': 1},
        {'key': 'max_volatility_pct', 'label': '最大波动率', 'type': 'number', 'default': 6, 'min': 1, 'max': 15, 'step': 0.5},
        {'key': 'enable_drawdown_filter', 'label': '启用回撤过滤', 'type': 'boolean', 'default': True},
        {'key': 'drawdown_window', 'label': '回撤窗口', 'type': 'number', 'default': 15, 'min': 5, 'max': 40, 'step': 1},
        {'key': 'max_drawdown_pct', 'label': '最大近期回撤', 'type': 'number', 'default': 8, 'min': 2, 'max': 20, 'step': 0.5},
        {'key': 'slippage_rate', 'label': '滑点比例', 'type': 'number', 'default': 0.001, 'min': 0.0, 'max': 0.02, 'step': 0.0005},
        {'key': 'buy_commission_rate', 'label': '买入佣金', 'type': 'number', 'default': 0.0003, 'min': 0.0, 'max': 0.005, 'step': 0.0001},
        {'key': 'sell_commission_rate', 'label': '卖出佣金', 'type': 'number', 'default': 0.0003, 'min': 0.0, 'max': 0.005, 'step': 0.0001},
        {'key': 'sell_stamp_duty_rate', 'label': '卖出印花税', 'type': 'number', 'default': 0.001, 'min': 0.0, 'max': 0.005, 'step': 0.0001},
        {'key': 'min_commission', 'label': '最低佣金', 'type': 'number', 'default': 5, 'min': 0, 'max': 20, 'step': 1},
        {'key': 'buy_limit_buffer', 'label': '买入挂单上浮', 'type': 'number', 'default': 0.01, 'min': 0.0, 'max': 0.05, 'step': 0.005},
        {'key': 'sell_limit_buffer', 'label': '卖出挂单下浮', 'type': 'number', 'default': 0.01, 'min': 0.0, 'max': 0.05, 'step': 0.005},
    ],
    'runner': run_backtest,
    'planner': build_plan,
}
