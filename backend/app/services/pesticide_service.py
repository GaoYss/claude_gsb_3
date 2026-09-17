"""药剂管理业务逻辑。

包含三类资源：

- ``PesticideService``：药剂档案建档、库存预警与删除保护；
- ``PesticideStockMovementService``：入库 / 领用出库流水，并据此维护库存余额；
- ``PesticideApplicationService``：施药记录，按药剂标签安全间隔期推算最早可进入时间，
  间隔期内同一区域再次施药给出软警告（确认后方可登记）。
"""

from datetime import datetime, timedelta

from sqlalchemy import func, or_

from ..errors import BadRequestError, ConflictError, ValidationError
from ..extensions import db
from ..models import (
    GreenSpace,
    Pesticide,
    PesticideApplication,
    PesticideStockMovement,
)
from ..utils.dates import at_time, format_date, format_datetime_minute, today
from ..utils.numbers import to_float
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import daily_prefix, year_prefix


# ================================================================ 药剂档案
class PesticideService(BaseService):
    """药剂档案：建档后库存只能通过出入库流水调整，保证库存可追溯。"""

    model = Pesticide
    label = "药剂档案"
    code_field = "code"
    code_width = 3

    SORTABLE = {
        "code": Pesticide.code,
        "name": Pesticide.name,
        "stock_quantity": Pesticide.stock_quantity,
        "safety_interval_days": Pesticide.safety_interval_days,
        "created_at": Pesticide.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return year_prefix("PC")

    # ------------------------------------------------------------ 写入
    @classmethod
    def prepare_instance(cls, instance, payload):
        interval = payload.get("safety_interval_days", instance.safety_interval_days)
        if interval is None:
            raise ValidationError(
                "保存失败", details={"safety_interval_days": "请填写标签登记的安全间隔期（天）"}
            )

    @classmethod
    def update(cls, obj_id, data):
        # 建档后期初库存不可直接改，库存只能由出入库流水增减
        data = dict(data)
        data.pop("stock_quantity", None)
        return super().update(obj_id, data)

    @classmethod
    def delete(cls, obj_id, force=False):
        pesticide = cls.get(obj_id)
        movement_count = (
            db.session.query(func.count(PesticideStockMovement.id))
            .filter(PesticideStockMovement.pesticide_id == pesticide.id)
            .scalar()
            or 0
        )
        application_count = (
            db.session.query(func.count(PesticideApplication.id))
            .filter(PesticideApplication.pesticide_id == pesticide.id)
            .scalar()
            or 0
        )
        if (movement_count or application_count) and not force:
            raise ConflictError(
                "该药剂已有出入库记录 {movement} 条、施药记录 {application} 条，"
                "删除将清除出入库流水（施药履历保留并解除关联），请确认后重试".format(
                    movement=movement_count, application=application_count
                ),
                details={
                    "stock_movement": movement_count,
                    "pesticide_application": application_count,
                },
            )
        db.session.delete(pesticide)
        db.session.commit()
        return {"stock_movement": movement_count, "pesticide_application": application_count}

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("pesticide_type"):
            query = query.filter(Pesticide.pesticide_type == filters["pesticide_type"])
        if filters.get("toxicity"):
            query = query.filter(Pesticide.toxicity == filters["toxicity"])
        if filters.get("low_stock"):
            query = query.filter(
                Pesticide.stock_low_threshold > 0,
                Pesticide.stock_quantity <= Pesticide.stock_low_threshold,
            )
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    Pesticide.name.like(like),
                    Pesticide.code.like(like),
                    Pesticide.registration_no.like(like),
                    Pesticide.active_ingredient.like(like),
                    Pesticide.manufacturer.like(like),
                )
            )
        return query

    @classmethod
    def list_pesticides(cls, filters, args):
        query = cls._apply_filters(db.session.query(Pesticide), filters)
        return query.order_by(parse_sort(args, cls.SORTABLE, Pesticide.code.asc()))

    @classmethod
    def detail(cls, obj_id):
        pesticide = cls.get(obj_id)
        recent_movements = (
            db.session.query(PesticideStockMovement)
            .filter(PesticideStockMovement.pesticide_id == pesticide.id)
            .order_by(
                PesticideStockMovement.movement_date.desc(),
                PesticideStockMovement.id.desc(),
            )
            .limit(10)
            .all()
        )
        recent_applications = (
            db.session.query(PesticideApplication)
            .filter(PesticideApplication.pesticide_id == pesticide.id)
            .order_by(
                PesticideApplication.application_date.desc(),
                PesticideApplication.id.desc(),
            )
            .limit(10)
            .all()
        )
        data = pesticide.to_dict(detail=True)
        data["recent_movements"] = [item.to_dict() for item in recent_movements]
        data["recent_applications"] = [item.to_dict() for item in recent_applications]
        return data

    @classmethod
    def options(cls, keyword=None, limit=50):
        """施药 / 领用选择药剂的下拉项，带出当前库存与安全间隔期。"""

        from ..constants import PESTICIDE_TYPE, PESTICIDE_UNIT

        query = db.session.query(Pesticide)
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(Pesticide.name.like(like), Pesticide.code.like(like)))
        query = query.order_by(Pesticide.code.asc()).limit(limit)
        items = []
        for item in query.all():
            stock = to_float(item.stock_quantity) or 0
            threshold = to_float(item.stock_low_threshold) or 0
            items.append({
                "id": item.id,
                "code": item.code,
                "name": item.name,
                "pesticide_type": item.pesticide_type,
                "pesticide_type_label": PESTICIDE_TYPE.label(item.pesticide_type),
                "toxicity": item.toxicity,
                "unit": item.unit,
                "unit_label": PESTICIDE_UNIT.label(item.unit),
                "safety_interval_days": item.safety_interval_days,
                "stock_quantity": stock,
                "is_low_stock": threshold > 0 and stock <= threshold,
            })
        return items

    @classmethod
    def summary(cls, filters):
        base = cls._apply_filters(db.session.query(Pesticide), filters)
        total = base.with_entities(func.count(Pesticide.id)).scalar() or 0
        low_stock = (
            db.session.query(func.count(Pesticide.id))
            .filter(
                Pesticide.stock_low_threshold > 0,
                Pesticide.stock_quantity <= Pesticide.stock_low_threshold,
            )
            .scalar()
            or 0
        )
        return {"total_count": total, "low_stock_count": low_stock}


# ================================================================ 出入库流水
class PesticideStockMovementService(BaseService):
    """入库补充库存、领用出库扣减库存；删除流水时反向回滚。"""

    model = PesticideStockMovement
    label = "药剂出入库记录"
    code_field = "movement_no"
    code_width = 3

    SORTABLE = {
        "movement_date": PesticideStockMovement.movement_date,
        "quantity": PesticideStockMovement.quantity,
        "created_at": PesticideStockMovement.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return daily_prefix("SM")

    @classmethod
    def update(cls, obj_id, data):
        # 出入库流水直接决定库存余额，修改数量/方向会造成库存二次增减；
        # 如登记有误请删除（库存自动回滚）后重新登记
        raise BadRequestError("出入库记录不支持修改，请删除后重新登记")

    # ------------------------------------------------------------ 校验与库存联动
    @classmethod
    def prepare_instance(cls, instance, payload):
        pesticide = db.session.get(Pesticide, instance.pesticide_id)
        if pesticide is None:
            raise ValidationError("登记失败", details={"pesticide_id": "所选药剂不存在"})

        quantity = payload.get("quantity", instance.quantity)
        movement_type = payload.get("movement_type", instance.movement_type)
        green_space_id = payload.get("green_space_id", instance.green_space_id)
        if green_space_id:
            space = db.session.get(GreenSpace, green_space_id)
            if space is None:
                raise ValidationError("登记失败", details={"green_space_id": "所选绿地不存在"})

        # 计量单位强制跟随档案，避免库存口径混乱
        instance.unit = pesticide.unit
        if movement_type == "in":
            pesticide.stock_quantity = (pesticide.stock_quantity or 0) + quantity
        else:
            current = pesticide.stock_quantity or 0
            if quantity > current:
                raise ConflictError(
                    f"药剂「{pesticide.name}」当前库存 {to_float(current)} {pesticide.unit}，"
                    f"本次领用 {to_float(quantity)}，库存不足，无法登记领用",
                    details={
                        "pesticide_id": pesticide.id,
                        "stock_quantity": to_float(current),
                        "requested_quantity": to_float(quantity),
                    },
                )
            pesticide.stock_quantity = current - quantity

    @classmethod
    def delete(cls, obj_id):
        movement = cls.get(obj_id)
        pesticide = db.session.get(Pesticide, movement.pesticide_id)
        restored = (pesticide.stock_quantity or 0) if pesticide else 0
        # 反向回滚：入库单删除则扣回，领用单删除则补回
        if movement.movement_type == "in":
            restored -= movement.quantity or 0
        else:
            restored += movement.quantity or 0
        if pesticide is not None and restored < 0:
            raise ConflictError(
                f"删除该记录后药剂「{pesticide.name}」库存将为负，无法删除，请先核对出入库流水"
            )
        if pesticide is not None:
            pesticide.stock_quantity = restored
        db.session.delete(movement)
        db.session.commit()
        return movement

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("pesticide_id"):
            query = query.filter(PesticideStockMovement.pesticide_id == filters["pesticide_id"])
        if filters.get("green_space_id"):
            query = query.filter(PesticideStockMovement.green_space_id == filters["green_space_id"])
        if filters.get("movement_type"):
            query = query.filter(PesticideStockMovement.movement_type == filters["movement_type"])
        if filters.get("date_from"):
            query = query.filter(PesticideStockMovement.movement_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(PesticideStockMovement.movement_date <= filters["date_to"])
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    PesticideStockMovement.movement_no.like(like),
                    PesticideStockMovement.receiver.like(like),
                    PesticideStockMovement.purpose.like(like),
                    PesticideStockMovement.operator.like(like),
                )
            )
        return query

    @classmethod
    def list_movements(cls, filters, args):
        query = cls._apply_filters(db.session.query(PesticideStockMovement), filters)
        return query.order_by(
            parse_sort(args, cls.SORTABLE, PesticideStockMovement.movement_date.desc())
        )

    @classmethod
    def detail(cls, obj_id):
        return cls.get(obj_id).to_dict(detail=True)


# ================================================================ 施药记录
class PesticideApplicationService(BaseService):
    """施药记录：安全间隔期推算与同区域重复施药提示。"""

    model = PesticideApplication
    label = "施药记录"
    code_field = "application_no"
    code_width = 3

    SORTABLE = {
        "application_date": PesticideApplication.application_date,
        "earliest_reentry_at": PesticideApplication.earliest_reentry_at,
        "dosage": PesticideApplication.dosage,
        "created_at": PesticideApplication.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return daily_prefix("PA")

    # ------------------------------------------------------------ 校验与派生
    @classmethod
    def prepare_instance(cls, instance, payload):
        green_space_id = payload.get("green_space_id", instance.green_space_id)
        space = db.session.get(GreenSpace, green_space_id) if green_space_id else None
        if space is None:
            raise ValidationError("登记失败", details={"green_space_id": "施药区域（绿地）不存在"})

        pesticide_id = payload.get("pesticide_id", instance.pesticide_id)
        pesticide = db.session.get(Pesticide, pesticide_id) if pesticide_id else None
        if pesticide is None:
            raise ValidationError("登记失败", details={"pesticide_id": "所选药剂不存在"})

        application_date = payload.get("application_date", instance.application_date)
        if application_date and space.established_date and application_date < space.established_date:
            raise ValidationError(
                "登记失败",
                details={"application_date": f"施药日期不能早于该绿地建成日期 {space.established_date}"},
            )

        # 药剂关键安全信息做施用时快照，档案后续调整或删除不影响历史履历
        instance.pesticide_name = pesticide.name
        instance.unit = pesticide.unit
        instance.safety_interval_days = pesticide.safety_interval_days

    @classmethod
    def apply_derived(cls, instance):
        instance.earliest_reentry_at = PesticideApplication.calc_reentry(
            instance.application_date, instance.application_time, instance.safety_interval_days
        )

    # ------------------------------------------------------------ 重复施药检测
    @classmethod
    def _interval_conflicts(cls, green_space_id, application_date, application_time, exclude_id=None):
        """返回该区域在给定施药时刻仍处于安全间隔期内的既有记录。"""

        applied_start = at_time(application_date, application_time)
        query = (
            db.session.query(PesticideApplication)
            .filter(
                PesticideApplication.green_space_id == green_space_id,
                PesticideApplication.earliest_reentry_at > applied_start,
            )
            .order_by(PesticideApplication.earliest_reentry_at.desc())
        )
        if exclude_id is not None:
            query = query.filter(PesticideApplication.id != exclude_id)
        return query.all()

    @classmethod
    def assert_interval_ok(cls, data, *, confirm, exclude_id=None, instance=None):
        """登记/更新前的间隔期预检；未确认时以 409 返回冲突明细供前端二次确认。"""

        if confirm:
            return
        current = instance
        green_space_id = data.get("green_space_id") or (current.green_space_id if current else None)
        application_date = data.get("application_date") or (
            current.application_date if current else None
        )
        application_time = data.get("application_time", None)
        if application_time is None and current is not None:
            application_time = current.application_time
        if not green_space_id or not application_date:
            return

        conflicts = cls._interval_conflicts(
            green_space_id, application_date, application_time, exclude_id=exclude_id
        )
        if not conflicts:
            return

        latest = conflicts[0]
        raise ConflictError(
            f"该区域仍有 {len(conflicts)} 条施药处于安全间隔期内，最近一次「{latest.pesticide_name}」"
            f"施药后最早可进入时间为 {format_datetime_minute(latest.earliest_reentry_at)}，"
            "间隔期内再次施药请确认已做好安全防护，确认后可继续登记",
            details={
                "confirm_required": True,
                "applied_at": format_datetime_minute(
                    at_time(application_date, application_time)
                ),
                "conflicts": [
                    {
                        "application_no": item.application_no,
                        "pesticide_name": item.pesticide_name,
                        "green_space_name": item.green_space.name if item.green_space else None,
                        "application_date": format_date(item.application_date),
                        "earliest_reentry_at": format_datetime_minute(item.earliest_reentry_at),
                        "safety_interval_days": item.safety_interval_days,
                    }
                    for item in conflicts
                ],
            },
        )

    @classmethod
    def create_application(cls, data, confirm=False):
        cls.assert_interval_ok(data, confirm=confirm)
        return cls.create(data)

    @classmethod
    def update_application(cls, obj_id, data, confirm=False):
        instance = cls.get(obj_id)
        cls.assert_interval_ok(data, confirm=confirm, exclude_id=obj_id, instance=instance)
        return cls.update(obj_id, data)

    @classmethod
    def interval_preview(cls, green_space_id, application_date, application_time=None,
                         exclude_id=None):
        """表单实时预检：返回该区域在所选时刻仍未解除的间隔期记录（只读提示）。"""

        space = db.session.get(GreenSpace, green_space_id) if green_space_id else None
        if space is None or not application_date:
            return {"within_interval": [], "latest_reentry_at": None}
        conflicts = cls._interval_conflicts(
            green_space_id, application_date, application_time, exclude_id=exclude_id
        )
        return {
            "within_interval": [
                {
                    "application_no": item.application_no,
                    "pesticide_name": item.pesticide_name,
                    "application_date": format_date(item.application_date),
                    "earliest_reentry_at": format_datetime_minute(item.earliest_reentry_at),
                    "safety_interval_days": item.safety_interval_days,
                }
                for item in conflicts
            ],
            "latest_reentry_at": (
                format_datetime_minute(conflicts[0].earliest_reentry_at) if conflicts else None
            ),
        }

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("green_space_id"):
            query = query.filter(PesticideApplication.green_space_id == filters["green_space_id"])
        if filters.get("pesticide_id"):
            query = query.filter(PesticideApplication.pesticide_id == filters["pesticide_id"])
        if filters.get("application_method"):
            query = query.filter(
                PesticideApplication.application_method == filters["application_method"]
            )
        if filters.get("date_from"):
            query = query.filter(PesticideApplication.application_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(PesticideApplication.application_date <= filters["date_to"])
        status = filters.get("interval_status")
        if status == "within":
            query = query.filter(PesticideApplication.earliest_reentry_at > datetime.now())
        elif status == "releasable":
            query = query.filter(PesticideApplication.earliest_reentry_at <= datetime.now())
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    PesticideApplication.application_no.like(like),
                    PesticideApplication.pesticide_name.like(like),
                    PesticideApplication.target_pest.like(like),
                    PesticideApplication.location.like(like),
                    PesticideApplication.operator.like(like),
                )
            )
        return query

    @classmethod
    def list_applications(cls, filters, args):
        query = cls._apply_filters(db.session.query(PesticideApplication), filters)
        return query.order_by(
            parse_sort(args, cls.SORTABLE, PesticideApplication.application_date.desc())
        )

    @classmethod
    def detail(cls, obj_id):
        return cls.get(obj_id).to_dict(detail=True)

    @classmethod
    def summary(cls, filters):
        base = cls._apply_filters(db.session.query(PesticideApplication), filters)
        total = base.with_entities(func.count(PesticideApplication.id)).scalar() or 0
        within_count = (
            db.session.query(func.count(PesticideApplication.id))
            .filter(PesticideApplication.earliest_reentry_at > datetime.now())
            .scalar()
            or 0
        )
        today_ = today()
        day_start = at_time(today_)
        day_end = at_time(today_ + timedelta(days=1))
        releasable_today = (
            db.session.query(func.count(PesticideApplication.id))
            .filter(
                PesticideApplication.earliest_reentry_at >= day_start,
                PesticideApplication.earliest_reentry_at < day_end,
            )
            .scalar()
            or 0
        )
        return {
            "total_count": total,
            "within_interval_count": within_count,
            "releasable_today_count": releasable_today,
        }

    @classmethod
    def active_intervals(cls, limit=10):
        """看板提醒：当前仍处于安全间隔期内、暂不可进入的施药区域。"""

        rows = (
            db.session.query(PesticideApplication)
            .filter(PesticideApplication.earliest_reentry_at > datetime.now())
            .order_by(PesticideApplication.earliest_reentry_at.asc())
            .limit(limit)
            .all()
        )
        return [item.to_dict() for item in rows]
