import httpx
import json
import asyncio
from typing import Dict, List, Any, Optional
from app.core.config import settings
from app.core.logging import logger, log_llm_call


class LLMService:
    """大模型服务"""
    
    @staticmethod
    async def call_deepseek_api(
        prompt: str,
        max_retries: int = 2,
        tag: str = "",
    ) -> Optional[Dict[str, Any]]:
        """调用DeepSeek API生成内容"""
        if not settings.DEEPSEEK_API_KEY:
            logger.error("未配置DeepSeek API密钥")
            return None
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 8192
        }
        
        retries = 0
        while retries <= max_retries:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        settings.DEEPSEEK_API_URL,
                        headers=headers,
                        json=payload,
                        timeout=700.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        raw_text = ""
                        try:
                            raw_text = data["choices"][0]["message"]["content"]
                        except (KeyError, IndexError):
                            pass
                        log_llm_call(
                            model="deepseek-chat",
                            prompt=prompt,
                            response=raw_text,
                            tag=tag,
                        )
                        return data
                    else:
                        err_msg = f"HTTP {response.status_code}: {response.text}"
                        logger.error("DeepSeek API调用失败: %s", err_msg)
                        log_llm_call(
                            model="deepseek-chat",
                            prompt=prompt,
                            response="",
                            tag=tag,
                            error=err_msg,
                        )
                        
            except Exception as e:
                logger.error(f"DeepSeek API调用异常: {str(e)}")
                logger.exception(e)
                log_llm_call(
                    model="deepseek-chat",
                    prompt=prompt,
                    response="",
                    tag=tag,
                    error=str(e),
                )
            
            retries += 1
            if retries <= max_retries:
                wait_time = 2 ** retries
                logger.info(f"第{retries}次重试，等待{wait_time}秒...")
                await asyncio.sleep(wait_time)
        
        return None
    
    @staticmethod
    def parse_json_response(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从API响应中提取JSON数据"""
        logger.info(f"原始输出：{response}")
        try:
            if not response or "choices" not in response:
                logger.error("API响应格式不正确，缺少choices字段")
                return None
                
            content = response["choices"][0]["message"]["content"]
            logger.info(f"API返回内容长度: {len(content)} 字符")
            
            # 尝试修复常见JSON错误
            content = content.replace('\n', ' ').replace('\r', '')
            
            # 1. 尝试整体解析
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"整体JSON解析失败: {str(e)}")
            
            # 2. 尝试从文本中提取JSON (通常包含在 ```json ... ``` 中)
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
            if json_match:
                try:
                    json_str = json_match.group(1).strip()
                    # 处理特殊情况：有些模型可能会返回```json { 而不是```json\n{
                    if json_str.startswith('{'):
                        return json.loads(json_str)
                    else:
                        # 去除可能的前导空格
                        json_str = re.sub(r'^\s*', '', json_str)
                        # 尝试提取大括号内的内容
                        bracket_match = re.search(r'\{([\s\S]*)\}', json_str)
                        if bracket_match:
                            return json.loads('{' + bracket_match.group(1) + '}')
                        return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"代码块中JSON解析失败: {str(e)}")
                    logger.warning(f"尝试修复的JSON字符串: {json_str[:100]}...")
            
            # 3. 尝试查找并修复常见的JSON格式问题
            logger.warning("尝试手动修复JSON格式问题")
            # 尝试找到完整的questions数组部分
            fixed_content = re.search(r'\{\s*"questions"\s*:\s*\[(.*?)\]\s*\}', content, re.DOTALL)
            if fixed_content:
                try:
                    # 构造完整的JSON结构
                    full_json = '{"questions": [' + fixed_content.group(1) + ']}'
                    return json.loads(full_json)
                except json.JSONDecodeError as e:
                    logger.warning(f"修复后JSON仍解析失败: {str(e)}")
                    
            # 尝试直接构建questions数组
            question_blocks = re.findall(r'\{\s*"content"\s*:.*?"explanation"\s*:.*?\}', content, re.DOTALL)
            if question_blocks:
                try:
                    questions_json = '[' + ','.join(question_blocks) + ']'
                    questions_data = json.loads(questions_json)
                    return {"questions": questions_data}
                except json.JSONDecodeError as e:
                    logger.warning(f"构建questions数组失败: {str(e)}")
                    
            logger.error("无法解析响应内容")
            logger.error(f"原始内容前200字符: {content[:200]}...")
            return None
            
        except Exception as e:
            logger.error(f"解析JSON响应失败: {str(e)}")
            logger.exception(e)  # 记录完整异常堆栈
            return None


# 创建服务实例
llm_service = LLMService()
