"""MCP 工具注册层 - 统一管理所有工具的注册.

大白话：这个文件就像一个"总仓库清单"。
1. 先导入各个工具模块（触发装饰器，把工具登记到注册表）
2. 然后提供 register_to_mcp 函数，一键把所有工具上架到 MCP 服务器
"""

from typing import Any
from mcp_server.auto_register import tool_registry

# 导入所有工具模块，触发装饰器注册
# 大白话：import 这行代码执行时，Python 会运行模块里的代码，
# 那些 @tool_registry.register 装饰器就会被执行，工具就自动登记了
import mcp_server.executors.math_tools       # 数学变换工具
import mcp_server.executors.time_series_tools # 时间序列工具
import mcp_server.executors.technical_tools   # 技术指标工具


def get_all_tools() -> dict[str, Any]:
    """获取所有已注册的工具定义."""
    return tool_registry.get_tool_definitions()


def register_to_mcp(mcp_instance: Any) -> None:
    """将所有工具注册到 FastMCP 实例."""
    tool_registry.register_to_mcp(mcp_instance)