"""
kg_extractor.py — Agent 1.5：往年题知识图谱提取

从 Agent 1 解析的 parsed_exams 中，调用 DeepSeek 自动提取课程知识图谱：
  - 节点（KnowledgePoint）：知识点名称 + 出现频次
  - 边（RELATED_TO / REQUIRES）：知识点间的关联/依赖关系

提取结果写入 Neo4j（使用 session_id 隔离，标签 ExamKP），同时返回给前端渲染。
"""

import json
import logging
import re
from typing import Optional

import httpx

from app.core.config import settings
from app.db.neo4j import neo4j

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Prompt 模板
# ─────────────────────────────────────────────────────────────────────────────

_KG_PROMPT_TEMPLATE = """\
你是一位大学课程知识点分析专家。以下是《{course_name}》历年考试的全部题目内容，请从中提取该课程的知识图谱。

【历年题目】
{exam_text}

【任务要求】
1. 提取所有重要知识点作为节点，每个节点包含：
   - id：知识点名称（简洁，3-12字）
   - freq：该知识点在历年题目中出现的频次（整数，至少1）
2. 提取知识点之间的关联关系作为边，包含：
   - source：源知识点 id
   - target：目标知识点 id
   - relation：关系类型，只能是 "RELATED_TO"（相关）或 "REQUIRES"（依赖/前置）
3. 节点数量控制在 15-40 个（太少失去意义，太多影响可读性）
4. 只提取本课程的核心知识点，不要列举太泛化的概念

请严格按照以下 JSON 格式输出，不要有任何额外说明文字：
{{
  "course_name": "{course_name}",
  "nodes": [
    {{"id": "知识点名称", "freq": 3}},
    {{"id": "另一知识点", "freq": 1}}
  ],
  "edges": [
    {{"source": "知识点A", "target": "知识点B", "relation": "RELATED_TO"}},
    {{"source": "基础知识点", "target": "高级知识点", "relation": "REQUIRES"}}
  ]
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────────────────────────────────────

def _format_exams_for_kg(parsed_exams: list[dict]) -> tuple[str, str]:
    """
    将解析的试卷整理成 LLM 可读的文本，并推断课程名。
    返回 (course_name, exam_text)
    """
    course_name = "未知课程"
    lines: list[str] = []

    for exam in parsed_exams:
        year = exam.get("year") or "未知年份"
        name = exam.get("course_name") or ""
        if name and course_name == "未知课程":
            course_name = name

        lines.append(f"\n【{year} 年试题】")
        for q in exam.get("raw_questions", []):
            number = q.get("number", "")
            content = q.get("content", "")
            if content:
                lines.append(f"  {number}. {content[:300]}")  # 截断超长题目

    return course_name, "\n".join(lines)


# JSON 规范允许的转义字符（与 question_generator.py 保持一致）
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


def _parse_kg_response(raw: str) -> Optional[dict]:
    """
    从 LLM 输出中提取知识图谱 JSON，兼容 markdown 代码块包裹和 LaTeX 反斜杠未转义。
    """
    # 尝试从 ```json ... ``` 中提取
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if m:
        raw = m.group(1)

    # 尝试找到第一个 { 到最后一个 } 的范围
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]

    # 先直接解析，失败时修复 LaTeX 反斜杠后再解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(_fix_latex_escapes(raw))
    except json.JSONDecodeError as e:
        logger.error("知识图谱 JSON 解析失败: %s\n原始输出前 300 字符: %s", e, raw[:300])
        return None


async def _call_deepseek(prompt: str) -> str:
    """调用 DeepSeek API，返回原始文本响应。"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 4096,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(settings.DEEPSEEK_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def _write_to_neo4j(session_id: str, course_name: str, nodes: list[dict], edges: list[dict]) -> None:
    """
    将知识图谱写入 Neo4j。
    使用 ExamKP label + session_id 属性隔离，不影响 v1 数据。
    """
    with neo4j.driver.session() as db_session:
        # 先清除该 session 的旧数据（支持重复触发）
        db_session.run(
            "MATCH (n:ExamKP {session_id: $sid}) DETACH DELETE n",
            sid=session_id,
        )

        # 写入节点
        for node in nodes:
            db_session.run(
                """
                MERGE (n:ExamKP {session_id: $sid, name: $name})
                SET n.freq = $freq, n.course_name = $course
                """,
                sid=session_id,
                name=node["id"],
                freq=node.get("freq", 1),
                course=course_name,
            )

        # 写入关系（RELATED_TO 或 REQUIRES）
        for edge in edges:
            rel_type = edge.get("relation", "RELATED_TO")
            if rel_type not in ("RELATED_TO", "REQUIRES"):
                rel_type = "RELATED_TO"
            db_session.run(
                f"""
                MATCH (a:ExamKP {{session_id: $sid, name: $src}})
                MATCH (b:ExamKP {{session_id: $sid, name: $tgt}})
                MERGE (a)-[:{rel_type}]->(b)
                """,
                sid=session_id,
                src=edge["source"],
                tgt=edge["target"],
            )

    logger.info(
        "Neo4j 写入完成：session=%s，%d 个节点，%d 条边",
        session_id,
        len(nodes),
        len(edges),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Agent 1.5 入口
# ─────────────────────────────────────────────────────────────────────────────

async def agent15_extract_kg(session: dict) -> dict:
    """
    Agent 1.5 入口函数（供 FastAPI 后台任务调用）。

    读取 session["parsed_exams"]，调用 DeepSeek 提取知识图谱，
    写入 Neo4j，返回包含 kg_status / kg_nodes / kg_edges 的更新字典。
    """
    session_id: str = session["session_id"]
    parsed_exams: list[dict] = session.get("parsed_exams", [])

    if not parsed_exams:
        logger.warning("Agent 1.5：parsed_exams 为空，跳过知识图谱提取")
        return {
            "kg_status": "error",
            "kg_nodes": [],
            "kg_edges": [],
            "kg_progress": {"error": "parsed_exams 为空，请先完成 PDF 解析"},
        }

    course_name, exam_text = _format_exams_for_kg(parsed_exams)
    logger.info("Agent 1.5 开始：课程=%s，共 %d 份试卷", course_name, len(parsed_exams))

    prompt = _KG_PROMPT_TEMPLATE.format(
        course_name=course_name,
        exam_text=exam_text,
    )

    raw = await _call_deepseek(prompt)
    kg_data = _parse_kg_response(raw)

    if not kg_data:
        return {
            "kg_status": "error",
            "kg_nodes": [],
            "kg_edges": [],
            "kg_progress": {"error": "LLM 返回的知识图谱 JSON 解析失败"},
        }

    nodes: list[dict] = kg_data.get("nodes", [])
    edges: list[dict] = kg_data.get("edges", [])

    # 过滤掉 source/target 不在节点中的孤立边
    node_ids = {n["id"] for n in nodes}
    valid_edges = [e for e in edges if e.get("source") in node_ids and e.get("target") in node_ids]

    logger.info(
        "Agent 1.5 提取完成：%d 节点，%d 有效边（原始 %d 边）",
        len(nodes),
        len(valid_edges),
        len(edges),
    )

    # 写入 Neo4j（容错：写入失败不影响前端展示）
    try:
        _write_to_neo4j(session_id, course_name, nodes, valid_edges)
        neo4j_ok = True
    except Exception as exc:
        logger.warning("Neo4j 写入失败（将仅在内存中保留图谱数据）: %s", exc)
        neo4j_ok = False

    return {
        "kg_status": "done",
        "kg_nodes": nodes,
        "kg_edges": valid_edges,
        "kg_progress": {
            "course_name": course_name,
            "node_count": len(nodes),
            "edge_count": len(valid_edges),
            "neo4j_saved": neo4j_ok,
        },
    }
