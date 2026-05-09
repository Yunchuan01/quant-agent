"""Quant Agent MCP Server - 独立的 MCP 服务器.

基于 FastMCP 框架，提供量化工具服务。
可以直接运行: python -m mcp_server.server
"""

import argparse
import sys
from pathlib import Path

# 确保项目根目录在 Python 的搜索路径中
# 大白话：让 Python 能找到 src/screening 等其他包
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from mcp.server.fastmcp import FastMCP
from mcp_server.registered_tools import register_to_mcp


def create_server() -> FastMCP:
    """创建 MCP 服务器实例.
    
    大白话：就像开一家店，先建好店面（FastMCP实例），再把商品上架（register_to_mcp）。
    """
    server = FastMCP(name="quant_agent_mcp")
    
    # 注册所有工具到服务器
    register_to_mcp(server)
    
    return server


def main():
    """主入口函数.
    
    大白话：开店营业！支持两种模式：
    - stdio：通过命令行输入输出通信（Agent主进程像打电话一样跟它交流）
    - sse：通过网络端口通信（像开了一个网站，别人可以远程访问）
    """
    parser = argparse.ArgumentParser(description="Quant Agent MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="通信协议 (默认: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="主机地址 (SSE模式用)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="端口 (SSE模式用)",
    )
    
    args = parser.parse_args()
    
    server = create_server()
    
    if args.transport == "sse":
        print(f"Starting MCP server on {args.host}:{args.port} (SSE)")
        server.run(transport="sse", host=args.host, port=args.port)
    else:
        print("Starting MCP server (stdio)")
        server.run(transport="stdio")


if __name__ == "__main__":
    main()