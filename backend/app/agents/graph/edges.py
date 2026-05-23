"""
edges.py — 边定义与条件边

工作流拓扑：
  START
    ↓
  node_parse
    ↓（parse_status == "done"）
  node_analyze
    ↓（analyze_status == "done"）
  node_wait_slots  ← interrupt() 挂起点
    ↓（slot_approval == True）
  node_generate
    ↓
  node_kg_extract  ← 可选旁路，不阻塞主流程
    ↓
  END
"""

from typing import Literal, Annotated

from app.agents.state import ExamState


def should_parse_continue(state: ExamState) -> Literal["analyze", "__end__"]:
    """
    边条件：parse 完成后决定是否进入 analyze。
    - parse_status == "done" → 继续 analyze
    - parse_status == "error" → 终止（出错）
    - 其他（pending/parsing）→ 异常，终止
    """
    if state.get("parse_status") == "done":
        return "analyze"
    return "__end__"


def should_analyze_continue(state: ExamState) -> Literal["wait_slots", "__end__"]:
    """
    边条件：analyze 完成后决定是否进入中断确认。
    - analyze_status == "done" → 进入 wait_slots（interrupt）
    - 否则（error/pending）→ 终止
    """
    if state.get("analyze_status") == "done":
        return "wait_slots"
    return "__end__"


def should_generate_continue(state: ExamState) -> Literal["kg_extract", "__end__"]:
    """
    边条件：generate 完成后决定是否提取知识图谱。
    - generate_status == "done" → 继续 kg_extract
    - generate_status == "error" → 终止（出错）
    - 其他 → 终止
    """
    if state.get("generate_status") == "done":
        return "kg_extract"
    return "__end__"


def should_generate(state: ExamState) -> Literal["generate", "__end__"]:
    """
    边条件：教师批准后决定是否继续生成。
    - slot_approval == True → 继续 generate
    - slot_approval == False → 拒绝，终止
    - 其他 → 异常终止

    注意：优先从 sessions 全局缓存读取 slot_approval，因为 should_generate
    在 checkpoint 恢复后的 state snapshot 上被调用，此时节点的返回值尚未合并。
    """
    # 优先从 sessions 缓存读取（本轮 node_wait_slots 已写入）
    sid = state.get("session_id")
    if sid:
        try:
            from app.api.agent import sessions as global_sessions
            if sid in global_sessions and global_sessions[sid].get("slot_approval") is True:
                return "generate"
        except Exception:
            pass

    # 回退到 state snapshot（checkpoint 恢复的旧值）
    approval = state.get("slot_approval")
    if approval is True:
        return "generate"
    return "__end__"


def should_kg_extract(state: ExamState) -> Literal["kg_extract", "__end__"]:
    """
    边条件：生成完成后可选触发知识图谱提取。
    kg_status 不影响主工作流结束，仅作为旁路。
    """
    # 只要生成就尝试提取（kg_extract 是独立旁路）
    if state.get("generate_status") == "done":
        return "kg_extract"
    return "__end__"
