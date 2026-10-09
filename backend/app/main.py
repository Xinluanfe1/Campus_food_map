"""校园美食地图后端入口。

第一阶段只提供健康检查接口，用于验证前后端可以正常连通。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="校园美食地图后端 API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
def read_root() -> dict:
    """浏览器直接访问根路径时给出中文提示。"""

    return {
        "success": True,
        "message": "校园美食地图后端已启动",
        "data": {"docs": "/docs", "health": f"{settings.api_prefix}/health"},
    }
