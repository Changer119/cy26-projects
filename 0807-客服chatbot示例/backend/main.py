"""服务入口。实际启动请使用项目根 scripts/start-backend.sh。"""
from app.server import create_app

app = create_app()
