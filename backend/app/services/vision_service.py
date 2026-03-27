"""
vision_service.py
封装 Qwen-VL-Max 视觉模型的异步 HTTP 调用。
"""

import base64
import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _encode_image(image_bytes: bytes) -> str:
    """将图片字节编码为 base64 字符串。"""
    return base64.b64encode(image_bytes).decode("utf-8")


async def call_vision_model(image_bytes: bytes, prompt: str) -> str:
    """
    将一张图片和文本提示发送给 Qwen-VL-Max，返回模型的文本输出。

    Args:
        image_bytes: PNG/JPEG 格式的图片字节数据。
        prompt: 发送给视觉模型的文本提示。

    Returns:
        模型返回的文本字符串。

    Raises:
        RuntimeError: API Key 未配置或 HTTP 请求失败时抛出。
    """
    if not settings.QWEN_VL_API_KEY:
        raise RuntimeError("QWEN_VL_API_KEY 未配置，请在 .env 文件中设置。")

    b64_image = _encode_image(image_bytes)

    payload = {
        "model": settings.QWEN_VL_MODEL,
        "messages": [
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
    }

    headers = {
        "Authorization": f"Bearer {settings.QWEN_VL_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            settings.QWEN_VL_API_URL,
            json=payload,
            headers=headers,
        )

    if response.status_code != 200:
        logger.error(
            "Qwen-VL-Max API 错误: status=%d, body=%s",
            response.status_code,
            response.text[:500],
        )
        raise RuntimeError(
            f"Qwen-VL-Max API 返回错误 {response.status_code}: {response.text[:200]}"
        )

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"解析 Qwen-VL-Max 响应失败: {data}") from exc

    return content
