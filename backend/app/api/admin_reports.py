"""管理员举报处理接口。"""

from fastapi import APIRouter, Query

from app.api.deps import AdminUser, DbSession
from app.schemas.review import ReportDismissRequest, ReportResolveRequest
from app.services import report_service

router = APIRouter(prefix="/admin", tags=["管理员"])


@router.get("/reports", summary="获取举报列表")
def list_reports(
    _admin: AdminUser,
    session: DbSession,
    status: str = Query("pending", pattern="^(pending|resolved|dismissed|all)$", description="按处理状态筛选"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量，最大 100"),
) -> dict:
    items, total = report_service.list_reports(session, status, page, page_size)
    return {
        "success": True,
        "message": "获取成功",
        "data": {"items": items, "page": page, "page_size": page_size, "total": total},
    }


@router.post("/reports/{report_id}/dismiss", summary="驳回举报并保留评价")
def dismiss_report(
    report_id: int,
    payload: ReportDismissRequest,
    admin: AdminUser,
    session: DbSession,
) -> dict:
    report = report_service.dismiss_report(session, report_id, admin, payload.handling_note)
    return {
        "success": True,
        "message": "举报已驳回，评价保留。",
        "data": {
            "id": report.id,
            "status": report.status,
            "handled_at": report.handled_at.isoformat() if report.handled_at else None,
        },
    }


@router.post("/reports/{report_id}/resolve", summary="处理举报并隐藏被举报评价")
def resolve_report(
    report_id: int,
    payload: ReportResolveRequest,
    admin: AdminUser,
    session: DbSession,
) -> dict:
    report = report_service.resolve_report(session, report_id, admin, payload.handling_note)
    return {
        "success": True,
        "message": "举报已处理，评价已隐藏。",
        "data": {
            "id": report.id,
            "status": report.status,
            "handled_at": report.handled_at.isoformat() if report.handled_at else None,
        },
    }
