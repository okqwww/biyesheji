from app.db.neo4j import neo4j
from app.models.course import Course
from app.models.knowledge import GraphData, KnowledgePoint
from typing import List, Dict, Any
from app.core.logging import logger


class GraphService:
    """知识图谱服务"""
    
    @staticmethod
    def get_all_courses() -> List[Course]:
        """获取所有课程信息"""
        try:
            courses_data = neo4j.get_courses()
            return [Course(**course) for course in courses_data]
        except Exception as e:
            logger.error(f"获取课程信息失败: {str(e)}")
            return []
    
    @staticmethod
    def get_course_graph(course_id: str) -> GraphData:
        """获取课程的知识图谱"""
        try:
            graph_data = neo4j.get_course_graph(course_id)
            return GraphData(**graph_data)
        except Exception as e:
            logger.error(f"获取知识图谱失败: {str(e)}")
            return GraphData(nodes=[], edges=[])
    
    @staticmethod
    def get_knowledge_points(knowledge_point_ids: List[str]) -> List[KnowledgePoint]:
        """获取指定ID的知识点详情"""
        try:
            kp_data = neo4j.get_knowledge_points(knowledge_point_ids)
            return [KnowledgePoint(**kp) for kp in kp_data]
        except Exception as e:
            logger.error(f"获取知识点详情失败: {str(e)}")
            return []


# 创建服务实例
graph_service = GraphService()
