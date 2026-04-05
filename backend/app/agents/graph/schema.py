"""
schema.py — LangGraph State Schema

扩展原始 ExamState，添加 LangGraph interrupt / 断点恢复所需的 3 个字段。
"""

from typing import TypedDict, Optional

from app.agents.state import ExamState


class GraphState(ExamState):
    """
    LangGraph 工作流的完整状态 Schema。

    新增 3 个字段用于 interrupt 和断点恢复：
    - last_completed_step : 上一步完成的节点名
    - interrupt_reason    : 中断原因描述
    - slot_approval       : None=未确认, True=已批准, False=已拒绝
    """

    # 新增：LangGraph interrupt / 断点恢复用
    last_completed_step: Optional[str]   # "parse" | "analyze" | "generate" | "kg"
    interrupt_reason: Optional[str]        # 中断原因描述
    slot_approval: Optional[bool]          # None=未确认, True=已批准, False=已拒绝
