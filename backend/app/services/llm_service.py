import json
import httpx
from typing import Dict, Any, Optional
from openai import AsyncOpenAI, APIError, APIConnectionError, APITimeoutError
from app.core.config import settings
from app.core.logging import logger, log_llm_call


def _make_llm_client() -> AsyncOpenAI:
    if not settings.DEEPSEEK_API_KEY:
        raise RuntimeError("未配置大模型 API 密钥，请在 .env 中设置 DEEPSEEK_API_KEY。")
    return AsyncOpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_API_URL,
        timeout=300.0,  # 思考模型单次响应可能超过 2 分钟
        max_retries=0,  # 禁用 SDK 内部重试，由外层 call_deepseek_api 统一管理
        http_client=httpx.AsyncClient(trust_env=False),  # 不读系统/环境代理，直连 API
    )


class LLMService:
    """大模型服务（OpenAI SDK 兼容接口）"""

    @staticmethod
    async def call_deepseek_api(
        prompt: str,
        max_retries: int = 3,
        tag: str = "",
    ) -> Optional[Dict[str, Any]]:
        """调用大模型 API，返回原始 response dict（兼容 OpenAI 格式）"""
        import asyncio
        import random

        client = _make_llm_client()
        last_error: Optional[str] = None

        for attempt in range(max_retries + 1):
            try:
                response = await client.chat.completions.create(
                    model=settings.DEEPSEEK_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    # max_tokens=32768,
                    max_tokens=8192,
                )
                raw_text = response.choices[0].message.content or ""
                log_llm_call(
                    model=settings.DEEPSEEK_MODEL,
                    prompt=prompt,
                    response=raw_text,
                    tag=tag,
                )
                # 返回与原 httpx 版本相同结构的 dict，下游代码无需改动
                return {
                    "choices": [
                        {"message": {"content": raw_text}}
                    ]
                }

            except (APIConnectionError, APITimeoutError) as e:
                last_error = f"连接/超时错误: {e}"
                logger.warning("大模型 API 连接异常 (%s)，准备重试...", last_error)
                log_llm_call(model=settings.DEEPSEEK_MODEL, prompt=prompt,
                             response="", tag=tag, error=last_error)

            except APIError as e:
                last_error = f"API 错误 HTTP {e.status_code}: {e.message}"
                logger.error("大模型 API 调用失败: %s", last_error)
                log_llm_call(model=settings.DEEPSEEK_MODEL, prompt=prompt,
                             response="", tag=tag, error=last_error)

            except Exception as e:
                last_error = str(e)
                logger.error("大模型 API 调用异常: %s", last_error)
                logger.exception(e)
                log_llm_call(model=settings.DEEPSEEK_MODEL, prompt=prompt,
                             response="", tag=tag, error=last_error)

            if attempt < max_retries:
                wait = min(2 ** (attempt + 1), 30) * random.uniform(0.5, 1.5)
                logger.info("第%d次重试（最多%d次），等待 %.1f 秒...", attempt + 1, max_retries, wait)
                await asyncio.sleep(wait)

        logger.error("大模型 API 重试 %d 次后仍失败，最后错误: %s", max_retries, last_error)
        return None

    @staticmethod
    async def call_agent4_deepseek_httpx(
        prompt: str,
        max_retries: int = 3,
        tag: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Agent 4 专用：使用 httpx POST 调用 DeepSeek 官方兼容接口（非 OpenAI SDK）。
        配置见 AGENT4_LLM_*；API Key 优先 AGENT4_LLM_API_KEY，否则回落 DEEPSEEK_API_KEY。
        """
        import asyncio
        import random

        base = settings.AGENT4_LLM_BASE_URL.rstrip("/")
        url = f"{base}/chat/completions"
        api_key = settings.AGENT4_LLM_API_KEY or settings.DEEPSEEK_API_KEY
        model = settings.AGENT4_LLM_MODEL
        if not api_key:
            logger.error("Agent4 httpx：未配置 AGENT4_LLM_API_KEY 或 DEEPSEEK_API_KEY")
            return None

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 8192,
        }
        last_error: Optional[str] = None

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=300.0, trust_env=False) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()

                raw_text = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    or ""
                )
                log_llm_call(
                    model=model,
                    prompt=prompt,
                    response=raw_text,
                    tag=tag,
                )
                return {
                    "choices": [{"message": {"content": raw_text}}],
                }

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
                logger.warning("Agent4 httpx HTTP 错误 (%s)，准备重试...", last_error)
                log_llm_call(model=model, prompt=prompt, response="", tag=tag, error=last_error)

            except httpx.RequestError as e:
                last_error = f"请求错误: {e}"
                logger.warning("Agent4 httpx 连接异常 (%s)，准备重试...", last_error)
                log_llm_call(model=model, prompt=prompt, response="", tag=tag, error=last_error)

            except Exception as e:
                last_error = str(e)
                logger.error("Agent4 httpx 异常: %s", last_error)
                logger.exception(e)
                log_llm_call(model=model, prompt=prompt, response="", tag=tag, error=last_error)

            if attempt < max_retries:
                wait = min(2 ** (attempt + 1), 30) * random.uniform(0.5, 1.5)
                logger.info("Agent4 httpx 第%d次重试，等待 %.1f 秒...", attempt + 1, wait)
                await asyncio.sleep(wait)

        logger.error("Agent4 httpx 重试 %d 次后仍失败: %s", max_retries, last_error)
        return None

    @staticmethod
    async def call_deepseek_api_streaming(
        prompt: str,
        max_retries: int = 3,
        tag: str = "",
    ) -> Optional[str]:
        """流式调用大模型 API，返回合并后的完整文本"""
        import asyncio
        import random

        client = _make_llm_client()
        last_error: Optional[str] = None

        for attempt in range(max_retries + 1):
            try:
                chunks = []
                stream = await client.chat.completions.create(
                    model=settings.DEEPSEEK_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    # max_tokens=32768,
                    max_tokens=8192,
                    stream=True,
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        chunks.append(delta)

                full_text = "".join(chunks)
                log_llm_call(settings.DEEPSEEK_MODEL, prompt, full_text, tag=tag)
                return full_text

            except (APIConnectionError, APITimeoutError) as e:
                last_error = f"连接/超时错误: {e}"
                logger.warning("大模型流式调用连接异常 (%s)，准备重试...", last_error)
                log_llm_call(model=settings.DEEPSEEK_MODEL, prompt=prompt,
                             response="", tag=tag, error=last_error)

            except APIError as e:
                last_error = f"API 错误 HTTP {e.status_code}: {e.message}"
                logger.error("大模型流式 API 失败: %s", last_error)
                log_llm_call(model=settings.DEEPSEEK_MODEL, prompt=prompt,
                             response="", tag=tag, error=last_error)

            except Exception as e:
                last_error = str(e)
                logger.warning("大模型流式调用异常: %s，准备重试", last_error)
                log_llm_call(model=settings.DEEPSEEK_MODEL, prompt=prompt,
                             response="", tag=tag, error=last_error)

            if attempt < max_retries:
                wait = min(2 ** (attempt + 1), 30) * random.uniform(0.5, 1.5)
                logger.info("流式调用第%d次重试，等待 %.1f 秒", attempt + 1, wait)
                await asyncio.sleep(wait)

        logger.error("大模型流式调用重试 %d 次后仍失败: %s", max_retries, last_error)
        return None

    @staticmethod
    def parse_json_response(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从 API 响应 dict 中提取并解析 JSON"""
        import re
        logger.info("原始输出：%s", response)
        try:
            if not response or "choices" not in response:
                logger.error("API 响应格式不正确，缺少 choices 字段")
                return None

            content = response["choices"][0]["message"]["content"]
            logger.info("API 返回内容长度: %d 字符", len(content))

            content = content.replace('\n', ' ').replace('\r', '')

            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning("整体 JSON 解析失败: %s", e)

            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
            if json_match:
                try:
                    json_str = json_match.group(1).strip()
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning("代码块中 JSON 解析失败: %s", e)

            fixed_content = re.search(r'\{\s*"questions"\s*:\s*\[(.*?)\]\s*\}', content, re.DOTALL)
            if fixed_content:
                try:
                    return json.loads('{"questions": [' + fixed_content.group(1) + ']}')
                except json.JSONDecodeError:
                    pass

            logger.error("无法解析响应内容，前200字符: %s...", content[:200])
            return None

        except Exception as e:
            logger.error("解析 JSON 响应失败: %s", e)
            logger.exception(e)
            return None


# 创建服务实例
llm_service = LLMService()
