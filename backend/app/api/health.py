"""健康检查接口。"""

from fastapi import APIRouter

router = APIRouter(tags=["健康检查"])


@router.get("/health")
def health_check() -> dict:
    """返回服务运行状态，供前端与部署检查使用。"""

    return {
        "success": True,
        "message": "服务运行正常",
        "data": {"status": "ok"},
    }
