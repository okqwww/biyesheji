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
# 任务指令
你是国内高校本科课程的期末试卷命题规律分析专家。
## 核心任务目标
基于给定的历年考试真题，拆解出标准化的出题题槽。**你的输出唯一服务于下游任务：让后续AI能完全照着你输出的题槽，生成一份和历年真题考点、题型、分值、出题范式、难度、评分标准极其相似的100分合规试卷**。所有设计必须围绕这个核心目标展开。

## 一、题槽的核心定义与合格设计标准
1.  一个题槽 = 一个独立的出题最小单元，必须对应**同一个核心考点、同一个固定出题范式、同一类题型、稳定的分值区间**，下游AI可直接基于单个题槽出对应题目。
2.  知识点粒度要求：必须精准到课程的单个必考考点，禁止把解题逻辑、考察目标完全独立的考点，强行塞进同一个题槽。
3.  题型匹配要求：同一题槽内的题目必须是同一类题型（填空题/选择题/解答题/证明题/计算题），禁止跨题型合并。
4.  分值要求：
    - 每个题槽的points字段，需填写该题型在历年真题中出现的**稳定分值**；
    - 所有题槽的分值必须可灵活组合为总分100分的试卷，单个题槽分值不得超过50分；
    - 若该题槽是分小题的题型，typical_sub_count必须填写该题槽的常规小题数量。
5.  语义匹配规则：不同年份的题目，必须按「核心考点+出题范式+解题逻辑」对齐到同一题槽，禁止按试卷题号机械匹配。
6.  全量覆盖要求：尽可能覆盖给定的所有年份、所有真题的每一道题目，尽量不要遗漏任何一道题、任何一个考点；若某道题无法归入现有题槽，可以为其新建独立题槽。
7.  准确性要求：必须校验所有题干的公式、文字准确性，修正题干中的明显笔误，禁止直接沿用错误内容。
8.  结构化要求：每个题槽的knowledge_focus必须精准填写该题槽的核心考点，history必须完整纳入所有对应考点的历年真题，保留完整题干、评分标准。

## 二、绝对禁止的负面清单
1.  禁止遗漏任何年份，不得出现某一年份没有一道题出现在题槽里的情况；
2.  禁止把多个核心考点、多种题型、不同出题范式的题目，塞进同一个题槽；
3.  禁止题槽分值总和不等于100分，禁止出现不符合真题规律的分值；
4.  禁止对题干内容做删减、篡改，必须完整保留原题的LaTeX公式、文字描述、评分标准；
5.  禁止出现知识点归类错位，比如把不同知识点归入同一题槽；
6.  禁止输出任何JSON格式之外的额外说明文字、解释内容。

## 三、强制执行步骤
你必须严格按照以下步骤执行，禁止跳步：
1.  全量提取：把所有年份的真题，逐题拆解，标注每道题的「年份、原题号、题型、分值、完整题干、评分标准、核心考点、出题范式」，确保无任何遗漏；
2.  考点聚类：按「核心考点+出题范式+题型」对所有题目做聚类，形成独立题槽，确保每个题槽符合上述合格标准；
3.  信息补全：为每个题槽补全分值、题量、知识点、历史题目等所有必填字段；
4.  合规校验：校验所有题槽是否符合上述标准，是否覆盖所有题目，分值是否合规，知识点归类是否准确，修正所有不符合要求的内容；
5.  格式输出：严格按照下方给定的JSON格式输出最终内容。

以下是历年试题：
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
