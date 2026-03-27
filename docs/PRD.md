# 智能出题系统 PRD文档

## 产品需求文档 (Product Requirements Document)

**项目名称**：基于大模型与知识图谱的智能出题系统  
**英文名称**：Intelligent Question Generation System (IQGS)  
**版本**：v1.0  
**作者**：北京邮电大学电子工程学院  
**日期**：2024年12月  

---

## 一、产品概述

### 1.1 产品背景

在高校教学过程中，教师出题是一项耗时且重复性高的工作。传统人工出题方式存在以下问题：
- 出题效率低，耗费大量时间精力
- 题目风格单一，难以保证多样性
- 难度把控依赖经验，缺乏客观标准
- 知识点覆盖不全面，容易遗漏

本系统旨在利用大语言模型（LLM）和知识图谱技术，为教师提供智能化的出题辅助工具，提高出题效率和质量。

### 1.2 产品定位

面向高校教师的智能出题辅助工具，通过可视化知识图谱选择考察范围，结合大模型自动生成高质量题目。

### 1.3 产品目标

1. 降低教师出题工作量，提升出题效率
2. 基于知识图谱确保题目覆盖关键知识点
3. 支持多种题型和难度等级，满足不同考核需求
4. 自动生成参考答案和评分标准，减轻批改负担

### 1.4 目标用户

**主要用户**：高校教师

**用户特征**：
- 需要定期为课程准备练习题、测验题、考试题
- 具备基本的计算机操作能力
- 希望提高出题效率，减少重复劳动

---

## 二、功能需求

### 2.1 功能概览

| 模块 | 功能 | 优先级 |
|------|------|--------|
| 首页 | 品牌展示、系统入口 | P0 |
| 课程选择 | 选择要出题的课程 | P0 |
| 知识图谱 | 可视化展示、知识点选择 | P0 |
| 题目生成 | 配置参数、调用LLM生成题目 | P0 |
| 题目展示 | 查看生成的题目和答案 | P0 |
| 题目编辑 | 修改题干、答案、评分点 | P1 |
| 题目保存 | 保存题目到数据库 | P1 |
| 题目导出 | 导出为Markdown格式 | P1 |
| 用户登录 | 用户认证（初版不做） | P2 |
| 历史题库 | 查看已保存题目（初版不做） | P2 |

### 2.2 详细功能说明

#### 2.2.1 首页模块

**功能描述**：系统入口页面，展示产品品牌形象

**设计风格**：参考Apple官网风格
- 简约大气，大量留白
- 高级感排版和配色
- 精致的滚动动效
- 清晰的行动引导

**页面元素**：
- 系统名称和Slogan
- 产品特性介绍（3-4个核心亮点）
- "开始使用"按钮（主CTA）
- 底部版权信息

#### 2.2.2 课程选择模块

**功能描述**：展示可用课程列表，用户选择要出题的课程

**支持课程**（初版）：
1. Web全栈开发
2. Python编程基础

**页面元素**：
- 课程卡片（含课程名称、简介、知识点数量）
- 返回首页按钮

**交互逻辑**：
- 点击课程卡片 → 进入该课程的知识图谱页面

#### 2.2.3 知识图谱模块

**功能描述**：可视化展示课程知识结构，支持用户选择考察的知识点

**可视化方式**：力导向图（Force-Directed Graph）

**图谱结构**：
```
课程 → 章节 → 知识点
            ↑
    知识点之间的关联关系
```

**节点设计**：
- 章节节点：较大尺寸，深色
- 知识点节点：较小尺寸，浅色
- 选中状态：高亮显示，带勾选标记

**交互功能**：
- 鼠标悬停：显示节点详情（名称、描述）
- 点击节点：切换选中/取消选中状态
- 拖拽节点：调整布局位置
- 滚轮缩放：调整视图大小
- 批量操作：点击章节节点可选中/取消该章节下所有知识点

**页面布局**：
```
┌────────────────────────────────────────────────────┐
│  ← 返回                        课程名称            │
├──────────────────────────────────┬─────────────────┤
│                                  │   出题配置面板   │
│                                  │                 │
│        知识图谱可视化区域         │  已选知识点: 3   │
│        (力导向图)                │                 │
│                                  │  题型: [下拉选择]│
│                                  │  难度: [单选]   │
│                                  │  数量: [1-7]    │
│                                  │                 │
│                                  │  [生成题目]     │
└──────────────────────────────────┴─────────────────┘
```

#### 2.2.4 出题配置面板

**功能描述**：配置题目生成参数

**配置项**：

| 参数 | 类型 | 选项 | 默认值 |
|------|------|------|--------|
| 已选知识点 | 展示 | - | - |
| 题型 | 单选下拉 | 单选题/多选题/填空题/解答题 | 单选题 |
| 难度 | 单选按钮 | 简单/中等/困难 | 中等 |
| 数量 | 数字输入 | 1-7 | 3 |

**校验规则**：
- 至少选择1个知识点
- 题目数量范围1-7

**按钮状态**：
- 未选择知识点时，"生成题目"按钮禁用
- 生成中显示loading状态

#### 2.2.5 题目生成与展示模块

**功能描述**：调用大模型生成题目，展示生成结果

**生成过程**：
1. 用户点击"生成题目"
2. 显示生成中状态（loading + 预计时间提示）
3. 后端调用LLM生成题目（失败自动重试2次）
4. 生成完成后跳转到题目结果页

**题目展示格式**：

**单选题**：
```
第1题 [单选] [中等] 
考察知识点：for循环

题目：以下哪个选项可以正确遍历列表？

A. for i in range(list)
B. for i in list
C. for i to list
D. foreach i in list

参考答案：B

解析：Python中使用 for...in 语法遍历可迭代对象...
```

**多选题**：
```
第2题 [多选] [困难]
考察知识点：列表操作、切片

题目：以下哪些操作可以获取列表的最后一个元素？

A. list[-1]
B. list[len(list)-1]
C. list.last()
D. list[:-1]

参考答案：A, B

解析：A使用负索引，B使用长度计算索引...
```

**填空题**：
```
第3题 [填空] [简单]
考察知识点：变量定义

题目：Python中使用 ____(1)____ 关键字定义函数，使用 ____(2)____ 关键字返回值。

参考答案：
(1) def
(2) return

解析：def是Python函数定义关键字...
```

**解答题**：
```
第4题 [解答] [困难]
考察知识点：递归、函数设计

题目：请编写一个递归函数，计算斐波那契数列的第n项。

参考答案：
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

评分标准：
• 正确使用递归结构（3分）
• 正确处理边界条件（2分）
• 递归逻辑正确（3分）
• 代码规范（2分）
```

**页面操作按钮**：
- 编辑：进入编辑模式，可修改题干、答案、评分点
- 保存：将题目保存到数据库
- 导出：导出为Markdown文件
- 重新生成：重新调用LLM生成
- 返回：返回知识图谱页面

#### 2.2.6 题目编辑功能

**功能描述**：允许用户修改生成的题目内容

**可编辑字段**：
- 题干内容
- 选项内容（选择题）
- 参考答案
- 解析/评分标准

**不可编辑字段**：
- 题型
- 难度
- 关联知识点

**交互方式**：
- 点击"编辑"按钮进入编辑模式
- 各字段变为可输入状态
- 点击"保存修改"确认，点击"取消"放弃修改

#### 2.2.7 题目保存功能

**功能描述**：将题目保存到Neo4j数据库

**保存时机**：用户手动点击"保存"按钮

**保存内容**：
- 题目完整信息
- 关联的知识点
- 创建时间
- 来源标记（ai_generated）

**保存反馈**：
- 成功：提示"保存成功"
- 失败：提示错误信息

#### 2.2.8 题目导出功能

**功能描述**：将生成的题目导出为Markdown文件

**导出格式示例**：
```markdown
# 题目导出

**课程**：Python编程基础  
**生成时间**：2024-12-12 14:30:00  
**题目数量**：5题

---

## 第1题 [单选] [中等]

**考察知识点**：for循环

**题目**：
以下哪个选项可以正确遍历列表？

A. for i in range(list)  
B. for i in list  
C. for i to list  
D. foreach i in list

**参考答案**：B

**解析**：Python中使用 for...in 语法遍历可迭代对象...

---

## 第2题 ...
```

**导出流程**：
1. 点击"导出"按钮
2. 浏览器自动下载.md文件
3. 文件名格式：`题目_课程名_日期时间.md`

---

## 三、非功能需求

### 3.1 性能需求

| 指标 | 要求 |
|------|------|
| 首页加载时间 | < 2秒 |
| 知识图谱渲染 | < 3秒（50个节点） |
| 题目生成时间 | < 30秒（7题） |
| 单题生成时间 | 3-8秒 |

### 3.2 兼容性需求

| 类型 | 要求 |
|------|------|
| 浏览器 | Chrome 90+, Firefox 90+, Edge 90+ |
| 分辨率 | 最小支持 1280×720 |
| 设备 | 桌面端优先（暂不适配移动端） |

### 3.3 可用性需求

- 界面简洁直观，无需培训即可上手
- 操作步骤清晰，有明确的引导
- 错误信息友好，提供解决建议

### 3.4 可靠性需求

- LLM调用失败自动重试2次
- 重试失败后给出友好提示，允许用户手动重试
- 关键操作有确认提示

---

## 四、技术架构

### 4.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                      前端 (Vue 3)                        │
│         Element Plus + ECharts/D3.js + Axios            │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTP/REST API
┌─────────────────────────┴───────────────────────────────┐
│                     后端 (FastAPI)                       │
│              Python 3.10+ / Uvicorn                     │
└──────────┬──────────────────────────────┬───────────────┘
           │                              │
    ┌──────┴──────┐                ┌──────┴──────┐
    │   Neo4j     │                │ DeepSeek    │
    │  知识图谱    │                │   API       │
    │  题目存储    │                │  题目生成    │
    └─────────────┘                └─────────────┘
```

### 4.2 技术栈明细

| 层级 | 技术选型 | 版本 | 说明 |
|------|----------|------|------|
| 前端框架 | Vue 3 | 3.4+ |  |
| UI组件库 | Element Plus | 2.4+ | 表单、按钮等组件 |
| 图可视化 |   D3.js | - | 力导向图 |
| HTTP客户端 | Axios | 1.6+ | API请求 |
| 构建工具 | Vite | 5.0+ | 开发服务器和打包 |
| 后端框架 | FastAPI | 0.109+ | Python异步Web框架 |
| 运行时 | Python | 3.10+ | - |
| ASGI服务器 | Uvicorn | 0.27+ | 开发和生产 |
| 图数据库 | Neo4j | 5.x | 知识图谱存储 |
| 大模型 | DeepSeek API | - | 题目生成 |

### 4.3 项目目录结构

```
intelligent-question-system/
├── frontend/                # 前端项目
│   ├── src/
│   │   ├── assets/         # 静态资源
│   │   ├── components/     # 公共组件
│   │   ├── views/          # 页面组件
│   │   │   ├── Home.vue
│   │   │   ├── CourseSelect.vue
│   │   │   ├── KnowledgeGraph.vue
│   │   │   └── QuestionResult.vue
│   │   ├── api/            # API请求封装
│   │   ├── router/         # 路由配置
│   │   ├── stores/         # Pinia状态管理
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
│
├── backend/                 # 后端项目
│   ├── app/
│   │   ├── api/            # API路由
│   │   │   ├── courses.py
│   │   │   ├── knowledge.py
│   │   │   └── questions.py
│   │   ├── core/           # 核心配置
│   │   │   ├── config.py
│   │   │   └── llm.py
│   │   ├── db/             # 数据库相关
│   │   │   └── neo4j.py
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   │   ├── graph_service.py
│   │   │   └── question_service.py
│   │   └── main.py
│   ├── requirements.txt
│   └── .env
│
├── data/                    # 知识图谱数据
│   ├── web_fullstack.json
│   └── python_basics.json
│
├── docs/                    # 文档
│   └── PRD.md
│
└── README.md
```

---

## 五、数据结构设计

### 5.1 Neo4j知识图谱Schema

#### 节点类型

**Course（课程）**
```cypher
(:Course {
  id: String,           // 唯一标识，如 "python_basics"
  name: String,         // 课程名称，如 "Python编程基础"
  description: String   // 课程简介
})
```

**Chapter（章节）**
```cypher
(:Chapter {
  id: String,           // 唯一标识，如 "python_basics_ch01"
  name: String,         // 章节名称，如 "Python基础语法"
  order: Integer        // 章节顺序，如 1
})
```

**KnowledgePoint（知识点）**
```cypher
(:KnowledgePoint {
  id: String,           // 唯一标识，如 "kp_for_loop"
  name: String,         // 知识点名称，如 "for循环"
  description: String,  // 知识点描述
  keywords: [String]    // 关键词，如 ["循环", "遍历", "迭代"]
})
```

**Question（题目）**
```cypher
(:Question {
  id: String,           // UUID
  type: String,         // 题型：single_choice/multiple_choice/fill_blank/short_answer
  difficulty: String,   // 难度：easy/medium/hard
  content: String,      // 题干
  options: String,      // 选项（JSON字符串，选择题用）
  answer: String,       // 参考答案
  explanation: String,  // 解析
  scoring_points: String, // 评分标准（JSON字符串，解答题用）
  created_at: DateTime, // 创建时间
  source: String        // 来源：ai_generated
})
```

#### 关系类型

```cypher
// 课程包含章节
(Course)-[:HAS_CHAPTER]->(Chapter)

// 章节包含知识点
(Chapter)-[:CONTAINS]->(KnowledgePoint)

// 知识点之间的关联
(KnowledgePoint)-[:RELATES_TO]->(KnowledgePoint)

// 题目考察知识点
(Question)-[:TESTS]->(KnowledgePoint)
```

### 5.2 API数据结构

#### 知识图谱响应结构

```typescript
interface GraphData {
  nodes: Node[];
  edges: Edge[];
}

interface Node {
  id: string;
  name: string;
  type: 'chapter' | 'knowledge_point';
  description?: string;
}

interface Edge {
  source: string;  // 源节点ID
  target: string;  // 目标节点ID
  type: 'contains' | 'relates_to';
}
```

#### 题目生成请求结构

```typescript
interface GenerateRequest {
  course_id: string;           // 课程ID
  knowledge_point_ids: string[]; // 知识点ID列表
  question_type: 'single_choice' | 'multiple_choice' | 'fill_blank' | 'short_answer';
  difficulty: 'easy' | 'medium' | 'hard';
  count: number;               // 1-7
}
```

#### 题目响应结构

```typescript
interface Question {
  id: string;
  type: string;
  difficulty: string;
  content: string;
  options?: string[];          // 选择题选项
  answer: string | string[];   // 答案（填空题为数组）
  explanation?: string;        // 解析
  scoring_points?: string[];   // 评分标准（解答题）
  knowledge_points: string[];  // 关联知识点名称
}

interface GenerateResponse {
  success: boolean;
  questions: Question[];
  message?: string;            // 错误信息
}
```

---

## 六、API设计

### 6.1 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/courses | 获取课程列表 |
| GET | /api/courses/{course_id}/graph | 获取课程知识图谱 |
| POST | /api/questions/generate | 生成题目 |


### 6.2 接口详细设计

#### 6.2.1 获取课程列表

**请求**
```
GET /api/courses
```

**响应**
```json
{
  "success": true,
  "data": [
    {
      "id": "python_basics",
      "name": "Python编程基础",
      "description": "Python语言基础知识，包括语法、数据类型、控制流程等",
      "knowledge_point_count": 35
    },
    {
      "id": "web_fullstack",
      "name": "Web全栈开发",
      "description": "前后端开发技术，包括HTML/CSS/JavaScript、Vue、Node.js等",
      "knowledge_point_count": 42
    }
  ]
}
```

#### 6.2.2 获取课程知识图谱

**请求**
```
GET /api/courses/{course_id}/graph
```

**响应**
```json
{
  "success": true,
  "data": {
    "course": {
      "id": "python_basics",
      "name": "Python编程基础"
    },
    "nodes": [
      {"id": "ch01", "name": "Python基础语法", "type": "chapter"},
      {"id": "kp_variable", "name": "变量定义", "type": "knowledge_point", "description": "Python变量的定义和使用"},
      {"id": "kp_data_type", "name": "数据类型", "type": "knowledge_point", "description": "Python基本数据类型"}
    ],
    "edges": [
      {"source": "ch01", "target": "kp_variable", "type": "contains"},
      {"source": "ch01", "target": "kp_data_type", "type": "contains"},
      {"source": "kp_variable", "target": "kp_data_type", "type": "relates_to"}
    ]
  }
}
```

#### 6.2.3 生成题目

**请求**
```
POST /api/questions/generate
Content-Type: application/json

{
  "course_id": "python_basics",
  "knowledge_point_ids": ["kp_for_loop", "kp_while_loop"],
  "question_type": "single_choice",
  "difficulty": "medium",
  "count": 3
}
```

**响应**
```json
{
  "success": true,
  "data": {
    "questions": [
      {
        "id": "temp_uuid_1",
        "type": "single_choice",
        "difficulty": "medium",
        "content": "以下哪个选项可以正确遍历列表？",
        "options": [
          "A. for i in range(list)",
          "B. for i in list",
          "C. for i to list",
          "D. foreach i in list"
        ],
        "answer": "B",
        "explanation": "Python中使用 for...in 语法遍历可迭代对象，选项B是正确的写法。",
        "knowledge_points": ["for循环"]
      }
    ]
  }
}
```

#### 6.2.4 保存题目

**请求**
```
POST /api/questions/save
Content-Type: application/json

{
  "questions": [
    {
      "type": "single_choice",
      "difficulty": "medium",
      "content": "题干内容",
      "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
      "answer": "B",
      "explanation": "解析内容",
      "knowledge_point_ids": ["kp_for_loop"]
    }
  ]
}
```

**响应**
```json
{
  "success": true,
  "message": "保存成功",
  "data": {
    "saved_count": 1,
    "question_ids": ["uuid_xxx"]
  }
}
```

#### 6.2.5 更新题目

**请求**
```
PUT /api/questions/{question_id}
Content-Type: application/json

{
  "content": "修改后的题干",
  "answer": "修改后的答案",
  "explanation": "修改后的解析"
}
```

**响应**
```json
{
  "success": true,
  "message": "更新成功"
}
```

---

## 七、页面流程图

```
┌─────────┐
│  首页   │
│ (品牌)  │
└────┬────┘
     │ 点击"开始使用"
     ▼
┌─────────┐
│课程选择 │
│  页面   │
└────┬────┘
     │ 点击课程卡片
     ▼
┌─────────────────────────────────┐
│        知识图谱页面              │
│  ┌─────────────┬──────────────┐ │
│  │ 知识图谱    │  出题配置     │ │
│  │ (力导向图)  │  - 已选知识点 │ │
│  │             │  - 题型选择   │ │
│  │  点击选择   │  - 难度选择   │ │
│  │  知识点     │  - 数量设置   │ │
│  │             │  [生成题目]   │ │
│  └─────────────┴──────────────┘ │
└────────────────┬────────────────┘
                 │ 点击"生成题目"
                 ▼
         ┌──────────────┐
         │  Loading...  │
         │  生成中...   │
         └──────┬───────┘
                │ 生成完成
                ▼
┌─────────────────────────────────┐
│        题目结果页面              │
│                                 │
│  题目1: [单选] [中等]           │
│  题干: ...                      │
│  选项: A/B/C/D                  │
│  答案: B                        │
│  解析: ...                      │
│  ─────────────────────          │
│  题目2: ...                     │
│                                 │
│  [编辑] [保存] [导出] [重新生成] │
│  [返回]                         │
└─────────────────────────────────┘
```

---

## 八、大模型Prompt设计

### 8.1 单选题Prompt模板

```
你是一位专业的高校教师，擅长出高质量的编程考试题目。

请根据以下要求生成单选题：

【课程】{course_name}
【知识点】{knowledge_points}
【难度】{difficulty}（简单/中等/困难）
【数量】{count}题

要求：
1. 题目紧扣指定知识点
2. 选项设计合理，干扰项有迷惑性但不能有歧义
3. 只有一个正确答案
4. 提供详细解析

请按以下JSON格式输出：
```json
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
```
```

### 8.2 多选题Prompt模板

```
你是一位专业的高校教师，擅长出高质量的编程考试题目。

请根据以下要求生成多选题：

【课程】{course_name}
【知识点】{knowledge_points}
【难度】{difficulty}
【数量】{count}题

要求：
1. 题目紧扣指定知识点
2. 正确答案为2-4个
3. 选项设计合理，干扰项有迷惑性
4. 提供详细解析

请按以下JSON格式输出：
```json
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
```
```

### 8.3 填空题Prompt模板

```
你是一位专业的高校教师，擅长出高质量的编程考试题目。

请根据以下要求生成填空题：

【课程】{course_name}
【知识点】{knowledge_points}
【难度】{difficulty}
【数量】{count}题

要求：
1. 使用 ____(1)____ 格式标记空格
2. 可以有1-3个空
3. 题目紧扣指定知识点
4. 提供详细解析

请按以下JSON格式输出：
```json
{
  "questions": [
    {
      "content": "Python中使用 ____(1)____ 关键字定义函数",
      "answer": ["def"],
      "explanation": "解析"
    }
  ]
}
```
```

### 8.4 解答题Prompt模板

```
你是一位专业的高校教师，擅长出高质量的编程考试题目。

请根据以下要求生成解答题：

【课程】{course_name}
【知识点】{knowledge_points}
【难度】{difficulty}
【数量】{count}题

要求：
1. 题目紧扣指定知识点
2. 提供完整的参考答案（含代码）
3. 提供详细的评分标准（总分10分）
4. 评分标准要具体、可操作

请按以下JSON格式输出：
```json
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
```
```

---

## 九、里程碑计划

基于任务书进度安排，细化开发里程碑：

| 阶段 | 时间 | 目标 | 交付物 |
|------|------|------|--------|
| M1 | 12.1-12.14 | 开题与技术调研 | 开题报告、技术选型文档 |
| M2 | 12.15-12.28 | 知识图谱设计 | Neo4j部署、Schema设计、数据导入 |
| M3 | 12.29-1.11 | 大模型对接 | DeepSeek API对接、Prompt模板、基础生成功能 |
| M4 | 1.12-1.25 | 后端开发 | FastAPI项目、全部API接口 |
| M5 | 1.26-2.8 | 前端开发 | Vue项目、全部页面、前后端联调 |
| M6 | 2.9-2.15 | 系统测试 | 功能测试、Bug修复、性能优化 |
| M7 | 2.16-2.22 | 论文撰写 | 论文初稿 |
| M8 | 2.23-2.28 | 答辩准备 | 论文终稿、答辩PPT |

---

## 十、风险与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| LLM生成质量不稳定 | 中 | 高 | 优化Prompt、增加重试机制、人工审核 |
| Neo4j学习曲线 | 中 | 中 | 提前学习、使用简单查询、参考官方示例 |
| 知识图谱数据准备耗时 | 中 | 中 | 用AI辅助生成、控制知识点数量 |
| 前端图可视化复杂 | 中 | 中 | 使用成熟库（ECharts）、参考现有案例 |
| 时间进度紧张 | 高 | 高 | 优先核心功能、砍掉P2需求 |

---

## 十一、术语表

| 术语 | 说明 |
|------|------|
| LLM | Large Language Model，大语言模型 |
| 知识图谱 | Knowledge Graph，用图结构表示知识及其关系 |
| Prompt | 提示词，用于引导大模型生成内容 |
| Neo4j | 图数据库，用于存储知识图谱 |
| FastAPI | Python高性能Web框架 |
| Vue 3 | 前端JavaScript框架 |
| 力导向图 | 一种图可视化算法，节点通过力学模拟自动布局 |

---

## 十二、版本记录

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2024-12-12 | 初始版本 | - |

---

**文档结束**
