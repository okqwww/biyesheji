from pydantic import BaseModel, Field
from typing import Optional, List, Union, Literal
from enum import Enum


class QuestionType(str, Enum):
    """题目类型枚举"""
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_BLANK = "fill_blank"
    SHORT_ANSWER = "short_answer"


class Difficulty(str, Enum):
    """题目难度枚举"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Question(BaseModel):
    """题目数据模型"""
    id: Optional[str] = None
    type: QuestionType
    difficulty: Difficulty
    content: str
    options: Optional[List[str]] = None
    answer: Union[str, List[str]]
    explanation: Optional[str] = None
    scoring_points: Optional[List[str]] = None
    knowledge_points: List[str] = Field(default_factory=list)


class GenerateQuestionRequest(BaseModel):
    """生成题目请求模型"""
    course_id: str
    knowledge_point_ids: List[str]
    question_type: QuestionType
    difficulty: Difficulty
    count: int = 3


class SaveQuestionRequest(BaseModel):
    """保存题目请求模型"""
    questions: List[Question]
    knowledge_point_ids: List[str]


class UpdateQuestionRequest(BaseModel):
    """更新题目请求模型"""
    content: Optional[str] = None
    options: Optional[List[str]] = None
    answer: Optional[Union[str, List[str]]] = None
    explanation: Optional[str] = None
    scoring_points: Optional[List[str]] = None


class QuestionResponse(BaseModel):
    """题目响应模型"""
    success: bool = True
    data: List[Question]
    message: Optional[str] = None


class SaveQuestionResponse(BaseModel):
    """保存题目响应模型"""
    success: bool = True
    message: str
    data: dict
    

class ExportFormat(str, Enum):
    """导出格式枚举"""
    MARKDOWN = "markdown"
