"""药剂管理接口：药剂档案、出入库流水、施药记录。"""

from flask import Blueprint, request

from ..schemas import (
    application_filters,
    pesticide_filters,
    stock_movement_filters,
    validate_application,
    validate_pesticide,
    validate_stock_movement,
)
from ..services import (
    PesticideApplicationService,
    PesticideService,
    PesticideStockMovementService,
)
from ..utils.dates import parse_date
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body, query_flag
from ..utils.responses import created, ok

bp = Blueprint("pesticides", __name__)


# ================================================================ 药剂档案
@bp.get("/pesticides")
def list_pesticides():
    filters = pesticide_filters(request.args)
    page, page_size = parse_page_args()
    query = PesticideService.list_pesticides(filters, request.args)
    data = paginate(query, page, page_size)
    data["summary"] = PesticideService.summary(filters)
    return ok(data)


@bp.get("/pesticides/options")
def pesticide_options():
    keyword = (request.args.get("keyword") or "").strip() or None
    return ok({"items": PesticideService.options(keyword=keyword)})


@bp.get("/pesticides/summary")
def pesticide_summary():
    return ok(PesticideService.summary(pesticide_filters(request.args)))


@bp.post("/pesticides")
def create_pesticide():
    payload = validate_pesticide(json_body())
    pesticide = PesticideService.create(payload)
    return created(pesticide.to_dict(detail=True), message="药剂档案创建成功")


@bp.get("/pesticides/<int:pesticide_id>")
def get_pesticide(pesticide_id):
    return ok(PesticideService.detail(pesticide_id))


@bp.put("/pesticides/<int:pesticide_id>")
def update_pesticide(pesticide_id):
    payload = validate_pesticide(json_body())
    pesticide = PesticideService.update(pesticide_id, payload)
    return ok(pesticide.to_dict(detail=True), message="药剂档案已更新")


@bp.delete("/pesticides/<int:pesticide_id>")
def delete_pesticide(pesticide_id):
    force = query_flag("force")
    PesticideService.delete(pesticide_id, force=force)
    return ok(None, message="药剂档案已删除" if not force else "药剂档案及出入库流水已删除")


# ================================================================ 出入库流水
@bp.get("/pesticide-stock-movements")
def list_stock_movements():
    filters = stock_movement_filters(request.args)
    page, page_size = parse_page_args()
    query = PesticideStockMovementService.list_movements(filters, request.args)
    return ok(paginate(query, page, page_size))


@bp.post("/pesticide-stock-movements")
def create_stock_movement():
    payload = validate_stock_movement(json_body())
    movement = PesticideStockMovementService.create(payload)
    action = "领用登记成功，库存已扣减" if movement.movement_type == "out" else "入库登记成功，库存已补充"
    return created(movement.to_dict(detail=True), message=action)


@bp.get("/pesticide-stock-movements/<int:movement_id>")
def get_stock_movement(movement_id):
    return ok(PesticideStockMovementService.detail(movement_id))


@bp.delete("/pesticide-stock-movements/<int:movement_id>")
def delete_stock_movement(movement_id):
    PesticideStockMovementService.delete(movement_id)
    return ok(None, message="出入库记录已删除，库存已回滚")


# ================================================================ 施药记录
@bp.get("/pesticide-applications")
def list_applications():
    filters = application_filters(request.args)
    page, page_size = parse_page_args()
    query = PesticideApplicationService.list_applications(filters, request.args)
    data = paginate(query, page, page_size)
    data["summary"] = PesticideApplicationService.summary(filters)
    return ok(data)


@bp.get("/pesticide-applications/summary")
def application_summary():
    return ok(PesticideApplicationService.summary(application_filters(request.args)))


@bp.get("/pesticide-applications/interval-check")
def application_interval_check():
    """录入施药记录前的实时预检：返回所选区域仍在安全间隔期内的记录。"""

    green_space_id = request.args.get("green_space_id", type=int)
    exclude_id = request.args.get("exclude_id", type=int)
    application_date = parse_date(request.args.get("application_date") or "", "施药日期")
    application_time_text = (request.args.get("application_time") or "").strip() or None
    application_time = None
    if application_time_text:
        from ..utils.dates import parse_time

        application_time = parse_time(application_time_text, "施药时刻")
    return ok(
        PesticideApplicationService.interval_preview(
            green_space_id, application_date, application_time, exclude_id=exclude_id
        )
    )


@bp.post("/pesticide-applications")
def create_application():
    payload = validate_application(json_body())
    application = PesticideApplicationService.create_application(
        payload, confirm=query_flag("confirm")
    )
    return created(application.to_dict(detail=True), message="施药记录登记成功")


@bp.get("/pesticide-applications/<int:application_id>")
def get_application(application_id):
    return ok(PesticideApplicationService.detail(application_id))


@bp.put("/pesticide-applications/<int:application_id>")
def update_application(application_id):
    payload = validate_application(json_body())
    application = PesticideApplicationService.update_application(
        application_id, payload, confirm=query_flag("confirm")
    )
    return ok(application.to_dict(detail=True), message="施药记录已更新")


@bp.delete("/pesticide-applications/<int:application_id>")
def delete_application(application_id):
    PesticideApplicationService.delete(application_id)
    return ok(None, message="施药记录已删除")
