"""
checkpoint.py — Checkpointer 配置

开发/测试阶段使用 MemorySaver（无依赖，即开即用，进程重启丢失）。
"""

from langgraph.checkpoint.memory import MemorySaver

# 共享单例（lazy init）
_checkpointer = None


def get_checkpointer():
    """获取全局 Checkpointer 实例（MemorySaver）。"""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MemorySaver()
    return _checkpointer
