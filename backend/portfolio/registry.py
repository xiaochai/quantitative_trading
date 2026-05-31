from __future__ import annotations

from typing import Any, Dict

from portfolio.strategies.hs300_rotation import STRATEGY as HS300_ROTATION_STRATEGY
from portfolio.strategies.hs300_rotation_enhanced import STRATEGY as HS300_ROTATION_ENHANCED_STRATEGY

PORTFOLIO_STRATEGIES: Dict[str, Dict[str, Any]] = {
    HS300_ROTATION_STRATEGY['id']: HS300_ROTATION_STRATEGY,
    HS300_ROTATION_ENHANCED_STRATEGY['id']: HS300_ROTATION_ENHANCED_STRATEGY,
}

DEFAULT_STRATEGY_ID = HS300_ROTATION_STRATEGY['id']
DEFAULT_UNIVERSE_ID = 'hs300'

UNIVERSE_OPTIONS = [
    {'id': 'hs300', 'label': '沪深300'},
    {'id': 'csi500', 'label': '中证500'},
]

PERIOD_OPTIONS = {
    '6m': 180,
    '1y': 365,
    '2y': 730,
    '3y': 1095,
    'custom': 0,
}

PERIOD_OPTION_LIST = [
    {'id': '6m', 'label': '近6个月'},
    {'id': '1y', 'label': '近1年'},
    {'id': '2y', 'label': '近2年'},
    {'id': '3y', 'label': '近3年'},
    {'id': 'custom', 'label': '自定义区间'},
]


def get_strategy_defaults(strategy_id: str) -> Dict[str, Any]:
    strategy = PORTFOLIO_STRATEGIES[strategy_id]
    return {field['key']: field['default'] for field in strategy['param_schema']}


def build_strategy_meta(strategy_id: str) -> Dict[str, Any]:
    strategy = PORTFOLIO_STRATEGIES[strategy_id]
    return {
        'id': strategy['id'],
        'name': strategy['name'],
        'description': strategy['description'],
        'rules': strategy['rules'],
        'param_schema': strategy['param_schema'],
        'defaults': get_strategy_defaults(strategy_id),
    }
