"""
question_generator.py — Agent 4: 题目生成器

职责：
  1. 为每个题槽构建独立的 Prompt（含改动幅度指令、历年题参考、其他题槽知识点摘要）
  2. asyncio.gather 并行调用 DeepSeek，每个题槽一次 LLM 调用
  3. 解析 LLM 输出，返回结构化题目列表
  4. 支持单题反馈重新生成（追加上次题目内容 + 教师反馈）
"""

import asyncio
import json
import logging
import re
from typing import Optional

from app.agents.state import ExamState
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 改动幅度映射
# ─────────────────────────────────────────────

_MODIFICATION_DESCRIPTIONS = {
    "small": "保持与往年题高度相似，主要改变具体数值、参数或条件，题型和基本场景保持不变。",
    "medium": "保持考察相同知识点，但换一种出题角度、背景或场景，让题目看起来与往年有明显不同。",
    "large": "在相同知识领域内全新设计题目，风格、场景、考察角度可以与往年题有较大差异。",
}


def _modification_desc(level: str) -> str:
    """将改动幅度标识映射为 Prompt 中的文字说明。"""
    return _MODIFICATION_DESCRIPTIONS.get(level, _MODIFICATION_DESCRIPTIONS["medium"])


# ─────────────────────────────────────────────
# Prompt 构建
# ─────────────────────────────────────────────

def _build_other_slots_summary(slots: list[dict], current_slot_id) -> str:
    """
    构建其他题槽已覆盖的知识点摘要，
    避免生成的题目与其他题槽重复考察同一知识点。
    """
    lines: list[str] = []
    for slot in slots:
        if slot.get("slot_id") == current_slot_id:
            continue
        kf = slot.get("knowledge_focus", [])
        if kf:
            kf_str = "、".join(kf) if isinstance(kf, list) else str(kf)
            lines.append(f"- 题槽 {slot.get('slot_id')}（{slot.get('type', '')}）：{kf_str}")
    return "\n".join(lines) if lines else "（无其他题槽）"


def _format_history(history: list[dict]) -> str:
    """将题槽历史题目格式化为可读文本。"""
    parts: list[str] = []
    for item in history:
        year = item.get("year", "未知年份")
        orig_num = item.get("original_number", "")
        content = item.get("content", "")
        answer = item.get("answer")
        scoring = item.get("scoring_criteria")
        has_fig = item.get("has_figure", False)
        fig_descs = item.get("figure_descriptions", [])

        block = f"--- {year}年（原题号：{orig_num}）---\n{content}"
        if has_fig and fig_descs:
            block += "\n[图示：" + "；".join(fig_descs) + "]"
        if answer:
            block += f"\n参考答案：{answer}"
        if scoring:
            criteria = "；".join(scoring) if isinstance(scoring, list) else str(scoring)
            block += f"\n评分标准：{criteria}"
        parts.append(block)
    return "\n\n".join(parts) if parts else "（暂无历史题目）"


def _build_generation_prompt(
    slot: dict,
    modification_level: str,
    other_summary: str,
    feedback_msg: Optional[str] = None,
    previous_content: Optional[str] = None,
) -> str:
    """
    构建单个题槽的完整生成 Prompt。

    Args:
        slot: 题槽信息（type/points/typical_sub_count/knowledge_focus/history）
        modification_level: "small" / "medium" / "large"
        other_summary: 其他题槽知识点摘要
        feedback_msg: 教师反馈文字（重新生成时使用）
        previous_content: 上次生成的题目内容（重新生成时使用）
    """
    slot_id = slot.get("slot_id", 0)
    q_type = slot.get("type", "未知题型")
    points = slot.get("points", 0)
    sub_count = slot.get("typical_sub_count")
    kf = slot.get("knowledge_focus", [])
    kf_str = "、".join(kf) if isinstance(kf, list) else str(kf)
    history = slot.get("history", [])
    history_text = _format_history(history)
    mod_desc = _modification_desc(modification_level)

    sub_count_line = ""
    if sub_count:
        sub_count_line = f"小题数量：约 {sub_count} 个\n"

    feedback_section = ""
    if feedback_msg and previous_content:
        feedback_section = f"""
【上次生成的题目】
{previous_content}

【教师反馈】
{feedback_msg}

请根据以上反馈重新生成该题目，保持相同题型和分值。
"""

    prompt = f"""你是一位专业的高校出题教师。

【任务】
为以下题槽生成一道新题目，同时提供完整的参考答案和评分标准。

【题槽信息】
题型：{q_type}
分值：{points} 分
{sub_count_line}核心知识点：{kf_str}

【改动幅度要求】
{mod_desc}

【往年该题槽的题目（请参考这些来出新题，但不要照抄）】
{history_text}

【其他题槽已覆盖的知识点（请尽量避免重复考察）】
{other_summary}

【特殊要求】
1. 数学公式使用 LaTeX 格式：行内公式用 $...$，独立公式块用 $$...$$
2. 若往年题有图且你无法生成图，优先改为不需要图的纯文字题目
3. 若必须用图且往年有可复用的原图，在 reused_figure 字段标注"复用{{year}}年{{题号}}图"
4. 参考答案要包含完整的解题步骤
5. 评分标准要列出每个得分点及对应分值
{feedback_section}
请严格按照以下 JSON 格式输出，不要有任何额外说明文字：
{{
  "slot_id": {slot_id},
  "type": "{q_type}",
  "points": {points},
  "content": "题目内容（LaTeX 格式）",
  "answer": "参考答案（含完整解题步骤，LaTeX 格式）",
  "scoring_criteria": ["得分点1（X分）", "得分点2（X分）"],
  "reused_figure": null
}}"""
    return prompt


# ─────────────────────────────────────────────
# JSON 解析
# ─────────────────────────────────────────────

# JSON 规范允许的转义字符（紧跟在 \ 后面的合法字符）
_JSON_VALID_ESCAPES = set('"\\\/bfnrtu')


def _fix_latex_escapes(text: str) -> str:
    """
    将 JSON 字符串中因 LaTeX 公式产生的非法转义序列（如 \\gamma、\\bar、\\frac 等）
    修复为合法的双反斜杠，同时保留已合法的 JSON 转义（\\n、\\t、\\\\ 等）。

    例：$\\gamma$ → $\\\\gamma$（json.loads 后恢复为 $\\gamma$，KaTeX 可正确渲染）
    """
    result: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '\\' and i + 1 < len(text):
            next_ch = text[i + 1]
            if next_ch in _JSON_VALID_ESCAPES:
                # 合法 JSON 转义，原样保留（反斜杠 + 后续字符都要保留）
                result.append(ch)
                result.append(next_ch)
            else:
                # 非法转义（LaTeX 反斜杠），补成双反斜杠，后续字符也要保留
                result.append('\\')
                result.append('\\')
                result.append(next_ch)
            i += 2  # 同时跳过反斜杠和后续字符
        else:
            result.append(ch)
            i += 1
    return ''.join(result)


def _try_parse(raw: str) -> Optional[dict]:
    """先直接解析，失败时修复 LaTeX 反斜杠后再解析。"""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(_fix_latex_escapes(raw))
    except json.JSONDecodeError:
        return None


def _parse_question_response(text: str) -> Optional[dict]:
    """
    从 LLM 返回文本中鲁棒地提取题目 JSON 对象。
    兼容 ```json ... ``` 包裹、前后有说明文字、以及 LaTeX 反斜杠未转义等情况。
    """
    text = text.strip()

    # 直接解析（含 LaTeX 修复）
    result = _try_parse(text)
    if result is not None:
        return result

    # ```json ... ``` 包裹
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if code_block:
        result = _try_parse(code_block.group(1).strip())
        if result is not None:
            return result

    # 找第一个 { ... } 块
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    end = -1
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        return None
    return _try_parse(text[start: end + 1])


# ─────────────────────────────────────────────
# 单题生成
# ─────────────────────────────────────────────

async def generate_one_question(
    slot: dict,
    modification_level: str,
    other_summary: str,
    feedback_msg: Optional[str] = None,
    previous_content: Optional[str] = None,
) -> dict:
    """
    为单个题槽调用 DeepSeek 生成一道题目。

    Returns:
        题目 dict，结构见 ExamState.generated_questions 注释。
        若生成失败，返回含 error 字段的 dict，slot_id 保留。
    """
    slot_id = slot.get("slot_id", 0)
    prompt = _build_generation_prompt(
        slot=slot,
        modification_level=modification_level,
        other_summary=other_summary,
        feedback_msg=feedback_msg,
        previous_content=previous_content,
    )

    logger.info("开始生成题槽 %s（%s，%s 分）...", slot_id, slot.get("type"), slot.get("points"))
    response = await llm_service.call_deepseek_api(prompt, max_retries=2)

    if not response:
        logger.error("题槽 %s：DeepSeek API 返回空响应", slot_id)
        return {
            "slot_id": slot_id,
            "type": slot.get("type"),
            "points": slot.get("points"),
            "content": "",
            "answer": "",
            "scoring_criteria": [],
            "reused_figure": None,
            "error": "DeepSeek API 返回空响应",
        }

    try:
        raw_text = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        logger.error("题槽 %s：解析响应结构失败: %s", slot_id, exc)
        return {
            "slot_id": slot_id,
            "type": slot.get("type"),
            "points": slot.get("points"),
            "content": "",
            "answer": "",
            "scoring_criteria": [],
            "reused_figure": None,
            "error": f"解析响应结构失败: {exc}",
        }

    result = _parse_question_response(raw_text)
    if not result:
        logger.error("题槽 %s：无法从响应中提取 JSON，预览：%s", slot_id, raw_text[:300])
        return {
            "slot_id": slot_id,
            "type": slot.get("type"),
            "points": slot.get("points"),
            "content": raw_text[:500],  # 至少保留原始文本，供人工检查
            "answer": "",
            "scoring_criteria": [],
            "reused_figure": None,
            "error": "无法解析 JSON，已保留原始文本",
        }

    # 确保 slot_id 正确（防止模型填错）
    result["slot_id"] = slot_id
    logger.info("题槽 %s 生成完成", slot_id)
    return result


# ─────────────────────────────────────────────
# LangGraph 节点入口
# ─────────────────────────────────────────────

async def agent4_generate_questions(state: ExamState) -> dict:
    """
    LangGraph 节点入口函数。

    读取 state["slot_template"] 和 state["modification_level"]，
    asyncio.gather 并行为每个题槽生成一道题目，
    将结果写入 state["generated_questions"]，更新 generate_status。
    """
    slots: list[dict] = state.get("slot_template", [])
    modification_level: str = state.get("modification_level", "medium")

    if not slots:
        logger.warning("agent4_generate_questions: slot_template 为空，跳过。")
        return {
            "generated_questions": [],
            "generate_status": "done",
            "generate_progress": {"warning": "slot_template 为空，无题目可生成。"},
        }

    logger.info(
        "Agent 4 开始生成：共 %d 个题槽，改动幅度=%s", len(slots), modification_level
    )

    # 为每个题槽构建其他槽摘要（只需构建一次，可复用）
    other_summaries = {
        slot["slot_id"]: _build_other_slots_summary(slots, slot["slot_id"])
        for slot in slots
    }

    tasks = [
        generate_one_question(
            slot=slot,
            modification_level=modification_level,
            other_summary=other_summaries[slot["slot_id"]],
        )
        for slot in slots
    ]

    results: list[dict] = await asyncio.gather(*tasks)

    error_count = sum(1 for r in results if "error" in r)
    logger.info(
        "Agent 4 完成：%d 道题目生成，其中 %d 个出错",
        len(results),
        error_count,
    )

    status = "done" if error_count == 0 else "error"
    return {
        "generated_questions": results,
        "generate_status": status,
        "generate_progress": {
            "total": len(results),
            "success": len(results) - error_count,
            "error_count": error_count,
        },
    }
