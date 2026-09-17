"""药剂档案业务逻辑。"""

from sqlalchemy import func, or_

from ..errors import ConflictError
from ..extensions import db
from ..models import (
    Pesticide,
    PesticideApplication,
    PesticideRequisition,
)
from ..utils.numbers import to_float
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import year_prefix


class PesticideService(BaseService):
    """药剂档案：建档、检索、库存维护与删除保护。"""

    model = Pesticide
    label = "药剂档案"
    code_field = "code"
    code_width = 4

    SORTABLE = {
        "code": Pesticide.code,
        "name": Pesticide.name,
        "safety_interval_days": Pesticide.safety_interval_days,
        "stock_quantity": Pesticide.stock_quantity,
        "created_at": Pesticide.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return year_prefix("PC")

    # ------------------------------------------------------------ 库存
    @classmethod
    def adjust_stock(cls, pesticide, delta):
        """调整库存，不足时抛出冲突。delta 为负表示出库。"""

        new_stock = (pesticide.stock_quantity or 0) + delta
        if new_stock < 0:
            raise ConflictError(
                f"药剂「{pesticide.name}」库存不足：当前 {to_float(pesticide.stock_quantity)}，"
                f"本次需出库 {to_float(abs(delta))}",
                details={"stock_quantity": to_float(pesticide.stock_quantity)},
            )
        pesticide.stock_quantity = new_stock

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("pesticide_type"):
            query = query.filter(Pesticide.pesticide_type == filters["pesticide_type"])
        if filters.get("toxicity"):
            query = query.filter(Pesticide.toxicity == filters["toxicity"])
        if filters.get("status"):
            query = query.filter(Pesticide.status == filters["status"])
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    Pesticide.code.like(like),
                    Pesticide.name.like(like),
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
    def options(cls, keyword=None, in_use_only=True, limit=50):
        """药剂下拉：供领用与施药登记选择。"""

        query = db.session.query(Pesticide)
        if in_use_only:
            query = query.filter(Pesticide.status == "in_use")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(Pesticide.name.like(like), Pesticide.code.like(like)))
        query = query.order_by(Pesticide.code.asc()).limit(limit)
        return [item.to_brief() for item in query.all()]

    @classmethod
    def summary(cls, filters):
        """档案汇总：档案件数、库存总量（按档案单位计）与状态分布。"""

        total, stock = cls._apply_filters(
            db.session.query(
                func.count(Pesticide.id),
                func.coalesce(func.sum(Pesticide.stock_quantity), 0),
            ),
            filters,
        ).one()
        rows = (
            cls._apply_filters(
                db.session.query(Pesticide.status, func.count(Pesticide.id)),
                filters,
            )
            .group_by(Pesticide.status)
            .all()
        )
        by_status = {status: 0 for status in ("in_use", "phase_out", "banned")}
        for status, count in rows:
            by_status[status] = count
        requisition_total = (
            db.session.query(func.count(PesticideRequisition.id))
            .join(Pesticide, PesticideRequisition.pesticide_id == Pesticide.id)
            .filter(*cls._filter_conditions(filters))
            .scalar()
            or 0
        )
        application_total = (
            db.session.query(func.count(PesticideApplication.id))
            .join(Pesticide, PesticideApplication.pesticide_id == Pesticide.id)
            .filter(*cls._filter_conditions(filters))
            .scalar()
            or 0
        )
        return {
            "total_count": total or 0,
            "total_stock_quantity": to_float(stock) or 0,
            "by_status": by_status,
            "requisition_count": requisition_total,
            "application_count": application_total,
        }

    @classmethod
    def _filter_conditions(cls, filters):
        """把档案过滤条件转成可复用于 join 查询的条件列表。"""

        conditions = []
        if filters.get("pesticide_type"):
            conditions.append(Pesticide.pesticide_type == filters["pesticide_type"])
        if filters.get("toxicity"):
            conditions.append(Pesticide.toxicity == filters["toxicity"])
        if filters.get("status"):
            conditions.append(Pesticide.status == filters["status"])
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            conditions.append(
                or_(
                    Pesticide.name.like(like),
                    Pesticide.code.like(like),
                    Pesticide.registration_no.like(like),
                )
            )
        return conditions

    # ------------------------------------------------------------ 删除
    @classmethod
    def delete(cls, obj_id, force=False):
        pesticide = cls.get(obj_id)
        counts = {
            "pesticide_requisition": db.session.query(func.count(PesticideRequisition.id))
            .filter(PesticideRequisition.pesticide_id == pesticide.id)
            .scalar()
            or 0,
            "pesticide_application": db.session.query(func.count(PesticideApplication.id))
            .filter(PesticideApplication.pesticide_id == pesticide.id)
            .scalar()
            or 0,
        }
        if sum(counts.values()) and not force:
            raise ConflictError(
                "该药剂已有领用记录 {pesticide_requisition} 条、施药记录 {pesticide_application} 条，"
                "删除将一并清除，请确认后重试".format(**counts),
                details=counts,
            )
        db.session.delete(pesticide)
        db.session.commit()
        return counts
