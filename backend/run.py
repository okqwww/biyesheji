import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print(f"启动智能出题系统后端服务...")
    print(f"API文档地址: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
