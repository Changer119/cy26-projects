"""项目入口：默认启动 CLI。HTTP / MCP 请使用 scripts/ 下的脚本启动。"""

from weather.adapters.cli import app

if __name__ == "__main__":
    app()
