"""
slot_analyzer.py — Agent 2: 题槽结构分析器

职责：
  1. 将 Agent 1 解析出的多份历年试卷格式化为 LLM 可读的纯文本上下文
  2. 调用 DeepSeek，要求其按知识点+题型做跨年度语义对齐
  3. 解析 LLM 返回的 JSON，生成统一的题槽模板（slot_template）
"""

import json
import logging
import re
from typing import Optional

from app.agents.state import ExamState
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Prompt 模板
# ─────────────────────────────────────────────

_SLOT_PROMPT_TEMPLATE = """\
你是一位考试出题结构分析专家。以下是《{course_name}》多年的考试试题，请分析其出题结构。

任务：
1. 识别该课程历年考试的固定题槽结构（几大题、每题类型、分值）
2. 将不同年份的题目按知识点和题型对齐到统一的题槽中
3. 注意：不同年份的题号可能不对应，要按内容语义匹配
4. 如果某个题槽在某一年没有对应题目，history 中可以不包含该年

历年试题：
{exams_text}

请严格按照以下 JSON 格式输出，不要有任何额外说明文字：
{{
  "course_name": "课程名",
  "total_points": 100,
  "slots": [
    {{
      "slot_id": 1,
      "type": "题型（如 填空题/判断题/选择题/计算题/证明题/问答题）",
      "points": 20,
      "typical_sub_count": 9,
      "knowledge_focus": ["知识点1", "知识点2"],
      "history": [
        {{
          "year": 2021,
          "original_number": "试题一",
          "content": "完整题目文字（含 LaTeX 公式）",
          "answer": "参考答案（若有，否则 null）",
          "scoring_criteria": ["评分标准1（若有）"],
          "has_figure": false,
          "figure_descriptions": []
        }}
      ]
    }}
  ]
}}

注意事项：
- 若往年题有图，has_figure 设为 true，figure_descriptions 填入图的文字描述
- 若无法识别课程名，course_name 填写你能推断出的名称
- total_points 填写试卷总分（通常为 100）
- typical_sub_count 为该大题通常包含的小题数量（如填空有 9 空，则填 9；整体一道大题则填 null）
"""


# ─────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────

def _format_exams_for_prompt(parsed_exams: list[dict]) -> tuple[str, str]:
    """
    将所有试卷格式化为 LLM 可读的纯文本上下文。

    所有文件（无论是否含答案）均纳入，因为题目与答案同页是常见情况，
    答案内容对 Agent 2 理解题型结构和 Agent 4 生成参考答案都有价值。

    Returns:
        (exams_text, course_name): 格式化的试卷文本和推断出的课程名。
    """
    parts: list[str] = []
    course_name = "未知课程"

    # 推断课程名（取第一个非空值）
    for exam in parsed_exams:
        if exam.get("course_name"):
            course_name = exam["course_name"]
            break

    for exam in parsed_exams:
        year = exam.get("year") or "未知年份"
        filename = exam.get("filename", "")
        questions = exam.get("raw_questions", [])

        year_label = f"{year}年" if isinstance(year, int) else str(year)
        year_text = f"[{year_label}]（文件：{filename}）\n"
        for q in questions:
            num = str(q.get("number", "")).strip()
            q_type = q.get("type") or "未知题型"
            points = q.get("points")
            points_str = f"（{points}分）" if points else ""
            content = q.get("content", "")
            figs = q.get("figure_descriptions", [])
            fig_str = ""
            if figs:
                fig_str = "\n  [图示：" + "；".join(figs) + "]"

            answer = q.get("answer")
            scoring = q.get("scoring_criteria")

            answer_str = ""
            if answer:
                answer_str = f"\n  参考答案：{answer}"
            if scoring:
                criteria_text = "；".join(scoring) if isinstance(scoring, list) else str(scoring)
                answer_str += f"\n  评分标准：{criteria_text}"

            year_text += f"  {num}. [{q_type}]{points_str} {content}{fig_str}{answer_str}\n\n"

        parts.append(year_text)

    exams_text = "\n".join(parts)
    return exams_text, course_name


# JSON 规范允许的转义字符
_JSON_VALID_ESCAPES = set('"\\\/bfnrtu')


def _fix_latex_escapes(text: str) -> str:
    """将 LaTeX 反斜杠（非法 JSON 转义）修复为双反斜杠，保留合法 JSON 转义。"""
    result: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '\\' and i + 1 < len(text):
            next_ch = text[i + 1]
            if next_ch in _JSON_VALID_ESCAPES:
                result.append(ch)
                result.append(next_ch)
            else:
                result.append('\\')
                result.append('\\')
                result.append(next_ch)
            i += 2
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


def _parse_slot_response(text: str) -> Optional[dict]:
    """
    从 LLM 返回文本中提取第一个有效 JSON 对象。
    兼容模型在 JSON 前后附加说明文字、```json ... ``` 包裹以及 LaTeX 反斜杠未转义等情况。
    """
    text = text.strip()

    # 先尝试整体解析（含 LaTeX 修复）
    result = _try_parse(text)
    if result is not None:
        return result

    # 尝试 ```json ... ``` 包裹
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if code_block:
        result = _try_parse(code_block.group(1).strip())
        if result is not None:
            return result

    # 尝试找第一个 { ... } 块
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
# 核心函数
# ─────────────────────────────────────────────

async def agent2_analyze_slots(state: ExamState) -> dict:
    """
    LangGraph 节点入口函数。

    读取 state["parsed_exams"]，调用 DeepSeek 分析题槽结构，
    将结果写入 state["slot_template"]，并更新 analyze_status。
    """
    parsed_exams: list[dict] = state.get("parsed_exams", [])

    if not parsed_exams:
        logger.warning("agent2_analyze_slots: parsed_exams 为空，跳过。")
        return {
            "slot_template": [],
            "analyze_status": "done",
            "analyze_progress": {"warning": "parsed_exams 为空，无法分析题槽。"},
        }

    # 1. 格式化上下文
    exams_text, course_name = _format_exams_for_prompt(parsed_exams)
    logger.info("Agent 2 开始分析课程：%s，共 %d 份试卷", course_name, len(parsed_exams))

    # 2. 构建 Prompt
    prompt = _SLOT_PROMPT_TEMPLATE.format(
        course_name=course_name,
        exams_text=exams_text,
    )

    # 3. 调用 DeepSeek
    logger.info("调用 DeepSeek API 分析题槽结构...")
    response = await llm_service.call_deepseek_api(prompt, max_retries=2, tag="Agent2/slot_analyze")

    if not response:
        logger.error("DeepSeek API 返回空响应")
        return {
            "slot_template": [],
            "analyze_status": "error",
            "analyze_progress": {"error": "DeepSeek API 返回空响应，请检查 API Key 和网络连接。"},
        }

    # 4. 提取 LLM 文本内容
    try:
        raw_text = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        logger.error("解析 DeepSeek 响应结构失败: %s", exc)
        return {
            "slot_template": [],
            "analyze_status": "error",
            "analyze_progress": {"error": f"解析 DeepSeek 响应结构失败: {exc}"},
        }

    logger.info("DeepSeek 返回内容长度：%d 字符", len(raw_text))

    # 5. 解析 JSON
    result_json = _parse_slot_response(raw_text)
    if not result_json:
        logger.error("无法从 DeepSeek 响应中提取 JSON，原始内容前 500 字符：%s", raw_text)
        return {
            "slot_template": [],
            "analyze_status": "error",
            "analyze_progress": {
                "error": "无法解析 LLM 返回的 JSON",
                "raw_preview": raw_text,
            },
        }

    slots = result_json.get("slots", [])
    logger.info("Agent 2 完成：识别到 %d 个题槽", len(slots))

    return {
        "slot_template": slots,
        "analyze_status": "done",
        "analyze_progress": {
            "course_name": result_json.get("course_name", course_name),
            "total_points": result_json.get("total_points"),
            "slot_count": len(slots),
        },
    }
