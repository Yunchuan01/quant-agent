"""自动注册装饰器 - 简化工具注册流程.

使用方式:
    @tool_registry.register(description="工具描述", category="math")
    def my_tool(column: str, window: int = 5) -> str:
        return "计算结果"

装饰器会自动：
1. 提取函数参数 → 生成 JSON Schema（告诉 Agent 这个工具需要什么参数）
2. 创建 Pydantic 验证器 → 自动校验参数类型和必填项
3. 把函数存进注册表 → 后面一键全部注册到 MCP 服务器
"""

import inspect
from typing import Any, Callable
from pydantic import BaseModel, create_model, Field


class ToolRegistry:
    """工具注册器 - 管理所有工具的定义和函数."""
    
    def __init__(self):
        self._tools: dict[str, dict[str, Any]] = {}       # 工具定义（名称、参数、描述）
        self._functions: dict[str, Callable] = {}          # 工具函数本体
        self._validators: dict[str, type[BaseModel]] = {}  # Pydantic 参数验证器
    
    def register(
        self,
        description: str,
        category: str,
        name: str | None = None
    ) -> Callable:
        """注册工具的装饰器.
        
        大白话：你在函数上面写 @tool_registry.register(description="xxx", category="yyy")，
        装饰器就会自动把函数"登记"到注册表里。
        - description: 工具的功能描述，Agent 看到这个描述就知道该不该用这个工具
        - category: 分类标签（math/technical/time_series 等）
        - name: 工具名称，如果不传就用函数名
        """
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            
            # 从函数签名提取参数信息
            # 大白话：inspect.signature(func) 就像看函数的"身份证"，获取参数名、类型、默认值
            sig = inspect.signature(func)
            properties = {}
            required = []
            
            for param_name, param in sig.parameters.items():
                # 跳过 self 和 data（data 是运行时自动注入的，不是 Agent 需要传的）
                if param_name in ('self', 'data'):
                    continue
                
                param_info = {"description": param_name}
                
                # 推断参数类型
                # 大白话：把 Python 的类型标注翻译成 JSON Schema 类型
                if param.annotation != inspect.Parameter.empty:
                    type_map = {
                        str: "string",
                        int: "integer",
                        float: "number",
                        bool: "boolean",
                    }
                    param_info["type"] = type_map.get(param.annotation, "string")
                
                # 检查是否有默认值
                if param.default != inspect.Parameter.empty:
                    param_info["default"] = param.default
                else:
                    required.append(param_name)  # 没有默认值的参数就是必填的
                
                properties[param_name] = param_info
            
            # 构建工具定义（这就是 Agent 看到的工具描述）
            self._tools[tool_name] = {
                "category": category,
                "description": description,
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
            
            # 保存函数本体
            self._functions[tool_name] = func
            
            # 动态创建 Pydantic 验证器
            # 大白话：根据参数信息自动生成一个数据校验类
            # 比如 rsi(column: str, window: int=14) 会生成一个 RsiParams 类，
            # 传入 {"column": "close", "window": 14} 时自动校验类型和必填项
            field_definitions = {}
            for param_name, param in sig.parameters.items():
                if param_name in ('self', 'data', 'stock_data', 'index_data'):
                    continue
                
                field_type = param.annotation if param.annotation != inspect.Parameter.empty else Any
                type_str = str(field_type)
                if 'DataFrame' in type_str or 'Series' in type_str:
                    field_type = Any  # DataFrame 等复杂类型用 Any 代替
                
                if param.default != inspect.Parameter.empty:
                    field_definitions[param_name] = (field_type, Field(default=param.default))
                else:
                    field_definitions[param_name] = (field_type, Field(...))  # ... 表示必填
            
            validator_class = create_model(
                f"{tool_name.capitalize()}Params",
                **field_definitions
            )
            self._validators[tool_name] = validator_class
            
            return func  # 装饰器不改变函数本身，只是"登记"了它
        
        return decorator
    
    def get_tool_definitions(self) -> dict[str, dict[str, Any]]:
        """获取所有工具定义."""
        return self._tools.copy()
    
    def get_all_functions(self) -> dict[str, Callable]:
        """获取所有工具函数."""
        return self._functions.copy()
    
    def register_to_mcp(self, mcp_instance: Any) -> None:
        """将所有工具注册到 FastMCP 实例.
        
        大白话：遍历注册表里的每个工具，给 MCP 服务器创建一个"包装函数"，
        然后用 mcp_instance.tool() 注册上去。
        Agent 调用工具时，MCP 服务器就会执行这个包装函数。
        """
        for tool_name, definition in self._tools.items():
            description = definition.get("description", "")
            
            def create_wrapper(name: str, desc: str):
                async def wrapper(**kwargs):
                    try:
                        from mcp_server.executors import execute_tool
                        
                        if 'data' not in kwargs:
                            return f"Tool '{name}' requires data context. Use via ExpressionEvaluator."
                        result = execute_tool(name, **kwargs)
                        return str(result)
                    except Exception as e:
                        return f"Error: {e}"
                
                wrapper.__name__ = name
                wrapper.__doc__ = desc
                return wrapper
            
            wrapper = create_wrapper(tool_name, description)
            
            try:
                mcp_instance.tool(
                    name=tool_name,
                    description=description,
                )(wrapper)
            except Exception as e:
                print(f"Warning: Failed to register tool '{tool_name}': {e}")


# 全局注册器实例 - 所有工具都注册到这里
tool_registry = ToolRegistry()

# # 2. 用装饰器 @ 注册你的第一个工具！
# @tool_registry.register(
#     description="两个数字相加",  # 给AI看的说明
#     category="数学计算"         # 分类
# )
# def add(a: int, b: int = 10):
#     """计算 a + b"""
#     return a + b


# # 3. 注册第二个工具
# @tool_registry.register(
#     description="计算数字平方",
#     category="数学计算"
# )
# def square(num: int):
#     return num * num


# # ------------------- 测试：看看注册成功了吗 -------------------
# if __name__ == "__main__":
#     # 看看注册了哪些工具
#     tools = tool_registry.get_tool_definitions()
#     print("=== 已注册的所有工具 ===")
#     for name, info in tools.items():
#         print(f"\n工具名: {name}")
#         print(f"描述: {info['description']}")
#         print(f"参数: {info['inputSchema']}")

#     # 直接调用函数（正常用）
#     print("\n=== 直接运行工具 ===")
#     print("add(2,3) =", add(2, 3))
#     print("square(5) =", square(5))