from pydantic import BaseModel
from typing import Optional, List


class Course(BaseModel):
    """课程数据模型"""
    id: str
    name: str
    description: str
    knowledge_point_count: int


class CourseList(BaseModel):
    """课程列表响应模型"""
    success: bool = True
    data: List[Course]
