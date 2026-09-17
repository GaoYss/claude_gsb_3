"""药剂领用记录模型。"""

from ..constants import PESTICIDE_TOXICITY, PESTICIDE_UNIT, REQUISITION_STATUS
from ..extensions import db
from ..utils.dates import format_date, format_datetime
from ..utils.numbers import to_float
from .mixins import TimestampMixin, quantity_column


class PesticideRequisition(TimestampMixin, db.Model):
    """药剂领用登记：谁在何时领用了多少药剂，退库时回补库存。"""

    __tablename__ = "pesticide_requisition"

    id = db.Column(db.Integer, primary_key=True)
    requisition_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    pesticide_id = db.Column(
        db.Integer, db.ForeignKey("pesticide.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity = db.Column(quantity_column(), nullable=False, default=0)
    unit = db.Column(db.String(16), nullable=False, default="milliliter")
    recipient = db.Column(db.String(64), nullable=False, index=True)
    issue_date = db.Column(db.Date, nullable=False, index=True)
    purpose = db.Column(db.String(255))
    status = db.Column(db.String(16), nullable=False, default="issued", index=True)
    returned_quantity = db.Column(quantity_column())
    returned_at = db.Column(db.Date)
    operator = db.Column(db.String(64))
    remark = db.Column(db.Text)

    pesticide = db.relationship("Pesticide", back_populates="requisitions", lazy="joined")

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "requisition_no": self.requisition_no,
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
            "quantity": to_float(self.quantity),
            "unit": self.unit,
            "unit_label": PESTICIDE_UNIT.label(self.unit),
            "recipient": self.recipient,
            "issue_date": format_date(self.issue_date),
            "purpose": self.purpose,
            "status": self.status,
            "status_label": REQUISITION_STATUS.label(self.status),
            "returned_quantity": to_float(self.returned_quantity),
            "returned_at": format_date(self.returned_at),
            "operator": self.operator,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["remark"] = self.remark
        return data
