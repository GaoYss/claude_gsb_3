"""药剂安全管控测试：档案、出入库库存联动、施药间隔期推算与重复施药提示。"""

from datetime import date

from app.utils.dates import today


# ================================================================ 药剂档案
def pesticide_payload(**overrides):
    payload = {
        "name": "吡虫啉可湿性粉剂",
        "pesticide_type": "insecticide",
        "toxicity": "low",
        "form": "wp",
        "active_ingredient": "吡虫啉 10%",
        "registration_no": "PD20240001",
        "manufacturer": "某农化有限公司",
        "unit": "bag",
        "stock_quantity": 100,
        "stock_low_threshold": 20,
        "safety_interval_days": 7,
        "target_pests": "蚜虫、飞虱",
    }
    payload.update(overrides)
    return payload


def test_create_pesticide_generates_code_and_labels(api):
    data = api.data(api.post("/api/v1/pesticides", pesticide_payload()), 201)
    assert data["code"].startswith("PC-")
    assert data["stock_quantity"] == 100.0
    assert data["is_low_stock"] is False
    assert data["pesticide_type_label"] == "杀虫剂"
    assert data["toxicity_label"] == "低毒"
    assert data["unit_label"] == "袋"
    assert data["safety_interval_days"] == 7


def test_pesticide_validation(api):
    response = api.post("/api/v1/pesticides", pesticide_payload(
        name="", pesticide_type="unknown", safety_interval_days=400))
    assert response.status_code == 422
    details = response.get_json()["data"]
    assert "name" in details
    assert "pesticide_type" in details
    assert "safety_interval_days" in details


def test_low_stock_flag(api):
    data = api.data(api.post(
        "/api/v1/pesticides", pesticide_payload(stock_quantity=8, stock_low_threshold=20)), 201)
    assert data["is_low_stock"] is True


def test_stock_cannot_be_edited_directly(api, make_pesticide):
    pesticide = make_pesticide(stock_quantity=100)
    data = api.data(api.put(f"/api/v1/pesticides/{pesticide.id}", pesticide_payload(
        name=pesticide.name, pesticide_type=pesticide.pesticide_type,
        safety_interval_days=pesticide.safety_interval_days, unit=pesticide.unit,
        stock_quantity=999)))
    assert data["stock_quantity"] == 100.0


def test_pesticide_options_include_stock(api, make_pesticide):
    make_pesticide(name="阿维菌素", stock_quantity=5, stock_low_threshold=10)
    data = api.data(api.get("/api/v1/pesticides/options", keyword="阿维"))
    assert len(data["items"]) == 1
    assert data["items"][0]["stock_quantity"] == 5.0
    assert data["items"][0]["is_low_stock"] is True


def test_delete_pesticide_blocked_until_force(api, make_application):
    application = make_application()
    pesticide_id = application.pesticide_id
    response = api.delete(f"/api/v1/pesticides/{pesticide_id}")
    assert response.status_code == 409
    assert response.get_json()["data"]["pesticide_application"] == 1

    # 强制删除档案后，施药履历保留并解除关联，名称走快照
    api.data(api.delete(f"/api/v1/pesticides/{pesticide_id}", force="true"))
    detail = api.data(api.get(f"/api/v1/pesticide-applications/{application.id}"))
    assert detail["pesticide_id"] is None
    assert detail["pesticide_name"] == application.pesticide_name


# ================================================================ 出入库与库存
def movement_payload(pesticide_id, **overrides):
    payload = {
        "pesticide_id": pesticide_id,
        "movement_type": "out",
        "quantity": 10,
        "movement_date": "2026-03-12",
        "receiver": "吴国强",
        "purpose": "蚜虫防治领用",
        "operator": "孙明华",
    }
    payload.update(overrides)
    return payload


def test_stock_in_and_out(api, make_pesticide):
    pesticide = make_pesticide(stock_quantity=100)

    in_data = api.data(api.post(
        "/api/v1/pesticide-stock-movements",
        movement_payload(pesticide.id, movement_type="in", quantity=20)), 201)
    assert in_data["movement_no"].startswith("SM-")
    assert in_data["unit_label"] == "袋"  # 计量单位跟随档案
    assert api.data(api.get(f"/api/v1/pesticides/{pesticide.id}"))["stock_quantity"] == 120.0

    api.data(api.post(
        "/api/v1/pesticide-stock-movements",
        movement_payload(pesticide.id, movement_type="out", quantity=50)), 201)
    assert api.data(api.get(f"/api/v1/pesticides/{pesticide.id}"))["stock_quantity"] == 70.0


def test_out_more_than_stock_is_rejected(api, make_pesticide):
    pesticide = make_pesticide(stock_quantity=8)
    response = api.post(
        "/api/v1/pesticide-stock-movements",
        movement_payload(pesticide.id, movement_type="out", quantity=20))
    assert response.status_code == 409
    body = response.get_json()
    assert "库存不足" in body["message"]
    assert body["data"]["stock_quantity"] == 8.0
    # 库存不发生变化
    assert api.data(api.get(f"/api/v1/pesticides/{pesticide.id}"))["stock_quantity"] == 8.0


def test_delete_movement_rolls_back_stock(api, make_pesticide):
    pesticide = make_pesticide(stock_quantity=100)
    inbound = api.data(api.post(
        "/api/v1/pesticide-stock-movements",
        movement_payload(pesticide.id, movement_type="in", quantity=30)), 201)
    outbound = api.data(api.post(
        "/api/v1/pesticide-stock-movements",
        movement_payload(pesticide.id, movement_type="out", quantity=20)), 201)
    assert api.data(api.get(f"/api/v1/pesticides/{pesticide.id}"))["stock_quantity"] == 110.0

    # 删除领用单：库存补回
    api.data(api.delete(f"/api/v1/pesticide-stock-movements/{outbound['id']}"))
    assert api.data(api.get(f"/api/v1/pesticides/{pesticide.id}"))["stock_quantity"] == 130.0
    # 删除入库单：库存扣回
    api.data(api.delete(f"/api/v1/pesticide-stock-movements/{inbound['id']}"))
    assert api.data(api.get(f"/api/v1/pesticides/{pesticide.id}"))["stock_quantity"] == 100.0


def test_movement_references_existing_pesticide(api):
    response = api.post("/api/v1/pesticide-stock-movements",
                        movement_payload(99999, movement_type="in", quantity=10))
    assert response.status_code == 422
    assert "pesticide_id" in response.get_json()["data"]


def test_movement_detached_when_green_space_deleted(api, make_space, make_pesticide):
    space = make_space()
    pesticide = make_pesticide(stock_quantity=50)
    # 登记一条关联绿地的领用流水
    from app.services import PesticideStockMovementService
    record = PesticideStockMovementService.create({
        "pesticide_id": pesticide.id,
        "movement_type": "out",
        "quantity": 2,
        "movement_date": date(2026, 3, 12),
        "green_space_id": space.id,
        "receiver": "吴国强",
    })
    movement_id = record.id
    api.data(api.delete(f"/api/v1/green-spaces/{space.id}", force="true"))
    detail = api.data(api.get(f"/api/v1/pesticide-stock-movements/{movement_id}"))
    assert detail["green_space_id"] is None
    assert detail["pesticide_id"] == pesticide.id


# ================================================================ 施药记录
def application_payload(space_id, pesticide_id, **overrides):
    payload = {
        "green_space_id": space_id,
        "pesticide_id": pesticide_id,
        "location": "东区草坪",
        "application_date": "2026-03-12",
        "application_time": "08:30",
        "target_pest": "蚜虫",
        "application_method": "spray",
        "dilution_ratio": "1:1500",
        "dosage": 3,
        "treated_area": 2400,
        "operator": "吴国强",
        "weather": "sunny",
    }
    payload.update(overrides)
    return payload


def test_create_application_snapshots_and_calculates_reentry(api, make_space, make_pesticide):
    space = make_space()
    pesticide = make_pesticide(safety_interval_days=7)
    data = api.data(api.post(
        "/api/v1/pesticide-applications",
        application_payload(space.id, pesticide.id)), 201)
    assert data["application_no"].startswith("PA-")
    assert data["pesticide_name"] == pesticide.name
    assert data["unit_label"] == "袋"
    assert data["earliest_reentry_at"] == "2026-03-19 08:30"
    assert data["applied_at"] == "2026-03-12 08:30"
    assert data["application_method_label"] == "喷雾"


def test_reentry_without_time_starts_at_midnight(api, make_space, make_pesticide):
    space = make_space()
    pesticide = make_pesticide(safety_interval_days=5)
    data = api.data(api.post(
        "/api/v1/pesticide-applications",
        application_payload(space.id, pesticide.id, application_time=None)), 201)
    assert data["earliest_reentry_at"] == "2026-03-17 00:00"


def test_application_required_fields(api, make_space, make_pesticide):
    space = make_space()
    pesticide = make_pesticide()
    response = api.post("/api/v1/pesticide-applications", {
        "green_space_id": space.id,
        "pesticide_id": pesticide.id,
        "application_date": "2026-03-12",
    })
    assert response.status_code == 422
    details = response.get_json()["data"]
    assert "target_pest" in details and "dosage" in details and "operator" in details


def test_application_date_not_before_established(api, make_space, make_pesticide):
    space = make_space(established_date=date(2020, 1, 1))
    pesticide = make_pesticide()
    response = api.post(
        "/api/v1/pesticide-applications",
        application_payload(space.id, pesticide.id, application_date="2019-05-01"))
    assert response.status_code == 422
    assert "application_date" in response.get_json()["data"]


def test_interval_check_preview(api, make_space, make_pesticide):
    space = make_space()
    pesticide = make_pesticide(safety_interval_days=7)
    api.data(api.post("/api/v1/pesticide-applications",
                      application_payload(space.id, pesticide.id, application_date="2026-03-10")), 201)
    data = api.data(api.get(
        "/api/v1/pesticide-applications/interval-check",
        green_space_id=space.id, application_date="2026-03-12"))
    assert len(data["within_interval"]) == 1
    assert data["latest_reentry_at"] == "2026-03-17 08:30"

    clear = api.data(api.get(
        "/api/v1/pesticide-applications/interval-check",
        green_space_id=space.id, application_date="2026-03-20"))
    assert clear["within_interval"] == []


def test_interval_check_excludes_self_when_editing(api, make_space, make_pesticide):
    space = make_space()
    pesticide = make_pesticide(safety_interval_days=30)
    app = api.data(api.post(
        "/api/v1/pesticide-applications",
        application_payload(space.id, pesticide.id, application_date="2026-03-10")), 201)
    # 不带 exclude 时该记录自身算冲突；带上 exclude_id（编辑场景）后不再提示自己
    with_self = api.data(api.get(
        "/api/v1/pesticide-applications/interval-check",
        green_space_id=space.id, application_date="2026-03-12"))
    assert len(with_self["within_interval"]) == 1

    without_self = api.data(api.get(
        "/api/v1/pesticide-applications/interval-check",
        green_space_id=space.id, application_date="2026-03-12", exclude_id=app["id"]))
    assert without_self["within_interval"] == []


def test_reapplication_within_interval_warns_then_confirms(api, make_space, make_pesticide):
    space = make_space()
    pesticide_a = make_pesticide(name="药剂甲", safety_interval_days=10)
    pesticide_b = make_pesticide(name="药剂乙", safety_interval_days=3)
    first_payload = application_payload(space.id, pesticide_a.id, application_date="2026-03-10")
    api.data(api.post("/api/v1/pesticide-applications", first_payload), 201)

    # 间隔期内（最早 3-20 才可进入）同区域再施药：先返回 409 软警告
    response = api.post(
        "/api/v1/pesticide-applications",
        application_payload(space.id, pesticide_b.id, application_date="2026-03-12"))
    assert response.status_code == 409
    body = response.get_json()
    assert body["data"]["confirm_required"] is True
    assert len(body["data"]["conflicts"]) == 1
    assert body["data"]["conflicts"][0]["pesticide_name"] == "药剂甲"

    # 未确认时不会落库
    listed = api.data(api.get("/api/v1/pesticide-applications", green_space_id=space.id))
    assert listed["meta"]["total"] == 1

    # 二次确认后允许登记（即便换了另一种药剂，仍按同一区域管控）
    resp2 = api.post("/api/v1/pesticide-applications?confirm=true",
                     json=application_payload(space.id, pesticide_b.id, application_date="2026-03-12"))
    assert resp2.status_code == 201
    listed = api.data(api.get("/api/v1/pesticide-applications", green_space_id=space.id))
    assert listed["meta"]["total"] == 2


def test_reapplication_after_interval_is_fine(api, make_space, make_pesticide):
    space = make_space()
    pesticide = make_pesticide(safety_interval_days=7)
    api.data(api.post("/api/v1/pesticide-applications",
                      application_payload(space.id, pesticide.id, application_date="2026-03-10")), 201)
    # 3-20 已超出最早可进入时间 3-17，不再提示
    resp = api.post("/api/v1/pesticide-applications",
                    json=application_payload(space.id, pesticide.id, application_date="2026-03-20"))
    assert resp.status_code == 201


def test_different_green_space_is_not_conflict(api, make_space, make_pesticide):
    space_a = make_space(name="绿地甲")
    space_b = make_space(name="绿地乙")
    pesticide = make_pesticide(safety_interval_days=10)
    api.data(api.post("/api/v1/pesticide-applications",
                      application_payload(space_a.id, pesticide.id, application_date="2026-03-10")), 201)
    resp = api.post("/api/v1/pesticide-applications",
                    json=application_payload(space_b.id, pesticide.id, application_date="2026-03-11"))
    assert resp.status_code == 201


def test_update_application_recomputes_reentry(api, make_space, make_pesticide):
    space = make_space()
    pesticide = make_pesticide(safety_interval_days=7)
    app = api.data(api.post("/api/v1/pesticide-applications",
                            application_payload(space.id, pesticide.id, application_date="2026-03-12")), 201)
    updated = api.data(api.put(
        f"/api/v1/pesticide-applications/{app['id']}",
        application_payload(space.id, pesticide.id,
                            application_date="2026-03-13", application_time="09:00")))
    assert updated["earliest_reentry_at"] == "2026-03-20 09:00"


def test_interval_status_filter_and_summary(api, make_space, make_pesticide):
    space = make_space()
    pesticide = make_pesticide(safety_interval_days=30)
    today_ = today()
    # 今日施药：仍在间隔期内
    api.data(api.post(
        "/api/v1/pesticide-applications",
        application_payload(space.id, pesticide.id,
                            application_date=today_.isoformat(), application_time="08:00")), 201)
    within = api.data(api.get(
        "/api/v1/pesticide-applications", interval_status="within"))
    assert within["meta"]["total"] >= 1
    assert within["items"][0]["reentry_status"] == "within_interval"
    summary = api.data(api.get("/api/v1/pesticide-applications/summary"))
    assert summary["within_interval_count"] >= 1
