"""药剂档案模型。"""

from ..constants import PESTICIDE_STATUS, PESTICIDE_TOXICITY, PESTICIDE_TYPE, PESTICIDE_UNIT
from ..extensions import db
from ..utils.dates import format_datetime
from ..utils.numbers import to_float
from .mixins import TimestampMixin, quantity_column


class Pesticide(TimestampMixin, db.Model):
    """药剂档案：登记农药基本信息、毒性与安全间隔期，作为领用与施药的依据。"""

    __tablename__ = "pesticide"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), nullable=False, unique=True, index=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    registration_no = db.Column(db.String(64), index=True)
    pesticide_type = db.Column(db.String(32), nullable=False, index=True)
    toxicity = db.Column(db.String(16), nullable=False, default="low", index=True)
    active_ingredient = db.Column(db.String(128))
    formulation = db.Column(db.String(32))
    manufacturer = db.Column(db.String(128))
    safety_interval_days = db.Column(db.Integer, nullable=False, default=7)
    stock_quantity = db.Column(quantity_column(), nullable=False, default=0)
    unit = db.Column(db.String(16), nullable=False, default="milliliter")
    status = db.Column(db.String(16), nullable=False, default="in_use", index=True)
    remark = db.Column(db.Text)

    requisitions = db.relationship(
        "PesticideRequisition", back_populates="pesticide", cascade="all, delete-orphan"
    )
    applications = db.relationship(
        "PesticideApplication", back_populates="pesticide", cascade="all, delete-orphan"
    )

    def to_brief(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "safety_interval_days": self.safety_interval_days,
            "unit": self.unit,
            "toxicity": self.toxicity,
        }

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "registration_no": self.registration_no,
            "pesticide_type": self.pesticide_type,
            "pesticide_type_label": PESTICIDE_TYPE.label(self.pesticide_type),
            "toxicity": self.toxicity,
            "toxicity_label": PESTICIDE_TOXICITY.label(self.toxicity),
            "active_ingredient": self.active_ingredient,
            "formulation": self.formulation,
            "manufacturer": self.manufacturer,
            "safety_interval_days": self.safety_interval_days,
            "stock_quantity": to_float(self.stock_quantity),
            "unit": self.unit,
            "unit_label": PESTICIDE_UNIT.label(self.unit),
            "status": self.status,
            "status_label": PESTICIDE_STATUS.label(self.status),
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["remark"] = self.remark
        return data
