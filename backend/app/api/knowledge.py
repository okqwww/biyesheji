from fastapi import APIRouter, HTTPException
from app.services.graph_service import graph_service
from app.models.knowledge import GraphResponse, KnowledgePoint
from typing import List

router = APIRouter(tags=["knowledge"])


@router.get("/courses/{course_id}/graph", response_model=GraphResponse)
async def get_course_graph(course_id: str):
    """获取课程的知识图谱"""
    graph_data = graph_service.get_course_graph(course_id)
    
    if not graph_data.nodes:
        raise HTTPException(status_code=404, detail=f"课程 {course_id} 的知识图谱不存在")
        
    return GraphResponse(data=graph_data)


@router.get("/knowledge-points", response_model=List[KnowledgePoint])
async def get_knowledge_points(ids: str):
    """获取知识点详情，多个ID用逗号分隔"""
    knowledge_point_ids = ids.split(",")
    knowledge_points = graph_service.get_knowledge_points(knowledge_point_ids)
    
    if not knowledge_points:
        raise HTTPException(status_code=404, detail=f"未找到指定的知识点")
        
    return knowledge_points
