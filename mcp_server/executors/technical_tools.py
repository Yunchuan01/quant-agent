"""Technical 工具执行器 - 技术指标类工具.

大白话：RSI、MACD、KDJ 这些指标是"看图派"（技术分析）最常用的工具。
它们通过数学公式把原始价格数据转换成一个"信号值"，
帮人判断该不该买/卖。
"""

import polars as pl
from mcp_server.auto_register import tool_registry


@tool_registry.register(
    description="相对强弱指标 RSI。衡量价格变动速度和幅度，0-100之间。>70 超买，<30 超卖。",
    category="technical"
)
def rsi(data: pl.DataFrame, column: str = "close", window: int = 14) -> pl.Series:
    """相对强弱指标 RSI.
    
    大白话：RSI 是一个 0~100 的数字：
    - RSI > 70 → 最近涨太多了（超买），可能要回调
    - RSI < 30 → 最近跌太多了（超卖），可能要反弹
    - RSI 在 30~70 → 正常波动
    
    计算步骤：
    1. 算出每天的涨跌幅（diff）
    2. 把涨的单独取出来求平均（gain），把跌的单独取出来求平均（loss）
    3. RS = gain / loss（涨的力量 / 跌的力量）
    4. RSI = 100 - 100/(1+RS)
    """
    delta = data[column].diff()
    gain = delta.clip(lower_bound=0).rolling_mean(window_size=window)
    loss = (-delta.clip(upper_bound=0)).rolling_mean(window_size=window)
    # 防止除以 0：把 0 替换成极小值
    rs = gain / loss.replace(0, None).fill_null(1e-10)
    return 100 - (100 / (1 + rs))


@tool_registry.register(
    description="MACD 指标。趋势跟踪动量指标，显示两条移动平均线的关系。",
    category="technical"
)
def macd(
    data: pl.DataFrame,
    column: str = "close",
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> pl.Series:
    """MACD 指标.
    
    大白话：MACD 由三部分组成：
    - MACD 线 = 快线EMA(12) - 慢线EMA(26)  → 看短期和长期趋势的差异
    - 信号线 = MACD 线的 EMA(9)             → MACD 线本身的平滑版
    - MACD 柱 = MACD 线 - 信号线            → 柱状图的高度
    
    本函数返回的是 MACD 柱（MACD Histogram）。
    MACD 柱 > 0 → 上涨力量在增强
    MACD 柱 < 0 → 下跌力量在增强
    MACD 柱从负变正 → "金叉"，可能是买入信号
    MACD 柱从正变负 → "死叉"，可能是卖出信号
    """
    ema_fast = data[column].ewm_mean(span=fast)
    ema_slow = data[column].ewm_mean(span=slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm_mean(span=signal)
    return macd_line - signal_line


@tool_registry.register(
    description="KDJ 随机指标。用于判断超买超卖状态和趋势反转。",
    category="technical"
)
def kdj(
    data: pl.DataFrame,
    high: str = "high",
    low: str = "low",
    close: str = "close",
    window: int = 9
) -> pl.Series:
    """KDJ 随机指标.
    
    大白话：KDJ 也是看超买超卖的：
    - J 值 > 100 → 超买，可能要跌
    - J 值 < 0 → 超卖，可能要涨
    
    计算步骤：
    1. RSV = (今天收盘价 - window天最低价) / (window天最高价 - window天最低价)
       → "今天的价格在近期区间里处于什么位置"
    2. K = RSV 的 EMA（平滑版）
    3. D = K 的 EMA（再平滑一次）
    4. J = 3K - 2D（更灵敏的版本）
    
    本函数返回 J 值。
    """
    lowest_low = data[low].rolling_min(window_size=window)
    highest_high = data[high].rolling_max(window_size=window)
    rsv = (data[close] - lowest_low) / (highest_high - lowest_low).replace(0, None).fill_null(1e-10) * 100
    k = rsv.ewm_mean(com=2)
    d = k.ewm_mean(com=2)
    j = 3 * k - 2 * d
    return j