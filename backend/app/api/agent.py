"""
agent.py — 多 Agent 出题系统 FastAPI 路由

提供以下接口：
  POST /api/agent/upload           上传一或多份 PDF，返回 session_id
  POST /api/agent/parse            触发 Agent 1 后台解析
  GET  /api/agent/parse/result     轮询解析结果
  POST /api/agent/analyze          触发 Agent 2 题槽分析
  GET  /api/agent/analyze/result   轮询题槽分析结果
  POST /api/agent/generate         触发 Agent 4 并行题目生成
  GET  /api/agent/generate/result  轮询生成结果
  POST /api/agent/regenerate       单题反馈重新生成
  POST /api/agent/kg/start         触发 Agent 1.5 知识图谱提取
  GET  /api/agent/kg/result        轮询知识图谱提取结果
  POST /api/agent/workflow/start   LangGraph 模式：启动完整工作流
  GET  /api/agent/workflow/status  LangGraph 模式：查询工作流状态
  POST /api/agent/workflow/resume  LangGraph 模式：中断点恢复继续
"""

import asyncio
import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.agents.parser import agent1_parse_pdfs
from app.agents.slot_analyzer import agent2_analyze_slots
from app.agents.question_generator import agent4_generate_questions, generate_one_question, _build_other_slots_summary
from app.agents.kg_extractor import agent15_extract_kg
from app.agents.state import ExamState
from app.core.config import settings

logger = logging.getLogger(__name__)

# LangGraph 工作流（条件导入，失败时优雅降级）
USE_LANGGRAPH = settings.USE_LANGGRAPH
_langgraph_workflow = None

if USE_LANGGRAPH:
    try:
        from app.agents.graph import get_exam_workflow
        _langgraph_workflow = get_exam_workflow()
        logger.info("LangGraph 模式已启用")
    except Exception as exc:
        logger.warning("LangGraph 加载失败，USE_LANGGRAPH=true 但将降级为 legacy 模式: %s", exc)
        USE_LANGGRAPH = False

router = APIRouter(prefix="/agent", tags=["agent"])

# ─────────────────────────────────────────────
# 内存会话存储（开发阶段；生产可替换为 Redis/DB）
# ─────────────────────────────────────────────
sessions: dict[str, ExamState] = {}

# LangGraph workflow 状态追踪（轻量，状态存 Checkpoint，状态字典仅用于快速轮询）
# 结构: { session_id: { "status": "running"|"interrupted"|"done"|"error", "error": str|None } }
_workflow_status: dict[str, dict] = {}


# ─────────────────────────────────────────────
# Pydantic 请求/响应模型
# ─────────────────────────────────────────────

class UploadResponse(BaseModel):
    session_id: str
    filenames: list[str]
    message: str


class ParseRequest(BaseModel):
    session_id: str


class ParseStatusResponse(BaseModel):
    session_id: str
    status: str          # "pending" / "parsing" / "done" / "error"
    progress: Optional[dict] = None
    parsed_exams: Optional[list[dict]] = None


class AnalyzeRequest(BaseModel):
    session_id: str


class AnalyzeStatusResponse(BaseModel):
    session_id: str
    status: str          # "pending" / "analyzing" / "done" / "error"
    progress: Optional[dict] = None
    slot_template: Optional[list[dict]] = None


class GenerateRequest(BaseModel):
    session_id: str
    modification_level: str = "medium"     # "small" / "medium" / "large"
    slot_template: Optional[list[dict]] = None  # 可选：教师编辑后的题槽列表


class GenerateStatusResponse(BaseModel):
    session_id: str
    status: str          # "pending" / "generating" / "done" / "error"
    progress: Optional[dict] = None
    generated_questions: Optional[list[dict]] = None


class RegenerateRequest(BaseModel):
    session_id: str
    slot_id: int
    message: str         # 教师反馈文字


class RegenerateResponse(BaseModel):
    slot_id: int
    question: dict


class KgRequest(BaseModel):
    session_id: str


class KgStatusResponse(BaseModel):
    session_id: str
    status: str          # "pending" / "extracting" / "done" / "error"
    progress: Optional[dict] = None
    kg_nodes: Optional[list[dict]] = None
    kg_edges: Optional[list[dict]] = None


# ─────────────────────────────────────────────
# LangGraph Workflow 模型
# ─────────────────────────────────────────────

class WorkflowStartRequest(BaseModel):
    session_id: str


class WorkflowStartResponse(BaseModel):
    session_id: str
    status: str          # "running" | "interrupted" | "done" | "error"
    message: str
    slot_template: Optional[list[dict]] = None   # interrupt 时返回当前题槽
    progress: Optional[dict] = None


class WorkflowStatusResponse(BaseModel):
    session_id: str
    status: str          # "running" | "interrupted" | "done" | "error"
    message: str
    slot_template: Optional[list[dict]] = None
    generated_questions: Optional[list[dict]] = None
    progress: Optional[dict] = None
    error: Optional[str] = None


class WorkflowResumeRequest(BaseModel):
    session_id: str
    slot_approval: bool                           # True=批准, False=拒绝
    slot_template: Optional[list[dict]] = None    # 可选：教师编辑后的题槽
    modification_level: str = "medium"            # "small" / "medium" / "large"


# ─────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────

def _get_session_or_404(session_id: str) -> ExamState:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在。")
    return sessions[session_id]


def _ensure_upload_dir(session_id: str) -> str:
    """创建并返回该会话的上传目录路径。"""
    upload_dir = os.path.join(settings.UPLOAD_DIR, session_id)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


async def _run_parse(session_id: str) -> None:
    """后台任务：执行 Agent 1 解析，将结果写回 sessions。"""
    session = sessions.get(session_id)
    if not session:
        logger.error("后台任务：找不到会话 %s", session_id)
        return

    sessions[session_id]["parse_status"] = "parsing"
    sessions[session_id]["parse_progress"] = None

    try:
        update = await agent1_parse_pdfs(session)
        sessions[session_id].update(update)
    except Exception as exc:
        logger.exception("后台解析会话 %s 时出错: %s", session_id, exc)
        sessions[session_id]["parse_status"] = "error"
        sessions[session_id]["parse_progress"] = {"error": str(exc)}


async def _run_analyze(session_id: str) -> None:
    """后台任务：执行 Agent 2 题槽分析，将结果写回 sessions。"""
    session = sessions.get(session_id)
    if not session:
        logger.error("后台任务：找不到会话 %s", session_id)
        return

    sessions[session_id]["analyze_status"] = "analyzing"
    sessions[session_id]["analyze_progress"] = None

    try:
        update = await agent2_analyze_slots(session)
        sessions[session_id].update(update)
    except Exception as exc:
        logger.exception("后台题槽分析会话 %s 时出错: %s", session_id, exc)
        sessions[session_id]["analyze_status"] = "error"
        sessions[session_id]["analyze_progress"] = {"error": str(exc)}


async def _run_generate(session_id: str) -> None:
    """后台任务：执行 Agent 4 并行题目生成，将结果写回 sessions。"""
    session = sessions.get(session_id)
    if not session:
        logger.error("后台任务：找不到会话 %s", session_id)
        return

    sessions[session_id]["generate_status"] = "generating"
    sessions[session_id]["generate_progress"] = None

    try:
        update = await agent4_generate_questions(session)
        sessions[session_id].update(update)
    except Exception as exc:
        logger.exception("后台题目生成会话 %s 时出错: %s", session_id, exc)
        sessions[session_id]["generate_status"] = "error"
        sessions[session_id]["generate_progress"] = {"error": str(exc)}


async def _run_kg(session_id: str) -> None:
    """后台任务：执行 Agent 1.5 知识图谱提取，将结果写回 sessions。"""
    session = sessions.get(session_id)
    if not session:
        logger.error("后台任务：找不到会话 %s", session_id)
        return

    sessions[session_id]["kg_status"] = "extracting"
    sessions[session_id]["kg_progress"] = None

    try:
        update = await agent15_extract_kg(session)
        sessions[session_id].update(update)
    except Exception as exc:
        logger.exception("后台知识图谱提取会话 %s 时出错: %s", session_id, exc)
        sessions[session_id]["kg_status"] = "error"
        sessions[session_id]["kg_progress"] = {"error": str(exc)}


# ─────────────────────────────────────────────
# 路由
# ─────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse)
async def upload_pdfs(files: list[UploadFile] = File(...)):
    """
    上传一或多份往年题 PDF 文件。

    - 为本次请求分配一个唯一 session_id
    - 将文件保存到 backend/uploads/{session_id}/
    - 返回 session_id 和文件名列表
    """
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一份 PDF 文件。")

    session_id = str(uuid.uuid4())
    upload_dir = _ensure_upload_dir(session_id)

    saved_paths: list[str] = []
    filenames: list[str] = []

    for upload_file in files:
        if not upload_file.filename:
            continue
        filename = upload_file.filename
        # 简单安全过滤：只保留文件名，不允许路径穿越
        safe_name = os.path.basename(filename)
        dest = os.path.join(upload_dir, safe_name)

        content = await upload_file.read()
        with open(dest, "wb") as f:
            f.write(content)

        saved_paths.append(dest)
        filenames.append(safe_name)
        logger.info("已保存上传文件: %s (session=%s)", safe_name, session_id)

    if not saved_paths:
        raise HTTPException(status_code=400, detail="没有成功保存任何文件，请检查文件格式。")

    # 初始化会话状态
    sessions[session_id] = ExamState(
        session_id=session_id,
        pdf_paths=saved_paths,
        parsed_exams=[],
        slot_template=[],
        modification_level="medium",
        generated_questions=[],
        feedback=None,
        parse_status="pending",
        parse_progress=None,
        analyze_status="pending",
        analyze_progress=None,
        generate_status="pending",
        generate_progress=None,
        kg_status="pending",
        kg_progress=None,
        kg_nodes=[],
        kg_edges=[],
        # LangGraph 新增字段
        last_completed_step=None,
        interrupt_reason=None,
        slot_approval=None,
    )

    return UploadResponse(
        session_id=session_id,
        filenames=filenames,
        message=f"成功上传 {len(saved_paths)} 份 PDF，session_id={session_id}",
    )


@router.post("/parse")
async def start_parse(request: ParseRequest, background_tasks: BackgroundTasks):
    """
    触发 Agent 1 对已上传的 PDF 进行解析。

    - 验证 session_id 合法性
    - 将解析任务放入后台（立即返回，不阻塞）
    - 客户端通过 GET /api/agent/parse/result 轮询进度
    """
    session = _get_session_or_404(request.session_id)

    current_status = session.get("parse_status", "pending")
    if current_status == "parsing":
        return {"message": "解析正在进行中，请勿重复提交。", "session_id": request.session_id}

    background_tasks.add_task(_run_parse, request.session_id)
    return {
        "message": "解析任务已启动，请通过 /api/agent/parse/result 轮询结果。",
        "session_id": request.session_id,
    }


@router.get("/parse/result", response_model=ParseStatusResponse)
async def get_parse_result(session_id: str):
    """
    查询 Agent 1 解析进度与结果。

    返回字段：
      - status: "pending" / "parsing" / "done" / "error"
      - progress: 进度信息（当前文件、页数等）
      - parsed_exams: 解析完成后返回结构化数据，解析中时为 null
    """
    session = _get_session_or_404(session_id)
    status = session.get("parse_status", "pending")

    return ParseStatusResponse(
        session_id=session_id,
        status=status,
        progress=session.get("parse_progress"),
        parsed_exams=session.get("parsed_exams") if status == "done" else None,
    )


@router.post("/analyze")
async def start_analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    触发 Agent 2 对已解析的试卷进行题槽结构分析。

    - 要求 parse_status 已为 "done"（Agent 1 必须先完成）
    - 将分析任务放入后台（立即返回，不阻塞）
    - 客户端通过 GET /api/agent/analyze/result 轮询进度
    """
    session = _get_session_or_404(request.session_id)

    if session.get("parse_status") != "done":
        raise HTTPException(
            status_code=400,
            detail="请先完成 PDF 解析（parse_status 须为 done）再触发题槽分析。",
        )

    current_status = session.get("analyze_status", "pending")
    if current_status == "analyzing":
        return {"message": "题槽分析正在进行中，请勿重复提交。", "session_id": request.session_id}

    background_tasks.add_task(_run_analyze, request.session_id)
    return {
        "message": "题槽分析任务已启动，请通过 /api/agent/analyze/result 轮询结果。",
        "session_id": request.session_id,
    }


@router.get("/analyze/result", response_model=AnalyzeStatusResponse)
async def get_analyze_result(session_id: str):
    """
    查询 Agent 2 题槽分析进度与结果。

    返回字段：
      - status: "pending" / "analyzing" / "done" / "error"
      - progress: 分析完成后的元信息（课程名、总分、题槽数量）或错误信息
      - slot_template: 分析完成后返回题槽列表，分析中时为 null
    """
    session = _get_session_or_404(session_id)
    status = session.get("analyze_status", "pending")

    return AnalyzeStatusResponse(
        session_id=session_id,
        status=status,
        progress=session.get("analyze_progress"),
        slot_template=session.get("slot_template") if status == "done" else None,
    )


@router.post("/generate")
async def start_generate(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    触发 Agent 4 并行生成所有题槽的新题目。

    - 要求 analyze_status 已为 "done"（Agent 2 必须先完成）
    - 若 request 中传入 slot_template，将覆盖 session 中的值（支持教师编辑题槽后提交）
    - 将生成任务放入后台（立即返回，不阻塞）
    - 客户端通过 GET /api/agent/generate/result 轮询进度
    """
    session = _get_session_or_404(request.session_id)

    if session.get("analyze_status") != "done":
        raise HTTPException(
            status_code=400,
            detail="请先完成题槽分析（analyze_status 须为 done）再触发题目生成。",
        )

    current_status = session.get("generate_status", "pending")
    if current_status == "generating":
        return {"message": "题目生成正在进行中，请勿重复提交。", "session_id": request.session_id}

    # 更新改动幅度
    sessions[request.session_id]["modification_level"] = request.modification_level

    # 若教师传入了编辑后的题槽，覆盖 session 中的值
    if request.slot_template is not None:
        sessions[request.session_id]["slot_template"] = request.slot_template

    background_tasks.add_task(_run_generate, request.session_id)
    return {
        "message": "题目生成任务已启动，请通过 /api/agent/generate/result 轮询结果。",
        "session_id": request.session_id,
        "modification_level": request.modification_level,
    }


@router.get("/generate/result", response_model=GenerateStatusResponse)
async def get_generate_result(session_id: str):
    """
    查询 Agent 4 题目生成进度与结果。

    返回字段：
      - status: "pending" / "generating" / "done" / "error"
      - progress: 生成统计（total/success/error_count）或错误信息
      - generated_questions: 生成完成后返回题目列表，生成中时为 null
    """
    session = _get_session_or_404(session_id)
    status = session.get("generate_status", "pending")

    return GenerateStatusResponse(
        session_id=session_id,
        status=status,
        progress=session.get("generate_progress"),
        generated_questions=session.get("generated_questions") if status in ("done", "error") else None,
    )


@router.post("/regenerate", response_model=RegenerateResponse)
async def regenerate_question(request: RegenerateRequest):
    """
    根据教师反馈，重新生成指定 slot_id 的单道题目。

    - 同步等待（通常 10-30 秒），直接返回新题目
    - 自动将新题目替换 session 中对应 slot_id 的旧题目
    """
    session = _get_session_or_404(request.session_id)

    slots: list[dict] = session.get("slot_template", [])
    target_slot = next((s for s in slots if s.get("slot_id") == request.slot_id), None)
    if not target_slot:
        raise HTTPException(
            status_code=404,
            detail=f"题槽 slot_id={request.slot_id} 不存在。",
        )

    # 找到上次生成的内容
    prev_questions: list[dict] = session.get("generated_questions", [])
    previous_content: Optional[str] = None
    for q in prev_questions:
        if q.get("slot_id") == request.slot_id:
            previous_content = q.get("content")
            break

    modification_level: str = session.get("modification_level", "medium")
    other_summary = _build_other_slots_summary(slots, request.slot_id)

    logger.info(
        "重新生成 slot_id=%s，反馈：%s", request.slot_id, request.message[:100]
    )

    new_question = await generate_one_question(
        slot=target_slot,
        modification_level=modification_level,
        other_summary=other_summary,
        feedback_msg=request.message,
        previous_content=previous_content,
    )

    # 替换 session 中对应题目
    updated_questions = [
        new_question if q.get("slot_id") == request.slot_id else q
        for q in prev_questions
    ]
    # 若原来没有该 slot 的题目（首次生成时出错的情况），追加
    if not any(q.get("slot_id") == request.slot_id for q in prev_questions):
        updated_questions.append(new_question)

    sessions[request.session_id]["generated_questions"] = updated_questions

    return RegenerateResponse(slot_id=request.slot_id, question=new_question)


@router.post("/kg/start")
async def start_kg(request: KgRequest, background_tasks: BackgroundTasks):
    """
    触发 Agent 1.5 从已解析的试卷中提取课程知识图谱。

    - 要求 parse_status 已为 "done"（Agent 1 必须先完成）
    - 提取结果自动写入 Neo4j（失败时仍返回内存中的图谱数据）
    - 客户端通过 GET /api/agent/kg/result 轮询进度
    """
    session = _get_session_or_404(request.session_id)

    if session.get("parse_status") != "done":
        raise HTTPException(
            status_code=400,
            detail="请先完成 PDF 解析（parse_status 须为 done）再触发知识图谱提取。",
        )

    current_status = session.get("kg_status", "pending")
    if current_status == "extracting":
        return {"message": "知识图谱提取正在进行中，请勿重复提交。", "session_id": request.session_id}

    background_tasks.add_task(_run_kg, request.session_id)
    return {
        "message": "知识图谱提取任务已启动，请通过 /api/agent/kg/result 轮询结果。",
        "session_id": request.session_id,
    }


@router.get("/kg/result", response_model=KgStatusResponse)
async def get_kg_result(session_id: str):
    """
    查询 Agent 1.5 知识图谱提取进度与结果。

    返回字段：
      - status: "pending" / "extracting" / "done" / "error"
      - progress: 提取完成后的元信息（课程名、节点数、边数、是否写入 Neo4j）
      - kg_nodes: 提取完成后返回节点列表，提取中时为 null
      - kg_edges: 提取完成后返回边列表，提取中时为 null
    """
    session = _get_session_or_404(session_id)
    status = session.get("kg_status", "pending")
    is_done = status == "done"

    return KgStatusResponse(
        session_id=session_id,
        status=status,
        progress=session.get("kg_progress"),
        kg_nodes=session.get("kg_nodes") if is_done else None,
        kg_edges=session.get("kg_edges") if is_done else None,
    )


# ─────────────────────────────────────────────
# LangGraph Workflow 路由（USE_LANGGRAPH=true 时启用）
# ─────────────────────────────────────────────

if USE_LANGGRAPH and _langgraph_workflow is not None:
    from langgraph.types import Command

    @router.post("/workflow/start", response_model=WorkflowStartResponse)
    async def workflow_start(request: WorkflowStartRequest):
        """
        启动 LangGraph 完整工作流（不走任何 legacy 路径）。

        执行 parse → analyze → interrupt（等待题槽确认），
        在 interrupt 处暂停，直接返回当前状态和 slot_template。
        前端确认后调用 /workflow/resume 继续。
        """
        session = _get_session_or_404(request.session_id)
        sid = request.session_id

        # 防止重复启动
        current_wf_status = _workflow_status.get(sid, {}).get("status")
        if current_wf_status in ("running", "interrupted"):
            raise HTTPException(
                status_code=409,
                detail=f"该会话的工作流已在运行中（status={current_wf_status}），请先调用 /workflow/resume 或等待完成。",
            )

        wf = _langgraph_workflow
        config = {"configurable": {"thread_id": sid}}
        _workflow_status[sid] = {"status": "running", "error": None}

        try:
            # async for 驱动 astream：interrupt() 表现为事件 {'__interrupt__': ...}，
            # astream 不会抛异常，正常迭代完毕后结束。
            async for event in wf.astream(session, config):
                if not event:
                    continue

                # 检测 interrupt 事件（interrupt() 在 node 内被调用时，
                # LangGraph 将检查点保存后把 __interrupt__ 作为事件 yield 出来，
                # stream 不中断，迭代完毕后正常结束。）
                if "__interrupt__" in event:
                    logger.info("[workflow] interrupt detected, pausing at checkpoint")
                    _workflow_status[sid] = {"status": "interrupted", "error": None}
                    return WorkflowStartResponse(
                        session_id=sid,
                        status="interrupted",
                        message="工作流已暂停，请确认题槽后调用 /workflow/resume 继续。",
                        slot_template=sessions[sid].get("slot_template", []),
                        progress={
                            "parse_status": sessions[sid]["parse_status"],
                            "analyze_status": sessions[sid]["analyze_status"],
                        },
                    )

                node_name = list(event.keys())[0]
                node_output = event[node_name]
                logger.info("[workflow] node=%s completed", node_name)

                if isinstance(node_output, dict):
                    sessions[sid].update(node_output)

                _workflow_status[sid] = {"status": "running", "error": None}

            # 能走到这里说明 astream 正常结束（无 interrupt）
            _workflow_status[sid] = {"status": "done", "error": None}
            sessions[sid]["generate_status"] = "done"
            return WorkflowStartResponse(
                session_id=sid,
                status="done",
                message="工作流已完成",
                generated_questions=sessions[sid].get("generated_questions"),
                progress={"parse_status": sessions[sid]["parse_status"],
                         "analyze_status": sessions[sid]["analyze_status"],
                         "generate_status": sessions[sid]["generate_status"]},
            )

        except Exception as exc:
            error_str = str(exc)
            logger.exception("[workflow] 工作流执行出错 session_id=%s", sid)
            _workflow_status[sid] = {"status": "error", "error": error_str}
            return WorkflowStartResponse(
                session_id=sid,
                status="error",
                message=f"工作流执行出错: {error_str}",
                progress={"error_detail": error_str},
            )

    @router.get("/workflow/status", response_model=WorkflowStatusResponse)
    async def workflow_status(session_id: str):
        """
        查询 LangGraph 工作流当前状态。

        - "running"：parse/analyze 阶段执行中
        - "interrupted"：到达题槽确认点，已暂停
        - "done"：完整工作流已完成
        - "error"：执行出错
        """
        _get_session_or_404(session_id)

        status_info = _workflow_status.get(session_id, {})
        wf_status = status_info.get("status", "unknown")
        wf_error = status_info.get("error")

        session = sessions[session_id]

        # 安全兜底：如果 _workflow_status 仍为 running，但 analyze 已完成且 generate 未开始，
        # 说明工作流可能卡在 interrupt 点未被正确捕获（极边缘情况）
        if wf_status == "running" and session.get("analyze_status") == "done" and session.get("generate_status") in ("pending", None):
            wf_status = "interrupted"

        message_map = {
            "running": "工作流执行中（parse 或 analyze 阶段）",
            "interrupted": "工作流已暂停，请确认题槽后调用 /workflow/resume 继续",
            "done": "工作流已完成",
            "error": f"工作流出错: {wf_error}",
            "unknown": "状态未知，请先调用 /workflow/start",
        }

        return WorkflowStatusResponse(
            session_id=session_id,
            status=wf_status,
            message=message_map.get(wf_status, wf_status),
            slot_template=session.get("slot_template") if wf_status == "interrupted" else None,
            generated_questions=session.get("generated_questions") if wf_status == "done" else None,
            progress={
                "parse_status": session.get("parse_status"),
                "analyze_status": session.get("analyze_status"),
                "generate_status": session.get("generate_status"),
                "kg_status": session.get("kg_status"),
            },
            error=wf_error,
        )

    @router.post("/workflow/resume", response_model=WorkflowStatusResponse)
    async def workflow_resume(request: WorkflowResumeRequest):
        """
        从 interrupt 点恢复工作流（不走任何 legacy 路径）。

        - slot_approval=True：批准题槽，Command(resume=True) 继续执行 generate → kg_extract
        - slot_approval=False：拒绝，终止工作流
        - 可传入编辑后的 slot_template 和 modification_level
        """
        session = _get_session_or_404(request.session_id)
        sid = request.session_id
        status_info = _workflow_status.get(sid, {})
        wf_status = status_info.get("status", "unknown")

        if wf_status not in ("interrupted", "running"):
            raise HTTPException(
                status_code=400,
                detail=f"工作流当前状态为 {wf_status}，无法 resume（必须先 /workflow/start）",
            )

        # 写入 session（checkpoint 恢复时会用到）
        sessions[sid]["slot_approval"] = request.slot_approval
        if request.slot_template is not None:
            sessions[sid]["slot_template"] = request.slot_template
        sessions[sid]["modification_level"] = request.modification_level

        if not request.slot_approval:
            # 拒绝，干净终止（不传 Command，让 workflow 自然结束）
            _workflow_status[sid] = {"status": "done", "error": None}
            return WorkflowStatusResponse(
                session_id=sid,
                status="done",
                message="教师拒绝，终止工作流",
                progress={"slot_approval": False},
            )

        # 批准：Command(resume=True) 传入 interrupt 的 resume 参数，
        # 令 node_wait_slots 中的 interrupt() 接受到 True 并正常返回，
        # 工作流继续执行 generate → kg_extract。
        _workflow_status[sid] = {"status": "running", "error": None}
        config = {"configurable": {"thread_id": sid}}

        try:
            async for event in _langgraph_workflow.astream(
                Command(resume=request.slot_approval),
                config,
            ):
                if "__interrupt__" in event:
                    # 理论上 resume 后不应该再遇到 interrupt（因为 slot_approval=True）
                    _workflow_status[sid] = {"status": "interrupted", "error": None}
                    return WorkflowStatusResponse(
                        session_id=sid,
                        status="interrupted",
                        message="异常：resume 后再次遇到中断点",
                    )

                node_name = list(event.keys())[0]
                node_output = event[node_name]
                logger.info("[workflow resume] node=%s completed", node_name)
                if isinstance(node_output, dict):
                    sessions[sid].update(node_output)

            # astream 正常结束
            _workflow_status[sid] = {"status": "done", "error": None}
            sessions[sid]["generate_status"] = "done"
            return WorkflowStatusResponse(
                session_id=sid,
                status="done",
                message="全部完成",
                generated_questions=sessions[sid].get("generated_questions"),
                progress={"generate_status": "done", "kg_status": sessions[sid].get("kg_status")},
            )

        except Exception as exc:
            error_str = str(exc)
            logger.exception("[workflow resume] 工作流执行出错 session_id=%s", sid)
            _workflow_status[sid] = {"status": "error", "error": error_str}
            return WorkflowStatusResponse(
                session_id=sid,
                status="error",
                message=f"工作流执行出错: {error_str}",
                error=error_str,
            )
