import logging
from app.core.config import settings

# 配置日志格式
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# 创建记录器
logger = logging.getLogger("app")
