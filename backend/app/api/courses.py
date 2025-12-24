from fastapi import APIRouter, HTTPException
from app.services.graph_service import graph_service
from app.models.course import Course, CourseList
from typing import List

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=CourseList)
async def get_courses():
    """获取所有课程"""
    courses = graph_service.get_all_courses()
    return CourseList(data=courses)


@router.get("/{course_id}", response_model=Course)
async def get_course(course_id: str):
    """获取单个课程详情"""
    courses = graph_service.get_all_courses()
    course = next((c for c in courses if c.id == course_id), None)
    
    if not course:
        raise HTTPException(status_code=404, detail=f"课程 {course_id} 不存在")
        
    return course
