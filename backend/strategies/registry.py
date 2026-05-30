from typing import Any, Dict

from strategies.bollinger_reversion import STRATEGY as BOLLINGER_REVERSION_STRATEGY
from strategies.short_trend import STRATEGY as SHORT_TREND_STRATEGY


BACKTEST_STRATEGIES: Dict[str, Dict[str, Any]] = {
    SHORT_TREND_STRATEGY["id"]: SHORT_TREND_STRATEGY,
    BOLLINGER_REVERSION_STRATEGY["id"]: BOLLINGER_REVERSION_STRATEGY,
}

DEFAULT_STRATEGY_ID = SHORT_TREND_STRATEGY["id"]

PERIOD_OPTIONS = {
    "3m": 90,
    "6m": 180,
    "1y": 365,
    "2y": 730,
    "3y": 1095,
    "all": None,
}

PERIOD_OPTION_LIST = [
    {"id": "3m", "label": "近3个月"},
    {"id": "6m", "label": "近6个月"},
    {"id": "1y", "label": "近1年"},
    {"id": "2y", "label": "近2年"},
    {"id": "3y", "label": "近3年"},
    {"id": "all", "label": "全部数据"},
]


def get_strategy_defaults(strategy_id: str) -> Dict[str, Any]:
    strategy = BACKTEST_STRATEGIES[strategy_id]
    return {field["key"]: field["default"] for field in strategy["param_schema"]}


def build_strategy_meta(strategy_id: str) -> Dict[str, Any]:
    strategy = BACKTEST_STRATEGIES[strategy_id]
    return {
        "id": strategy["id"],
        "name": strategy["name"],
        "description": strategy["description"],
        "rules": strategy["rules"],
        "chart_overlays": strategy["chart_overlays"],
        "param_schema": strategy["param_schema"],
        "defaults": get_strategy_defaults(strategy_id),
    }
