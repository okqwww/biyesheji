from app.services.llm_service import llm_service
from app.services.graph_service import graph_service
from app.db.neo4j import neo4j
from app.models.question import Question, QuestionType, Difficulty
from app.core.logging import logger
from typing import List, Dict, Any, Optional
import json
import asyncio


class QuestionService:
    """题目生成服务"""
    
    @staticmethod
    async def generate_questions(
        course_id: str, 
        knowledge_point_ids: List[str],
        question_type: QuestionType,
        difficulty: Difficulty,
        count: int = 3
    ) -> List[Question]:
        """生成题目"""
        try:
            # 1. 获取课程信息
            courses = graph_service.get_all_courses()
            course = next((c for c in courses if c.id == course_id), None)
            if not course:
                logger.error(f"课程不存在: {course_id}")
                return []
            
            # 2. 获取知识点信息
            knowledge_points = graph_service.get_knowledge_points(knowledge_point_ids)
            if not knowledge_points:
                logger.error(f"找不到指定的知识点")
                return []
            
            # 3. 根据题型生成Prompt
            prompt = QuestionService._create_prompt(
                course.name,
                [kp.name for kp in knowledge_points],
                question_type,
                difficulty,
                count
            )
            
            # 4. 调用大模型生成题目
            response = await llm_service.call_deepseek_api(prompt)
            if not response:
                logger.error("大模型调用失败")
                return []
            
            # 5. 解析响应
            parsed_response = llm_service.parse_json_response(response)
            if not parsed_response or "questions" not in parsed_response:
                logger.error("解析响应失败")
                return []
            
            # 6. 构造题目对象
            questions_data = parsed_response["questions"]
            questions = []
            
            for q_data in questions_data:
                # 添加知识点信息到题目
                q_data["knowledge_points"] = [kp.name for kp in knowledge_points]
                
                # 处理不同题型
                if question_type == QuestionType.SINGLE_CHOICE or question_type == QuestionType.MULTIPLE_CHOICE:
                    # 确保选项格式正确
                    if "options" not in q_data or not q_data["options"]:
                        q_data["options"] = ["选项缺失"]
                
                # 构造Question对象
                try:
                    question = Question(
                        type=question_type,
                        difficulty=difficulty,
                        **q_data
                    )
                    questions.append(question)
                except Exception as e:
                    logger.error(f"构造题目对象失败: {str(e)}")
            
            return questions
            
        except Exception as e:
            logger.error(f"生成题目失败: {str(e)}")
            return []
    
    @staticmethod
    def save_questions(questions: List[Question], knowledge_point_ids: List[str]) -> Dict[str, Any]:
        """保存题目"""
        try:
            saved_ids = []
            
            for question in questions:
                # 将题目转换为字典格式
                q_dict = question.model_dump()
                
                # 保存到Neo4j
                question_id = neo4j.save_question(q_dict, knowledge_point_ids)
                saved_ids.append(question_id)
            
            return {
                "saved_count": len(saved_ids),
                "question_ids": saved_ids
            }
            
        except Exception as e:
            logger.error(f"保存题目失败: {str(e)}")
            return {
                "saved_count": 0,
                "question_ids": []
            }
    
    @staticmethod
    def update_question(question_id: str, update_data: Dict[str, Any]) -> bool:
        """更新题目"""
        try:
            return neo4j.update_question(question_id, update_data)
        except Exception as e:
            logger.error(f"更新题目失败: {str(e)}")
            return False
    
    @staticmethod
    def export_markdown(questions: List[Question]) -> str:
        """导出为Markdown格式"""
        if not questions:
            return "# 无题目数据"
            
        lines = ["# 题目导出\n"]
        
        # 添加基本信息
        import datetime
        lines.append(f"**生成时间**：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
        lines.append(f"**题目数量**：{len(questions)}题\n")
        
        # 添加题目
        for i, question in enumerate(questions):
            difficulty_map = {
                "easy": "简单",
                "medium": "中等",
                "hard": "困难"
            }
            
            type_map = {
                "single_choice": "单选题",
                "multiple_choice": "多选题",
                "fill_blank": "填空题",
                "short_answer": "解答题"
            }
            
            lines.append(f"---\n")
            lines.append(f"## 第{i+1}题 [{type_map.get(question.type, question.type)}] [{difficulty_map.get(question.difficulty, question.difficulty)}]\n")
            
            # 考察知识点
            if question.knowledge_points:
                lines.append(f"**考察知识点**：{', '.join(question.knowledge_points)}\n")
            
            # 题干
            lines.append(f"**题目**：\n{question.content}\n")
            
            # 选项（如果有）
            if question.options:
                lines.append("\n**选项**：")
                for option in question.options:
                    lines.append(f"  {option}")
                lines.append("")
            
            # 答案
            lines.append(f"**参考答案**：")
            if isinstance(question.answer, list):
                lines.append(", ".join(question.answer))
            else:
                lines.append(str(question.answer))
            lines.append("")
            
            # 解析
            if question.explanation:
                lines.append(f"**解析**：\n{question.explanation}\n")
            
            # 评分点
            if question.scoring_points:
                lines.append(f"**评分标准**：")
                for point in question.scoring_points:
                    lines.append(f"- {point}")
                lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def _create_prompt(
        course_name: str,
        knowledge_points: List[str],
        question_type: QuestionType,
        difficulty: Difficulty,
        count: int
    ) -> str:
        """创建Prompt模板"""
        
        difficulty_text = {
            "easy": "简单",
            "medium": "中等",
            "hard": "困难"
        }
        
        # 基础Prompt模板
        prompt = f"""你是一位专业的高校教师，擅长出高质量的编程考试题目。

请根据以下要求生成{question_type.value}：

【课程】{course_name}
【知识点】{', '.join(knowledge_points)}
【难度】{difficulty_text.get(difficulty, difficulty)}
【数量】{count}题

"""
        
        # 根据题型添加具体要求
        if question_type == QuestionType.SINGLE_CHOICE:
            prompt += """要求：
1. 题目紧扣指定知识点
2. 选项设计合理，干扰项有迷惑性但不能有歧义
3. 只有一个正确答案
4. 提供详细解析

请直接返回原始JSON，不要使用Markdown代码块或```json标记。只返回以下格式的纯 JSON：
{
  "questions": [
    {
      "content": "题干",
      "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
      "answer": "正确选项字母",
      "explanation": "解析"
    }
  ]
}
"""
        elif question_type == QuestionType.MULTIPLE_CHOICE:
            prompt += """要求：
1. 题目紧扣指定知识点
2. 正确答案为2-4个
3. 选项设计合理，干扰项有迷惑性
4. 提供详细解析

请直接返回原始JSON，不要使用Markdown代码块或```json标记。只返回以下格式的纯 JSON：
{
  "questions": [
    {
      "content": "题干",
      "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
      "answer": ["正确选项字母1", "正确选项字母2"],
      "explanation": "解析"
    }
  ]
}
"""
        elif question_type == QuestionType.FILL_BLANK:
            prompt += """要求：
1. 使用 ____(1)____ 格式标记空格
2. 可以有1-3个空
3. 题目紧扣指定知识点
4. 提供详细解析

请直接返回原始JSON，不要使用Markdown代码块或```json标记。只返回以下格式的纯 JSON：
{
  "questions": [
    {
      "content": "Python中使用 ____(1)____ 关键字定义函数",
      "answer": ["def"],
      "explanation": "解析"
    }
  ]
}
"""
        elif question_type == QuestionType.SHORT_ANSWER:
            prompt += """要求：
1. 题目紧扣指定知识点
2. 提供完整的参考答案（含代码）
3. 提供详细的评分标准（总分10分）
4. 评分标准要具体、可操作

请直接返回原始JSON，不要使用Markdown代码块或```json标记。只返回以下格式的纯 JSON：
{
  "questions": [
    {
      "content": "题目描述",
      "answer": "参考答案（含代码）",
      "scoring_points": [
        "正确定义函数（2分）",
        "正确使用循环（3分）",
        "逻辑正确（3分）",
        "代码规范（2分）"
      ]
    }
  ]
}
"""
        return prompt


# 创建服务实例
question_service = QuestionService()
