"""药剂施用业务逻辑。

安全管控规则：

1. 施药记录必须关联药剂档案与施药区域（绿地），可关联同一绿地的养护记录；
2. 最早可进入时间 = 施药日期 + 药剂档案登记的安全间隔期；
3. 同一区域在安全间隔期内再次施药，默认拒绝并返回冲突明细，
   经人工确认后携带 force=true 方可登记；
4. 更新施药记录时同样重新校验间隔期冲突（排除自身）。
"""

from datetime import timedelta

from sqlalchemy import and_, func, or_

from ..errors import ConflictError, ValidationError
from ..extensions import db
from ..models import (
    GreenSpace,
    MaintenanceRecord,
    Pesticide,
    PesticideApplication,
)
from ..utils.dates import format_date, today
from ..utils.numbers import to_float
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import daily_prefix


class PesticideApplicationService(BaseService):
    """施药记录登记与安全间隔期管控。"""

    model = PesticideApplication
    label = "施药记录"
    code_field = "application_no"
    code_width = 3

    SORTABLE = {
        "application_date": PesticideApplication.application_date,
        "dosage": PesticideApplication.dosage,
        "created_at": PesticideApplication.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return daily_prefix("PA")

    # ------------------------------------------------------------ 校验
    @classmethod
    def prepare_instance(cls, instance, payload):
        pesticide_id = payload.get("pesticide_id", instance.pesticide_id)
        pesticide = db.session.get(Pesticide, pesticide_id) if pesticide_id else None
        if pesticide is None:
            raise ValidationError("施药登记失败", details={"pesticide_id": "所选药剂不存在"})
        if pesticide.status == "banned":
            raise ConflictError(f"药剂「{pesticide.name}」为禁用药剂，禁止施用")

        green_space_id = payload.get("green_space_id", instance.green_space_id)
        space = db.session.get(GreenSpace, green_space_id) if green_space_id else None
        if space is None:
            raise ValidationError("施药登记失败", details={"green_space_id": "所选施药区域不存在"})

        record_id = payload.get("maintenance_record_id", instance.maintenance_record_id)
        if record_id:
            record = db.session.get(MaintenanceRecord, record_id)
            if record is None:
                raise ValidationError(
                    "施药登记失败", details={"maintenance_record_id": "关联的养护记录不存在"}
                )
            if record.green_space_id != space.id:
                raise ValidationError(
                    "施药登记失败",
                    details={"maintenance_record_id": "关联的养护记录不属于所选施药区域"},
                )

        application_date = payload.get("application_date", instance.application_date)
        if application_date and application_date > today():
            raise ValidationError(
                "施药登记失败", details={"application_date": "施药日期不能晚于今天"}
            )
        if application_date and space.established_date and application_date < space.established_date:
            raise ValidationError(
                "施药登记失败",
                details={"application_date": f"施药日期不能早于该绿地建成日期 {space.established_date}"},
            )

        # 计量单位随药剂档案，保证用药量与档案口径一致
        instance.unit = pesticide.unit

    @classmethod
    def before_flush(cls, instance, payload, **options):
        force = options.get("force", False)
        values = {
            "pesticide_id": instance.pesticide_id,
            "green_space_id": instance.green_space_id,
            "application_date": instance.application_date,
        }
        cls.assert_safety_window(values, force=force, exclude_id=instance.id)

    # ------------------------------------------------------------ 安全间隔期
    @classmethod
    def active_conflicts(cls, values, exclude_id=None):
        """查找同一施药区域内与本次施药间隔期冲突的已有记录。

        冲突双向判定：

        - 本次施药日落在此前记录的安全间隔期内（最常见）；
        - 本次施药的间隔期会覆盖区域内更晚的一次施药（补录历史数据场景）。
        """

        green_space_id = values.get("green_space_id")
        application_date = values.get("application_date")
        pesticide = db.session.get(Pesticide, values.get("pesticide_id"))
        if green_space_id is None or application_date is None or pesticide is None:
            return []

        new_days = int(pesticide.safety_interval_days or 0)
        new_earliest = application_date + timedelta(days=new_days)

        query = db.session.query(PesticideApplication).filter(
            PesticideApplication.green_space_id == green_space_id,
        )
        if exclude_id is not None:
            query = query.filter(PesticideApplication.id != exclude_id)

        conflicts = []
        with db.session.no_autoflush:
            candidates = query.all()
        for previous in candidates:
            if application_date <= previous.application_date:
                # 本次施药更早（补录历史）或同日：用本次间隔期约束更晚的那次施药
                collide = previous.application_date < new_earliest
            else:
                # 本次更晚：落入此前记录的安全间隔期内才算冲突
                collide = application_date < previous.earliest_entry_date
            if collide:
                conflicts.append(previous)
        return conflicts

    @classmethod
    def assert_safety_window(cls, values, *, force=False, exclude_id=None):
        """间隔期内重复施药拦截，force=True 表示作业人员已确认风险。"""

        conflicts = cls.active_conflicts(values, exclude_id=exclude_id)
        if conflicts and not force:
            latest = max(conflicts, key=lambda item: item.application_date)
            raise ConflictError(
                f"施药区域在安全间隔期内：该区域最近于 {format_date(latest.application_date)} "
                f"施用「{latest.pesticide.name}」，最早可进入时间为 "
                f"{format_date(latest.earliest_entry_date)}，请确认是否仍要再次施药",
                details={
                    "force_required": True,
                    "conflicts": [
                        {
                            "application_no": item.application_no,
                            "pesticide_name": item.pesticide.name,
                            "application_date": format_date(item.application_date),
                            "earliest_entry_date": format_date(item.earliest_entry_date),
                            "days_remaining": item.days_remaining,
                        }
                        for item in conflicts
                    ],
                },
            )
        return conflicts

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("pesticide_id"):
            query = query.filter(PesticideApplication.pesticide_id == filters["pesticide_id"])
        if filters.get("green_space_id"):
            query = query.filter(PesticideApplication.green_space_id == filters["green_space_id"])
        if filters.get("maintenance_record_id"):
            query = query.filter(
                PesticideApplication.maintenance_record_id == filters["maintenance_record_id"]
            )
        if filters.get("date_from"):
            query = query.filter(PesticideApplication.application_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(PesticideApplication.application_date <= filters["date_to"])
        safety_status = filters.get("safety_status")
        if safety_status:
            # 按各药剂的间隔天数分组做日期比较，兼容 SQLite 与 PostgreSQL
            interval_days = [
                row[0]
                for row in db.session.query(Pesticide.safety_interval_days).distinct().all()
            ]
            clauses = []
            for days in interval_days:
                boundary = today() - timedelta(days=days)
                if safety_status == "locked":
                    condition = PesticideApplication.application_date > boundary
                else:
                    condition = PesticideApplication.application_date <= boundary
                clauses.append(and_(Pesticide.safety_interval_days == days, condition))
            if clauses:
                query = query.join(
                    Pesticide, PesticideApplication.pesticide_id == Pesticide.id
                ).filter(or_(*clauses))
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    PesticideApplication.application_no.like(like),
                    PesticideApplication.target_pest.like(like),
                    PesticideApplication.operator.like(like),
                    PesticideApplication.equipment.like(like),
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
        """施药汇总：总条数、当前仍在间隔期内的区域数、本月施药次数。"""

        query = cls._apply_filters(db.session.query(PesticideApplication), filters)
        total = query.count()

        def _count_with_status(status):
            sub_filters = dict(filters)
            sub_filters["safety_status"] = status
            return cls._apply_filters(
                db.session.query(PesticideApplication), sub_filters
            ).count()

        locked_count = _count_with_status("locked")
        month_start = today().replace(day=1)
        month_count = (
            cls._apply_filters(
                db.session.query(func.count(PesticideApplication.id)),
                filters,
            )
            .filter(PesticideApplication.application_date >= month_start)
            .scalar()
            or 0
        )
        area_count = (
            cls._apply_filters(
                db.session.query(
                    func.count(func.distinct(PesticideApplication.green_space_id))
                ),
                filters,
            )
            .scalar()
            or 0
        )
        return {
            "total_count": total,
            "locked_count": locked_count,
            "month_count": month_count,
            "area_count": area_count,
        }
