"""命名空间构建器 - 管理工具计算的中间变量."""

import re


class NamespaceBuilder:
    """命名空间构建器 - 把数据列名变成变量名，让表达式能直接引用."""

    @staticmethod
    def build_namespace(data) -> dict:
        """从数据构建初始命名空间.

        大白话：把 DataFrame 里的每一列都变成一个变量。
        比如数据里有 close 列，构建后 namespace["close"] = 数据的收盘价序列。
        这样表达式里写 close > 10 就能直接计算了。
        """
        namespace = {}
        for col in data.columns:
            namespace[col] = data[col]  # 把列名和列数据绑定
        return namespace

    @staticmethod
    def extract_variables(expression: str) -> set[str]:
        """从表达式中提取变量名.

        大白话：比如表达式是 "rsi_14 < 30 and pct_change_5 > 0.05"，
        提取出 {rsi_14, pct_change_5} 这两个变量名。
        后续会检查这些变量是否在命名空间里有对应的值。
        """
        # 用正则找出所有"标识符"（变量名、函数名等）
        identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', expression)

        # 排除 Python 关键字（True、False、and、or 等）和内置函数（abs、max 等）
        keywords = {
            'True', 'False', 'None', 'and', 'or', 'not', 'if', 'else',
            'for', 'while', 'in', 'is', 'lambda', 'def', 'class', 'return'
        }
        builtins = {'abs', 'max', 'min', 'sum', 'len', 'int', 'float', 'str'}

        return set(identifiers) - keywords - builtins