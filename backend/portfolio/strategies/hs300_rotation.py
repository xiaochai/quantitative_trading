from __future__ import annotations

from typing import Any, Dict, List, Optional

from portfolio.utils import (
    annualized_return_pct,
    build_analysis_lines,
    clamp,
    safe_float,
    to_lot_shares,
)


def _candidate_reason(quote: Dict[str, Any], score_parts: Dict[str, float]) -> str:
    return (
        f"20日涨幅 {safe_float(quote.get('change_20d_pct')):.2f}%、"
        f"收盘/MA20 {safe_float(quote.get('close')) / max(safe_float(quote.get('ma20'), 1e-9), 1e-9):.3f}、"
        f"MA20/MA60 {safe_float(quote.get('ma20')) / max(safe_float(quote.get('ma60'), 1e-9), 1e-9):.3f}、"
        f"RSI {safe_float(quote.get('rsi')):.1f}、MACD柱 {safe_float(quote.get('macd_hist')):.4f}；"
        f"动量 {score_parts['momentum']:.1f} / 趋势 {score_parts['trend']:.1f} / 结构 {score_parts['structure']:.1f} / RSI {score_parts['rsi']:.1f} / MACD {score_parts['macd']:.1f}"
    )


def _is_eligible(quote: Dict[str, Any], meta: Dict[str, Any], params: Dict[str, Any]) -> bool:
    close = quote.get('close')
    ma20 = quote.get('ma20')
    ma60 = quote.get('ma60')
    rsi = safe_float(quote.get('rsi'), 50)
    macd_hist = safe_float(quote.get('macd_hist'))
    change_20d_pct = safe_float(quote.get('change_20d_pct'))

    if not close or not ma20 or not ma60:
        return False
    if meta.get('is_st') or meta.get('is_delisted'):
        return False
    listed_days = meta.get('listed_days')
    if listed_days is not None and listed_days < int(params['min_listed_days']):
        return False
    if close <= ma20 or ma20 <= ma60:
        return False
    if change_20d_pct <= 0:
        return False
    if macd_hist <= 0:
        return False
    if rsi < float(params['min_rsi']) or rsi > float(params['max_rsi']):
        return False
    return True


def _score_universe(quotes_for_day: Dict[str, Dict[str, Any]], universe_meta: Dict[str, Dict[str, Any]], params: Dict[str, Any]) -> List[Dict[str, Any]]:
    ranked = []
    for stock_code, quote in quotes_for_day.items():
        meta = universe_meta.get(stock_code)
        if not meta:
            continue
        if not _is_eligible(quote, meta, params):
            continue

        momentum = clamp(safe_float(quote.get('change_20d_pct')), 0, 25) * 1.4
        trend = clamp((safe_float(quote.get('close')) / max(safe_float(quote.get('ma20'), 1e-9), 1e-9) - 1) * 100, 0, 10) * 1.4
        structure = clamp((safe_float(quote.get('ma20')) / max(safe_float(quote.get('ma60'), 1e-9), 1e-9) - 1) * 100, 0, 10) * 1.8
        rsi = safe_float(quote.get('rsi'), 50)
        rsi_score = max(0.0, 16 - abs(rsi - 60) * 0.7)
        macd_score = 8.0
        if safe_float(quote.get('macd')) > safe_float(quote.get('macd_signal')):
            macd_score += 4.0
        turnover = safe_float(quote.get('turnover_rate'))
        liquidity_score = 5.0 if 0.5 <= turnover <= 5.0 else 2.5 if turnover > 0 else 0.0

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
            'reason': _candidate_reason(quote, score_parts),
            'quote': quote,
        })

    ranked.sort(key=lambda item: item['score'], reverse=True)
    for idx, item in enumerate(ranked, start=1):
        item['rank'] = idx
    return ranked


def _build_target_codes(rankings: List[Dict[str, Any]], current_holdings: Dict[str, Dict[str, Any]], max_positions: int, keep_buffer: int) -> List[str]:
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


def _portfolio_value(cash: float, holdings: Dict[str, Dict[str, Any]], quote_map: Dict[str, Dict[str, Any]], price_key: str) -> float:
    value = cash
    for stock_code, holding in holdings.items():
        quote = quote_map.get(stock_code)
        price = quote.get(price_key) if quote else None
        if price:
            value += holding['shares'] * price
    return value


def _exit_reason(stock_code: str, target_codes: List[str], ranking_map: Dict[str, Dict[str, Any]], signal_quote: Dict[str, Any]) -> str:
    if stock_code not in target_codes:
        ranked = ranking_map.get(stock_code)
        if not ranked:
            return '不再满足趋势与动量过滤，移出组合'
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


def _build_metrics(initial_capital: float, final_capital: float, equity_curve: List[Dict[str, Any]], trade_records: List[Dict[str, Any]], rebalance_events: List[Dict[str, Any]]) -> Dict[str, Any]:
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


def run_backtest(context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    dates = context['dates']
    quotes_by_date = context['quotes_by_date']
    universe_meta = context['universe_meta']
    index_close_by_date = context.get('hs300_index_close_by_date') or {}
    initial_capital = float(context['initial_capital'])
    max_positions = int(context['max_positions'])
    cash_reserve_ratio = float(context['cash_reserve_ratio'])
    keep_buffer = int(params['keep_buffer'])
    min_holding_days = int(params['min_holding_days'])
    stop_loss_pct = float(params['stop_loss_pct'])
    enable_intraday_stop = bool(params.get('enable_intraday_stop'))
    intraday_stop_loss_pct = float(params.get('intraday_stop_loss_pct') or 0.0)
    enable_market_risk = bool(params.get('enable_market_risk_control'))
    market_ma_window = int(params.get('market_ma_window') or 60)

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

        rankings = _score_universe(signal_quotes, universe_meta, params)
        latest_candidates = rankings[:10]
        ranking_map = {item['stock_code']: item for item in rankings}
        market_risk = _market_risk_off(signal_date, index_close_by_date, market_ma_window) if enable_market_risk else None
        target_codes = [] if market_risk else _build_target_codes(rankings, holdings, max_positions, keep_buffer)
        execute_date = dates[idx + 1]
        execute_quotes = quotes_by_date[execute_date]

        sells = []
        estimated_cash = cash
        for stock_code, holding in list(holdings.items()):
            signal_quote = signal_quotes.get(stock_code, {})
            close = signal_quote.get('close')
            ma20 = signal_quote.get('ma20')
            ma60 = signal_quote.get('ma60')
            macd_hist = safe_float(signal_quote.get('macd_hist'))
            holding_days = idx - holding['entry_index']
            hard_exit = (
                (close and ma20 and close <= ma20 * 0.98) or
                (ma20 and ma60 and ma20 <= ma60) or
                macd_hist <= 0 or
                (close and close <= holding['cost_price'] * (1 - stop_loss_pct))
            )
            soft_exit = stock_code not in target_codes and holding_days >= min_holding_days
            should_exit = bool(market_risk) or hard_exit or soft_exit
            if not should_exit:
                continue
            execute_quote = execute_quotes.get(stock_code)
            if not execute_quote or not execute_quote.get('open'):
                continue
            open_price = execute_quote['open']
            proceeds = holding['shares'] * open_price
            profit = (open_price - holding['cost_price']) * holding['shares']
            estimated_cash += proceeds
            sells.append({
                'action': 'SELL',
                'signal_date': signal_date,
                'execute_date': execute_date,
                'stock_code': stock_code,
                'stock_name': holding['stock_name'],
                'shares': holding['shares'],
                'price': round(open_price, 2),
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
                if not execute_quote or not execute_quote.get('open'):
                    buy_skipped.append({
                        'stock_code': candidate['stock_code'],
                        'stock_name': candidate['stock_name'],
                        'reason': '执行日缺少开盘价（数据缺失/停牌）',
                        'rank': candidate.get('rank'),
                    })
                    continue
                open_price = float(execute_quote['open'])
                budget = min(target_position_value, cash)
                shares = to_lot_shares(budget, open_price)
                if shares < 100:
                    buy_skipped.append({
                        'stock_code': candidate['stock_code'],
                        'stock_name': candidate['stock_name'],
                        'reason': f'资金不足买入1手（预算 {budget:.2f}，开盘价 {open_price:.2f}）',
                        'rank': candidate.get('rank'),
                    })
                    continue
                amount = shares * open_price
                cash -= amount
                holdings[candidate['stock_code']] = {
                    'stock_code': candidate['stock_code'],
                    'stock_name': candidate['stock_name'],
                    'shares': shares,
                    'cost_price': open_price,
                    'entry_index': idx + 1,
                }
                buy_record = {
                    'action': 'BUY',
                    'signal_date': signal_date,
                    'execute_date': execute_date,
                    'stock_code': candidate['stock_code'],
                    'stock_name': candidate['stock_name'],
                    'shares': shares,
                    'price': round(open_price, 2),
                    'amount': round(amount, 2),
                    'reason': f"入选第 {candidate['rank']} 名，得分 {candidate['score']:.2f}。{candidate['reason']}",
                    'score': round(candidate['score'], 2),
                    'rank': candidate['rank'],
                }
                trade_records.append(buy_record)
                buys.append(buy_record)
                if len(buys) >= available_slots:
                    break

        stop_sells = []
        if enable_intraday_stop and intraday_stop_loss_pct > 0:
            for stock_code, holding in list(holdings.items()):
                prev_quote = signal_quotes.get(stock_code)
                if not prev_quote or not prev_quote.get('close'):
                    continue
                execute_quote = execute_quotes.get(stock_code)
                if not execute_quote:
                    continue
                low_price = execute_quote.get('low')
                open_price = execute_quote.get('open')
                prev_close = float(prev_quote['close'])
                stop_price = prev_close * (1 - intraday_stop_loss_pct)
                if not low_price or stop_price <= 0:
                    continue
                if low_price > stop_price:
                    continue
                executed_price = open_price if open_price and open_price <= stop_price else stop_price
                proceeds = holding['shares'] * executed_price
                profit = (executed_price - holding['cost_price']) * holding['shares']
                cash += proceeds
                holdings.pop(stock_code, None)
                stop_sells.append({
                    'action': 'SELL',
                    'signal_date': signal_date,
                    'execute_date': execute_date,
                    'stock_code': stock_code,
                    'stock_name': holding['stock_name'],
                    'shares': holding['shares'],
                    'price': round(executed_price, 2),
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

        if buys or sells or stop_sells or buy_skipped:
            rebalance_events.append({
                'signal_date': signal_date,
                'execute_date': execute_date,
                'buy_count': len(buys),
                'sell_count': len(sells) + len(stop_sells),
                'buy_stocks': [f"{item['stock_name']}({item['stock_code']})" for item in buys],
                'sell_stocks': [f"{item['stock_name']}({item['stock_code']})" for item in sells + stop_sells],
                'target_stocks': target_stocks,
                'buy_skipped': buy_skipped[:10],
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
            *build_analysis_lines(metrics, latest_candidates),
        ],
        'final_holdings': list(holdings.values()),
    }


def build_plan(context: Dict[str, Any], params: Dict[str, Any], holdings_input: List[Dict[str, Any]], current_cash: float) -> Dict[str, Any]:
    dates = context['dates']
    signal_date = dates[-1]
    quotes_by_date = context['quotes_by_date']
    signal_quotes = quotes_by_date[signal_date]
    universe_meta = context['universe_meta']
    index_close_by_date = context.get('hs300_index_close_by_date') or {}
    rankings = _score_universe(signal_quotes, universe_meta, params)
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
        close_price = signal_quote['close']
        if stock_code not in target_codes:
            reference_price = round(close_price * (1 - sell_limit_buffer), 2)
            estimated_cash += holding['shares'] * reference_price
            next_day_actions.append({
                'action': 'SELL',
                'stock_code': stock_code,
                'stock_name': holding['stock_name'],
                'shares': holding['shares'],
                'reference_price': reference_price,
                'reference_amount': round(holding['shares'] * reference_price, 2),
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
            reference_price = round(signal_quote['close'] * (1 + buy_limit_buffer), 2)
            budget = min(target_position_value, estimated_cash)
            shares = to_lot_shares(budget, reference_price)
            if shares < 100:
                continue
            estimated_cash -= shares * reference_price
            next_day_actions.append({
                'action': 'BUY',
                'stock_code': candidate['stock_code'],
                'stock_name': candidate['stock_name'],
                'shares': shares,
                'reference_price': reference_price,
                'reference_amount': round(shares * reference_price, 2),
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
            f"收盘后候选前 {max_positions} 名将作为下一交易日的目标组合。",
            f"结合当前持仓和资金，预计需要处理 {len(next_day_actions)} 笔委托。",
            f"盘中止损：{'已开启' if enable_intraday_stop else '未开启'}（比例 {intraday_stop_loss_pct * 100:.2f}%）。",
        ],
    }


STRATEGY = {
    'id': 'hs300_rotation',
    'name': '沪深300日频趋势轮动',
    'description': '在沪深300中按动量、均线结构、RSI 和 MACD 综合打分，收盘后选股，下一交易日开盘前委托。',
    'rules': [
        '仅在沪深300成分股中选股，剔除 ST、退市风险和上市时间过短的股票。',
        '要求收盘价站上 MA20、MA20 高于 MA60、20日涨幅为正、MACD 柱线为正。',
        '按动量、趋势结构、RSI 区间和 MACD 动能打分，优先持有综合得分最高的股票。',
        '已有持仓若仍处于较优排名则继续持有，否则在下一交易日开盘前计划卖出。',
    ],
    'param_schema': [
        {'key': 'enable_market_risk_control', 'label': '启用市场风控', 'type': 'boolean', 'default': False},
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
        {'key': 'buy_limit_buffer', 'label': '买入挂单上浮', 'type': 'number', 'default': 0.01, 'min': 0.0, 'max': 0.05, 'step': 0.005},
        {'key': 'sell_limit_buffer', 'label': '卖出挂单下浮', 'type': 'number', 'default': 0.01, 'min': 0.0, 'max': 0.05, 'step': 0.005},
    ],
    'runner': run_backtest,
    'planner': build_plan,
}
