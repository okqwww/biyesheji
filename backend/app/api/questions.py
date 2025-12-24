from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from app.services.question_service import question_service
from app.services.graph_service import graph_service
from app.models.question import (
    GenerateQuestionRequest,
    SaveQuestionRequest,
    UpdateQuestionRequest,
    QuestionResponse,
    SaveQuestionResponse,
    ExportFormat
)
from typing import List

router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("/generate", response_model=QuestionResponse)
async def generate_questions(request: GenerateQuestionRequest):
    """生成题目"""
    questions = await question_service.generate_questions(
        request.course_id,
        request.knowledge_point_ids,
        request.question_type,
        request.difficulty,
        request.count
    )
    
    if not questions:
        raise HTTPException(status_code=500, detail="题目生成失败")
        
    return QuestionResponse(data=questions)


@router.post("/save", response_model=SaveQuestionResponse)
async def save_questions(request: SaveQuestionRequest):
    """保存题目到数据库"""
    # 校验知识点ID是否存在（否则Neo4j里会创建Question但无法建立TESTS关系）
    kp_list = graph_service.get_knowledge_points(request.knowledge_point_ids)
    found_ids = {kp.id for kp in kp_list}
    missing_ids = [kp_id for kp_id in request.knowledge_point_ids if kp_id not in found_ids]
    if missing_ids:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "knowledge_point_ids中包含不存在的知识点ID",
                "missing_knowledge_point_ids": missing_ids,
            },
        )

    result = question_service.save_questions(request.questions, request.knowledge_point_ids)
    
    if result["saved_count"] == 0:
        raise HTTPException(status_code=500, detail="题目保存失败")
        
    return SaveQuestionResponse(
        message=f"成功保存 {result['saved_count']} 道题目",
        data=result
    )


@router.put("/{question_id}")
async def update_question(question_id: str, request: UpdateQuestionRequest):
    """更新题目信息"""
    # 转换为字典，排除None值
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="没有提供更新数据")
        
    success = question_service.update_question(question_id, update_data)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"题目 {question_id} 不存在或更新失败")
        
    return {"success": True, "message": "更新成功"}


@router.post("/export/{format}")
async def export_questions(
    format: ExportFormat,
    questions: List[dict],
    background_tasks: BackgroundTasks
):
    """导出题目"""
    from app.models.question import Question
    
    # 将字典转换为Question对象
    question_objects = []
    try:
        for q in questions:
            question_objects.append(Question(**q))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"题目格式错误: {str(e)}")
    
    # 目前仅支持Markdown格式
    if format == ExportFormat.MARKDOWN:
        markdown = question_service.export_markdown(question_objects)
        return PlainTextResponse(markdown)
    else:
        raise HTTPException(status_code=400, detail=f"不支持的导出格式: {format}")
