"""筛选执行器 - 负责高效执行数据筛选逻辑."""

import logging
from typing import Any, Optional
import polars as pl

logger = logging.getLogger(__name__)


class ScreeningExecutor:
    """数据筛选执行器 - 组合预筛选和批量计算."""

    def __init__(self, data: pl.DataFrame, screening_date: Optional[str] = None):
        """初始化筛选器.

        Args:
            data: 市场数据 DataFrame，必须包含 ts_code（股票代码）、trade_date（交易日期）等列
            screening_date: 筛选日期（YYYYMMDD 格式），如果不传就用数据里最新的日期
        """
        self.data = data

        # 获取所有交易日期，排好序
        all_dates_pl = data.select(pl.col("trade_date").unique()).to_series().sort().to_list()

        if len(all_dates_pl) == 0:
            raise ValueError("数据中不包含任何交易日")

        # 如果没传 screening_date，就用数据里最后一天
        if screening_date is None:
            self.latest_date = all_dates_pl[-1]
        else:
            self.latest_date = screening_date
            # 确保数据里有这个日期，如果没有就往前找最近的一天
            available_dates = [d for d in all_dates_pl if d <= self.latest_date]
            if not available_dates:
                raise ValueError(f"数据中没有筛选日期 {screening_date} 及之前的数据")
            self.latest_date = available_dates[-1]

        # 提取所有股票代码
        self.all_stock_codes = data.select(pl.col("ts_code").unique()).to_series().to_list()

    def run_screening(
        self, screening_logic: dict, top_n: int = 20, query: str = ""
    ) -> list[dict[str, Any]]:
        """执行数据筛选.

        Args:
            screening_logic: 筛选逻辑配置（JSON 格式），包含 tools、expression、confidence_formula 等
            top_n: 返回前 N 只股票
            query: 原始查询文本（用于日志记录）

        Returns:
            筛选结果列表，每个元素是一个字典，包含 ts_code、confidence、metrics 等
        """
        # 第一步：过滤有效股票（数据量充足的）
        valid_stocks, valid_data = self._filter_valid_stocks(self.all_stock_codes)

        if not valid_stocks:
            logger.warning("无可用股票")
            return []

        # 第二步：调用批量计算器（Step 2 之后才实现，这里先用简单逻辑）
        # 简化版：直接用 expression 做 eval 筛选
        expression = screening_logic.get("expression", "")
        confidence_formula = screening_logic.get("confidence_formula", "1.0")
        rationale = screening_logic.get("rationale", "")

        # 构建命名空间（把数据列变成变量名）
        namespace = {}
        latest_data = valid_data.filter(pl.col("trade_date") == self.latest_date)
        for col in latest_data.columns:
            namespace[col] = latest_data[col]

        namespace["_stock_index"] = latest_data["ts_code"].to_list()

        # 评估筛选表达式
        matched_stocks = self._evaluate_expression(expression, namespace, valid_stocks)

        # 构建结果
        candidates = self._build_candidates(
            matched_stocks, confidence_formula, namespace, valid_data, rationale
        )

        # 按置信度排序，取 Top N
        results = sorted(candidates, key=lambda x: x["confidence"], reverse=True)[:top_n]
        return results

    def _filter_valid_stocks(self, stock_codes: list[str]) -> tuple[list[str], pl.DataFrame]:
        """过滤出有效股票（交易天数 >= 20 且有最新日期数据）."""
        subset_data = self.data.filter(pl.col("ts_code").is_in(stock_codes))

        if subset_data.is_empty():
            return [], subset_data

        # 每只股票至少有 20 天数据才算"有效"
        stock_day_counts = subset_data.group_by("ts_code").agg(
            pl.count().alias("day_count")
        )
        sufficient_stocks = stock_day_counts.filter(pl.col("day_count") >= 20)["ts_code"].to_list()

        # 还得有最新日期的数据
        latest_data = subset_data.filter(pl.col("trade_date") == self.latest_date)
        stocks_with_latest = set(latest_data["ts_code"].to_list())

        valid_stocks = [s for s in sufficient_stocks if s in stocks_with_latest]
        valid_data = subset_data.filter(pl.col("ts_code").is_in(valid_stocks))

        logger.info(f"数据过滤：{len(stock_codes)} -> {len(valid_stocks)} 只有效股票")
        return valid_stocks, valid_data

    def _evaluate_expression(
        self, expression: str, namespace: dict, valid_stocks: list[str]
    ) -> list[str]:
        """评估筛选表达式，返回匹配的股票代码列表."""
        if not expression or not expression.strip():
            return valid_stocks  # 没有表达式就返回全部

        try:
            result = eval(expression, {"__builtins__": {}}, namespace)
            if isinstance(result, pl.Series):
                # Series: 取出 True 对应的股票
                stock_index = namespace["_stock_index"]
                matched = [
                    code for code, is_match in zip(stock_index, result.to_list())
                    if is_match
                ]
                return matched
            elif isinstance(result, bool):
                return valid_stocks if result else []
            else:
                return valid_stocks
        except Exception as e:
            logger.error(f"表达式评估失败：{e}")
            return []

    def _build_candidates(
        self,
        matched_stocks: list[str],
        confidence_formula: str,
        namespace: dict,
        valid_data: pl.DataFrame,
        rationale: str,
    ) -> list[dict[str, Any]]:
        """构建候选结果列表."""
        if not matched_stocks:
            return []

        candidates = []
        for ts_code in matched_stocks:
            # 计算置信度（简化版：默认 0.5）
            confidence = 0.5
            try:
                conf_raw = eval(confidence_formula, {"__builtins__": {}}, namespace)
                if isinstance(conf_raw, (int, float)):
                    import math
                    confidence = 1.0 / (1.0 + math.exp(-conf_raw))  # sigmoid 转换
            except Exception:
                confidence = 0.5

            # 提取股票名称
            name = ts_code
            if "name" in valid_data.columns:
                try:
                    name_row = valid_data.filter(pl.col("ts_code") == ts_code)
                    if not name_row.is_empty():
                        name = str(name_row["name"][0])
                except Exception:
                    name = ts_code

            candidates.append({
                "ts_code": ts_code,
                "name": name,
                "confidence": confidence,
                "reason": rationale,
                "metrics": {},
            })

        return candidates