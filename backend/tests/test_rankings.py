"""排行榜、搜索与贡献榜测试：对应第七步验收标准。"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Campus, Review, Shop, User

VIEWER_USERNAME = "榜单查看者"
VIEWER_PASSWORD = "榜单查看密码-2026"

RANKINGS_URL = "/api/v1/campuses/rank_campus/rankings/shops"
CONTRIBUTORS_URL = "/api/v1/campuses/rank_campus/rankings/contributors"
SEARCH_URL = "/api/v1/campuses/rank_campus/search"


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def create_user(session: Session, user_id: int, username: str, password: str, role: str = "user") -> None:
    session.add(
        User(
            id=user_id,
            username=username,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
    )


def create_campus(session: Session, campus_id: str = "rank_campus") -> None:
    session.add(
        Campus(
            campus_id=campus_id,
            campus_name="排行榜测试校园",
            map_type="image",
            map_asset_url=f"/assets/maps/{campus_id}.png",
            map_attribution="测试署名",
            allow_off_campus=False,
            image_width=1000,
            image_height=800,
            default_map_x=0.5,
            default_map_y=0.5,
            default_zoom=1,
            is_active=True,
        )
    )


def create_shop(
    session: Session,
    shop_id: int,
    name: str,
    shop_type: str,
    submitted_by: int,
    status: str = "approved",
    reviewed_at: str | None = "2026-10-01T01:00:00Z",
    rejection_reason: str | None = None,
    campus_id: str = "rank_campus",
) -> None:
    session.add(
        Shop(
            id=shop_id,
            campus_id=campus_id,
            name=name,
            description=f"{name}的简介。",
            shop_type=shop_type,
            submitted_by=submitted_by,
            status=status,
            rejection_reason=rejection_reason,
            map_x=0.3,
            map_y=0.4,
            reviewed_by=2 if status != "pending" else None,
            reviewed_at=_dt(reviewed_at) if reviewed_at and status != "pending" else None,
        )
    )


def create_review(session: Session, review_id: int, shop_id: int, user_id: int, rating: int) -> None:
    session.add(
        Review(
            id=review_id,
            shop_id=shop_id,
            user_id=user_id,
            rating=rating,
            content=f"{rating} 星评价。",
            status="visible",
        )
    )


def create_scenario(engine: Engine) -> None:
    """构建排行榜测试数据：

    - 601 商铺（提交者 1）：评价 5、5 → 平均 5.00，2 条
    - 602 摊贩（提交者 1）：评价 3 → 平均 3.00，1 条
    - 603 商铺（提交者 2）：评价 4、4、4 → 平均 4.00，3 条
    - 604 摊贩（提交者 2）：无评价（不进入评分排行榜）
    - 605 商铺（提交者 3）：待审核（不进入任何公开榜单）
    - 校园平均分 C = (5+5+3+4+4+4) / 6 = 4.1667
    """

    with Session(engine) as session:
        create_campus(session)
        create_user(session, 1, "提交者一", "提交者密码-2026")
        create_user(session, 2, "提交者二", "提交者密码-2026")
        create_user(session, 3, "提交者三", "提交者密码-2026")
        create_user(session, 11, "评价者一", "评价者密码-2026")
        create_user(session, 12, "评价者二", "评价者密码-2026")
        create_user(session, 13, "评价者三", "评价者密码-2026")
        create_user(session, 21, VIEWER_USERNAME, VIEWER_PASSWORD)
        session.commit()

        create_shop(session, 601, "示例一食堂", "shop", 1, reviewed_at="2026-10-01T01:00:00Z")
        create_shop(session, 602, "示例烤肠摊", "vendor", 1, reviewed_at="2026-10-05T01:00:00Z")
        create_shop(session, 603, "示例面馆", "shop", 2, reviewed_at="2026-10-03T01:00:00Z")
        create_shop(session, 604, "示例水果摊", "vendor", 2, reviewed_at="2026-10-07T01:00:00Z")
        create_shop(session, 605, "待审核店铺", "shop", 3, status="pending", reviewed_at=None)
        session.commit()

        create_review(session, 1, 601, 11, 5)
        create_review(session, 2, 601, 12, 5)
        create_review(session, 3, 602, 11, 3)
        create_review(session, 4, 603, 11, 4)
        create_review(session, 5, 603, 12, 4)
        create_review(session, 6, 603, 13, 4)
        create_review(session, 7, 605, 11, 5)
        session.commit()


def login_viewer(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": VIEWER_USERNAME, "password": VIEWER_PASSWORD},
    )
    assert response.status_code == 200, response.text


def test_rankings_require_login(client: TestClient, engine: Engine) -> None:
    """验收标准 11：游客不能查看排行榜、搜索结果与贡献榜。"""

    create_scenario(engine)

    assert client.get(RANKINGS_URL).status_code == 401
    assert client.get(SEARCH_URL + "?q=食堂").status_code == 401
    assert client.get(CONTRIBUTORS_URL).status_code == 401
    assert client.get("/api/v1/users/me/contributions").status_code == 401


def test_ranking_default_desc_and_weighted_formula(client: TestClient, engine: Engine) -> None:
    """验收标准 1、4、5：默认按加权评分降序，公式与文档一致，无评价店铺不入选。"""

    create_scenario(engine)
    login_viewer(client)

    response = client.get(RANKINGS_URL)
    assert response.status_code == 200
    data = response.json()["data"]
    items = data["items"]

    assert [item["shop_id"] for item in items] == [601, 603, 602]
    assert [item["rank"] for item in items] == [1, 2, 3]
    # 604 无有效评价，不进入评分排行榜；605 待审核，也不进入
    assert 604 not in [item["shop_id"] for item in items]
    assert 605 not in [item["shop_id"] for item in items]

    # 加权评分公式：S = v/(v+m)·R + m/(v+m)·C，m=5，C=4.1667
    by_id = {item["shop_id"]: item for item in items}
    assert by_id[601]["average_rating"] == 5.0
    assert by_id[601]["review_count"] == 2
    assert by_id[601]["weighted_rating"] == 4.4
    assert by_id[603]["average_rating"] == 4.0
    assert by_id[603]["review_count"] == 3
    assert by_id[603]["weighted_rating"] == 4.1
    assert by_id[602]["weighted_rating"] == 3.97


def test_ranking_sort_asc_and_type_filter(client: TestClient, engine: Engine) -> None:
    """验收标准 2、3：支持升序与按商铺/摊贩筛选。"""

    create_scenario(engine)
    login_viewer(client)

    ascending = client.get(f"{RANKINGS_URL}?sort=asc").json()["data"]["items"]
    assert [item["shop_id"] for item in ascending] == [602, 603, 601]
    assert [item["rank"] for item in ascending] == [1, 2, 3]

    shops_only = client.get(f"{RANKINGS_URL}?shop_type=shop").json()["data"]["items"]
    assert [item["shop_id"] for item in shops_only] == [601, 603]
    assert all(item["shop_type"] == "shop" for item in shops_only)

    vendors_only = client.get(f"{RANKINGS_URL}?shop_type=vendor").json()["data"]["items"]
    assert [item["shop_id"] for item in vendors_only] == [602]
    assert all(item["shop_type"] == "vendor" for item in vendors_only)


def test_ranking_pagination_and_parameter_validation(client: TestClient, engine: Engine) -> None:
    """验收标准 12：分页正确，非法的分页、排序与筛选参数被拒绝。"""

    create_scenario(engine)
    login_viewer(client)

    first_page = client.get(f"{RANKINGS_URL}?page=1&page_size=2").json()["data"]
    assert [item["shop_id"] for item in first_page["items"]] == [601, 603]
    assert first_page["total"] == 3
    assert first_page["page_size"] == 2

    second_page = client.get(f"{RANKINGS_URL}?page=2&page_size=2").json()["data"]
    assert [item["shop_id"] for item in second_page["items"]] == [602]
    assert second_page["items"][0]["rank"] == 3

    assert client.get(f"{RANKINGS_URL}?page=0").status_code == 422
    assert client.get(f"{RANKINGS_URL}?page_size=101").status_code == 422
    assert client.get(f"{RANKINGS_URL}?sort=sideways").status_code == 422
    assert client.get(f"{RANKINGS_URL}?shop_type=restaurant").status_code == 422


def test_ranking_stable_tie_breaks(client: TestClient, engine: Engine) -> None:
    """验收标准 10：同分时先按有效评价数量从高到低，再按店铺 ID 从小到大。"""

    with Session(engine) as session:
        create_campus(session, "tie_campus")
        create_user(session, 2, "并列管理员", "并列管理员密码-2026", role="admin")
        create_user(session, 41, "并列提交者", "并列提交者密码-2026")
        create_user(session, 42, "并列评价者", "并列评价者密码-2026")
        create_user(session, 21, VIEWER_USERNAME, VIEWER_PASSWORD)
        session.commit()

        # 三家店铺的评价星级都是 5，校园平均分 C = 5，因此加权评分完全相同
        create_shop(session, 801, "并列店铺甲", "shop", 41, campus_id="tie_campus")
        create_shop(session, 802, "并列店铺乙", "shop", 41, campus_id="tie_campus")
        create_shop(session, 803, "并列店铺丙", "shop", 41, campus_id="tie_campus")
        session.commit()

        create_review(session, 30, 801, 41, 5)
        create_review(session, 31, 801, 42, 5)
        create_review(session, 32, 802, 41, 5)
        create_review(session, 33, 802, 42, 5)
        create_review(session, 34, 803, 41, 5)
        session.commit()

    login_viewer(client)
    items = client.get("/api/v1/campuses/tie_campus/rankings/shops").json()["data"]["items"]

    assert [item["weighted_rating"] for item in items] == [5.0, 5.0, 5.0]
    # 甲、乙各 2 条评价（同为满分）→ 按 ID 升序；丙只有 1 条 → 排最后
    assert [item["shop_id"] for item in items] == [801, 802, 803]
    assert [item["rank"] for item in items] == [1, 2, 3]


def test_ranking_updates_after_hide_or_delete(client: TestClient, engine: Engine) -> None:
    """验收标准 6：评价被隐藏或删除后，评分统计与排名立即更新。"""

    create_scenario(engine)
    login_viewer(client)

    # 隐藏 601 的两条评价：601 因无有效评价退出排行榜，603 升为第一名
    with Session(engine) as session:
        reviews = session.scalars(select(Review).where(Review.shop_id == 601)).all()
        for review in reviews:
            review.status = "hidden"
        session.commit()

    after_hide = client.get(RANKINGS_URL).json()["data"]["items"]
    assert [item["shop_id"] for item in after_hide][0] == 603
    assert 601 not in [item["shop_id"] for item in after_hide]

    # 删除 603 的一条评价：有效评价数量与加权评分同步变化
    with Session(engine) as session:
        review = session.scalar(select(Review).where(Review.shop_id == 603, Review.user_id == 13))
        session.delete(review)
        session.commit()

    after_delete = {item["shop_id"]: item for item in client.get(RANKINGS_URL).json()["data"]["items"]}
    assert after_delete[603]["review_count"] == 2
    # 隐藏 601 的两条评价并删除 603 的一条评价后：
    # C = (3 + 4 + 4) / 3 = 3.6667，603 的加权评分 = 2/7 × 4 + 5/7 × 3.6667 = 3.76
    assert after_delete[603]["weighted_rating"] == 3.76


def test_search_only_returns_public_shops_in_campus(client: TestClient, engine: Engine) -> None:
    """验收标准 7：搜索只返回当前校园的公开店铺。"""

    create_scenario(engine)
    login_viewer(client)

    with Session(engine) as session:
        create_campus(session, "other_campus")
        create_user(session, 31, "外部提交者", "外部提交者密码-2026")
        session.commit()
        create_shop(session, 701, "外部食堂", "shop", 31, campus_id="other_campus")
        create_shop(
            session,
            702,
            "隐藏食堂",
            "shop",
            1,
            status="rejected",
            rejection_reason="测试拒绝",
        )
        session.commit()

    result = client.get(f"{SEARCH_URL}?q=食堂").json()["data"]
    ids = [item["id"] for item in result["items"]]
    assert 601 in ids
    assert 702 not in ids  # 被拒绝的店铺不公开
    assert 701 not in ids  # 其他校园的店铺不返回
    assert result["keyword"] == "食堂"


def test_search_handles_case_and_whitespace(client: TestClient, engine: Engine) -> None:
    """验收标准 8：搜索忽略首尾空格并支持大小写不敏感。"""

    create_scenario(engine)
    login_viewer(client)

    with Session(engine) as session:
        create_shop(session, 703, "Cafe Latte 西餐厅", "shop", 1, reviewed_at="2026-10-02T01:00:00Z")
        session.commit()

    lower = client.get(f"{SEARCH_URL}?q=cafe").json()["data"]["items"]
    upper = client.get(f"{SEARCH_URL}?q=CAFE").json()["data"]["items"]
    padded = client.get(f"{SEARCH_URL}?q=%20%20Cafe%20%20").json()["data"]["items"]
    by_description = client.get(f"{SEARCH_URL}?q=简介").json()["data"]["items"]

    assert [item["id"] for item in lower] == [703]
    assert [item["id"] for item in upper] == [703]
    assert [item["id"] for item in padded] == [703]
    assert len(by_description) >= 1  # 简介也可以作为搜索条件

    empty = client.get(f"{SEARCH_URL}?q=%20%20")
    assert empty.status_code == 400
    assert empty.json()["message"] == "请输入搜索关键词。"

    wildcard = client.get(f"{SEARCH_URL}?q=%25").json()["data"]
    assert wildcard["total"] == 0  # % 被转义，不会匹配全部店铺


def test_contributor_ranking_counts_only_approved_shops(client: TestClient, engine: Engine) -> None:
    """验收标准 9、10：贡献榜只统计审核通过的店铺，同数量时排序稳定。"""

    create_scenario(engine)
    login_viewer(client)

    data = client.get(CONTRIBUTORS_URL).json()["data"]
    items = data["items"]

    # 提交者一：601、602（2 家，第 2 家通过时间 2026-10-05）
    # 提交者二：603、604（2 家，第 2 家通过时间 2026-10-07）
    # 提交者三：605 待审核，不计入
    assert [item["username"] for item in items] == ["提交者一", "提交者二"]
    assert [item["approved_shop_count"] for item in items] == [2, 2]
    assert [item["rank"] for item in items] == [1, 2]
    assert "提交者三" not in [item["username"] for item in items]

    # 删除提交者二的一家店铺后，其贡献数量下降
    with Session(engine) as session:
        shop = session.get(Shop, 604)
        session.delete(shop)
        session.commit()

    after_delete = client.get(CONTRIBUTORS_URL).json()["data"]["items"]
    counts = {item["username"]: item["approved_shop_count"] for item in after_delete}
    assert counts["提交者一"] == 2
    assert counts["提交者二"] == 1


def test_personal_contribution_summary(client: TestClient, engine: Engine) -> None:
    """用户可以查看个人贡献统计（指定校园时包含排名）。"""

    create_scenario(engine)
    login_viewer(client)

    viewer_summary = client.get("/api/v1/users/me/contributions?campus_id=rank_campus").json()["data"]
    assert viewer_summary["approved_shop_count"] == 0
    assert viewer_summary["rank"] is None

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": client.cookies.get("csrf_token") or ""})
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "提交者一", "password": "提交者密码-2026"},
    )
    assert response.status_code == 200
    summary = client.get("/api/v1/users/me/contributions?campus_id=rank_campus").json()["data"]
    assert summary["approved_shop_count"] == 2
    assert summary["rank"] == 1

    all_campuses = client.get("/api/v1/users/me/contributions").json()["data"]
    assert all_campuses["approved_shop_count"] == 2
    assert all_campuses["rank"] is None
