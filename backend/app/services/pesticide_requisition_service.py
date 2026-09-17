"""药剂领用业务逻辑。"""

from sqlalchemy import func, or_

from ..errors import ConflictError, ValidationError
from ..extensions import db
from ..models import Pesticide, PesticideRequisition
from ..utils.dates import today
from ..utils.numbers import to_float
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import daily_prefix
from .pesticide_service import PesticideService


class PesticideRequisitionService(BaseService):
    """药剂领用登记：出库扣减库存，退库回补库存。"""

    model = PesticideRequisition
    label = "药剂领用记录"
    code_field = "requisition_no"
    code_width = 3

    SORTABLE = {
        "issue_date": PesticideRequisition.issue_date,
        "quantity": PesticideRequisition.quantity,
        "created_at": PesticideRequisition.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return daily_prefix("RC")

    # ------------------------------------------------------------ 校验与库存联动
    @classmethod
    def prepare_instance(cls, instance, payload):
        pesticide_id = payload.get("pesticide_id", instance.pesticide_id)
        # 领用记录创建后不允许改换药剂，否则两个药剂的库存都会失真
        if instance.id is not None and pesticide_id != instance.pesticide_id:
            raise ValidationError(
                "领用更新失败", details={"pesticide_id": "领用记录创建后不能改换药剂"}
            )
        # 新建时必须先走发放流程，退库只能在已发放记录上通过退库登记办理
        if instance.id is None and payload.get("status") == "returned":
            raise ValidationError(
                "领用登记失败",
                details={"status": "新建领用记录不能直接登记为已退库，请先发放再办理退库"},
            )
        pesticide = db.session.get(Pesticide, pesticide_id) if pesticide_id else None
        if pesticide is None:
            raise ValidationError("领用登记失败", details={"pesticide_id": "所选药剂不存在"})
        if pesticide.status == "banned":
            raise ConflictError(f"药剂「{pesticide.name}」为禁用药剂，禁止领用")
        if pesticide.status == "phase_out":
            raise ConflictError(f"药剂「{pesticide.name}」已停用待处理，禁止领用")

        quantity = payload.get("quantity", instance.quantity)
        if quantity is not None:
            # 更新记录时，该单当前净占用的库存仍在账外，校验可用库存时应加回：
            # 已发放为整单领用数量，已退库为领用数量减退库数量
            already_out = 0.0
            if instance.id is not None:
                already_out = float(instance.quantity or 0)
                if instance.status == "returned":
                    already_out -= float(instance.returned_quantity or 0)
            available = float(pesticide.stock_quantity or 0) + already_out
            if quantity > available:
                raise ConflictError(
                    f"药剂「{pesticide.name}」库存不足：当前可用库存 {to_float(available)}，"
                    f"本次申请领用 {to_float(quantity)}",
                    details={"quantity": "领用数量不能大于当前可用库存"},
                )

        issue_date = payload.get("issue_date", instance.issue_date)
        if issue_date and issue_date > today():
            raise ValidationError(
                "领用登记失败", details={"issue_date": "领用日期不能晚于今天"}
            )

        returned_quantity = payload.get("returned_quantity", instance.returned_quantity)
        returned_at = payload.get("returned_at", instance.returned_at)
        if returned_quantity is not None:
            if returned_at is None and instance.returned_at is None:
                raise ValidationError(
                    "退库登记失败", details={"returned_at": "请填写退库日期"}
                )
            if quantity is not None and returned_quantity > quantity:
                raise ValidationError(
                    "退库登记失败", details={"returned_quantity": "退库数量不能大于领用数量"}
                )

        # 计量单位以药剂档案为准，避免领用与档案单位不一致
        instance.unit = pesticide.unit

    @classmethod
    def after_create(cls, instance, payload, **options):
        if not options.get("skip_stock") and instance.status == "issued":
            PesticideService.adjust_stock(instance.pesticide, -instance.quantity)

    @classmethod
    def prepare_update(cls, instance, payload):
        # 状态只能通过退库接口流转，避免直接改状态绕过库存回补
        if "status" in payload and payload["status"] != instance.status:
            raise ValidationError(
                "领用更新失败",
                details={"status": "领用状态不可直接修改，退库请使用退库登记"},
            )
        payload.pop("status", None)
        setattr(instance, "_previous_quantity", float(instance.quantity or 0))
        setattr(instance, "_previous_returned",
                float(instance.returned_quantity or 0) if instance.status == "returned" else 0)
        cls.prepare_instance(instance, payload)

    @classmethod
    def after_update(cls, instance, payload, **options):
        if options.get("skip_stock"):
            return
        # 净占用库存：已发放为领用总量，已退库为领用减退库；
        # 数量编辑后按新旧净占用差额调整库存
        previous_net = getattr(instance, "_previous_quantity", float(instance.quantity or 0)) \
            - getattr(instance, "_previous_returned", 0)
        current_net = float(instance.quantity or 0)
        if instance.status == "returned":
            current_net -= float(instance.returned_quantity or 0)
        delta = previous_net - current_net
        if delta:
            PesticideService.adjust_stock(instance.pesticide, delta)

    # ------------------------------------------------------------ 退库
    @classmethod
    def register_return(cls, obj_id, payload):
        requisition = cls.get(obj_id)
        if requisition.status == "returned":
            raise ConflictError("该领用记录已办理退库，不能重复退库")
        returned_quantity = payload["returned_quantity"]
        if returned_quantity > requisition.quantity:
            raise ValidationError(
                "退库登记失败",
                details={"returned_quantity": "退库数量不能大于领用数量"},
            )
        returned_at = payload["returned_at"]
        if returned_at < requisition.issue_date:
            raise ValidationError(
                "退库登记失败", details={"returned_at": "退库日期不能早于领用日期"}
            )
        requisition.status = "returned"
        requisition.returned_quantity = returned_quantity
        requisition.returned_at = returned_at
        # 退库回补库存
        PesticideService.adjust_stock(requisition.pesticide, returned_quantity)
        db.session.commit()
        return requisition

    # ------------------------------------------------------------ 删除
    @classmethod
    def delete(cls, obj_id):
        """删除领用记录：把仍占用库存的净出库量（领用 - 已退库）回补，保证账实相符。"""

        requisition = cls.get(obj_id)
        deducted = float(requisition.quantity or 0)
        if requisition.status == "returned":
            deducted -= float(requisition.returned_quantity or 0)
        pesticide = requisition.pesticide
        db.session.delete(requisition)
        db.session.flush()
        if deducted > 0 and pesticide is not None:
            PesticideService.adjust_stock(pesticide, deducted)
        db.session.commit()
        return requisition

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("pesticide_id"):
            query = query.filter(PesticideRequisition.pesticide_id == filters["pesticide_id"])
        if filters.get("status"):
            query = query.filter(PesticideRequisition.status == filters["status"])
        if filters.get("recipient"):
            query = query.filter(PesticideRequisition.recipient.like(
                f"%{filters['recipient']}%"))
        if filters.get("date_from"):
            query = query.filter(PesticideRequisition.issue_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(PesticideRequisition.issue_date <= filters["date_to"])
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    PesticideRequisition.requisition_no.like(like),
                    PesticideRequisition.recipient.like(like),
                    PesticideRequisition.purpose.like(like),
                    PesticideRequisition.operator.like(like),
                )
            )
        return query

    @classmethod
    def list_requisitions(cls, filters, args):
        query = cls._apply_filters(db.session.query(PesticideRequisition), filters)
        return query.order_by(
            parse_sort(args, cls.SORTABLE, PesticideRequisition.issue_date.desc())
        )

    @classmethod
    def detail(cls, obj_id):
        return cls.get(obj_id).to_dict(detail=True)

    @classmethod
    def summary(cls, filters):
        """领用汇总：发放条数、领用总量、退库总量。"""

        total, issued_quantity, returned_quantity = cls._apply_filters(
            db.session.query(
                func.count(PesticideRequisition.id),
                func.coalesce(func.sum(PesticideRequisition.quantity), 0),
                func.coalesce(func.sum(PesticideRequisition.returned_quantity), 0),
            ),
            filters,
        ).one()
        returned_count = (
            cls._apply_filters(
                db.session.query(func.count(PesticideRequisition.id)),
                filters,
            )
            .filter(PesticideRequisition.status == "returned")
            .scalar()
            or 0
        )
        return {
            "total_count": total or 0,
            "issued_quantity": to_float(issued_quantity) or 0,
            "returned_count": returned_count,
            "returned_quantity": to_float(returned_quantity) or 0,
        }
