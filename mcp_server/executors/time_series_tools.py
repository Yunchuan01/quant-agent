"""Time Series 工具执行器 - 时间序列类工具.

大白话：这些工具都是"向后看"的计算。
比如 rolling_mean 是看过去 window 天的平均值，
pct_change 是看跟之前 periods 天相比涨了多少。
"""

import polars as pl
from mcp_server.auto_register import tool_registry


@tool_registry.register(
    description="计算移动平均线（MA）。用于平滑价格数据，识别趋势方向。",
    category="time_series"
)
def rolling_mean(data: pl.DataFrame, column: str = "close", window: int = 5) -> pl.Series:
    """移动平均.
    
    大白话：看过去 window 天的平均值。比如 window=5 就是 5 日均线（MA5）。
    作用是"抹平"短期波动，让你看到长期趋势方向。
    """
    result = (
        data
        .sort(["ts_code", "trade_date"])  # 先按股票代码和日期排序
        .with_columns(
            pl.col(column)
            .rolling_mean(window_size=window, min_periods=1)  # 滑动窗口计算平均
            .over("ts_code")  # 对每只股票单独算（不能把不同股票的数据混在一起）
            .alias(f"{column}_ma{window}")
        )
    )
    return result[f"{column}_ma{window}"]


@tool_registry.register(
    description="计算百分比变化（收益率）。用于衡量价格变动幅度。",
    category="time_series"
)
def pct_change(data: pl.DataFrame, column: str = "close", periods: int = 1) -> pl.Series:
    """百分比变化.
    
    大白话：今天的价格比 periods 天前涨了多少百分比。
    比如 pct_change(column="close", periods=5) 就是 5 日涨幅。
    返回的是 (今天价格 - 5天前价格) / 5天前价格
    """
    result = (
        data
        .sort(["ts_code", "trade_date"])
        .with_columns(
            (pl.col(column) / pl.col(column).shift(periods) - 1)  # shift(periods) 就是取 periods 天前的值
            .over("ts_code")
            .alias(f"{column}_pct{periods}")
        )
    )
    return result[f"{column}_pct{periods}"]


@tool_registry.register(
    description="计算滚动标准差（波动率）。用于衡量价格波动程度，值越大表示波动越剧烈。",
    category="time_series"
)
def rolling_std(data: pl.DataFrame, column: str = "close", window: int = 20) -> pl.Series:
    """移动标准差.
    
    大白话：看过去 window 天的价格波动有多"分散"。
    标准差大 → 价格忽高忽低，风险大
    标准差小 → 价格稳定，风险小
    """
    result = (
        data
        .sort(["ts_code", "trade_date"])
        .with_columns(
            pl.col(column)
            .rolling_std(window_size=window, min_periods=1)
            .over("ts_code")
            .alias(f"{column}_std{window}")
        )
    )
    return result[f"{column}_std{window}"]


@tool_registry.register(
    description="计算滚动最大值。用于识别近期高点、阻力位。",
    category="time_series"
)
def rolling_max(data: pl.DataFrame, column: str = "high", window: int = 20) -> pl.Series:
    """移动最大值.
    
    大白话：过去 window 天里最高的价格是多少？
    这就是"阻力位"——价格很难超过这个高点。
    """
    result = (
        data
        .sort(["ts_code", "trade_date"])
        .with_columns(
            pl.col(column)
            .rolling_max(window_size=window, min_periods=1)
            .over("ts_code")
            .alias(f"{column}_max{window}")
        )
    )
    return result[f"{column}_max{window}"]


@tool_registry.register(
    description="计算滚动最小值。用于识别近期低点、支撑位。",
    category="time_series"
)
def rolling_min(data: pl.DataFrame, column: str = "low", window: int = 20) -> pl.Series:
    """移动最小值.
    
    大白话：过去 window 天里最低的价格是多少？
    这就是"支撑位"——价格很难跌破这个低点。
    """
    result = (
        data
        .sort(["ts_code", "trade_date"])
        .with_columns(
            pl.col(column)
            .rolling_min(window_size=window, min_periods=1)
            .over("ts_code")
            .alias(f"{column}_min{window}")
        )
    )
    return result[f"{column}_min{window}"]


@tool_registry.register(
    description="计算指数加权移动平均（EMA）。对近期数据赋予更高权重，反应更灵敏。",
    category="time_series"
)
def ewm(data: pl.DataFrame, column: str = "close", span: int = 12) -> pl.Series:
    """指数加权移动平均.
    
    大白话：和普通移动平均类似，但"越近的数据权重越大"。
    比如 12 日 EMA，最近 1 天的权重远大于 12 天前的。
    所以 EMA 比 MA 更"灵敏"，能更快捕捉趋势变化。
    """
    return data[column].ewm_mean(span=span, adjust=True)