"""
nodes.py — LangGraph 节点定义

每个节点都是一个 thin wrapper，调用原始 agent 函数并返回更新字段。
interrupt 节点在题槽确认点挂起工作流。
"""

import logging
from typing import Literal

from langgraph.types import interrupt

from app.agents.state import ExamState
from app.agents import parser      # Agent 1
from app.agents import slot_analyzer  # Agent 2
from app.agents import question_generator  # Agent 4
from app.agents import kg_extractor  # Agent 1.5

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 节点函数签名规范
# 每个函数接收 state: ExamState，返回 dict（LangGraph 会合并到 state）
# ─────────────────────────────────────────────


async def node_parse(state: ExamState) -> dict:
    """
    节点 1：调用 Agent 1 解析上传的 PDF 文件。

    做的事：
      - 更新 parse_status = "parsing"
      - 调用 agent1_parse_pdfs(state)
      - 更新 parse_status = "done" | "error"
      - 更新 parse_progress
    """
    parsed_exams: list[dict] = state.get("parsed_exams", [])

    if not parsed_exams:
        # 首次启动，走完整解析
        logger.info("[node_parse] 启动 Agent1 PDF 解析，session_id=%s", state.get("session_id"))
        result = await parser.agent1_parse_pdfs(state)
        return result
    else:
        # 断点恢复：parsed_exams 已存在，直接跳过解析
        logger.info("[node_parse] 检测到 parsed_exams 已存在，跳过解析（断点恢复）")
        return {
            "parse_status": "done",
            "parse_progress": {"restored_from_checkpoint": True, "parsed_count": len(parsed_exams)},
        }


async def node_analyze(state: ExamState) -> dict:
    """
    节点 2：调用 Agent 2 分析题槽结构。

    在 Agent 1 完成之后执行。
    """
    logger.info("[node_analyze] 启动 Agent2 题槽分析，session_id=%s", state.get("session_id"))
    result = await slot_analyzer.agent2_analyze_slots(state)
    return result


def node_wait_slots(state: ExamState) -> dict:
    """
    节点 3（interrupt）：挂起工作流，等待教师确认/修改题槽。

    interrupt() 会将控制权返回给 API 调用方，工作流状态已保存到 Checkpoint。
    前端通过 /agent/workflow/resume 端点传入 slot_template 和 slot_approval 继续。

    恢复执行时：
    - 若 slot_approval=True：interrupt() 返回 True，继续流向 generate
    - 若 slot_approval=False：interrupt() 返回 False，edge should_generate 终止工作流

    注意：slot_approval 写入 sessions 全局缓存（边函数 should_generate 在 checkpoint
    恢复的 state snapshot 上被调用，无法通过 node 返回值传递，需借助全局缓存）。
    """
    from app.api.agent import sessions as global_sessions

    interrupt_reason = (
        "请确认题槽结构并设置改动幅度。批准后继续生成题目，拒绝则终止工作流。"
    )

    # 第一次执行：挂起，yield __interrupt__ 事件
    # 第二次执行（resume）：interrupt() 返回 Command(resume=...) 传入的值
    slot_approval: bool = interrupt(interrupt_reason)

    # 写入 sessions 缓存，供 should_generate 边函数读取（边函数在 state snapshot
    # 上被调用，无法通过 node 返回的 dict 传递本轮 approval）
    sid = state.get("session_id")
    if sid and sid in global_sessions:
        global_sessions[sid]["slot_approval"] = slot_approval

    return {
        "slot_approval": slot_approval,
        "interrupt_reason": interrupt_reason,
    }


async def node_generate(state: ExamState) -> dict:
    """
    节点 4：调用 Agent 4 并行生成新题目。

    在教师批准题槽之后执行。
    asyncio.gather 并行逻辑保留在 agent4_generate_questions 内部。
    """
    logger.info("[node_generate] 启动 Agent4 题目生成，session_id=%s", state.get("session_id"))
    result = await question_generator.agent4_generate_questions(state)
    return result


async def node_kg_extract(state: ExamState) -> dict:
    """
    节点 5（可选旁路）：调用 Agent 1.5 提取知识图谱。

    独立于主工作流，在 node_generate 之后触发，写入 Neo4j。
    LangGraph 不阻塞此节点（由 API 层单独触发）。
    """
    logger.info("[node_kg_extract] 启动 Agent1.5 知识图谱提取，session_id=%s", state.get("session_id"))
    # agent15_extract_kg 接收 dict 而非 ExamState，TypedDict 是 dict 子类，直接传即可
    result = await kg_extractor.agent15_extract_kg(state)
    return result
