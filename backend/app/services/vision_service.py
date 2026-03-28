"""
vision_service.py
封装视觉模型的异步调用（通过 NewAPI 中台，使用 OpenAI SDK）。
"""

import base64
import logging

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import log_llm_call

logger = logging.getLogger(__name__)


def _encode_image(image_bytes: bytes) -> str:
    """将图片字节编码为 base64 字符串。"""
    return base64.b64encode(image_bytes).decode("utf-8")


def _make_client() -> AsyncOpenAI:
    """创建 AsyncOpenAI 客户端，指向 NewAPI 中台。"""
    if not settings.QWEN_VL_API_KEY:
        raise RuntimeError("QWEN_VL_API_KEY 未配置，请在 .env 文件中设置。")
    return AsyncOpenAI(
        api_key=settings.QWEN_VL_API_KEY,
        base_url=settings.QWEN_VL_API_URL,
    )


async def call_vision_model(image_bytes: bytes, prompt: str) -> str:
    """
    将一张图片和文本提示发送给视觉模型，返回模型的文本输出。

    Args:
        image_bytes: PNG/JPEG 格式的图片字节数据。
        prompt: 发送给视觉模型的文本提示。

    Returns:
        模型返回的文本字符串。

    Raises:
        RuntimeError: API Key 未配置或调用失败时抛出。
    """
    b64_image = _encode_image(image_bytes)
    client = _make_client()

    try:
        response = await client.chat.completions.create(
            model=settings.QWEN_VL_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_image}"
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
            max_tokens=8192,
        )
    except Exception as exc:
        err_msg = str(exc)
        logger.error("视觉模型 API 调用失败: %s", err_msg)
        log_llm_call(
            model=settings.QWEN_VL_MODEL,
            prompt=prompt,
            response="",
            tag="Agent1/vision_parse",
            error=err_msg,
        )
        raise RuntimeError(f"视觉模型 API 调用失败: {err_msg}") from exc

    content = response.choices[0].message.content or ""
    log_llm_call(
        model=settings.QWEN_VL_MODEL,
        prompt=prompt,
        response=content,
        tag="Agent1/vision_parse",
    )
    return content
