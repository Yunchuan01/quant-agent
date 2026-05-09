"""表达式评估器 - 负责向量化评估筛选表达式和置信度."""

import math
import numpy as np
import polars as pl
import logging

from src.screening.namespace_builder import NamespaceBuilder

logger = logging.getLogger(__name__)


class ExpressionEvaluator:
    """表达式评估器 - 判断股票是否符合条件 + 计算置信度."""

    @staticmethod
    def evaluate_expression(
        expression: str,
        expression_vars: set[str],
        namespace: dict,
        valid_stocks: list[str],
    ) -> tuple[list[str], dict[str, int]]:
        """评估筛选表达式，返回匹配的股票和统计信息.

        大白话：把表达式当成一道判断题，对每只股票算一遍。
        比如 rsi_14 < 30，就是对所有股票检查"它的14日RSI是否小于30"。
        算出来 True 的股票留下，False 的淘汰。
        """
        stats = {"false_count": 0, "nan_count": 0, "eval_error_count": 0}
        stock_index = namespace.get("_stock_index", valid_stocks)

        # 没有表达式就返回全部
        if not expression or not expression.strip():
            return valid_stocks, stats

        # 确保表达式里的每个变量在 namespace 里有值
        for var in expression_vars:
            if var not in namespace:
                # 没有? 那就填一个全 NaN 的序列，代表"不知道"
                namespace[var] = pl.Series([np.nan] * len(stock_index))

        try:
            # eval() 就是"把字符串当成 Python 代码执行"
            # 比如 "rsi_14 < 30" 会变成一个布尔序列 [True, False, True, ...]
            result = eval(expression, {"__builtins__": {}}, namespace)

            if isinstance(result, pl.Series):
                # 把结果转成 True/False
                match_bool = result.fill_null(False).cast(pl.Boolean)
                stats["false_count"] = int((~match_bool).sum())
                matched_mask = match_bool.to_list()
                matched_stocks = [
                    code for code, is_match in zip(stock_index, matched_mask)
                    if is_match
                ]
            elif isinstance(result, bool):
                matched_stocks = valid_stocks if result else []
            else:
                matched_stocks = valid_stocks

        except Exception as e:
            stats["eval_error_count"] = 1
            logger.error(f"表达式评估失败：{e}")
            matched_stocks = []

        return matched_stocks, stats

    @staticmethod
    def calculate_confidence(
        confidence_formula: str,
        namespace: dict,
        valid_stocks: list[str],
    ) -> list[float]:
        """计算置信度 - 给每只股票打一个 0~1 的分数.

        大白话：置信度就像"这道筛选有多可靠"。
        用 sigmoid 函数（S型曲线）把原始分数转换到 0~1 之间。
        公式：confidence = 1 / (1 + e^(-x))
        x 越大，confidence 越接近 1（非常可靠）
        x 越小，confidence 越接近 0（不太可靠）
        x = 0 时，confidence = 0.5（半信半疑）
        """
        # 简化版：如果公式就是常数，直接返回
        try:
            conf_raw = eval(confidence_formula, {"__builtins__": {}}, namespace)
            if isinstance(conf_raw, (int, float)):
                return [1.0 / (1.0 + math.exp(-float(conf_raw)))] * len(valid_stocks)
            elif isinstance(conf_raw, pl.Series):
                return (1.0 / (1.0 + np.exp(-conf_raw.to_numpy()))).tolist()
        except Exception:
            pass

        # 默认返回 0.5（半信半疑）
        return [0.5] * len(valid_stocks)