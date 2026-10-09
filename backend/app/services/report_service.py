"""举报与管理员处理业务逻辑（对应开发文档 6.8 与 7.10）。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.db.base import utc_now
from app.models import Report, Review, Shop, User
from app.schemas.review import ReportCreateRequest, ReportItem


def create_report(
    session: Session,
    review: Review,
    user: User,
    payload: ReportCreateRequest,
) -> Report:
    """举报评价：只能举报可见评价，且不能重复提交未处理举报。"""

    if review.status != "visible":
        raise BusinessError(400, "只能举报可见的评价。")

    existing = session.scalar(
        select(Report).where(
            Report.review_id == review.id,
            Report.reported_by == user.id,
            Report.status == "pending",
        )
    )
    if existing is not None:
        raise BusinessError(409, "你已经举报过这条评价，请等待管理员处理。")

    report = Report(
        review_id=review.id,
        reported_by=user.id,
        reason=payload.reason,
        status="pending",
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def get_pending_report(session: Session, report_id: int) -> Report:
    report = session.get(Report, report_id)
    if report is None:
        raise BusinessError(404, "举报记录不存在。")
    if report.status != "pending":
        raise BusinessError(400, "只有待处理的举报可以执行处理操作。")
    return report


def _build_report_item(session: Session, report: Report) -> dict:
    review = session.get(Review, report.review_id)
    shop = session.get(Shop, review.shop_id) if review is not None else None
    reporter = session.get(User, report.reported_by)

    return ReportItem(
        id=report.id,
        review_id=report.review_id,
        review_content=review.content if review is not None else None,
        review_status=review.status if review is not None else None,
        shop_id=shop.id if shop is not None else None,
        shop_name=shop.name if shop is not None else None,
        reporter_id=report.reported_by,
        reporter_username=reporter.username if reporter is not None else "已注销用户",
        reason=report.reason,
        status=report.status,
        handled_by=report.handled_by,
        handled_at=report.handled_at,
        handling_note=report.handling_note,
        created_at=report.created_at,
    ).model_dump(mode="json")


def list_reports(
    session: Session,
    status: str,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    """获取举报列表：默认只返回待处理举报，status=all 时返回全部。"""

    conditions = [] if status == "all" else [Report.status == status]
    total = session.scalar(select(func.count()).select_from(Report).where(*conditions)) or 0
    reports = session.scalars(
        select(Report)
        .where(*conditions)
        .order_by(Report.created_at.asc(), Report.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return [_build_report_item(session, report) for report in reports], int(total)


def dismiss_report(session: Session, report_id: int, admin: User, note: str | None) -> Report:
    """驳回举报并保留评价，保存处理管理员、处理时间与备注。"""

    report = get_pending_report(session, report_id)
    report.status = "dismissed"
    report.handled_by = admin.id
    report.handled_at = utc_now()
    report.handling_note = note
    session.commit()
    session.refresh(report)
    return report


def resolve_report(session: Session, report_id: int, admin: User, note: str | None) -> Report:
    """处理举报：隐藏被举报评价，并把该评价的全部待处理举报标记为已处理。"""

    report = get_pending_report(session, report_id)
    review = session.get(Review, report.review_id)
    if review is not None:
        review.status = "hidden"

    handled_at = utc_now()
    pending_reports = session.scalars(
        select(Report).where(
            Report.review_id == report.review_id,
            Report.status == "pending",
        )
    ).all()
    for item in pending_reports:
        item.status = "resolved"
        item.handled_by = admin.id
        item.handled_at = handled_at
        item.handling_note = note

    session.commit()
    session.refresh(report)
    return report
