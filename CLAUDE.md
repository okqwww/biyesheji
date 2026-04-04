# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Intelligent exam question generation system using LLM and Knowledge Graphs ( graduation thesis project).

**Two main workflows:**
1. **Knowledge Graph Mode (v1)**: Select knowledge points from a course graph, configure parameters, and generate questions
2. **Past Exam Agent Mode (v2)**: Upload past exam PDFs, AI analyzes question slots, then regenerates new questions with configurable modification levels (small/medium/large)

## Architecture

```
biyesheji/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes (courses, knowledge, questions, agent)
│   │   ├── agents/         # Multi-agent system for PDF-based generation
│   │   │   ├── parser.py           # Agent 1: PDF parsing (PyMuPDF + Vision LLM)
│   │   │   ├── slot_analyzer.py    # Agent 2: Question slot structure analysis
│   │   │   ├── question_generator.py # Agent 4: Parallel question generation
│   │   │   ├── kg_extractor.py     # Agent 1.5: Knowledge graph extraction from PDFs
│   │   │   └── state.py            # ExamState session storage
│   │   ├── core/config.py  # Settings (loads from .env)
│   │   ├── db/neo4j.py      # Neo4j connection and queries
│   │   ├── models/         # Pydantic models (course, knowledge, question)
│   │   ├── services/        # Business logic (graph_service, question_service, llm_service)
│   │   └── main.py          # FastAPI app with CORS, middleware, routes
│   ├── uploads/            # Uploaded PDF storage by session_id
│   └── run.py              # Entry point
├── frontend/               # Vue 3 + Vite frontend
│   ├── src/
│   │   ├── api/            # Axios HTTP clients
│   │   ├── views/          # Pages (Home, CourseSelect, KnowledgeGraph, QuestionResult, Agent*)
│   │   ├── stores/         # Pinia stores (course, question, agent)
│   │   ├── components/     # Reusable components (GraphView, ConfigPanel, LatexRenderer)
│   │   └── router/         # Vue Router config
│   └── package.json
├── data/                   # Knowledge graph JSON data (python_basics.json, web_fullstack.json)
├── docs/                   # Documentation
├── log/                    # Logs (app.log, llm.log)
└── neo4j community/        # Neo4j 5.15.0 Community Edition
```

## Commands

### Neo4j (Terminal 1)
```powershell
cd "G:\biyesheji\neo4j community\neo4j-community-5.15.0\bin"
.\neo4j.bat console
```
Verify: Browser access http://localhost:7474 (login: neo4j / 211BUPTzyj)

### Backend (Terminal 2)
```powershell
# Activate uv environment
& g:/biyesheji/.venv/Scripts/Activate.ps1

# Navigate to backend
cd backend

# Run backend
python run.py
```
Verify: See "Neo4j连接成功" and "Application startup complete"

### Frontend (Terminal 3)
```powershell
# Activate uv environment
& g:/biyesheji/.venv/Scripts/Activate.ps1

# Navigate to frontend
cd frontend

# Run frontend dev server
npm run dev
```
Verify: Browser access http://localhost:5173

### Install Dependencies
```powershell
# Backend - uv pip install since dependencies were installed with pip
cd G:\biyesheji\backend
.\.venv\Scripts\activate
uv pip install -r ../requirements.txt

# Frontend
cd G:\biyesheji\frontend
npm install
```

### Import Knowledge Graph Data
```powershell
cd G:\biyesheji
.\.venv\Scripts\activate
python scripts\import_knowledge_graph.py
```

## API Endpoints

**Core API** (`/api`):
- `GET /api/courses` - Get course list
- `GET /api/courses/{course_id}/graph` - Get course knowledge graph
- `POST /api/questions/generate` - Generate questions from knowledge points
- `POST /api/questions/save` - Save questions to Neo4j
- `PUT /api/questions/{id}` - Update question
- `POST /api/questions/export/{format}` - Export questions (Markdown)

**Agent API** (`/api/agent`):
- `POST /api/agent/upload` - Upload past exam PDFs, returns session_id
- `POST /api/agent/parse` - Trigger Agent 1 PDF parsing (background)
- `GET /api/agent/parse/result` - Poll parsing status
- `POST /api/agent/analyze` - Trigger Agent 2 slot analysis
- `GET /api/agent/analyze/result` - Poll analysis status
- `POST /api/agent/generate` - Trigger Agent 4 question generation
- `GET /api/agent/generate/result` - Poll generation status
- `POST /api/agent/regenerate` - Regenerate single question with feedback
- `POST /api/agent/kg/start` - Trigger Agent 1.5 knowledge graph extraction
- `GET /api/agent/kg/result` - Poll KG extraction status

## Key Technologies

- **Backend**: FastAPI, Pydantic, Neo4j (bolt driver), LangGraph
- **LLM**: DeepSeek API (question generation, slot analysis, KG extraction)
- **Vision LLM**: Qwen-VL-Max or Gemini via NewAPI (PDF parsing)
- **Frontend**: Vue 3 (Composition API), Vite, Element Plus, ECharts, KaTeX, Pinia
- **Database**: Neo4j 5.15.0 Community (knowledge graphs and question storage)
- **PDF Processing**: PyMuPDF (fitz) - renders PDF pages as images for vision model

## Agent Workflow (v2)

Multi-agent system for past exam PDF processing:

1. **Upload** → Files saved to `backend/uploads/{session_id}/`
2. **Agent 1 Parse** → Extracts text/images from PDFs using PyMuPDF + Vision LLM
3. **Agent 1.5 KG Extract** → Extracts knowledge graph from parsed content (writes to Neo4j)
4. **Agent 2 Analyze** → Identifies question slot structure across years
5. **Interrupt 1** → Teacher confirms/edits slot structure + sets modification level
6. **Agent 4 Generate** → Creates new questions based on slots (parallel asyncio.gather)
7. **Interrupt 2** → Teacher reviews each question, can feedback to regenerate individual questions

## Configuration

Backend config in `backend/.env`:
- `NEO4J_URI=bolt://localhost:7687`
- `NEO4J_USER=neo4j`
- `NEO4J_PASSWORD=211BUPTzyj`
- `DEEPSEEK_API_KEY`, `DEEPSEEK_API_URL` - LLM
- `QWEN_VL_API_KEY`, `QWEN_VL_API_URL`, `QWEN_VL_MODEL` - Vision LLM for PDF parsing
- `API_PORT=8000`, `DEBUG=true`

## Environment

- **Python**: 3.11.13 with uv virtual environment at `G:\biyesheji\backend\.venv`
- **Node.js**: Vue 3 project with npm at `G:\biyesheji\frontend`
- **Neo4j**: 5.15.0 Community at `G:\biyesheji\neo4j community\neo4j-community-5.15.0`

## Logging

Two log files in `log/` directory:
- `app.log` - System run logs (INFO/WARNING/ERROR), daily rotation, 30-day retention
- `llm.log` - Complete LLM/VLM input/output logs for debugging prompts
