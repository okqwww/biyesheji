from neo4j import GraphDatabase
from typing import Dict, List, Any, Optional
from app.core.config import settings
from app.core.logging import logger
from contextlib import asynccontextmanager


class Neo4jConnection:
    """Neo4j数据库连接类"""
    
    def __init__(self):
        """初始化连接"""
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            
    def verify_connectivity(self) -> bool:
        """验证连接是否可用"""
        try:
            self.driver.verify_connectivity()
            logger.info("Neo4j连接成功")
            return True
        except Exception as e:
            logger.error(f"Neo4j连接失败: {str(e)}")
            return False
            
    def get_courses(self) -> List[Dict[str, Any]]:
        """获取所有课程信息"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Course)
                OPTIONAL MATCH (c)-[:HAS_CHAPTER]->(:Chapter)-[:CONTAINS]->(kp:KnowledgePoint)
                RETURN c.id as id, c.name as name, c.description as description,
                       count(DISTINCT kp) as knowledge_point_count
                ORDER BY c.name
            """)
            return [dict(record) for record in result]
            
    def get_course_graph(self, course_id: str) -> Dict[str, Any]:
        """获取课程的知识图谱"""
        with self.driver.session() as session:
            # 获取节点
            nodes_query = """
                MATCH (c:Course {id: $course_id})
                OPTIONAL MATCH (c)-[:HAS_CHAPTER]->(ch:Chapter)
                OPTIONAL MATCH (ch)-[:CONTAINS]->(kp:KnowledgePoint)
                WITH collect(DISTINCT {
                    id: ch.id, 
                    name: ch.name, 
                    type: 'chapter',
                    order: ch.order
                }) as chapters,
                collect(DISTINCT {
                    id: kp.id, 
                    name: kp.name, 
                    type: 'knowledge_point',
                    description: kp.description
                }) as knowledge_points
                RETURN chapters + knowledge_points as nodes
            """
            
            # 获取边
            edges_query = """
                MATCH (c:Course {id: $course_id})
                OPTIONAL MATCH (c)-[:HAS_CHAPTER]->(ch:Chapter)
                OPTIONAL MATCH (ch)-[:CONTAINS]->(kp:KnowledgePoint)
                OPTIONAL MATCH (kp1:KnowledgePoint)-[r:RELATES_TO]->(kp2:KnowledgePoint)
                WHERE (c)-[:HAS_CHAPTER]->(:Chapter)-[:CONTAINS]->(kp1) 
                  AND (c)-[:HAS_CHAPTER]->(:Chapter)-[:CONTAINS]->(kp2)
                WITH collect(DISTINCT {
                    source: c.id, 
                    target: ch.id, 
                    type: 'has_chapter'
                }) as course_chapter_edges,
                collect(DISTINCT {
                    source: ch.id, 
                    target: kp.id, 
                    type: 'contains'
                }) as chapter_kp_edges,
                collect(DISTINCT {
                    source: kp1.id, 
                    target: kp2.id, 
                    type: 'relates_to'
                }) as kp_relations
                RETURN course_chapter_edges + chapter_kp_edges + kp_relations as edges
            """
            
            nodes_result = session.run(nodes_query, course_id=course_id)
            edges_result = session.run(edges_query, course_id=course_id)
            
            nodes = nodes_result.single()["nodes"] if nodes_result.peek() else []
            edges = edges_result.single()["edges"] if edges_result.peek() else []
            
            return {
                "nodes": nodes,
                "edges": edges
            }
    
    def get_knowledge_points(self, knowledge_point_ids: List[str]) -> List[Dict[str, Any]]:
        """获取指定ID的知识点详情"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (kp:KnowledgePoint)
                WHERE kp.id IN $ids
                RETURN kp.id as id, kp.name as name, kp.description as description,
                       kp.keywords as keywords
            """, ids=knowledge_point_ids)
            return [dict(record) for record in result]
    
    def save_question(self, question: Dict[str, Any], knowledge_point_ids: List[str]) -> str:
        """保存题目并关联到知识点"""
        with self.driver.session() as session:
            result = session.run("""
                CREATE (q:Question {
                    id: randomUUID(),
                    type: $type,
                    difficulty: $difficulty,
                    content: $content,
                    options: $options,
                    answer: $answer,
                    explanation: $explanation,
                    scoring_points: $scoring_points,
                    created_at: datetime(),
                    source: 'ai_generated'
                })
                RETURN q.id as id
            """, 
            type=question.get("type"),
            difficulty=question.get("difficulty"),
            content=question.get("content"),
            options=str(question.get("options", [])),
            answer=str(question.get("answer")),
            explanation=question.get("explanation", ""),
            scoring_points=str(question.get("scoring_points", []))
            )
            
            question_id = result.single()["id"]
            
            # 创建关联关系
            for kp_id in knowledge_point_ids:
                session.run("""
                    MATCH (q:Question {id: $q_id})
                    MATCH (kp:KnowledgePoint {id: $kp_id})
                    CREATE (q)-[:TESTS]->(kp)
                """, q_id=question_id, kp_id=kp_id)
            
            return question_id
    
    def update_question(self, question_id: str, update_data: Dict[str, Any]) -> bool:
        """更新题目信息"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (q:Question {id: $id})
                SET q += $updates
                RETURN q
            """, id=question_id, updates=update_data)
            return result.single() is not None


# 创建全局连接实例
neo4j = Neo4jConnection()
