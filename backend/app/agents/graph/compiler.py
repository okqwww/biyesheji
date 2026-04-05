"""
compiler.py — Graph 编译与两模调度器

负责：
  1. 定义完整 StateGraph（5 个节点 + 条件边）
  2. graph.compile(checkpointer=...)
  3. 导出 exam_workflow 单例
  4. 两模调度函数：run_workflow() 根据 USE_LANGGRAPH 走对应路径
"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.state import ExamState
from app.agents.graph.schema import GraphState
from app.agents.graph import nodes, edges
from app.agents.graph.checkpoint import get_checkpointer

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 构建图
# ─────────────────────────────────────────────

def _build_graph() -> StateGraph:
    """
    构建完整工作流图。
    节点：parse → analyze → wait_slots → generate → kg_extract → END
    """
    graph = StateGraph(GraphState)

    # 注册节点
    graph.add_node("parse",      nodes.node_parse)
    graph.add_node("analyze",    nodes.node_analyze)
    graph.add_node("wait_slots", nodes.node_wait_slots)
    graph.add_node("generate",   nodes.node_generate)
    graph.add_node("kg_extract", nodes.node_kg_extract)

    # 设置入口点
    graph.set_entry_point("parse")

    # 普通边
    graph.add_edge("parse",      "analyze")
    graph.add_edge("generate",   "kg_extract")
    graph.add_edge("kg_extract", END)

    # 条件边
    graph.add_conditional_edges(
        "analyze",
        edges.should_wait_slots,
        {
            "wait_slots": "wait_slots",
            "__end__": END,
        },
    )

    graph.add_conditional_edges(
        "wait_slots",
        edges.should_generate,
        {
            "generate": "generate",
            "__end__": END,
        },
    )

    return graph


# ─────────────────────────────────────────────
# 编译（单例）
# ─────────────────────────────────────────────

_exam_workflow = None


def get_exam_workflow():
    """获取编译后的 workflow 单例。"""
    global _exam_workflow
    if _exam_workflow is None:
        checkpointer = get_checkpointer()
        _exam_workflow = _build_graph().compile(checkpointer=checkpointer)
        logger.info(
            "LangGraph workflow 已编译，checkpointer=%s",
            checkpointer.__class__.__name__,
        )
    return _exam_workflow


def exam_workflow():
    """供外部导入使用的 workflow 对象（延迟初始化）。"""
    return get_exam_workflow()
