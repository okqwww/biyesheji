from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from app.core.config import settings
from app.db.neo4j import neo4j
from app.core.logging import logger

# 导入API路由
from app.api import courses, knowledge, questions

# 创建FastAPI应用
app = FastAPI(
    title="智能出题系统API",
    description="基于大模型与知识图谱的智能出题系统后端API",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加API路由
app.include_router(courses.router, prefix=settings.API_PREFIX)
app.include_router(knowledge.router, prefix=settings.API_PREFIX)
app.include_router(questions.router, prefix=settings.API_PREFIX)


# 请求计时中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        logger.error(f"请求处理错误: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "内部服务器错误"}
        )


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"全局异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# 应用启动事件
@app.on_event("startup")
async def startup_event():
    logger.info("应用启动...")
    # 验证Neo4j连接
    if not neo4j.verify_connectivity():
        logger.error("Neo4j连接失败，应用可能无法正常工作")


# 应用关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("应用关闭...")
    # 关闭Neo4j连接
    neo4j.close()


# 根路由
@app.get("/")
async def root():
    return {
        "message": "智能出题系统API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


# 健康检查
@app.get("/health")
async def health_check():
    # 检查Neo4j连接
    neo4j_status = neo4j.verify_connectivity()
    
    if not neo4j_status:
        raise HTTPException(status_code=503, detail="数据库连接异常")
        
    return {
        "status": "healthy",
        "database": "connected"
    }
