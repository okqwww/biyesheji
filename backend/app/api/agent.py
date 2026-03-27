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
from app.agents.state import ExamState
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])

# ─────────────────────────────────────────────
# 内存会话存储（开发阶段；生产可替换为 Redis/DB）
# ─────────────────────────────────────────────
sessions: dict[str, ExamState] = {}


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
