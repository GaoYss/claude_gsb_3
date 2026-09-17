"""药剂施用记录模型。"""

from datetime import timedelta

from ..constants import PESTICIDE_TOXICITY, PESTICIDE_UNIT
from ..extensions import db
from ..utils.dates import format_date, format_datetime, today
from ..utils.numbers import to_float
from .mixins import TimestampMixin, quantity_column


class PesticideApplication(TimestampMixin, db.Model):
    """施药记录：登记施药区域、防治对象、稀释浓度、用药量与施药人员。

    安全管控派生信息（不落库，按药剂档案的安全间隔期实时推算）：

    - earliest_entry_date：施药日期 + 安全间隔天数，即最早可安全进入时间；
    - safety_status：截至今天区域是否仍处于间隔期内（locked / releasable）。
    """

    __tablename__ = "pesticide_application"

    id = db.Column(db.Integer, primary_key=True)
    application_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    pesticide_id = db.Column(
        db.Integer, db.ForeignKey("pesticide.id", ondelete="CASCADE"), nullable=False, index=True
    )
    green_space_id = db.Column(
        db.Integer, db.ForeignKey("green_space.id", ondelete="CASCADE"), nullable=False, index=True
    )
    maintenance_record_id = db.Column(
        db.Integer,
        db.ForeignKey("maintenance_record.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    application_date = db.Column(db.Date, nullable=False, index=True)
    target_pest = db.Column(db.String(128), nullable=False)
    apply_area = db.Column(quantity_column())
    dilution_ratio = db.Column(db.String(64), nullable=False)
    dosage = db.Column(quantity_column(), nullable=False, default=0)
    unit = db.Column(db.String(16), nullable=False, default="milliliter")
    operator = db.Column(db.String(64), nullable=False, index=True)
    equipment = db.Column(db.String(64))
    remark = db.Column(db.Text)

    pesticide = db.relationship("Pesticide", back_populates="applications", lazy="joined")
    green_space = db.relationship("GreenSpace", lazy="joined")
    record = db.relationship("MaintenanceRecord")

    # ------------------------------------------------------------ 安全间隔期派生
    @property
    def interval_days(self):
        return int(self.pesticide.safety_interval_days or 0) if self.pesticide else 0

    @property
    def earliest_entry_date(self):
        if self.application_date is None:
            return None
        return self.application_date + timedelta(days=self.interval_days)

    @property
    def safety_status(self):
        """截至今天：releasable 已到最早进入时间；locked 仍在安全间隔期内。"""

        earliest = self.earliest_entry_date
        if earliest is None:
            return "releasable"
        return "locked" if today() < earliest else "releasable"

    @property
    def days_remaining(self):
        """距最早可进入时间的剩余天数（已到期为 0）。"""

        earliest = self.earliest_entry_date
        if earliest is None:
            return 0
        return max((earliest - today()).days, 0)

    def to_dict(self, detail=False):
        pesticide_brief = None
        if self.pesticide:
            pesticide_brief = {
                "id": self.pesticide.id,
                "code": self.pesticide.code,
                "name": self.pesticide.name,
                "toxicity": self.pesticide.toxicity,
                "toxicity_label": PESTICIDE_TOXICITY.label(self.pesticide.toxicity),
                "safety_interval_days": self.interval_days,
            }
        data = {
            "id": self.id,
            "application_no": self.application_no,
            "pesticide_id": self.pesticide_id,
            "pesticide": pesticide_brief,
            "green_space_id": self.green_space_id,
            "green_space": self.green_space.to_brief() if self.green_space else None,
            "maintenance_record_id": self.maintenance_record_id,
            "record": (
                {
                    "id": self.record.id,
                    "record_no": self.record.record_no,
                    "record_date": format_date(self.record.record_date),
                }
                if self.record
                else None
            ),
            "application_date": format_date(self.application_date),
            "target_pest": self.target_pest,
            "apply_area": to_float(self.apply_area),
            "dilution_ratio": self.dilution_ratio,
            "dosage": to_float(self.dosage),
            "unit": self.unit,
            "unit_label": PESTICIDE_UNIT.label(self.unit),
            "operator": self.operator,
            "equipment": self.equipment,
            "safety_interval_days": self.interval_days,
            "earliest_entry_date": format_date(self.earliest_entry_date),
            "safety_status": self.safety_status,
            "days_remaining": self.days_remaining,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["remark"] = self.remark
        return data
