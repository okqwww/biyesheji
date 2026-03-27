from typing import TypedDict, Optional


class ExamState(TypedDict):
    """LangGraph 多 Agent 流程的共享状态"""

    # 会话标识
    session_id: str

    # Agent 1 输入：用户上传的 PDF 文件路径列表
    pdf_paths: list[str]

    # Agent 1 输出：解析后的结构化试卷数据
    # 每项结构：
    # {
    #   "filename": str,
    #   "year": int | None,
    #   "course_name": str | None,
    #   "is_answer_sheet": bool,
    #   "raw_questions": [
    #     {
    #       "number": str,           # 题号，如 "试题一" / "1"
    #       "type": str | None,      # 题型，如 "填空题" / "计算题"
    #       "points": int | None,    # 分值
    #       "content": str,          # 题目内容（LaTeX 格式）
    #       "figure_descriptions": list[str],  # 图的文字描述
    #       "answer": str | None,    # 参考答案（答案卷才有）
    #       "scoring_criteria": list[str] | None  # 评分标准
    #     }
    #   ]
    # }
    parsed_exams: list[dict]

    # Agent 2 输出：题槽模板（跨年度对齐后）
    # 每项结构：
    # {
    #   "slot_id": int,
    #   "type": str,
    #   "points": int,
    #   "typical_sub_count": int | None,
    #   "knowledge_focus": list[str],
    #   "history": [
    #     {
    #       "year": int,
    #       "content": str,
    #       "answer": str | None,
    #       "scoring_criteria": list[str] | None,
    #       "figure_descriptions": list[str]
    #     }
    #   ]
    # }
    slot_template: list[dict]

    # 用户在暂停点 1 设置的改动幅度："small" / "medium" / "large"
    modification_level: str

    # Agent 4 输出：生成的新题目
    # 每项结构：
    # {
    #   "slot_id": int,
    #   "type": str,
    #   "points": int,
    #   "content": str,           # LaTeX 格式
    #   "answer": str,
    #   "scoring_criteria": list[str] | None,
    #   "reused_figure": str | None
    # }
    generated_questions: list[dict]

    # 用户对单道题的反馈（用于触发单题重新生成）
    # 结构：{"slot_id": int, "message": str}
    feedback: Optional[dict]

    # 解析状态："pending" / "parsing" / "done" / "error"
    parse_status: str

    # 解析进度信息
    parse_progress: Optional[dict]
    # 结构：{"parsed_pages": int, "total_pages": int, "current_file": str}

    # Agent 2 题槽分析状态："pending" / "analyzing" / "done" / "error"
    analyze_status: str

    # Agent 2 分析进度/错误信息
    analyze_progress: Optional[dict]

    # Agent 4 题目生成状态："pending" / "generating" / "done" / "error"
    generate_status: str

    # Agent 4 生成进度/错误信息
    generate_progress: Optional[dict]

    # Agent 1.5 知识图谱提取状态："pending" / "extracting" / "done" / "error"
    kg_status: str

    # Agent 1.5 提取进度/结果摘要
    kg_progress: Optional[dict]

    # Agent 1.5 输出：知识点节点列表
    # 每项结构：{"id": "知识点名称", "freq": 3}
    kg_nodes: list[dict]

    # Agent 1.5 输出：知识点关系边列表
    # 每项结构：{"source": "A", "target": "B", "relation": "RELATED_TO"}
    kg_edges: list[dict]
