"""入口：启动台风大屏服务。"""

import uvicorn

from app.config import SERVER_HOST, SERVER_PORT
from app.server import app

if __name__ == "__main__":
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, log_level="info")
