# 基于大模型与知识图谱的智能出题系统 — 产品需求文档

## Product Requirements Document

**项目名称**：基于大模型与知识图谱的智能出题系统  
**英文名称**：Intelligent Question Generation System (IQGS)  
**版本**：v2.0（v1.0 → v2.0 迭代）  
**作者**：北京邮电大学电子工程学院 周奕君  
**日期**：2026 年 3 月  

---

## 一、产品概述

### 1.1 产品背景

在高校教学过程中，教师出题是一项耗时且重复性高的工作。传统人工出题方式存在以下问题：
- 出题效率低，耗费大量时间精力
- 题目风格单一，难以保证多样性
- 难度把控依赖经验，缺乏客观标准
- 知识点覆盖不全面，容易遗漏

**v1.0** 采用"知识图谱 + 单 LLM"模式，由教师手动选择知识点后从零生成题目，初步实现了辅助出题的目标，但与高校教师实际出题流程存在脱节：现实中教师出题的核心工作是参考多年往年真题 PDF，在此基础上进行改动，形成新试卷。不同年份基本不会有完全一样的原题，但大部分题目是往年题的变式——有的只改数据，有的换一种考法，有的在同一知识点上全新设计。

**v2.0** 在保留 v1.0 功能的基础上，引入多 Agent 架构，以往年真题为蓝本，自动解析试卷结构、对齐题槽、按可控的改动幅度生成变式新题，真正贴合高校教师的实际工作流。

### 1.2 产品定位

面向高校教师的智能出题辅助工具，提供两种出题模式：

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **知识图谱模式**（v1） | 在可视化知识图谱上选择知识点，单次调用 LLM 直接生成题目 | 快速生成练习题、无往年题时 |
| **往年题 Agent 模式**（v2） | 上传历年真题 PDF，多 Agent 自动分析结构并生成变式新题，支持教师逐题审核反馈 | 正式期中/期末出题，需较高质量 |

### 1.3 产品目标

**v1.0 目标（已实现）**：
1. 降低教师出题工作量，提升出题效率
2. 基于知识图谱确保题目覆盖关键知识点
3. 支持多种题型和难度等级

**v2.0 新增目标**：
1. **贴合实际**：以往年真题为锚点，而非从零生成
2. **质量可控**：教师可设置改动幅度（小改/中改/大改）
3. **人在环中**：教师可审核每道题，对不满意的题目给出具体反馈并重新生成
4. **公式友好**：正确识别和渲染 LaTeX 数学公式（尤其适合理工科课程）
5. **知识图谱**：从往年题中自动提取课程知识图谱，可视化展示考点频次

### 1.4 目标用户

**主要用户**：高校教师，尤其是：
- 每学期需出期中/期末试卷的课程负责教师
- 手里积攒了多年往年真题 PDF 的教师
- 需要定期为课程准备练习题、测验题、考试题
- 具备基本计算机操作能力，希望提高出题效率、减少重复劳动

### 1.5 核心使用场景（v2）

**场景**：数学物理方法课程的老师要出今年的期末试卷。

1. 老师把 2016–2019 年共 4 份期末试卷 PDF 上传到系统
2. 系统自动调用视觉模型解析每份试卷的所有题目（含 LaTeX 公式和图的描述）
3. 系统分析出该课程固定的题槽结构（计算题、证明题等固定大题结构）
4. 老师确认题槽结构、设置改动幅度为"中改"
5. 系统并行生成所有题槽的新题目
6. 老师逐题审核，对某道题给出反馈："这道题太简单了，加大难度"
7. 系统仅重新生成这一道题
8. 最终试卷在页面上完整展示（含 KaTeX 公式渲染），老师自行复制到 Word

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + Element Plus)                    │
│  KaTeX 公式渲染 · 文件上传 · 知识图谱可视化 · 题槽编辑 · 反馈交互  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST API
┌────────────────────────────┴────────────────────────────────────┐
│                         后端 (FastAPI)                            │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │                    v2 多 Agent 流程                      │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │     │
│  │  │ Agent 1  │→│ Agent 1.5│→│ Agent 2  │→│Agent 4│  │     │
│  │  │ PDF解析  │  │知识图谱  │  │题槽分析  │  │题目生成│  │     │
│  │  │(视觉模型)│  │ 提取器   │  │ 分析器   │  │  器    │  │     │
│  │  └──────────┘  └──────────┘  └──────────┘  └────────┘  │     │
│  │       ↑              ↓                         ↑↓        │     │
│  │   Gemini/VLM    Neo4j写入              人在环(反馈循环)   │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │                    v1 知识图谱出题流程                    │     │
│  │        DeepSeek API + Neo4j 知识图谱 + 单次 LLM 调用     │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                  │
│  LLM: DeepSeek API（题槽分析 + 知识图谱提取 + 题目生成）          │
│  视觉模型: Gemini via NewAPI 中台（PDF 页面识别）                  │
└──────────────────────────────────────────────────────────────────┘
                         │
              ┌──────────┴──────────┐
              │      Neo4j          │
              │  知识图谱存储与查询   │
              └─────────────────────┘
```

### 2.2 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 前端框架 | Vue 3 | 3.5+ | Composition API |
| UI 组件库 | Element Plus | 2.13+ | 表单/按钮/对话框 |
| 公式渲染 | KaTeX | latest | 前端 LaTeX 公式渲染 |
| 图可视化 | ECharts | latest | 知识图谱力导向图 |
| 状态管理 | Pinia | 3.0+ | 全局状态 |
| HTTP 客户端 | Axios | 1.13+ | API 请求 |
| 构建工具 | Vite | 7.2+ | 开发服务器和打包 |
| 后端框架 | FastAPI | 0.125+ | Python 异步 Web 框架 |
| 图数据库 | Neo4j | 5.x | 知识图谱存储 |
| 大语言模型 | DeepSeek API | deepseek-chat | 题槽分析/知识图谱/题目生成 |
| 视觉模型 | Gemini (via NewAPI) | gemini-3-flash-preview | PDF 页面识别（含公式/图） |
| PDF 处理 | PyMuPDF (fitz) | latest | PDF 页面渲染为图片 |
| Python | Python | 3.8+ | 后端运行时 |
| ASGI 服务器 | Uvicorn | 0.27+ | 开发和生产 |

### 2.3 v2 Agent 状态设计

```python
from typing import TypedDict, Optional, List, Dict

class ExamState(TypedDict):
    session_id: str
    pdf_paths: List[str]

    # Agent 1 输出：解析后的结构化试卷数据
    parsed_exams: List[Dict]
    # [{
    #   "filename": str, "year": int|None, "course_name": str,
    #   "is_answer_sheet": bool,
    #   "raw_questions": [{
    #     "number": str, "type": str|None, "points": int|None,
    #     "content": str,  # LaTeX 格式
    #     "figure_descriptions": List[str],
    #     "answer": Optional[str],
    #     "scoring_criteria": Optional[List[str]]
    #   }]
    # }]

    # Agent 2 输出：题槽模板（跨年度对齐后）
    slot_template: List[Dict]
    # [{
    #   "slot_id": int, "type": str, "points": int,
    #   "typical_sub_count": Optional[int],
    #   "knowledge_focus": List[str],
    #   "history": [{
    #     "year": int|None, "original_number": str,
    #     "content": str, "answer": Optional[str],
    #     "scoring_criteria": Optional[List[str]],
    #     "has_figure": bool, "figure_descriptions": List[str]
    #   }]
    # }]

    modification_level: str   # "small" / "medium" / "large"

    # Agent 4 输出：生成的新题目
    generated_questions: List[Dict]
    # [{
    #   "slot_id": int, "type": str, "points": int,
    #   "content": str, "answer": str,
    #   "scoring_criteria": Optional[List[str]],
    #   "reused_figure": Optional[str]
    # }]

    feedback: Optional[Dict]  # {"slot_id": int, "message": str} | None
    parse_status: str         # "pending"/"parsing"/"done"/"error"
    parse_progress: Optional[Dict]
    analyze_status: str
    analyze_progress: Optional[Dict]
    generate_status: str
    generate_progress: Optional[Dict]
    kg_status: str
    kg_progress: Optional[Dict]
    kg_nodes: List[Dict]
    kg_edges: List[Dict]
```

### 2.4 v2 处理流程图

```
          ┌──────────────┐
          │   START      │
          │ 接收 PDF 列表 │
          └──────┬───────┘
                 ↓
          ┌──────────────┐
          │   Agent 1    │  并行处理多份 PDF
          │  PDF 解析    │  每页调用视觉模型
          │  (视觉模型)  │
          └──────┬───────┘
                 ↓
          ┌──────────────┐
          │  Agent 1.5   │
          │ 知识图谱提取 │──→ Neo4j（副线，不影响主流程）
          └──────┬───────┘
                 ↓
          ┌──────────────┐
          │   Agent 2    │
          │  题槽分析    │
          │  跨年度对齐  │
          └──────┬───────┘
                 ↓
          ┌──────────────┐
          │ ⏸ 暂停点 1   │ ← 前端：教师确认/编辑题槽 + 设置改动幅度
          └──────┬───────┘
                 ↓
          ┌──────────────┐
          │  Agent 4 ×N  │  asyncio.gather 并行生成
          │  并行题目生成 │
          └──────┬───────┘
                 ↓
          ┌──────────────┐
     ┌──→│ ⏸ 暂停点 2   │ ← 前端：教师逐题审核
     │   └──────┬───────┘
     │          │
     │  不满意（有 feedback）      满意
     │          ↓                   ↓
     │   ┌──────────────┐    ┌──────────────┐
     └───│ Agent 4 ×1   │    │    END       │
         │ 单题重新生成  │    │ 展示最终试卷  │
         └──────────────┘    └──────────────┘
```

---

## 三、各 Agent 详细设计

### 3.1 Agent 1：PDF 解析器

#### 职责
将原始 PDF 文件转换为结构化文字数据。这是整个系统的地基，其输出质量决定了后续所有 Agent 的上限。

#### 处理过程
1. 使用 PyMuPDF 将 PDF 的每一页渲染为 PNG 图片（200 DPI）
2. 多份 PDF 文件并发处理（asyncio.gather）
3. 将每页图片发送给视觉模型，让其识别页面上的所有内容
4. 视觉模型输出：文字内容、数学公式（LaTeX 格式）、图的文字描述
5. 合并多页结果，按题号切分为结构化数据

#### 视觉模型 Prompt（核心设计）

```
你是一名专业的试卷 OCR 助手。请仔细识别这张试卷图片中的所有内容，以 JSON 格式输出。

输出要求：
1. 数学公式、符号、方程：必须使用 LaTeX 语法，行内公式用 $...$，独立公式用 $$...$$
2. 图、表、电路图、示意图：不要试图描述像素，改用 [图: 简要文字描述] 占位符
3. 严格按以下 JSON schema 输出，不要有多余说明文字

{
  "page_questions": [
    {
      "number": "题号",
      "type": "题型（填空题/判断题/选择题/计算题/证明题/问答题，无法判断则 null）",
      "points": 分值（整数，如无则 null）,
      "content": "完整题目正文（含 LaTeX 公式和图占位符）",
      "figure_descriptions": ["图1描述"],
      "answer": "参考答案（仅答案卷有，否则 null）",
      "scoring_criteria": ["给分点1", "给分点2"]
    }
  ],
  "section_title": "大题标题（若有，否则 null）",
  "is_answer_page": true 或 false
}

这是第 {page_num} 页，共 {total_pages} 页。
```

#### 关键技术决策
- **为什么用视觉模型而非文字提取**：PDF 文字提取对数学公式完全失效，视觉模型直接看渲染后的页面图片，能准确识别公式并输出 LaTeX
- **视觉模型选择**：Gemini via NewAPI 中台（OpenAI 兼容接口），免费额度高，对复杂数学公式识别准确，max_tokens=8192 避免复杂页面截断
- **JSON 解析容错**：三层兜底：直接解析 → 提取 ` ```json ``` ` 代码块 → 括号计数兜底；同时用 `_fix_latex_escapes` 处理单反斜杠 LaTeX

---

### 3.2 Agent 1.5：知识图谱提取器

#### 职责
从解析后的所有试题内容中，自动总结出课程的知识点结构和关联关系，写入 Neo4j 图数据库。此过程与出题流程完全解耦，知识图谱不参与后续出题环节，仅用于可视化展示。

#### 处理过程
1. 将 `parsed_exams` 中所有题目内容发给 DeepSeek
2. LLM 分析所有题目涉及的知识点、知识点之间的关联关系、每个知识点出现的频次
3. 后端 Python 代码调用 Neo4j driver 自动将节点和关系写入数据库

#### LLM Prompt 设计

```
你是一位课程知识结构分析专家。以下是《{课程名}》多年考试试题，请从中提取知识图谱。

要求：
1. 提取该课程的核心知识点（15-40个）
2. 标注每个知识点在历年试题中出现的频次
3. 标注知识点之间的关联关系（如"前置知识"、"相关知识"）
4. 知识点粒度适中：不要太粗（如"微波"），也不要太细（如"公式3.2"）

请按以下 JSON 格式输出：
{
  "course": "课程名",
  "knowledge_points": [
    {"id": "kp_001", "name": "知识点名称", "exam_frequency": 4, "description": "简述"}
  ],
  "relationships": [
    {"source": "kp_001", "target": "kp_002", "type": "RELATES_TO"}
  ]
}
```

#### Neo4j Schema

```cypher
(:Course { id: String, name: String, exam_count: Integer })
(:KnowledgePoint { id: String, name: String, description: String, exam_frequency: Integer })

(Course)-[:HAS_KNOWLEDGE_POINT]->(KnowledgePoint)
(KnowledgePoint)-[:RELATES_TO]->(KnowledgePoint)
```

---

### 3.3 Agent 2：题槽结构分析器

#### 职责
这是整个系统中最关键的 Agent。它需要将不同年份、格式可能不同、题号可能不对应的试卷，归并到统一的"题槽"结构中，并把历年题目精确映射到对应的题槽。

#### 核心难点
不能简单按题号对齐，需要按**知识点和题型**做语义匹配。例如：2021 年"第三题"和 2022 年"第四题"考的是同一个知识点，Agent 2 要识别出它们属于同一个题槽。

#### LLM Prompt 设计

```
你是一位考试出题结构分析专家。以下是《{course_name}》多年的考试试题，请分析其出题结构。

任务：
1. 识别该课程历年考试的固定题槽结构（几大题、每题类型、分值）
2. 将不同年份的题目按知识点和题型对齐到统一的题槽中
3. 注意：不同年份的题号可能不对应，要按内容语义匹配
4. 如果某个题槽在某一年没有对应题目，history 中可以不包含该年

历年试题：
[2021年]（文件：xxx.pdf）
  ...
[2022年]（文件：yyy.pdf）
  ...

请按以下 JSON 格式输出：
{
  "course_name": "课程名",
  "total_points": 100,
  "slots": [
    {
      "slot_id": 1,
      "type": "题型",
      "points": 20,
      "typical_sub_count": 5,
      "knowledge_focus": ["知识点1", "知识点2"],
      "history": [
        {
          "year": 2021,
          "original_number": "试题一",
          "content": "完整题目文字...",
          "answer": "答案（如有）",
          "scoring_criteria": ["评分标准（如有）"],
          "has_figure": false,
          "figure_descriptions": []
        }
      ]
    }
  ]
}
```

---

### 3.4 暂停点 1：教师确认与编辑题槽

前端展示 Agent 2 输出的题槽列表，教师可以：

| 操作 | 说明 |
|------|------|
| 查看题槽 | 每个题槽展示：类型、分值、知识点标签、历年题目折叠预览（n 题） |
| 编辑题槽 | 修改类型、分值、知识点标签 |
| 设置改动幅度 | 全局选择：小改 / 中改 / 大改 |
| 确认出题 | 提交后触发 Agent 4 并行生成 |

**改动幅度含义**：

| 级别 | 含义 | Prompt 中的指令 |
|------|------|----------------|
| 小改 | 仅改数值/参数，保持题型和基本场景不变 | "保持与往年相似，主要改变具体数值和参数" |
| 中改 | 相同知识点，换一种考法或场景 | "保持考察相同知识点，但换一种出题角度或场景" |
| 大改 | 知识点相同，题目全新设计 | "在相同知识领域内全新设计题目，风格可以较大不同" |

---

### 3.5 Agent 4：题目生成器

#### 职责
为每个题槽生成一道新题目（含参考答案和评分标准）。每个题槽独立调用一次 LLM，多个题槽 async 并行。

#### Prompt 设计

```
你是一位专业的高校出题教师。

【任务】为以下题槽生成一道新题目，同时提供参考答案和评分标准。

【题槽信息】
类型：{type} | 分值：{points}分 | 小题数量：约{typical_sub_count}个（如适用）

【改动幅度】{modification_level_description}

【往年该题槽的题目（请参考这些来出新题）】
--- {year1}年 ---
{content1}
参考答案：{answer1}
评分标准：{scoring_criteria1}

【其他题槽已覆盖的知识点（请避免重复）】
- 题槽1：传输线特征阻抗、驻波比
- ...

【特殊要求】
1. 公式使用 LaTeX 格式，行内用 $...$，独立公式用 $$...$$
2. 若往年题有图，优先改为不需要图的纯文字题目
3. 若必须复用图，标注"[复用{year}年{题号}图]"
4. 参考答案要有完整的解题步骤

【输出前自检（重要）】
在输出 JSON 之前，先默默检查：
① 题目内部数据是否自洽（数值计算是否无矛盾）
② 参考答案与题目给定条件是否完全对应
③ 题目设定的物理/工程情形是否符合现实常识
④ 若涉及多个小问，各小问之间是否逻辑一致

请按以下 JSON 格式输出：
{
  "slot_id": {slot_id},
  "type": "{type}",
  "points": {points},
  "content": "题目内容（LaTeX 格式）",
  "answer": "参考答案（含步骤，LaTeX 格式）",
  "scoring_criteria": ["得分点1（X分）", "得分点2（X分）"],
  "reused_figure": null
}
```

---

### 3.6 暂停点 2：教师逐题审核与反馈

前端展示所有生成的题目，每道题卡片包含：
- 题目内容（KaTeX 渲染 LaTeX 公式）
- 参考答案与评分标准
- 操作：✅ 满意 / 💬 不满意（展开反馈输入框）

不满意时输入具体意见后点击"重新生成这道"，系统仅重新调用该题槽的 Agent 4，其他题目不受影响。

---

## 四、功能模块说明

### 4.1 v1 功能模块（知识图谱出题）

| 模块 | 功能 | 状态 |
|------|------|------|
| 首页 | 品牌展示、双模式入口 | ✅ 已实现 |
| 课程选择 | 选择要出题的课程 | ✅ 已实现 |
| 知识图谱可视化 | 力导向图展示，支持节点选择 | ✅ 已实现 |
| 出题配置 | 选择题型、难度、数量 | ✅ 已实现 |
| 题目生成与展示 | 单次 LLM 生成，结果展示 | ✅ 已实现 |
| 题目编辑 | 修改题干、答案、评分点 | ✅ 已实现 |
| 题目导出 | 导出为 Markdown 文件 | ✅ 已实现 |

### 4.2 v2 功能模块（多 Agent 往年题出题）

| 模块 | 路由 | 状态 |
|------|------|------|
| PDF 上传页 | `/agent/upload` | ✅ 已实现 |
| 解析进度页 | `/agent/parsing` | ✅ 已实现 |
| 题槽确认页 | `/agent/slots` | ✅ 已实现 |
| 试卷草稿页 | `/agent/draft` | ✅ 已实现 |
| 知识图谱页 | `/agent/knowledge` | ✅ 已实现 |

---

## 五、前端设计

### 5.1 首页改造

```
┌────────────────────────────────────────────────────────────────┐
│              基于大模型与知识图谱的智能出题系统                    │
│                                                                │
│  ┌──────────────────────────┐    ┌──────────────────────────┐  │
│  │    根据知识图谱生题        │    │    根据往年题智能出题      │  │
│  │    (单 LLM，快速)         │    │    (多 Agent，高质量)     │  │
│  │                          │    │                          │  │
│  │  适合：快速生成练习题       │    │  适合：出期中/期末试卷     │  │
│  │  无需往年题                │    │  需要上传往年题 PDF       │  │
│  └──────────────────────────┘    └──────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### 5.2 PDF 上传页（v2）

- Element Plus 的 `el-upload` 组件，支持拖拽上传
- 仅支持 PDF 格式，可一次上传多个文件
- 上传后展示文件列表，教师可删除误上传的文件
- 点击"开始解析"触发 Agent 1

### 5.3 解析进度页（v2）

- 进度条展示：正在解析第 X / N 页
- 实时展示已解析的试卷列表（通过轮询 API）
- 全部解析完成后自动触发 Agent 1.5 + Agent 2，结束后跳转到题槽确认页

### 5.4 题槽确认页（v2）

- 每个题槽一个卡片，展示：题型（可编辑）、分值（可编辑）、知识点标签（可增删）、历年题目折叠预览（n 题）
- 底部固定：改动幅度选择（小改/中改/大改）+ "开始生成"按钮

### 5.5 试卷草稿页（v2）

- 每道题一个卡片，KaTeX 渲染所有 LaTeX 公式
- 每道题底部：满意 / 不满意操作
- 不满意时展开反馈输入框 + "重新生成这道"按钮（通过轮询等待结果更新）
- 顶部汇总：总分、题目数量

### 5.6 公式渲染方案

前端封装 `<LatexRenderer>` Vue 组件，使用 KaTeX：
- 行内公式 `$...$` → 行内渲染
- 独立公式 `$$...$$` → 块级渲染
- 对不支持的语法优雅降级，显示原始 LaTeX 文本

### 5.7 v1 知识图谱页面

- 力导向图（ECharts）展示课程知识结构
- 节点：章节节点（大）+ 知识点节点（小，大小代表考频）
- 交互：悬停显示详情，点击选中/取消，拖拽调整布局，滚轮缩放
- 侧边栏：出题配置面板（题型、难度、数量）

---

## 六、后端 API 设计

### 6.1 v1 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/courses` | 获取课程列表 |
| GET | `/api/courses/{course_id}/graph` | 获取课程知识图谱 |
| POST | `/api/questions/generate` | 生成题目 |
| POST | `/api/questions/save` | 保存题目到 Neo4j |
| PUT | `/api/questions/{question_id}` | 更新题目 |

### 6.2 v2 API（`/api/agent/` 前缀，与 v1 隔离）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/agent/upload` | 上传 PDF 文件 |
| POST | `/api/agent/parse` | 启动 Agent 1 解析 |
| GET | `/api/agent/parse/result` | 查询解析进度与结果 |
| POST | `/api/agent/analyze` | 启动 Agent 2 题槽分析 |
| GET | `/api/agent/analyze/result` | 获取题槽分析结果 |
| POST | `/api/agent/generate` | 启动 Agent 4 题目生成 |
| GET | `/api/agent/generate/result` | 获取生成结果与进度 |
| POST | `/api/agent/regenerate` | 单题反馈重新生成 |
| GET | `/api/agent/knowledge-graph` | 获取知识图谱数据 |

#### 关键 API 示例

**上传 PDF**
```
POST /api/agent/upload (multipart/form-data)
→ { "session_id": "uuid-xxx", "files": [{"filename": "...", "pages": 7}] }
```

**启动解析**
```
POST /api/agent/parse
{ "session_id": "uuid-xxx" }
→ { "message": "解析已启动", "session_id": "uuid-xxx" }
```

**查询进度**
```
GET /api/agent/parse/result?session_id=uuid-xxx
→ { "status": "parsing"/"done"/"error", "parsed_pages": 20, "total_pages": 35, ... }
```

**触发单题重生成**
```
POST /api/agent/regenerate
{ "session_id": "uuid-xxx", "slot_id": 3, "feedback": "太简单了，加大难度" }
→ { "message": "正在重新生成第3题" }
```

---

## 七、数据结构设计

### 7.1 v1 Neo4j Schema

```cypher
(:Course { id: String, name: String, description: String })
(:Chapter { id: String, name: String, order: Integer })
(:KnowledgePoint { id: String, name: String, description: String, keywords: [String] })
(:Question { id: String, type: String, difficulty: String, content: String,
             options: String, answer: String, explanation: String,
             scoring_points: String, created_at: DateTime, source: String })

(Course)-[:HAS_CHAPTER]->(Chapter)
(Chapter)-[:CONTAINS]->(KnowledgePoint)
(KnowledgePoint)-[:RELATES_TO]->(KnowledgePoint)
(Question)-[:TESTS]->(KnowledgePoint)
```

### 7.2 v2 Neo4j Schema

```cypher
(:Course { id: String, name: String, exam_count: Integer })
(:KnowledgePoint { id: String, name: String, description: String, exam_frequency: Integer })

(Course)-[:HAS_KNOWLEDGE_POINT]->(KnowledgePoint)
(KnowledgePoint)-[:RELATES_TO]->(KnowledgePoint)
```

### 7.3 会话状态存储

使用 Python 字典（in-memory `sessions: dict[str, ExamState]`）以 `session_id` 为 key 存储会话状态，支持跨 API 请求的状态传递。

---

## 八、日志系统

系统实现双层日志，输出到 `log/` 目录：

| 文件 | 内容 | 说明 |
|------|------|------|
| `log/app.log` | 系统运行日志（INFO/WARNING/ERROR） | 每日轮转，保留 30 天 |
| `log/llm.log` | **所有 LLM/VLM 完整输入输出** | 不截断，方便调试 prompt 效果 |

`llm.log` 记录格式：
```
================================================================================
[时间戳]  MODEL: gemini-3-flash-preview  TAG: Agent1/vision_parse
================================================================================
>>> PROMPT >>>
{完整 prompt 内容}

<<< RESPONSE <<<
{完整模型输出}
================================================================================
```

---

## 九、里程碑计划

| 里程碑 | 目标 | 状态 |
|--------|------|------|
| M1 | Agent 1：PDF 解析器（单页调用视觉模型、JSON 提取） | ✅ 完成 |
| M2 | Agent 2：题槽分析器（跨年度语义对齐） | ✅ 完成 |
| M3 | Agent 4：题目生成器（并行生成、改动幅度、单题重生成） | ✅ 完成 |
| M4 | 后端串联（FastAPI + 会话状态 + 全流程 API） | ✅ 完成 |
| M5 | 前端开发（全部页面、KaTeX 渲染、题槽编辑） | ✅ 完成 |
| M6 | Agent 1.5 + 知识图谱可视化页面 | ✅ 完成 |
| M7 | 系统调试与优化（视觉模型切换、JSON 解析容错、日志系统） | 🔄 进行中 |
| M8 | 端到端多科目测试、论文撰写、答辩准备 | ⬜ 待开始 |

---

## 十、非功能需求

### 10.1 性能需求

| 指标 | 要求 |
|------|------|
| 首页加载时间 | < 2 秒 |
| 知识图谱渲染 | < 3 秒（50 个节点） |
| PDF 解析速度 | 约 5-10 秒/页（视觉模型限制） |
| 题目生成时间 | < 60 秒（7 题并行） |
| 单题重生成时间 | 10-20 秒 |

### 10.2 兼容性需求

| 类型 | 要求 |
|------|------|
| 浏览器 | Chrome 90+, Firefox 90+, Edge 90+ |
| 分辨率 | 最小支持 1280×720 |
| 设备 | 桌面端优先（暂不适配移动端） |

### 10.3 可靠性需求

- LLM/VLM 调用失败自动重试（最多 2 次）
- JSON 解析三层兜底（直接解析 → 代码块提取 → 括号计数 → LaTeX 转义修复）
- 视觉模型通过 NewAPI 中台，支持自动降级和失败重试

---

## 十一、风险与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| 视觉模型对复杂公式识别不准 | 中 | 高 | 选用 Gemini 等高质量模型；三层 JSON 解析兜底；fix_latex_escapes 修复 |
| Agent 2 跨年度对齐出错 | 中 | 中 | 暂停点 1 让教师检查和编辑 |
| 生成的题目有逻辑错误或不自洽 | 中 | 中 | Prompt 内置自检指令（检查数据自洽、答案对应、物理常识） |
| 含图题目无法完美处理 | 高 | 中 | Prompt 引导倾向生成无图题；支持复用原图标注 |
| LLM 生成质量不稳定 | 中 | 中 | 人在环反馈机制；支持单题重新生成 |
| API 调用成本 | 低 | 低 | 视觉模型使用免费额度较高的模型；DeepSeek 成本较低 |

---

## 十二、项目目录结构

```
g:\biyesheji\
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── courses.py        # v1 路由
│   │   │   ├── knowledge.py      # v1 路由
│   │   │   ├── questions.py      # v1 路由
│   │   │   └── agent.py          # v2 多 Agent API 路由
│   │   ├── agents/               # v2 Agent 相关代码
│   │   │   ├── state.py          # ExamState 类型定义
│   │   │   ├── parser.py         # Agent 1：PDF 解析器
│   │   │   ├── kg_extractor.py   # Agent 1.5：知识图谱提取
│   │   │   ├── slot_analyzer.py  # Agent 2：题槽分析器
│   │   │   └── question_generator.py  # Agent 4：题目生成器
│   │   ├── core/
│   │   │   ├── config.py         # 配置（含视觉模型 API 配置）
│   │   │   └── logging.py        # 双层日志（app.log + llm.log）
│   │   ├── services/
│   │   │   ├── llm_service.py    # DeepSeek API 封装
│   │   │   └── vision_service.py # 视觉模型 API 封装（OpenAI SDK）
│   │   └── main.py
│   ├── uploads/                  # 用户上传的 PDF 存放目录
│   ├── .env                      # API Key 配置
│   └── run.py
│
├── frontend/
│   └── src/
│       ├── views/
│       │   ├── Home.vue           # 首页（两个入口按钮）
│       │   ├── CourseSelect.vue   # v1 课程选择
│       │   ├── KnowledgeGraph.vue # v1 知识图谱
│       │   ├── QuestionResult.vue # v1 题目结果
│       │   ├── AgentUpload.vue    # v2 上传页
│       │   ├── AgentParsing.vue   # v2 解析进度页（含知识图谱展示）
│       │   ├── AgentSlots.vue     # v2 题槽确认页
│       │   ├── AgentDraft.vue     # v2 试卷草稿页
│       │   └── AgentGraph.vue     # v2 知识图谱可视化页
│       ├── components/
│       │   ├── LatexRenderer.vue  # LaTeX 公式渲染组件
│       │   └── ConfigPanel.vue    # v1 出题配置面板
│       ├── api/
│       │   ├── index.js           # v1 API
│       │   └── agent.js           # v2 API
│       └── stores/
│           ├── graph.js           # v1 状态
│           └── agent.js           # v2 状态
│
├── log/
│   ├── app.log                    # 系统运行日志
│   └── llm.log                    # LLM/VLM 完整输入输出日志
│
└── docs/
    └── PRD.md                     # 本文档（v1 + v2 合并版）
```

---

## 十三、依赖清单

### 后端 Python 包

| 包名 | 用途 |
|------|------|
| fastapi | Web 框架 |
| uvicorn | ASGI 服务器 |
| pydantic-settings | 配置管理 |
| neo4j | Neo4j Python 驱动 |
| openai | OpenAI SDK（兼容 DeepSeek / NewAPI） |
| httpx | 异步 HTTP（历史遗留） |
| PyMuPDF (fitz) | PDF 页面渲染为图片 |
| python-multipart | 文件上传支持 |
| python-dotenv | .env 文件加载 |

### 前端 npm 包

| 包名 | 用途 |
|------|------|
| vue | 前端框架 |
| element-plus | UI 组件库 |
| pinia | 状态管理 |
| axios | HTTP 客户端 |
| echarts | 知识图谱力导向图 |
| katex | LaTeX 公式渲染 |

---

## 十四、版本记录

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| v1.0 | 2024-12-12 | 初始版本：知识图谱 + 单 LLM 出题模式 |
| v2.0 | 2026-03 | 新增多 Agent 往年题驱动模式：Agent 1/1.5/2/4 + 人在环反馈 + KaTeX 渲染 + 日志系统 |

---

**文档结束**
