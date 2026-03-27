# 智能出题系统 v2 — 基于往年题的多 Agent 智能出题

## 产品需求文档 (Product Requirements Document)

**项目名称**：基于大模型与知识图谱的智能出题系统（v2：多 Agent 往年题驱动模式）  
**版本**：v2.0  
**作者**：北京邮电大学电子工程学院 周奕君  
**日期**：2026 年 3 月  

---

## 一、产品概述

### 1.1 产品背景

高校期中/期末出题的现实流程是：负责出题的教师参考电脑里的 N 年往年真题 PDF，在此基础上进行或大或小的改动，最终形成一套新试卷。不同年份基本不会有完全一样的原题，但大部分题目是往年题的变式——有的只改数据，有的换一种考法，有的在同一知识点上全新设计。

现有系统（v1）采用"知识图谱 + 单 LLM"模式从零生成题目，与实际出题流程脱节。v2 版本引入多 Agent 架构，以往年真题为蓝本，自动解析试卷结构、对齐题槽、按可控的改动幅度生成变式新题，真正贴合高校教师的实际工作流。

### 1.2 产品定位

面向高校教师的智能出题辅助工具。教师上传历年真题 PDF，系统自动分析出题结构和规律，生成一套"保底相似度、可控改动幅度"的新试卷草稿，教师逐题审核和反馈后得到最终结果。

### 1.3 产品目标

1. **贴合实际**：以往年真题为锚点，而非从零生成
2. **质量可控**：教师可设置改动幅度（小改/中改/大改）
3. **人在环中**：教师可审核每道题，对不满意的题目给出具体反馈并重新生成
4. **公式友好**：正确识别和渲染 LaTeX 数学公式
5. **知识图谱**：从往年题中自动提取课程知识图谱，可视化展示考点频次

### 1.4 与 v1 的关系

v2 与 v1 共存于同一个系统中：
- 首页提供两个入口按钮
- 左侧按钮"根据知识图谱生题"→ 进入现有 v1 逻辑（保持不动）
- 右侧按钮"根据往年题智能出题"→ 进入 v2 多 Agent 新流程
- v2 新增的后端代码与 v1 在路由层隔离（不同 prefix），互不影响

---

## 二、目标用户与使用场景

### 2.1 目标用户

高校教师，尤其是：
- 每学期需出期中/期末试卷的课程负责教师
- 手里积攒了多年往年真题 PDF 的教师
- 希望在往年题基础上高效产出新卷的教师

### 2.2 核心使用场景

**场景**：微波工程课程的李老师要出今年的期中试卷。

1. 李老师把 2020-2024 年共 5 份期中试卷 PDF 上传到系统
2. 系统自动解析每份试卷的所有题目（含公式和图的描述）
3. 系统分析出该课程固定的题槽结构（填空 20 分 + 简答 20 分 + 计算题×4 + 证明题 15 分）
4. 李老师确认题槽结构、设置改动幅度为"中改"
5. 系统并行生成 7 个题槽的新题目
6. 李老师逐题审核，对第 3 题不满意："这道太简单了，加大难度"
7. 系统仅重新生成第 3 题，李老师满意
8. 最终试卷在页面上完整展示（含 LaTeX 公式渲染），李老师自行复制到 Word

---

## 三、系统架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + Element Plus)                │
│         KaTeX 公式渲染 · 文件上传 · 题槽编辑 · 反馈交互       │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/REST + SSE(进度推送)
┌────────────────────────────┴────────────────────────────────┐
│                    后端 (FastAPI + LangGraph)                 │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Agent 1  │→│ Agent 1.5│→│ Agent 2  │→│ Agent 4  │    │
│  │ PDF解析  │  │知识图谱  │  │题槽分析  │  │题目生成  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│       ↑              ↓                          ↑↓           │
│   视觉模型       Neo4j 图数据库           人在环(反馈循环)     │
│  (Qwen-VL)                                                   │
│                                                              │
│  LLM: DeepSeek API (题槽分析 + 知识图谱提取 + 题目生成)       │
│  视觉模型: Qwen-VL-Max (PDF 页面识别)                         │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 前端框架 | Vue 3 | 3.5+ | Composition API |
| UI 组件库 | Element Plus | 2.13+ | 表单/按钮/对话框 |
| 公式渲染 | KaTeX | latest | 前端 LaTeX 公式渲染 |
| 状态管理 | Pinia | 3.0+ | 全局状态 |
| HTTP 客户端 | Axios | 1.13+ | API 请求 |
| 构建工具 | Vite | 7.2+ | 开发服务器和打包 |
| 后端框架 | FastAPI | 0.125+ | Python 异步 Web 框架 |
| Agent 编排 | LangGraph | latest | 多 Agent DAG + 人在环 |
| 图数据库 | Neo4j | 5.x | 知识图谱存储与可视化 |
| 大语言模型 | DeepSeek API | deepseek-chat | 题槽分析/知识图谱/题目生成 |
| 视觉模型 | 通义千问 Qwen-VL-Max | latest | PDF 页面识别（含公式/图） |
| PDF 处理 | PyMuPDF (fitz) | latest | PDF 页面渲染为图片 |
| Python | Python | 3.11+ | 后端运行时 |

### 3.3 LangGraph 状态设计

```python
from typing import TypedDict, Optional

class ExamState(TypedDict):
    # 用户上传的 PDF 文件路径列表
    pdf_paths: list[str]

    # Agent 1 输出：解析后的试卷数据
    parsed_exams: list[dict]
    # 结构: [{
    #   "filename": str,
    #   "year": int,
    #   "course_name": str,
    #   "is_answer_sheet": bool,
    #   "raw_questions": [{
    #     "number": int,
    #     "type": str,           # "填空题" / "计算题" / "证明题" / ...
    #     "points": int,
    #     "content": str,        # LaTeX 格式
    #     "figure_descriptions": list[str],
    #     "answer": Optional[str],
    #     "scoring_criteria": Optional[list[str]]
    #   }]
    # }]

    # Agent 2 输出：题槽模板（跨年度对齐后）
    slot_template: list[dict]
    # 结构: [{
    #   "slot_id": int,
    #   "type": str,
    #   "points": int,
    #   "typical_sub_count": Optional[int],
    #   "knowledge_focus": list[str],
    #   "history": [{
    #     "year": int,
    #     "content": str,          # 该年该题槽的完整题目文字
    #     "answer": Optional[str],
    #     "scoring_criteria": Optional[list[str]],
    #     "figure_descriptions": list[str]
    #   }]
    # }]

    # 用户在暂停点1设置的改动幅度
    modification_level: str  # "small" / "medium" / "large"

    # Agent 4 输出：生成的新题目
    generated_questions: list[dict]
    # 结构: [{
    #   "slot_id": int,
    #   "type": str,
    #   "points": int,
    #   "content": str,           # LaTeX 格式
    #   "answer": str,
    #   "scoring_criteria": Optional[list[str]],
    #   "reused_figure": Optional[str]  # "2021年试题三图" / null
    # }]

    # 用户对某道题的反馈（用于重新生成）
    feedback: Optional[dict]
    # 结构: {"slot_id": int, "message": str} / None
```

### 3.4 LangGraph 流程图

```
          ┌──────────────┐
          │  START        │
          │  接收 PDF 列表│
          └──────┬───────┘
                 ↓
          ┌──────────────┐
          │   Agent 1    │
          │  PDF 解析    │
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
          │ ⏸️ 暂停点 1   │  interrupt()
          │ 教师确认/编辑 │  ← 前端提交确认 + modification_level
          │ 题槽结构     │
          └──────┬───────┘
                 ↓
          ┌──────────────┐
          │  Agent 4 ×N  │
          │  并行题目生成 │  asyncio.gather
          └──────┬───────┘
                 ↓
          ┌──────────────┐
     ┌──→│ ⏸️ 暂停点 2   │  interrupt()
     │   │ 教师逐题审核  │  ← 前端提交反馈或确认
     │   └──────┬───────┘
     │          │
     │   不满意（有feedback）    满意（无feedback）
     │          ↓                      ↓
     │   ┌──────────────┐      ┌──────────────┐
     │   │ Agent 4 ×1   │      │    END       │
     └───│ 单题重新生成  │      │  展示最终试卷 │
         └──────────────┘      └──────────────┘
```

---

## 四、各 Agent 详细设计

### 4.1 Agent 1：PDF 解析器

#### 职责
将原始 PDF 文件转换为结构化文字数据。这是整个系统的地基，其输出质量决定了后续所有 Agent 的上限。

#### 处理过程
1. 使用 PyMuPDF 将 PDF 的每一页渲染为 PNG 图片（分辨率 200-300 DPI）
2. 将每页图片发送给视觉模型（Qwen-VL-Max），让其识别页面上的所有内容
3. 视觉模型输出：文字内容、数学公式（LaTeX 格式）、图的文字描述
4. 判断该 PDF 是题目卷还是答案卷（根据文件名关键词或页面标题）
5. 合并多页结果，按题号切分为结构化数据

#### 视觉模型 Prompt 设计

```
你是一位专业的试卷 OCR 助手。请识别以下考试试卷页面的所有内容。

要求：
1. 所有数学公式使用 LaTeX 格式输出，用 $ 包裹行内公式，用 $$ 包裹独立公式
2. 如果页面有图（电路图、函数图、结构图等），用文字详细描述图的内容，
   格式为 [图: 描述内容]
3. 保持题号结构，清楚标注每道题的题号、分值
4. 如果是答案卷，保持答案与题号的对应关系
5. 表格内容用 Markdown 表格格式输出

请按以下 JSON 格式输出：
{
  "page_number": 1,
  "questions": [
    {
      "number": "试题一",
      "type": "填空题",
      "points": 20,
      "content": "题目内容（含 LaTeX 公式）",
      "figures": ["图的文字描述"],
      "answer": "答案（如果有）",
      "scoring_criteria": ["评分标准（如果有）"]
    }
  ]
}
```

#### 输入
- 用户上传的 PDF 文件列表

#### 输出
- `State.parsed_exams`：结构化试卷数据列表

#### 关键技术决策
- **为什么用视觉模型而非文字提取**：PDF 文字提取（PyMuPDF / pdfplumber）对数学公式完全失效，提取出来的是乱排的字符碎片。视觉模型直接看渲染后的页面图片，能准确识别公式并输出 LaTeX。
- **视觉模型选择**：Qwen-VL-Max 对中文试卷识别效果好，成本约 0.01-0.02 元/页。也可替换为 Gemini 2.0 Flash（免费额度高）。
- **处理速度**：每页约 5-10 秒。5 年 × 7 页 = 35 页，总耗时约 3-6 分钟。需要前端展示进度条。

---

### 4.2 Agent 1.5：知识图谱提取器

#### 职责
从解析后的所有试题内容中，自动总结出课程的知识点结构和关联关系，写入 Neo4j 图数据库。此过程与出题流程完全解耦，知识图谱不参与后续出题环节，仅用于可视化展示。

#### 处理过程
1. 将 `parsed_exams` 中所有题目内容发给 DeepSeek
2. LLM 分析所有题目涉及的知识点、知识点之间的关联关系、每个知识点出现的频次
3. 输出结构化 JSON
4. 后端 Python 代码调用 Neo4j driver 自动将节点和关系写入数据库

#### LLM Prompt 设计

```
你是一位课程知识结构分析专家。以下是《{课程名}》多年考试试题，请从中提取知识图谱。

要求：
1. 提取该课程的核心知识点（15-40个）
2. 标注每个知识点在历年试题中出现的频次
3. 标注知识点之间的关联关系（如"前置知识"、"相关知识"）
4. 知识点粒度适中：不要太粗（如"微波"），也不要太细（如"公式3.2"）

试题内容：
{所有试题的文字内容}

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

#### 输入
- `State.parsed_exams`

#### 输出
- JSON → 自动写入 Neo4j（不进 State）
- Neo4j 中创建的节点：`(:Course)`, `(:KnowledgePoint {name, exam_frequency})`
- Neo4j 中创建的关系：`(:KnowledgePoint)-[:RELATES_TO]->(:KnowledgePoint)`

#### 前端可视化
复用 v1 现有的力导向图组件（ECharts），节点大小代表考频，颜色深浅代表难度。

---

### 4.3 Agent 2：题槽结构分析器

#### 职责
这是整个系统中最关键的 Agent。它需要将不同年份、格式可能不同、题号可能不对应的试卷，归并到统一的"题槽"结构中，并把历年题目精确映射到对应的题槽。

#### 核心难点
不能简单按题号对齐，需要按**知识点和题型**做语义匹配。例如：
- 2021 年"试题五"和 2022 年"试题六"考的是同一个知识点（并联短路支节匹配），Agent 2 要识别出它们属于同一个题槽。

#### LLM Prompt 设计

```
你是一位考试出题结构分析专家。以下是《{课程名}》多年的考试试题，请分析其出题结构。

任务：
1. 识别该课程历年考试的固定题槽结构（几大题、每题类型、分值）
2. 将不同年份的题目按知识点和题型对齐到统一的题槽中
3. 注意：不同年份的题号可能不对应，要按内容语义匹配

历年试题：
[2021年]
{2021年全部题目}

[2022年]
{2022年全部题目}

...

请按以下 JSON 格式输出：
{
  "course_name": "课程名",
  "total_points": 100,
  "slots": [
    {
      "slot_id": 1,
      "type": "填空题",
      "points": 20,
      "typical_sub_count": 9,
      "knowledge_focus": ["传输线特征阻抗", "驻波比", "Smith圆图"],
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

#### 输入
- `State.parsed_exams`

#### 输出
- `State.slot_template`

#### 上下文预估
- 5 年 × 每份约 3000 tokens = 15,000 tokens
- Prompt 指令约 2,000 tokens
- 输出约 5,000 tokens
- **总计约 22,000 tokens**，远小于 DeepSeek 的 64K 上下文限制

---

### 4.4 暂停点 1：教师确认与编辑题槽

#### 交互设计

前端展示 Agent 2 输出的题槽列表，教师可以：

| 操作 | 说明 |
|------|------|
| 查看题槽 | 每个题槽展示：类型、分值、知识点标签、历年题目预览 |
| 编辑题槽 | 修改类型、分值、知识点标签 |
| 调整映射 | 将某年的某题从一个题槽移到另一个题槽 |
| 增删题槽 | 新增一个空题槽 / 删除不需要的题槽 |
| 设置改动幅度 | 全局滑块：小改 / 中改 / 大改 |
| 确认出题 | 提交后触发 Agent 4 |

#### 改动幅度含义

| 级别 | 含义 | Prompt 中的指令 |
|------|------|----------------|
| 小改 | 仅改数值/参数，保持题型和基本场景不变 | "保持与往年相似，主要改变具体数值和参数" |
| 中改 | 相同知识点，换一种考法或场景 | "保持考察相同知识点，但换一种出题角度或场景" |
| 大改 | 知识点相同，题目全新设计 | "在相同知识领域内全新设计题目，风格可以较大不同" |

#### 技术实现
- LangGraph 的 `interrupt()` 暂停执行
- 前端将用户编辑后的 `slot_template` + `modification_level` POST 到后端
- 后端调用 LangGraph 的 `resume()`，传入更新后的 State

---

### 4.5 Agent 4：题目生成器

#### 职责
为每个题槽生成一道新题目（含参考答案和评分标准）。每个题槽独立调用一次 LLM，多个题槽 async 并行。

#### 每次调用收到的上下文

```
你是一位专业的高校出题教师。

【任务】
为以下题槽生成一道新题目，同时提供参考答案和评分标准。

【题槽信息】
类型：{type}
分值：{points}分
小题数量：约{typical_sub_count}个（如适用）

【改动幅度】
{modification_level_description}

【往年该题槽的题目（请参考这些来出新题）】
--- {year1}年 ---
{content1}
参考答案：{answer1}
评分标准：{scoring_criteria1}

--- {year2}年 ---
{content2}
参考答案：{answer2}

【其他题槽已覆盖的知识点（请避免重复考察）】
- 题槽1：传输线特征阻抗、驻波比
- 题槽3：负载阻抗匹配
- ...

【特殊要求】
1. 公式使用 LaTeX 格式，行内用 $...$，独立公式用 $$...$$
2. 若往年题有图且你无法生成图，优先改为不需要图的纯文字题目
3. 若必须用图且往年有可复用的原图，标注"[复用{year}年{题号}图]"
4. 参考答案要有完整的解题步骤

请按以下 JSON 格式输出：
{
  "slot_id": {slot_id},
  "type": "{type}",
  "points": {points},
  "content": "题目内容（LaTeX 格式）",
  "answer": "参考答案（含步骤，LaTeX 格式）",
  "scoring_criteria": ["得分点1（X分）", "得分点2（X分）"],
  "reused_figure": null 或 "复用说明"
}
```

#### 并行调用

```python
async def generate_all_questions(state: ExamState) -> dict:
    slots = state["slot_template"]
    other_slots_summary = build_other_slots_summary(slots)

    tasks = [
        generate_one_question(slot, state, other_slots_summary)
        for slot in slots
    ]
    results = await asyncio.gather(*tasks)
    return {"generated_questions": results}
```

#### 上下文预估（每次调用）
- 当前题槽历年题目：约 2,000-5,000 tokens
- Prompt 指令 + 其他题槽摘要：约 1,500 tokens
- **总计约 4,000-7,000 tokens/次**，远在安全范围内

---

### 4.6 暂停点 2：教师逐题审核与反馈

#### 交互设计

前端展示所有生成的题目，每道题卡片包含：
- 题目内容（KaTeX 渲染 LaTeX 公式）
- 参考答案
- 评分标准
- 操作按钮：✅ 满意 / 💬 不满意

不满意时展开反馈输入框，教师输入具体意见后点击"重新生成这道"。

#### 反馈重新生成的 Prompt 追加

```
【上次生成的题目】
{previous_content}

【教师反馈】
{feedback_message}

请根据反馈重新生成该题槽的题目，保持同样的题型和分值。
```

#### 技术实现
- 每次反馈只重新调用该题槽的 Agent 4 节点（非并行，sequential）
- 更新 `State.generated_questions` 中对应 `slot_id` 的结果
- 循环直到所有题槽都被标记为"满意"或教师点击"确认出卷"

---

## 五、前端设计

### 5.1 新增页面

| 页面 | 路由 | 功能 |
|------|------|------|
| 首页（改造） | `/` | 两个入口按钮 |
| 上传页 | `/agent/upload` | 拖拽上传多个 PDF |
| 解析进度页 | `/agent/parsing` | Agent 1 处理进度展示 |
| 题槽确认页 | `/agent/slots` | Agent 2 结果展示 + 教师编辑 + 改动幅度设置 |
| 试卷草稿页 | `/agent/draft` | Agent 4 结果展示 + 逐题反馈 + KaTeX 渲染 |
| 知识图谱页 | `/agent/knowledge` | Agent 1.5 提取的知识图谱可视化 |

### 5.2 首页改造

```
┌─────────────────────────────────────────────────────────────────┐
│              基于大模型与知识图谱的智能出题系统                     │
│                                                                 │
│  ┌───────────────────────┐    ┌───────────────────────────┐     │
│  │   根据知识图谱生题     │    │   根据往年题智能出题       │     │
│  │   (单 LLM，快速)      │    │   (多 Agent，高质量)      │     │
│  │                       │    │                           │     │
│  │   适合：快速生成练习题  │    │   适合：出期中/期末试卷    │     │
│  │   无需往年题           │    │   需要上传往年题 PDF       │     │
│  └───────────────────────┘    └───────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 上传页

- Element Plus 的 `el-upload` 组件，支持拖拽上传
- 仅支持 PDF 格式
- 可一次上传多个文件
- 上传后展示文件列表，教师可删除误上传的文件
- 点击"开始解析"触发 Agent 1

### 5.4 解析进度页

- 进度条展示：正在解析第 X / N 页
- 实时展示已解析的试卷列表
- 全部解析完成后自动跳转到题槽确认页

### 5.5 题槽确认页

- 每个题槽一个卡片，展示：题型、分值、知识点标签、历年题目折叠预览
- 支持编辑题槽信息、调整映射、增删题槽
- 底部：改动幅度滑块 + "开始生成"按钮
- 侧边栏：知识图谱可视化入口链接

### 5.6 试卷草稿页

- 每道题一个卡片
- KaTeX 渲染所有 LaTeX 公式
- 每道题底部：满意/不满意操作
- 不满意时展开反馈输入框 + "重新生成这道"按钮
- 顶部汇总信息：总分、题目数量
- 全部满意后："确认完成"按钮

### 5.7 公式渲染方案

前端引入 KaTeX 库：
- 行内公式 `$...$` → `katex.renderToString()`
- 独立公式 `$$...$$` → 块级渲染
- 可封装为 Vue 组件 `<LatexRenderer :text="content" />`

---

## 六、后端 API 设计

### 6.1 新增 API 列表

所有新 API 以 `/api/agent/` 为前缀，与 v1 的 `/api/` 隔离。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/agent/upload` | 上传 PDF 文件 |
| POST | `/api/agent/parse` | 启动 Agent 1 解析 |
| GET | `/api/agent/parse/status` | 查询解析进度 |
| GET | `/api/agent/parse/result` | 获取解析结果 |
| GET | `/api/agent/slots` | 获取 Agent 2 的题槽分析结果 |
| POST | `/api/agent/slots/confirm` | 教师确认/编辑后的题槽 + 改动幅度 |
| GET | `/api/agent/generate/status` | 查询题目生成进度 |
| GET | `/api/agent/draft` | 获取生成的试卷草稿 |
| POST | `/api/agent/feedback` | 提交对某道题的反馈 |
| POST | `/api/agent/regenerate` | 触发单题重新生成 |
| GET | `/api/agent/knowledge-graph` | 获取提取的知识图谱数据 |

### 6.2 关键 API 详细设计

#### 6.2.1 上传 PDF

```
POST /api/agent/upload
Content-Type: multipart/form-data

参数：files (多个 PDF 文件)

响应：
{
  "success": true,
  "session_id": "uuid-xxx",
  "files": [
    {"filename": "微波2021.pdf", "pages": 7, "size_kb": 320},
    {"filename": "微波2022.pdf", "pages": 8, "size_kb": 380}
  ]
}
```

#### 6.2.2 启动解析

```
POST /api/agent/parse
{
  "session_id": "uuid-xxx"
}

响应：
{
  "success": true,
  "message": "解析已启动",
  "total_pages": 35
}
```

#### 6.2.3 查询解析进度

```
GET /api/agent/parse/status?session_id=uuid-xxx

响应：
{
  "status": "parsing",          // "parsing" / "analyzing_slots" / "done"
  "parsed_pages": 20,
  "total_pages": 35,
  "current_file": "微波2022.pdf"
}
```

#### 6.2.4 确认题槽

```
POST /api/agent/slots/confirm
{
  "session_id": "uuid-xxx",
  "slot_template": [...],       // 教师编辑后的题槽模板
  "modification_level": "medium"
}

响应：
{
  "success": true,
  "message": "开始生成题目",
  "slot_count": 7
}
```

#### 6.2.5 提交反馈并重新生成

```
POST /api/agent/feedback
{
  "session_id": "uuid-xxx",
  "slot_id": 3,
  "message": "这道题太简单了，加大难度，考察Smith圆图"
}

响应：
{
  "success": true,
  "message": "正在重新生成第3题"
}
```

---

## 七、数据结构设计

### 7.1 Neo4j 知识图谱 Schema（Agent 1.5 写入）

#### 节点类型

```cypher
(:Course {
  id: String,
  name: String,
  exam_count: Integer
})

(:KnowledgePoint {
  id: String,
  name: String,
  description: String,
  exam_frequency: Integer
})
```

#### 关系类型

```cypher
(Course)-[:HAS_KNOWLEDGE_POINT]->(KnowledgePoint)
(KnowledgePoint)-[:RELATES_TO]->(KnowledgePoint)
```

### 7.2 会话状态存储

使用 LangGraph 内置的 Checkpoint 机制，以 `session_id` 为 key：
- 开发阶段：`MemorySaver`（内存存储）
- 生产阶段：可替换为 `SqliteSaver` 或 `PostgresSaver`

每个会话的完整 State 会在每次暂停点自动持久化，即使用户刷新页面也能恢复。

---

## 八、开发里程碑

### 里程碑 1：Agent 1 — PDF 解析（基础）

**目标**：能把一份 PDF 准确解析为结构化 JSON。

**开发内容**：
- PDF 页面渲染为图片（PyMuPDF）
- 调用 Qwen-VL-Max API 识别每页内容
- 解析 LLM 返回的 JSON
- 合并多页结果、按题号切分
- 判断试题卷/答案卷
- 答案卷与试题卷的题目关联

**验证标准**：
- 用微波工程 2021、2022 两份 PDF 测试
- 手动比对解析结果与原 PDF，公式准确率 > 90%
- 能正确区分试题卷和答案卷

**预估工时**：2-3 天

---

### 里程碑 2：Agent 2 — 题槽分析（核心）

**目标**：能从多年解析结果中识别出稳定的题槽结构，并正确映射历年题目。

**开发内容**：
- Prompt 设计（跨年度语义对齐）
- 解析 LLM 返回的题槽 JSON
- 验证映射合理性的辅助逻辑

**验证标准**：
- 用微波工程 2021+2022 测试
- 能识别出 7 个题槽
- 跨年度对齐正确（如2021题五→2022题六）

**预估工时**：1-2 天

---

### 里程碑 3：Agent 4 — 单题生成（核心）

**目标**：给定一个题槽和历年题目，能生成质量合格的新题。

**开发内容**：
- Prompt 设计（含改动幅度指令、其他题槽摘要）
- 并行调用框架（asyncio.gather）
- 反馈重新生成逻辑

**验证标准**：
- 生成微波工程填空题、计算题各一道
- 人工评估：知识点准确、难度合理、公式正确
- 小改/中改/大改三种幅度有明显区别

**预估工时**：1-2 天

---

### 里程碑 4：LangGraph 串联（整合）

**目标**：用 LangGraph 将所有 Agent 串联为完整流程，包含两个暂停点。

**开发内容**：
- State 类型定义
- LangGraph 节点注册与边连接
- interrupt/resume 机制
- 会话状态持久化（MemorySaver）
- 后端 API 路由（与 LangGraph 交互）

**验证标准**：
- 命令行可跑通完整流程：上传→解析→题槽分析→生成→反馈→重新生成
- 暂停和恢复机制正常工作

**预估工时**：2-3 天

---

### 里程碑 5：前端开发（体验）

**目标**：完整的前端交互界面。

**开发内容**：
- 首页改造（两个入口）
- 上传页（el-upload 拖拽上传 PDF）
- 解析进度页（进度条 + 轮询状态）
- 题槽确认页（展示 + 编辑 + 改动幅度滑块）
- 试卷草稿页（KaTeX 渲染 + 逐题反馈 UI）
- 新增路由、Pinia store、API 封装

**验证标准**：
- 能在浏览器中走完全流程
- LaTeX 公式渲染正确
- 反馈重新生成交互流畅

**预估工时**：3-4 天

---

### 里程碑 6：知识图谱（加分项）

**目标**：从往年题自动提取知识图谱，可视化展示。

**开发内容**：
- Agent 1.5 的 Prompt 设计
- LLM 返回 JSON → 自动写入 Neo4j
- 前端知识图谱可视化页面（复用 v1 的 ECharts 力导向图）

**验证标准**：
- Neo4j 中有知识点节点和关系
- 前端图谱页能正常渲染，节点大小代表考频

**预估工时**：1-2 天

---

### 里程碑 7：测试与收尾

**目标**：完善错误处理、边界情况、UI 细节。

**开发内容**：
- 错误处理（API 调用失败、解析异常、LLM 返回格式错误）
- 多科目测试（用 former_exam 中不同科目的 PDF）
- UI 细节打磨
- 文档更新

**验证标准**：
- 至少用 3 个不同科目完成端到端测试
- 无致命 Bug

**预估工时**：2-3 天

---

## 九、新增依赖

### 后端新增 Python 包

| 包名 | 用途 |
|------|------|
| `langgraph` | Agent 编排、状态管理、人在环 |
| `langchain-core` | LangGraph 依赖 |
| `langchain-openai` | OpenAI 兼容的 LLM 调用（DeepSeek 兼容 OpenAI 接口） |
| `PyMuPDF` (fitz) | PDF 页面渲染为图片 |
| `httpx` | 异步 HTTP 调用（调用视觉模型 API） |
| `Pillow` | 图片处理 |

### 前端新增 npm 包

| 包名 | 用途 |
|------|------|
| `katex` | LaTeX 公式渲染 |

---

## 十、配置新增

### backend/.env 新增项

```bash
# 视觉模型 API 配置（通义千问 Qwen-VL-Max）
QWEN_VL_API_KEY=sk-xxx
QWEN_VL_API_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
QWEN_VL_MODEL=qwen-vl-max
```

---

## 十一、风险与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| 视觉模型对复杂公式识别不准 | 中 | 高 | 实测多个模型选最优；对关键公式人工校验 |
| Agent 2 跨年度对齐出错 | 中 | 高 | 暂停点1让教师检查和编辑 |
| 生成的题目质量不稳定 | 中 | 中 | 人在环反馈机制；多次重试 |
| LangGraph 学习曲线 | 低 | 中 | 先用最简单的线性图+interrupt |
| 并行调用触发 API 限流 | 低 | 低 | 控制并发数；增加重试 |
| 含图题目无法完美处理 | 高 | 中 | Prompt 引导生成无图题；支持复用原图 |

---

## 十二、项目目录结构（新增部分）

```
g:\biyesheji\
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── courses.py        # v1（不动）
│   │   │   ├── knowledge.py      # v1（不动）
│   │   │   ├── questions.py      # v1（不动）
│   │   │   └── agent.py          # 🆕 v2 多 Agent API 路由
│   │   ├── agents/               # 🆕 Agent 相关代码
│   │   │   ├── __init__.py
│   │   │   ├── state.py          # ExamState 类型定义
│   │   │   ├── graph.py          # LangGraph 流程定义
│   │   │   ├── parser.py         # Agent 1：PDF 解析器
│   │   │   ├── knowledge_extractor.py  # Agent 1.5：知识图谱提取
│   │   │   ├── slot_analyzer.py  # Agent 2：题槽分析器
│   │   │   └── question_generator.py   # Agent 4：题目生成器
│   │   ├── services/
│   │   │   ├── vision_service.py # 🆕 视觉模型调用封装
│   │   │   └── ...               # v1 services 不动
│   │   └── ...
│   └── uploads/                  # 🆕 用户上传的 PDF 存放目录
│
├── frontend/
│   └── src/
│       ├── views/
│       │   ├── Home.vue           # 改造：两个入口按钮
│       │   ├── AgentUpload.vue    # 🆕 上传页
│       │   ├── AgentParsing.vue   # 🆕 解析进度页
│       │   ├── AgentSlots.vue     # 🆕 题槽确认页
│       │   ├── AgentDraft.vue     # 🆕 试卷草稿页
│       │   └── AgentKnowledge.vue # 🆕 知识图谱页
│       ├── components/
│       │   └── LatexRenderer.vue  # 🆕 LaTeX 公式渲染组件
│       ├── api/
│       │   └── agent.js           # 🆕 v2 API 封装
│       └── stores/
│           └── agent.js           # 🆕 v2 状态管理
│
└── docs/
    ├── PRD.md                     # v1 PRD（不动）
    └── PRD-v2-多Agent智能出题系统.md  # 🆕 本文档
```

---

**文档版本**：v2.0  
**最后更新**：2026-03-04
