"""药剂管理接口与安全管控规则测试。"""

from datetime import timedelta

from app.utils.dates import today


def pesticide_payload(**overrides):
    payload = {
        "name": "10% 吡虫啉可湿性粉剂",
        "registration_no": "PD20181234",
        "pesticide_type": "insecticide",
        "toxicity": "low",
        "active_ingredient": "吡虫啉 10%",
        "safety_interval_days": 7,
        "stock_quantity": 5000,
        "unit": "gram",
    }
    payload.update(overrides)
    return payload


def requisition_payload(pesticide_id, **overrides):
    payload = {
        "pesticide_id": pesticide_id,
        "quantity": 500,
        "recipient": "王海涛",
        "issue_date": today().isoformat(),
        "purpose": "蚜虫防治用药",
    }
    payload.update(overrides)
    return payload


def application_payload(pesticide_id, space_id, **overrides):
    payload = {
        "pesticide_id": pesticide_id,
        "green_space_id": space_id,
        "application_date": today().isoformat(),
        "target_pest": "蚜虫",
        "apply_area": 3000,
        "dilution_ratio": "1:1500",
        "dosage": 300,
        "operator": "李建民",
        "equipment": "背负式电动喷雾器",
    }
    payload.update(overrides)
    return payload


# ================================================================ 药剂档案
def test_create_pesticide_generates_code(api):
    data = api.data(api.post("/api/v1/pesticides", pesticide_payload()), 201)
    assert data["code"].startswith("PC-")
    assert data["name"] == "10% 吡虫啉可湿性粉剂"
    assert data["pesticide_type_label"] == "杀虫剂"
    assert data["toxicity_label"] == "低毒"
    assert data["safety_interval_days"] == 7
    assert data["status_label"] == "在用"


def test_pesticide_required_fields_validated(api):
    response = api.post("/api/v1/pesticides",
                        pesticide_payload(name="", pesticide_type="x", toxicity=None,
                                          safety_interval_days=400))
    assert response.status_code == 422
    details = response.get_json()["data"]
    assert "name" in details
    assert "pesticide_type" in details
    assert "toxicity" in details
    assert "safety_interval_days" in details


def test_pesticide_options_excludes_inactive(api, make_pesticide):
    make_pesticide(name="在用药剂")
    make_pesticide(name="停用药剂", status="phase_out")
    data = api.data(api.get("/api/v1/pesticides/options"))
    names = [item["name"] for item in data["items"]]
    assert "在用药剂" in names
    assert "停用药剂" not in names

    all_data = api.data(api.get("/api/v1/pesticides/options", include_inactive="true"))
    assert "停用药剂" in [item["name"] for item in all_data["items"]]


def test_list_pesticides_filters_by_type_and_status(api, make_pesticide):
    make_pesticide(pesticide_type="fungicide")
    make_pesticide(pesticide_type="insecticide", status="banned")

    data = api.data(api.get("/api/v1/pesticides", pesticide_type="fungicide"))
    assert data["meta"]["total"] == 1
    assert data["items"][0]["pesticide_type"] == "fungicide"

    banned = api.data(api.get("/api/v1/pesticides", status="banned"))
    assert banned["meta"]["total"] == 1


def test_delete_pesticide_blocked_with_records(api, make_application):
    application = make_application()
    pesticide_id = application.pesticide_id

    response = api.delete(f"/api/v1/pesticides/{pesticide_id}")
    assert response.status_code == 409
    assert response.get_json()["data"]["pesticide_application"] == 1

    api.data(api.delete(f"/api/v1/pesticides/{pesticide_id}", force="true"))
    assert api.get(f"/api/v1/pesticides/{pesticide_id}").status_code == 404


# ================================================================ 药剂领用
def test_requisition_deducts_stock(api, make_pesticide):
    pesticide = make_pesticide(stock_quantity=5000)
    data = api.data(
        api.post("/api/v1/pesticide-requisitions",
                 requisition_payload(pesticide.id, quantity=1200)),
        201,
    )
    assert data["requisition_no"].startswith("RC-")
    assert data["status"] == "issued"
    stock = api.data(api.get(f"/api/v1/pesticides/{pesticide.id}"))["stock_quantity"]
    assert stock == 3800.0


def test_requisition_over_stock_rejected(api, make_pesticide):
    pesticide = make_pesticide(stock_quantity=100)
    response = api.post("/api/v1/pesticide-requisitions",
                        requisition_payload(pesticide.id, quantity=500))
    assert response.status_code == 409
    assert "库存不足" in response.get_json()["message"]


def test_banned_pesticide_cannot_be_requisitioned(api, make_pesticide):
    pesticide = make_pesticide(status="banned", stock_quantity=9999)
    response = api.post("/api/v1/pesticide-requisitions",
                        requisition_payload(pesticide.id))
    assert response.status_code == 409
    assert "禁用" in response.get_json()["message"]


def test_return_requisition_replenishes_stock(api, make_requisition, make_pesticide):
    pesticide = make_pesticide(stock_quantity=1000)
    requisition = make_requisition(pesticide=pesticide, quantity=400,
                                   issue_date=today() - timedelta(days=2))
    data = api.data(api.patch(
        f"/api/v1/pesticide-requisitions/{requisition.id}/return",
        {"returned_quantity": 100, "returned_at": today().isoformat()},
    ))
    assert data["status"] == "returned"
    assert data["returned_quantity"] == 100.0
    stock = api.data(api.get(f"/api/v1/pesticides/{pesticide.id}"))["stock_quantity"]
    # 领用扣 400，退库补 100
    assert stock == 700.0


def test_return_cannot_repeat_or_exceed_quantity(api, make_requisition):
    requisition = make_requisition(quantity=200)
    api.patch(f"/api/v1/pesticide-requisitions/{requisition.id}/return",
              {"returned_quantity": 50, "returned_at": today().isoformat()})

    repeat = api.patch(f"/api/v1/pesticide-requisitions/{requisition.id}/return",
                       {"returned_quantity": 10, "returned_at": today().isoformat()})
    assert repeat.status_code == 409

    over = make_requisition(quantity=100)
    response = api.patch(f"/api/v1/pesticide-requisitions/{over.id}/return",
                         {"returned_quantity": 150, "returned_at": today().isoformat()})
    assert response.status_code == 422
    assert "退库数量不能大于领用数量" in response.get_json()["data"]["returned_quantity"]


def test_requisition_future_date_rejected(api, make_pesticide):
    pesticide = make_pesticide()
    response = api.post(
        "/api/v1/pesticide-requisitions",
        requisition_payload(pesticide.id,
                            issue_date=(today() + timedelta(days=1)).isoformat()),
    )
    assert response.status_code == 422


# ================================================================ 施药记录与安全间隔期
def test_application_computes_earliest_entry_date(api, make_pesticide, make_space):
    pesticide = make_pesticide(safety_interval_days=7)
    space = make_space()
    app_date = today() - timedelta(days=2)
    data = api.data(api.post(
        "/api/v1/pesticide-applications",
        application_payload(pesticide.id, space.id, application_date=app_date.isoformat()),
    ), 201)
    assert data["application_no"].startswith("PA-")
    assert data["safety_interval_days"] == 7
    assert data["earliest_entry_date"] == (app_date + timedelta(days=7)).isoformat()
    assert data["safety_status"] == "locked"
    assert data["days_remaining"] == 5
    assert data["unit_label"] == "毫升"
    assert data["pesticide"]["safety_interval_days"] == 7


def test_application_releasable_after_interval(api, make_pesticide, make_space):
    pesticide = make_pesticide(safety_interval_days=3)
    space = make_space()
    app_date = today() - timedelta(days=5)
    data = api.data(api.post(
        "/api/v1/pesticide-applications",
        application_payload(pesticide.id, space.id, application_date=app_date.isoformat()),
    ), 201)
    assert data["safety_status"] == "releasable"
    assert data["days_remaining"] == 0


def test_reapply_within_interval_is_blocked_then_forced(api, make_pesticide, make_space):
    pesticide = make_pesticide(safety_interval_days=14)
    space = make_space()
    first_date = today() - timedelta(days=3)
    api.data(api.post(
        "/api/v1/pesticide-applications",
        application_payload(pesticide.id, space.id,
                            application_date=first_date.isoformat()),
    ), 201)

    # 间隔期内再次施药：默认 409，返回冲突明细
    response = api.post(
        "/api/v1/pesticide-applications",
        application_payload(pesticide.id, space.id, application_date=today().isoformat()),
    )
    assert response.status_code == 409
    body = response.get_json()
    assert body["data"]["force_required"] is True
    assert len(body["data"]["conflicts"]) == 1
    assert "最早可进入时间" in body["message"]

    # 人工确认 force=true 后允许登记
    forced = api.post(
        "/api/v1/pesticide-applications?force=true",
        application_payload(pesticide.id, space.id, application_date=today().isoformat()),
    )
    assert forced.status_code == 201


def test_reapply_after_interval_allowed(api, make_pesticide, make_space):
    pesticide = make_pesticide(safety_interval_days=7)
    space = make_space()
    api.data(api.post(
        "/api/v1/pesticide-applications",
        application_payload(pesticide.id, space.id,
                            application_date=(today() - timedelta(days=10)).isoformat()),
    ), 201)
    response = api.post(
        "/api/v1/pesticide-applications",
        application_payload(pesticide.id, space.id,
                           application_date=today().isoformat()),
    )
    assert response.status_code == 201


def test_other_green_space_not_conflicted(api, make_pesticide, make_space):
    pesticide = make_pesticide(safety_interval_days=30)
    space_a = make_space(name="A 绿地")
    space_b = make_space(name="B 绿地")
    api.data(api.post(
        "/api/v1/pesticide-applications",
        application_payload(pesticide.id, space_a.id,
                            application_date=today().isoformat()),
    ), 201)
    # 不同区域不受影响
    response = api.post(
        "/api/v1/pesticide-applications",
        application_payload(pesticide.id, space_b.id,
                            application_date=today().isoformat()),
    )
    assert response.status_code == 201


def test_application_record_must_belong_to_same_space(api, make_pesticide, make_record,
                                                      make_space):
    pesticide = make_pesticide()
    other_space = make_space(name="无关绿地")
    record = make_record()
    response = api.post(
        "/api/v1/pesticide-applications",
        application_payload(pesticide.id, other_space.id,
                            maintenance_record_id=record.id),
    )
    assert response.status_code == 422
    assert "不属于所选施药区域" in response.get_json()["data"]["maintenance_record_id"]


def test_application_future_date_rejected(api, make_pesticide, make_space):
    pesticide = make_pesticide()
    space = make_space()
    response = api.post(
        "/api/v1/pesticide-applications",
        application_payload(pesticide.id, space.id,
                            application_date=(today() + timedelta(days=1)).isoformat()),
    )
    assert response.status_code == 422


def test_banned_pesticide_application_rejected(api, make_pesticide, make_space):
    pesticide = make_pesticide(status="banned")
    space = make_space()
    response = api.post(
        "/api/v1/pesticide-applications",
        application_payload(pesticide.id, space.id),
    )
    assert response.status_code == 409


def test_update_application_rechecks_interval_excluding_self(api, make_application):
    application = make_application()
    # 编辑自身不应对自身报冲突
    response = api.put(
        f"/api/v1/pesticide-applications/{application.id}",
        application_payload(
            application.pesticide_id,
            application.green_space_id,
            application_date=application.application_date.isoformat(),
            target_pest="网蝽",
            dilution_ratio="1:1000",
            dosage=260,
            operator="张凤英",
        ),
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["target_pest"] == "网蝽"


def test_application_safety_status_filter(api, make_pesticide, make_space):
    pesticide = make_pesticide(safety_interval_days=10)
    space = make_space()
    # 一条间隔期内、一条已到期
    api.data(api.post("/api/v1/pesticide-applications",
                      application_payload(pesticide.id, space.id,
                                          application_date=today().isoformat())), 201)
    api.data(api.post("/api/v1/pesticide-applications?force=true",
                      application_payload(pesticide.id, space.id,
                                          application_date=(today() - timedelta(days=20)).isoformat())),
             201)

    locked = api.data(api.get("/api/v1/pesticide-applications", safety_status="locked"))
    releasable = api.data(api.get("/api/v1/pesticide-applications",
                                  safety_status="releasable"))
    assert all(item["safety_status"] == "locked" for item in locked["items"])
    assert all(item["safety_status"] == "releasable" for item in releasable["items"])
    assert locked["summary"]["locked_count"] == 1


def test_application_summary_counts(api, make_application):
    make_application(application_date=today() - timedelta(days=1))
    make_application(application_date=today() - timedelta(days=40))
    data = api.data(api.get("/api/v1/pesticide-applications/summary"))
    assert data["total_count"] == 2
    assert data["locked_count"] >= 1
    assert data["area_count"] >= 1


def test_requisition_summary(api, make_requisition):
    make_requisition(quantity=300)
    make_requisition(quantity=200)
    data = api.data(api.get("/api/v1/pesticide-requisitions/summary"))
    assert data["total_count"] == 2
    assert data["issued_quantity"] == 500.0


def test_update_requisition_adjusts_stock(api, make_requisition, make_pesticide):
    pesticide = make_pesticide(stock_quantity=1000)
    requisition = make_requisition(pesticide=pesticide, quantity=400)
    # 400 已出库，库存 600；改领 300，库存应回升到 700
    data = api.data(api.put(f"/api/v1/pesticide-requisitions/{requisition.id}", {
        "pesticide_id": pesticide.id,
        "quantity": 300,
        "recipient": requisition.recipient,
        "issue_date": requisition.issue_date.isoformat(),
    }))
    assert data["quantity"] == 300.0
    stock = api.data(api.get(f"/api/v1/pesticides/{pesticide.id}"))["stock_quantity"]
    assert stock == 700.0


def test_update_requisition_respects_available_stock(api, make_requisition, make_pesticide):
    pesticide = make_pesticide(stock_quantity=100)
    requisition = make_requisition(pesticide=pesticide, quantity=100)
    # 库存已为 0，但原 100 算可用，改领 150 应被拒绝
    response = api.put(f"/api/v1/pesticide-requisitions/{requisition.id}", {
        "pesticide_id": pesticide.id,
        "quantity": 150,
        "recipient": requisition.recipient,
        "issue_date": requisition.issue_date.isoformat(),
    })
    assert response.status_code == 409


def test_update_requisition_cannot_change_pesticide(api, make_requisition, make_pesticide):
    requisition = make_requisition()
    other = make_pesticide(name="另一种药剂")
    response = api.put(f"/api/v1/pesticide-requisitions/{requisition.id}", {
        "pesticide_id": other.id,
        "quantity": requisition.quantity,
        "recipient": requisition.recipient,
        "issue_date": requisition.issue_date.isoformat(),
    })
    assert response.status_code == 422
    assert "不能改换药剂" in response.get_json()["data"]["pesticide_id"]


def test_requisition_status_cannot_be_edited_directly(api, make_requisition):
    requisition = make_requisition()
    response = api.put(f"/api/v1/pesticide-requisitions/{requisition.id}", {
        "pesticide_id": requisition.pesticide_id,
        "quantity": requisition.quantity,
        "recipient": requisition.recipient,
        "issue_date": requisition.issue_date.isoformat(),
        "status": "returned",
    })
    assert response.status_code == 422
    assert "状态不可直接修改" in response.get_json()["data"]["status"]


def test_delete_issued_requisition_replenishes_stock(api, make_requisition, make_pesticide):
    pesticide = make_pesticide(stock_quantity=1000)
    requisition = make_requisition(pesticide=pesticide, quantity=400)
    api.data(api.delete(f"/api/v1/pesticide-requisitions/{requisition.id}"))
    stock = api.data(api.get(f"/api/v1/pesticides/{pesticide.id}"))["stock_quantity"]
    assert stock == 1000.0


def test_delete_returned_requisition_replenishes_net_only(api, make_requisition,
                                                          make_pesticide):
    pesticide = make_pesticide(stock_quantity=1000)
    requisition = make_requisition(pesticide=pesticide, quantity=400)
    api.data(api.patch(f"/api/v1/pesticide-requisitions/{requisition.id}/return",
                       {"returned_quantity": 100, "returned_at": today().isoformat()}))
    # 库存 700；删除该已退库记录只回补净占用 300
    api.data(api.delete(f"/api/v1/pesticide-requisitions/{requisition.id}"))
    stock = api.data(api.get(f"/api/v1/pesticides/{pesticide.id}"))["stock_quantity"]
    assert stock == 1000.0


def test_returned_quantity_cannot_exceed_on_edit(api, make_requisition):
    requisition = make_requisition(quantity=300)
    api.data(api.patch(f"/api/v1/pesticide-requisitions/{requisition.id}/return",
                       {"returned_quantity": 200, "returned_at": today().isoformat()}))
    # 已退库 200，领用数量不得改为小于退库量
    response = api.put(f"/api/v1/pesticide-requisitions/{requisition.id}", {
        "pesticide_id": requisition.pesticide_id,
        "quantity": 100,
        "recipient": requisition.recipient,
        "issue_date": requisition.issue_date.isoformat(),
    })
    assert response.status_code == 422
    assert "退库数量不能大于领用数量" in response.get_json()["data"]["returned_quantity"]
