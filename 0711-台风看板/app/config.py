"""全局配置：数据源、刷新周期、服务端口等。"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
STATIC_DIR = PROJECT_ROOT / "static"

# 数据源：浙江省水利厅台风路径 API
API_BASE = "https://typhoon.slt.zj.gov.cn/Api"

# 目标台风：巴威 BAVI（2026年第9号台风）
TARGET_TFID = "202609"
TARGET_ENNAME = "BAVI"

# 数据刷新周期（秒）—— 每 1 分钟更新一次最新台风数据
REFRESH_INTERVAL_SECONDS = 60

# HTTP 请求超时（秒）
HTTP_TIMEOUT_SECONDS = 20

# 服务监听
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8710
