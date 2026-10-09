"""校园美食地图后端入口。"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.admin import router as admin_router
from app.api.admin_campuses import router as admin_campuses_router
from app.api.assets import router as assets_router
from app.api.auth import router as auth_router
from app.api.campuses import router as campuses_router
from app.api.health import router as health_router
from app.api.shops import router as shops_router
from app.api.uploads import router as uploads_router
from app.api.users import router as users_router
from app.core.config import settings
from app.core.csrf import CsrfProtectionMiddleware
from app.core.errors import BusinessError

logger = logging.getLogger(__name__)

# 生产环境关闭交互式接口文档，避免暴露调试入口。
docs_enabled = settings.app_env != "production"

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="校园美食地图后端 API",
    docs_url="/docs" if docs_enabled else None,
    redoc_url=None,
    openapi_url="/openapi.json" if docs_enabled else None,
)

# 注意：Starlette 中后添加的中间件位于外层，因此先添加 CSRF 校验，再添加跨域处理。
app.add_middleware(CsrfProtectionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(users_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(campuses_router, prefix=settings.api_prefix)
app.include_router(admin_campuses_router, prefix=settings.api_prefix)
app.include_router(shops_router, prefix=settings.api_prefix)
app.include_router(uploads_router, prefix=settings.api_prefix)
app.include_router(assets_router)


def _error_response(status_code: int, message: str, data: object = None) -> JSONResponse:
    """统一的中文错误响应格式。"""

    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message, "data": data},
    )


@app.exception_handler(BusinessError)
async def handle_business_error(_request: Request, error: BusinessError) -> JSONResponse:
    return _error_response(error.status_code, error.message)


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(_request: Request, error: StarletteHTTPException) -> JSONResponse:
    if error.status_code == 404:
        message = "请求的接口不存在。"
    elif error.status_code == 405:
        message = "请求方法不被允许。"
    else:
        message = str(error.detail)
    return _error_response(error.status_code, message)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
    """把输入校验错误转换为中文提示。"""

    details = []
    for item in error.errors():
        location = ".".join(str(part) for part in item.get("loc", []) if part != "body") or "body"
        raw_message = str(item.get("msg", ""))
        if item.get("type") == "extra_forbidden":
            text = "请求包含不允许的字段。"
        elif item.get("type") == "missing":
            text = "缺少必填字段。"
        elif raw_message.startswith("Value error, "):
            text = raw_message.removeprefix("Value error, ")
        else:
            text = "输入内容不合法。"
        details.append({"field": location, "message": text})

    return _error_response(422, "请求参数校验失败，请检查输入内容。", {"errors": details})


@app.exception_handler(Exception)
async def handle_unexpected_error(_request: Request, error: Exception) -> JSONResponse:
    """兜底处理未预期异常，不向用户暴露堆栈信息。"""

    logger.exception("未处理的服务器异常：%s", error)
    return _error_response(500, "服务器内部错误，请稍后再试。")


@app.get("/", include_in_schema=False)
def read_root() -> dict:
    """浏览器直接访问根路径时给出中文提示。"""

    return {
        "success": True,
        "message": "校园美食地图后端已启动",
        "data": {
            "docs": "/docs" if docs_enabled else None,
            "health": f"{settings.api_prefix}/health",
        },
    }
