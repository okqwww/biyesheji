"""
logging.py — 统一日志配置

日志文件（写入项目根目录 log/ 文件夹）：
  - log/app-YYYYMMDD.log   应用运行日志（等同于终端输出）
  - log/llm-YYYYMMDD.log   所有 LLM 调用的完整 Prompt + Response（不截断）

用法：
  from app.core.logging import logger      # 普通日志
  from app.core.logging import log_llm_call  # 记录一次 LLM 调用
"""

import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from app.core.config import settings

# ── 日志目录（项目根 / log/）──────────────────────────────────────────────────
_LOG_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "log")
)
os.makedirs(_LOG_DIR, exist_ok=True)

# ── 公共格式 ─────────────────────────────────────────────────────────────────
_FMT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

# ── 根 logger：控制台 + app 文件 ──────────────────────────────────────────────
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(logging.Formatter(_FMT, datefmt=_DATEFMT))

_app_file_handler = TimedRotatingFileHandler(
    filename=os.path.join(_LOG_DIR, "app.log"),
    when="midnight",
    backupCount=30,
    encoding="utf-8",
)
_app_file_handler.suffix = "%Y%m%d"
_app_file_handler.setFormatter(logging.Formatter(_FMT, datefmt=_DATEFMT))

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    handlers=[_console_handler, _app_file_handler],
)

# 主 logger（其他模块用 logging.getLogger(__name__) 自动继承根 logger 的 handler）
logger = logging.getLogger("app")

# ── LLM 专用 logger：只写 llm.log，不打印到控制台 ─────────────────────────────
_llm_file_handler = TimedRotatingFileHandler(
    filename=os.path.join(_LOG_DIR, "llm.log"),
    when="midnight",
    backupCount=30,
    encoding="utf-8",
)
_llm_file_handler.setFormatter(logging.Formatter("%(message)s"))  # 纯内容，无前缀

_llm_logger = logging.getLogger("llm_calls")
_llm_logger.setLevel(logging.DEBUG)
_llm_logger.addHandler(_llm_file_handler)
_llm_logger.propagate = False  # 不向上传递，避免混入 app.log / 控制台


# ── 公开接口 ──────────────────────────────────────────────────────────────────

def log_llm_call(
    model: str,
    prompt: str,
    response: str,
    *,
    tag: str = "",
    error: str = "",
) -> None:
    """
    记录一次 LLM 调用到 log/llm.log。

    Args:
        model:    模型名称，如 "deepseek-chat" / "qwen-vl-max"
        prompt:   发送给模型的完整 Prompt（不截断）
        response: 模型返回的完整文本（不截断）
        tag:      可选标注，如 "Agent2/slot_analyze"，方便搜索
        error:    若调用出错，传入错误信息
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sep = "=" * 80
    lines = [
        "",
        sep,
        f"[{ts}]  MODEL: {model}  TAG: {tag or '(none)'}",
        sep,
        ">>> PROMPT >>>",
        prompt,
        "",
        "<<< RESPONSE <<<",
        response if response else f"[ERROR: {error}]",
        sep,
    ]
    _llm_logger.debug("\n".join(lines))
