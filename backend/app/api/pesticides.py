"""药剂管理接口：药剂档案、领用登记、施药记录与安全间隔期管控。"""

from flask import Blueprint, request

from ..schemas import (
    application_filters,
    pesticide_filters,
    requisition_filters,
    validate_application,
    validate_pesticide,
    validate_requisition,
    validate_requisition_return,
)
from ..services import (
    PesticideApplicationService,
    PesticideRequisitionService,
    PesticideService,
)
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
    in_use_only = not query_flag("include_inactive", default=False)
    return ok({"items": PesticideService.options(keyword=keyword, in_use_only=in_use_only)})


@bp.get("/pesticides/summary")
def pesticide_summary():
    return ok(PesticideService.summary(pesticide_filters(request.args)))


@bp.post("/pesticides")
def create_pesticide():
    payload = validate_pesticide(json_body())
    pesticide = PesticideService.create(payload)
    return created(pesticide.to_dict(detail=True), message="药剂档案建立成功")


@bp.get("/pesticides/<int:pesticide_id>")
def get_pesticide(pesticide_id):
    return ok(PesticideService.get(pesticide_id).to_dict(detail=True))


@bp.put("/pesticides/<int:pesticide_id>")
def update_pesticide(pesticide_id):
    payload = validate_pesticide(json_body())
    pesticide = PesticideService.update(pesticide_id, payload)
    return ok(pesticide.to_dict(detail=True), message="药剂档案已更新")


@bp.delete("/pesticides/<int:pesticide_id>")
def delete_pesticide(pesticide_id):
    """删除档案。已有领用或施药记录时需 force=true 确认后级联清除。"""

    force = query_flag("force")
    PesticideService.delete(pesticide_id, force=force)
    return ok(None, message="药剂档案已删除")


# ================================================================ 药剂领用
@bp.get("/pesticide-requisitions")
def list_requisitions():
    filters = requisition_filters(request.args)
    page, page_size = parse_page_args()
    query = PesticideRequisitionService.list_requisitions(filters, request.args)
    data = paginate(query, page, page_size)
    data["summary"] = PesticideRequisitionService.summary(filters)
    return ok(data)


@bp.get("/pesticide-requisitions/summary")
def requisition_summary():
    return ok(PesticideRequisitionService.summary(requisition_filters(request.args)))


@bp.post("/pesticide-requisitions")
def create_requisition():
    payload = validate_requisition(json_body())
    requisition = PesticideRequisitionService.create(payload)
    return created(requisition.to_dict(detail=True), message="药剂领用登记成功")


@bp.get("/pesticide-requisitions/<int:requisition_id>")
def get_requisition(requisition_id):
    return ok(PesticideRequisitionService.detail(requisition_id))


@bp.put("/pesticide-requisitions/<int:requisition_id>")
def update_requisition(requisition_id):
    payload = validate_requisition(json_body())
    requisition = PesticideRequisitionService.update(requisition_id, payload)
    return ok(requisition.to_dict(detail=True), message="药剂领用记录已更新")


@bp.patch("/pesticide-requisitions/<int:requisition_id>/return")
def return_requisition(requisition_id):
    """剩余药剂退库登记，自动回补库存。"""

    payload = validate_requisition_return(json_body())
    requisition = PesticideRequisitionService.register_return(requisition_id, payload)
    return ok(requisition.to_dict(detail=True), message="退库登记成功，库存已回补")


@bp.delete("/pesticide-requisitions/<int:requisition_id>")
def delete_requisition(requisition_id):
    PesticideRequisitionService.delete(requisition_id)
    return ok(None, message="药剂领用记录已删除")


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


@bp.post("/pesticide-applications")
def create_application():
    payload = validate_application(json_body())
    force = query_flag("force")
    application = PesticideApplicationService.create(payload, force=force)
    return created(application.to_dict(detail=True), message="施药记录登记成功")


@bp.get("/pesticide-applications/<int:application_id>")
def get_application(application_id):
    return ok(PesticideApplicationService.detail(application_id))


@bp.put("/pesticide-applications/<int:application_id>")
def update_application(application_id):
    payload = validate_application(json_body())
    force = query_flag("force")
    application = PesticideApplicationService.update(application_id, payload, force=force)
    return ok(application.to_dict(detail=True), message="施药记录已更新")


@bp.delete("/pesticide-applications/<int:application_id>")
def delete_application(application_id):
    PesticideApplicationService.delete(application_id)
    return ok(None, message="施药记录已删除")
