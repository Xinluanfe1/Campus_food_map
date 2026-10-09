"""评价、顶踩、回复与举报测试：对应第六步验收标准。"""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Campus, Report, Review, ReviewReaction, ReviewReply, Shop, User

AUTHOR_USERNAME = "评价作者"
AUTHOR_PASSWORD = "评价作者密码-2026"
OTHER_USERNAME = "互动用户"
OTHER_PASSWORD = "互动用户密码-2026"
ADMIN_USERNAME = "举报管理员"
ADMIN_PASSWORD = "举报管理员密码-2026"


def create_user(engine: Engine, username: str, password: str, role: str = "user") -> int:
    with Session(engine) as session:
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id


def create_approved_shop(engine: Engine, shop_id: int = 501) -> None:
    """创建测试校园与已审核通过的店铺。"""

    with Session(engine) as session:
        session.add(
            Campus(
                campus_id="review_campus",
                campus_name="评价测试校园",
                map_type="image",
                map_asset_url="/assets/maps/review.png",
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
        session.add(
            User(
                id=1,
                username="店铺提交者",
                password_hash=hash_password("店铺提交者密码-2026"),
                role="user",
                is_active=True,
            )
        )
        session.commit()
        session.add(
            Shop(
                id=shop_id,
                campus_id="review_campus",
                name="评价测试店铺",
                description="用于评价测试的店铺。",
                shop_type="shop",
                submitted_by=1,
                status="approved",
                map_x=0.3,
                map_y=0.4,
            )
        )
        session.commit()


def login(client: TestClient, username: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text


def csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("csrf_token")
    if token is None:
        client.get("/api/v1/health")
        token = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": token or ""}


def submit_review(client: TestClient, shop_id: int = 501, rating: int = 5, content: str = "味道不错。"):
    return client.post(
        f"/api/v1/shops/{shop_id}/reviews",
        json={"rating": rating, "content": content},
        headers=csrf_headers(client),
    )


def prepare_author(engine: Engine, client: TestClient) -> int:
    create_approved_shop(engine)
    create_user(engine, AUTHOR_USERNAME, AUTHOR_PASSWORD)
    login(client, AUTHOR_USERNAME, AUTHOR_PASSWORD)
    response = submit_review(client)
    assert response.status_code == 201
    return response.json()["data"]["id"]


def logout(client: TestClient) -> None:
    client.post("/api/v1/auth/logout", headers=csrf_headers(client))


def test_review_requires_login(client: TestClient, engine: Engine) -> None:
    """验收标准 2：未登录用户不能提交评价。"""

    create_approved_shop(engine)
    response = client.post(
        "/api/v1/shops/501/reviews",
        json={"rating": 5, "content": "匿名评价"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 401
    assert response.json()["message"] == "当前操作需要登录。"


def test_review_validates_rating_and_content(client: TestClient, engine: Engine) -> None:
    """验收标准 1：评分必须是 1 至 5 的整数，内容不能为空。"""

    create_approved_shop(engine)
    create_user(engine, AUTHOR_USERNAME, AUTHOR_PASSWORD)
    login(client, AUTHOR_USERNAME, AUTHOR_PASSWORD)

    bad_rating = submit_review(client, rating=6)
    assert bad_rating.status_code == 422
    assert bad_rating.json()["data"]["errors"][0]["message"] == "评分必须是 1 至 5 的整数。"

    empty_content = submit_review(client, content="   ")
    assert empty_content.status_code == 422
    assert empty_content.json()["data"]["errors"][0]["message"] == "评价内容不能为空。"


def test_review_only_for_approved_shop(client: TestClient, engine: Engine) -> None:
    """评价只能关联审核通过的店铺。"""

    create_approved_shop(engine)
    create_user(engine, AUTHOR_USERNAME, AUTHOR_PASSWORD)
    with Session(engine) as session:
        shop = session.get(Shop, 501)
        shop.status = "pending"
        session.commit()

    login(client, AUTHOR_USERNAME, AUTHOR_PASSWORD)
    response = submit_review(client)
    assert response.status_code == 404
    assert response.json()["message"] == "店铺不存在或未公开。"


def test_review_upsert_keeps_single_record(client: TestClient, engine: Engine) -> None:
    """验收标准 3、4：同一用户对同一家店铺只保留一条主评价，更新不产生重复记录。"""

    create_approved_shop(engine)
    create_user(engine, AUTHOR_USERNAME, AUTHOR_PASSWORD)
    login(client, AUTHOR_USERNAME, AUTHOR_PASSWORD)

    first = submit_review(client, rating=5)
    assert first.status_code == 201
    second = submit_review(client, rating=3, content="再想想，改成三星。")
    assert second.status_code == 200
    assert second.json()["message"] == "评价已更新。"

    with Session(engine) as session:
        count = session.scalar(select(func.count()).select_from(Review)) or 0
        review = session.scalar(select(Review))
        assert count == 1
        assert review.rating == 3
        assert review.content == "再想想，改成三星。"


def test_only_author_can_edit_or_delete_review(client: TestClient, engine: Engine) -> None:
    """验收标准 5：用户只能修改或删除自己的评价。"""

    review_id = prepare_author(engine, client)
    logout(client)
    create_user(engine, OTHER_USERNAME, OTHER_PASSWORD)
    login(client, OTHER_USERNAME, OTHER_PASSWORD)

    forbidden_edit = client.patch(
        f"/api/v1/reviews/{review_id}",
        json={"rating": 1},
        headers=csrf_headers(client),
    )
    assert forbidden_edit.status_code == 403
    assert forbidden_edit.json()["message"] == "只能修改或删除自己的评价。"

    forbidden_delete = client.delete(f"/api/v1/reviews/{review_id}", headers=csrf_headers(client))
    assert forbidden_delete.status_code == 403

    logout(client)
    login(client, AUTHOR_USERNAME, AUTHOR_PASSWORD)
    edited = client.patch(
        f"/api/v1/reviews/{review_id}",
        json={"rating": 2, "content": "修改后的评价内容。"},
        headers=csrf_headers(client),
    )
    assert edited.status_code == 200
    assert edited.json()["data"]["rating"] == 2

    deleted = client.delete(f"/api/v1/reviews/{review_id}", headers=csrf_headers(client))
    assert deleted.status_code == 200
    assert deleted.json()["message"] == "评价已删除。"

    with Session(engine) as session:
        assert (session.scalar(select(func.count()).select_from(Review)) or 0) == 0


def test_review_list_requires_login_and_hides_hidden_reviews(client: TestClient, engine: Engine) -> None:
    """验收标准 12：隐藏评价不得被普通用户读取。"""

    review_id = prepare_author(engine, client)

    with Session(engine) as session:
        review = session.get(Review, review_id)
        review.status = "hidden"
        session.commit()

    listed = client.get("/api/v1/shops/501/reviews")
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 0

    logout(client)
    guest = client.get("/api/v1/shops/501/reviews")
    assert guest.status_code == 401


def test_reaction_set_switch_and_cancel(client: TestClient, engine: Engine) -> None:
    """验收标准 6、7：顶踩互斥、重复操作不产生重复记录。"""

    review_id = prepare_author(engine, client)
    logout(client)
    create_user(engine, OTHER_USERNAME, OTHER_PASSWORD)
    login(client, OTHER_USERNAME, OTHER_PASSWORD)

    liked = client.put(
        f"/api/v1/reviews/{review_id}/reaction",
        json={"reaction_type": "like"},
        headers=csrf_headers(client),
    )
    assert liked.status_code == 200

    # 幂等：重复点赞仍是同一条记录
    client.put(
        f"/api/v1/reviews/{review_id}/reaction",
        json={"reaction_type": "like"},
        headers=csrf_headers(client),
    )
    with Session(engine) as session:
        assert (session.scalar(select(func.count()).select_from(ReviewReaction)) or 0) == 1

    # 切换为点踩：不能同时存在两种互动
    client.put(
        f"/api/v1/reviews/{review_id}/reaction",
        json={"reaction_type": "dislike"},
        headers=csrf_headers(client),
    )
    with Session(engine) as session:
        reactions = session.scalars(select(ReviewReaction)).all()
        assert len(reactions) == 1
        assert reactions[0].reaction_type == "dislike"

    detail = client.get("/api/v1/shops/501/reviews").json()["data"]["items"][0]
    assert detail["like_count"] == 0
    assert detail["dislike_count"] == 1
    assert detail["my_reaction"] == "dislike"

    cancelled = client.delete(f"/api/v1/reviews/{review_id}/reaction", headers=csrf_headers(client))
    assert cancelled.status_code == 200
    with Session(engine) as session:
        assert (session.scalar(select(func.count()).select_from(ReviewReaction)) or 0) == 0

    invalid = client.put(
        f"/api/v1/reviews/{review_id}/reaction",
        json={"reaction_type": "love"},
        headers=csrf_headers(client),
    )
    assert invalid.status_code == 422
    assert invalid.json()["data"]["errors"][0]["message"] == (
        "互动类型只允许 like（点赞）或 dislike（点踩）。"
    )


def test_reaction_requires_login_and_visible_review(client: TestClient, engine: Engine) -> None:
    """隐藏评价不能进行新的互动，游客不能互动。"""

    review_id = prepare_author(engine, client)

    with Session(engine) as session:
        review = session.get(Review, review_id)
        review.status = "hidden"
        session.commit()

    hidden = client.put(
        f"/api/v1/reviews/{review_id}/reaction",
        json={"reaction_type": "like"},
        headers=csrf_headers(client),
    )
    assert hidden.status_code == 404
    assert hidden.json()["message"] == "评价不存在或已被隐藏。"

    logout(client)
    guest = client.put(
        f"/api/v1/reviews/{review_id}/reaction",
        json={"reaction_type": "like"},
        headers=csrf_headers(client),
    )
    assert guest.status_code == 401


def test_reply_is_single_level(client: TestClient, engine: Engine) -> None:
    """验收标准 8：支持一级回复，不支持多层嵌套回复。"""

    review_id = prepare_author(engine, client)
    logout(client)
    create_user(engine, OTHER_USERNAME, OTHER_PASSWORD)
    login(client, OTHER_USERNAME, OTHER_PASSWORD)

    created = client.post(
        f"/api/v1/reviews/{review_id}/replies",
        json={"content": "我也觉得不错。"},
        headers=csrf_headers(client),
    )
    assert created.status_code == 201
    reply_id = created.json()["data"]["id"]

    replies = client.get(f"/api/v1/reviews/{review_id}/replies")
    assert replies.status_code == 200
    items = replies.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["username"] == OTHER_USERNAME

    nested = client.post(
        f"/api/v1/replies/{reply_id}/replies",
        json={"content": "对回复的回复"},
        headers=csrf_headers(client),
    )
    assert nested.status_code == 404

    empty = client.post(
        f"/api/v1/reviews/{review_id}/replies",
        json={"content": "   "},
        headers=csrf_headers(client),
    )
    assert empty.status_code == 422
    assert empty.json()["data"]["errors"][0]["message"] == "回复内容不能为空。"


def test_reply_delete_by_author_and_hide_by_admin(client: TestClient, engine: Engine) -> None:
    """回复作者可以删除自己的回复，管理员可以隐藏违规回复。"""

    review_id = prepare_author(engine, client)
    author_user_id = create_user(engine, OTHER_USERNAME, OTHER_PASSWORD)
    logout(client)
    login(client, OTHER_USERNAME, OTHER_PASSWORD)

    first_reply = client.post(
        f"/api/v1/reviews/{review_id}/replies",
        json={"content": "第一条回复"},
        headers=csrf_headers(client),
    ).json()["data"]["id"]
    second_reply = client.post(
        f"/api/v1/reviews/{review_id}/replies",
        json={"content": "第二条回复"},
        headers=csrf_headers(client),
    ).json()["data"]["id"]

    # 其他用户不能删除他人回复
    logout(client)
    login(client, AUTHOR_USERNAME, AUTHOR_PASSWORD)
    forbidden = client.delete(f"/api/v1/replies/{first_reply}", headers=csrf_headers(client))
    assert forbidden.status_code == 403

    # 管理员可以隐藏违规回复
    logout(client)
    create_user(engine, ADMIN_USERNAME, ADMIN_PASSWORD, role="admin")
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    hidden = client.delete(f"/api/v1/replies/{second_reply}", headers=csrf_headers(client))
    assert hidden.status_code == 200
    assert hidden.json()["data"]["action"] == "hidden"

    with Session(engine) as session:
        reply = session.get(ReviewReply, second_reply)
        assert reply is not None
        assert reply.status == "hidden"

    # 作者自己删除第一条回复
    logout(client)
    login(client, OTHER_USERNAME, OTHER_PASSWORD)
    deleted = client.delete(f"/api/v1/replies/{first_reply}", headers=csrf_headers(client))
    assert deleted.status_code == 200
    assert deleted.json()["data"]["action"] == "deleted"
    assert review_id  # 保持变量被使用，便于阅读
    assert author_user_id


def test_report_does_not_hide_review_automatically(client: TestClient, engine: Engine) -> None:
    """验收标准 9、10：用户可以举报评价，举报不会自动隐藏评价。"""

    review_id = prepare_author(engine, client)
    logout(client)
    create_user(engine, OTHER_USERNAME, OTHER_PASSWORD)
    login(client, OTHER_USERNAME, OTHER_PASSWORD)

    reported = client.post(
        f"/api/v1/reviews/{review_id}/reports",
        json={"reason": "评价内容包含不适当信息。"},
        headers=csrf_headers(client),
    )
    assert reported.status_code == 201

    # 重复举报受限制
    duplicated = client.post(
        f"/api/v1/reviews/{review_id}/reports",
        json={"reason": "再次举报。"},
        headers=csrf_headers(client),
    )
    assert duplicated.status_code == 409
    assert duplicated.json()["message"] == "你已经举报过这条评价，请等待管理员处理。"

    # 评价仍然可见
    listed = client.get("/api/v1/shops/501/reviews")
    assert listed.json()["data"]["total"] == 1

    empty_reason = client.post(
        f"/api/v1/reviews/{review_id}/reports",
        json={"reason": "   "},
        headers=csrf_headers(client),
    )
    assert empty_reason.status_code == 422
    assert empty_reason.json()["data"]["errors"][0]["message"] == "请填写举报理由。"


def test_admin_reports_require_admin(client: TestClient, engine: Engine) -> None:
    """验收标准 14：举报处理接口必须经过管理员权限校验。"""

    prepare_author(engine, client)

    logout(client)
    guest = client.get("/api/v1/admin/reports")
    assert guest.status_code == 401

    create_user(engine, OTHER_USERNAME, OTHER_PASSWORD)
    login(client, OTHER_USERNAME, OTHER_PASSWORD)
    ordinary = client.get("/api/v1/admin/reports")
    assert ordinary.status_code == 403
    assert ordinary.json()["message"] == "当前操作需要管理员权限。"


def test_admin_can_dismiss_report_and_keep_review(client: TestClient, engine: Engine) -> None:
    """验收标准 11：管理员可以驳回举报并保留评价，处理记录可追溯。"""

    review_id = prepare_author(engine, client)
    logout(client)
    create_user(engine, OTHER_USERNAME, OTHER_PASSWORD)
    login(client, OTHER_USERNAME, OTHER_PASSWORD)
    client.post(
        f"/api/v1/reviews/{review_id}/reports",
        json={"reason": "疑似广告内容。"},
        headers=csrf_headers(client),
    )

    logout(client)
    admin_id = create_user(engine, ADMIN_USERNAME, ADMIN_PASSWORD, role="admin")
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    listed = client.get("/api/v1/admin/reports")
    assert listed.status_code == 200
    data = listed.json()["data"]
    assert data["total"] == 1
    item = data["items"][0]
    assert item["review_content"] == "味道不错。"
    assert item["shop_name"] == "评价测试店铺"
    assert item["reporter_username"] == OTHER_USERNAME
    assert item["reason"] == "疑似广告内容。"

    dismissed = client.post(
        f"/api/v1/admin/reports/{item['id']}/dismiss",
        json={"handling_note": "经核实，评价内容正常。"},
        headers=csrf_headers(client),
    )
    assert dismissed.status_code == 200
    assert dismissed.json()["message"] == "举报已驳回，评价保留。"

    with Session(engine) as session:
        report = session.get(Report, item["id"])
        assert report.status == "dismissed"
        assert report.handled_by == admin_id
        assert report.handled_at is not None
        assert report.handling_note == "经核实，评价内容正常。"

    # 评价仍然可见
    assert client.get("/api/v1/shops/501/reviews").json()["data"]["total"] == 1


def test_admin_resolve_hides_review_and_updates_rating(client: TestClient, engine: Engine) -> None:
    """验收标准 11、12、13：隐藏评价后立即从评价列表与评分统计中移除。"""

    review_id = prepare_author(engine, client)

    before = client.get("/api/v1/campuses/review_campus/shops/501").json()["data"]["rating"]
    assert before["review_count"] == 1
    assert before["average_rating"] == 5.0

    logout(client)
    create_user(engine, OTHER_USERNAME, OTHER_PASSWORD)
    login(client, OTHER_USERNAME, OTHER_PASSWORD)
    client.post(
        f"/api/v1/reviews/{review_id}/reports",
        json={"reason": "包含人身攻击。"},
        headers=csrf_headers(client),
    )

    logout(client)
    create_user(engine, ADMIN_USERNAME, ADMIN_PASSWORD, role="admin")
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    report_id = client.get("/api/v1/admin/reports").json()["data"]["items"][0]["id"]
    resolved = client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        json={"action": "hide_review", "handling_note": "评价违反平台内容规范。"},
        headers=csrf_headers(client),
    )
    assert resolved.status_code == 200
    assert resolved.json()["data"]["status"] == "resolved"

    # 隐藏后评价不再出现在公开评价列表
    assert client.get("/api/v1/shops/501/reviews").json()["data"]["total"] == 0

    # 评分统计立即更新（排行榜在第七步实现，届时使用同一份统计数据）
    after = client.get("/api/v1/campuses/review_campus/shops/501").json()["data"]["rating"]
    assert after["review_count"] == 0
    assert after["average_rating"] is None
    assert after["weighted_rating"] is None

    with Session(engine) as session:
        review = session.get(Review, review_id)
        assert review.status == "hidden"

    # 处理动作只允许 hide_review
    invalid_action = client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        json={"action": "delete_review"},
        headers=csrf_headers(client),
    )
    assert invalid_action.status_code in (400, 422)
