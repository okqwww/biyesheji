from pydantic import BaseModel
from typing import Optional, List, Literal


class Node(BaseModel):
    """图谱节点模型"""
    id: str
    name: str
    type: Literal["chapter", "knowledge_point"]
    description: Optional[str] = None
    order: Optional[int] = None


class Edge(BaseModel):
    """图谱边模型"""
    source: str
    target: str
    type: Literal["has_chapter", "contains", "relates_to"]


class GraphData(BaseModel):
    """知识图谱数据模型"""
    nodes: List[Node]
    edges: List[Edge]


class KnowledgePoint(BaseModel):
    """知识点数据模型"""
    id: str
    name: str
    description: str
    keywords: List[str]


class GraphResponse(BaseModel):
    """知识图谱响应模型"""
    success: bool = True
    data: GraphData
