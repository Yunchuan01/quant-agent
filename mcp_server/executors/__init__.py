"""执行器统一注册中心.

大白话：所有工具函数都集中在这里，形成一个"函数字典"。
key 是工具名（比如 "rsi"），value 是对应的 Python 函数。
调用 execute_tool("rsi", data=xxx, column="close", window=14)
就能执行 RSI 计算。
"""

import polars as pl
from typing import Any, Callable

# 导入各个执行器模块里的函数
from .math_tools import (
    abs_value,
    log_transform,
    sqrt_transform,
    power_transform,
    rank_normalize,
    zscore_normalize,
)
from .time_series_tools import (
    rolling_mean,
    pct_change,
    rolling_std,
    rolling_max,
    rolling_min,
    ewm,
)
from .technical_tools import (
    rsi,
    macd,
    kdj,
)

# 工具函数注册表 - 工具名 → 函数 的映射
TOOL_FUNCTIONS: dict[str, Callable[..., pl.Series | pl.DataFrame]] = {
    # Math 数学变换
    "abs_value": abs_value,
    "log_transform": log_transform,
    "sqrt_transform": sqrt_transform,
    "power_transform": power_transform,
    "rank_normalize": rank_normalize,
    "zscore_normalize": zscore_normalize,
    
    # Time Series 时间序列
    "rolling_mean": rolling_mean,
    "pct_change": pct_change,
    "rolling_std": rolling_std,
    "rolling_max": rolling_max,
    "rolling_min": rolling_min,
    "ewm": ewm,
    
    # Technical 技术指标
    "rsi": rsi,
    "macd": macd,
    "kdj": kdj,
}


def execute_tool(tool_name: str, **kwargs) -> pl.Series | pl.DataFrame:
    """执行指定工具.
    
    大白话：传入工具名和参数，从字典里找到对应的函数，然后调用它。
    比如 execute_tool("rsi", data=df, column="close", window=14)
    就会调用 rsi(df, column="close", window=14)，返回 RSI 计算结果。
    
    Args:
        tool_name: 工具名称（如 "rsi", "macd"）
        **kwargs: 工具参数（必须包含 data）
        
    Returns:
        计算结果 Series 或 DataFrame
    """
    if tool_name not in TOOL_FUNCTIONS:
        available = list(TOOL_FUNCTIONS.keys())
        raise ValueError(f"Unknown tool: {tool_name}. Available: {available}")
    
    if 'data' not in kwargs:
        raise ValueError(f"Tool '{tool_name}' requires 'data' parameter")
    
    try:
        func = TOOL_FUNCTIONS[tool_name]
        return func(**kwargs)
    except ValueError:
        raise
    except Exception as e:
        raise Exception(f"Tool '{tool_name}' failed: {e}") from e


def get_available_tools() -> list[str]:
    """获取所有可用工具列表."""
    return list(TOOL_FUNCTIONS.keys())