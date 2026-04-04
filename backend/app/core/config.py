from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


class Settings(BaseSettings):
    """应用配置"""
    # Neo4j配置
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")
    
    # API配置
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_PREFIX: str = os.getenv("API_PREFIX", "/api")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # 大模型API配置
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_API_URL: str = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # Agent 4 专用：httpx 直连 DeepSeek 官方（与全局 OpenAI SDK 通道分离，便于其它 Agent 仍走 MiniMax 等）
    AGENT4_LLM_BASE_URL: str = os.getenv("AGENT4_LLM_BASE_URL", "https://api.deepseek.com/v1")
    AGENT4_LLM_API_KEY: Optional[str] = os.getenv("AGENT4_LLM_API_KEY")
    AGENT4_LLM_MODEL: str = os.getenv("AGENT4_LLM_MODEL", "deepseek-chat")

    # 视觉模型API配置（通义千问 Qwen-VL-Max）
    QWEN_VL_API_KEY: Optional[str] = os.getenv("QWEN_VL_API_KEY")
    QWEN_VL_API_URL: str = os.getenv("QWEN_VL_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
    QWEN_VL_MODEL: str = os.getenv("QWEN_VL_MODEL", "qwen-vl-max")

    # 上传文件存储目录
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"


# 全局设置实例
settings = Settings()
