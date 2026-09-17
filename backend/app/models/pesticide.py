"""药剂管理模型：药剂档案、出入库流水与施药记录。"""

from datetime import datetime, timedelta

from ..constants import (
    APPLICATION_METHOD,
    PESTICIDE_FORM,
    PESTICIDE_TOXICITY,
    PESTICIDE_TYPE,
    PESTICIDE_UNIT,
    STOCK_MOVEMENT_TYPE,
)
from ..extensions import db
from ..utils.dates import (
    at_time,
    format_date,
    format_datetime,
    format_datetime_minute,
    format_time,
)
from ..utils.numbers import to_float
from .mixins import TimestampMixin, quantity_column


class Pesticide(TimestampMixin, db.Model):
    """药剂档案：一种药剂一条台账，登记证号与安全间隔期随标签维护。"""

    __tablename__ = "pesticide"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), nullable=False, unique=True, index=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    pesticide_type = db.Column(db.String(32), nullable=False, index=True)
    toxicity = db.Column(db.String(16), nullable=False, default="low")
    form = db.Column(db.String(16), nullable=False, default="ec")
    active_ingredient = db.Column(db.String(128))
    registration_no = db.Column(db.String(64), index=True)
    manufacturer = db.Column(db.String(128))
    unit = db.Column(db.String(16), nullable=False, default="bottle")
    stock_quantity = db.Column(quantity_column(), nullable=False, default=0)
    stock_low_threshold = db.Column(quantity_column(), nullable=False, default=0)
    # 标签登记的安全间隔期（天）：施药后最早可进入时间据此推算
    safety_interval_days = db.Column(db.Integer, nullable=False, default=7)
    target_pests = db.Column(db.String(255))
    storage_condition = db.Column(db.String(255))
    remark = db.Column(db.Text)

    movements = db.relationship(
        "PesticideStockMovement",
        back_populates="pesticide",
        cascade="all, delete-orphan",
        order_by="PesticideStockMovement.movement_date.desc(), PesticideStockMovement.id.desc()",
    )
    applications = db.relationship("PesticideApplication", back_populates="pesticide")

    def to_brief(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "pesticide_type": self.pesticide_type,
            "unit": self.unit,
            "safety_interval_days": self.safety_interval_days,
        }

    def to_dict(self, detail=False):
        stock = to_float(self.stock_quantity) or 0
        threshold = to_float(self.stock_low_threshold) or 0
        data = {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "pesticide_type": self.pesticide_type,
            "pesticide_type_label": PESTICIDE_TYPE.label(self.pesticide_type),
            "toxicity": self.toxicity,
            "toxicity_label": PESTICIDE_TOXICITY.label(self.toxicity),
            "form": self.form,
            "form_label": PESTICIDE_FORM.label(self.form),
            "active_ingredient": self.active_ingredient,
            "registration_no": self.registration_no,
            "manufacturer": self.manufacturer,
            "unit": self.unit,
            "unit_label": PESTICIDE_UNIT.label(self.unit),
            "stock_quantity": stock,
            "stock_low_threshold": threshold,
            "is_low_stock": threshold > 0 and stock <= threshold,
            "safety_interval_days": self.safety_interval_days,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["target_pests"] = self.target_pests
            data["storage_condition"] = self.storage_condition
            data["remark"] = self.remark
        return data


class PesticideStockMovement(TimestampMixin, db.Model):
    """药剂出入库流水：入库补充库存，领用出库扣减库存，库存余额只增删此表维护。"""

    __tablename__ = "pesticide_stock_movement"

    id = db.Column(db.Integer, primary_key=True)
    movement_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    pesticide_id = db.Column(
        db.Integer, db.ForeignKey("pesticide.id", ondelete="CASCADE"), nullable=False, index=True
    )
    movement_type = db.Column(db.String(8), nullable=False, index=True)
    quantity = db.Column(quantity_column(), nullable=False, default=0)
    unit = db.Column(db.String(16), nullable=False, default="bottle")
    movement_date = db.Column(db.Date, nullable=False, index=True)
    # 出库时的领用人；入库时为经办人
    receiver = db.Column(db.String(64))
    green_space_id = db.Column(
        db.Integer, db.ForeignKey("green_space.id", ondelete="SET NULL"), nullable=True, index=True
    )
    purpose = db.Column(db.String(255))
    operator = db.Column(db.String(64))
    remark = db.Column(db.Text)

    pesticide = db.relationship("Pesticide", back_populates="movements", lazy="joined")
    green_space = db.relationship("GreenSpace", lazy="joined")

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "movement_no": self.movement_no,
            "pesticide_id": self.pesticide_id,
            "pesticide": (
                {
                    "id": self.pesticide.id,
                    "code": self.pesticide.code,
                    "name": self.pesticide.name,
                    "toxicity": self.pesticide.toxicity,
                    "toxicity_label": PESTICIDE_TOXICITY.label(self.pesticide.toxicity),
                }
                if self.pesticide
                else None
            ),
            "movement_type": self.movement_type,
            "movement_type_label": STOCK_MOVEMENT_TYPE.label(self.movement_type),
            "quantity": to_float(self.quantity),
            "unit": self.unit,
            "unit_label": PESTICIDE_UNIT.label(self.unit),
            "movement_date": format_date(self.movement_date),
            "receiver": self.receiver,
            "green_space_id": self.green_space_id,
            "green_space": self.green_space.to_brief() if self.green_space else None,
            "purpose": self.purpose,
            "operator": self.operator,
            "created_at": format_datetime(self.created_at),
        }
        if detail:
            data["remark"] = self.remark
        return data


class PesticideApplication(TimestampMixin, db.Model):
    """施药记录：登记施药区域、防治对象、稀释浓度、用药量与施药人员，

    并按药剂标签的安全间隔期推算最早可进入时间。间隔期内同一区域再次施药
    由 service 层检测并给出提示。
    """

    __tablename__ = "pesticide_application"

    id = db.Column(db.Integer, primary_key=True)
    application_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    green_space_id = db.Column(
        db.Integer, db.ForeignKey("green_space.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pesticide_id = db.Column(
        db.Integer, db.ForeignKey("pesticide.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # 药剂档案可能被删除，保留施用时的名称与间隔期快照，安全履历不随之丢失
    pesticide_name = db.Column(db.String(128), nullable=False)
    location = db.Column(db.String(128))
    application_date = db.Column(db.Date, nullable=False, index=True)
    application_time = db.Column(db.Time)
    target_pest = db.Column(db.String(128), nullable=False)
    application_method = db.Column(db.String(16))
    dilution_ratio = db.Column(db.String(64))
    dosage = db.Column(quantity_column(), nullable=False, default=0)
    unit = db.Column(db.String(16), nullable=False, default="bottle")
    treated_area = db.Column(quantity_column())
    safety_interval_days = db.Column(db.Integer, nullable=False, default=7)
    earliest_reentry_at = db.Column(db.DateTime, nullable=False, index=True)
    operator = db.Column(db.String(64), nullable=False)
    weather = db.Column(db.String(16))
    remark = db.Column(db.Text)

    green_space = db.relationship("GreenSpace", back_populates="pesticide_applications",
                                  lazy="joined")
    pesticide = db.relationship("Pesticide", back_populates="applications", lazy="joined")

    @staticmethod
    def calc_reentry(application_date, application_time, interval_days):
        """最早可进入时间 = 施药日期(时刻) + 安全间隔期天数。"""

        return at_time(application_date, application_time) + timedelta(days=int(interval_days or 0))

    @property
    def is_within_interval(self):
        return self.earliest_reentry_at > datetime.now()

    def to_dict(self, detail=False):
        within = self.is_within_interval
        data = {
            "id": self.id,
            "application_no": self.application_no,
            "green_space_id": self.green_space_id,
            "green_space": self.green_space.to_brief() if self.green_space else None,
            "pesticide_id": self.pesticide_id,
            "pesticide": self.pesticide.to_brief() if self.pesticide else None,
            "pesticide_name": self.pesticide_name,
            "location": self.location,
            "application_date": format_date(self.application_date),
            "application_time": format_time(self.application_time),
            "applied_at": (
                f"{format_date(self.application_date)} {format_time(self.application_time)}"
                if self.application_time
                else format_date(self.application_date)
            ),
            "target_pest": self.target_pest,
            "application_method": self.application_method,
            "application_method_label": (
                APPLICATION_METHOD.label(self.application_method) if self.application_method else None
            ),
            "dilution_ratio": self.dilution_ratio,
            "dosage": to_float(self.dosage),
            "unit": self.unit,
            "unit_label": PESTICIDE_UNIT.label(self.unit),
            "treated_area": to_float(self.treated_area),
            "safety_interval_days": self.safety_interval_days,
            "earliest_reentry_at": format_datetime_minute(self.earliest_reentry_at),
            "is_within_interval": within,
            "reentry_status": "within_interval" if within else "releasable",
            "operator": self.operator,
            "weather": self.weather,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["remark"] = self.remark
        return data
