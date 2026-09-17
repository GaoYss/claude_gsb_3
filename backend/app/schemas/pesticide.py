"""药剂管理校验规则。"""

from ..constants import (
    PESTICIDE_STATUS,
    PESTICIDE_TOXICITY,
    PESTICIDE_TYPE,
    PESTICIDE_UNIT,
    REQUISITION_STATUS,
)
from .common import PayloadValidator


def validate_pesticide(payload):
    return (
        PayloadValidator(payload)
        .string("code", "药剂编号", max_length=32)
        .string("name", "药剂名称", required=True, max_length=128)
        .string("registration_no", "农药登记证号", max_length=64)
        .enum("pesticide_type", "药剂类别", group=PESTICIDE_TYPE, required=True)
        .enum("toxicity", "毒性级别", group=PESTICIDE_TOXICITY, required=True)
        .string("active_ingredient", "有效成分", max_length=128)
        .string("formulation", "剂型", max_length=32)
        .string("manufacturer", "生产厂家", max_length=128)
        .integer("safety_interval_days", "安全间隔期（天）", required=True,
                 min_value=0, max_value=365)
        .number("stock_quantity", "库存数量", min_value=0, max_value=99999999)
        .enum("unit", "计量单位", group=PESTICIDE_UNIT, default="milliliter")
        .enum("status", "档案状态", group=PESTICIDE_STATUS, default="in_use")
        .text("remark", "备注", max_length=2000)
        .done()
    )


def validate_requisition(payload):
    return (
        PayloadValidator(payload)
        .integer("pesticide_id", "领用药剂", required=True, min_value=1)
        .number("quantity", "领用数量", required=True, min_value=0.01, max_value=999999)
        .string("recipient", "领用人", required=True, max_length=64)
        .date("issue_date", "领用日期", required=True)
        .string("purpose", "用途说明", max_length=255)
        .enum("status", "状态", group=REQUISITION_STATUS)
        .number("returned_quantity", "退库数量", min_value=0, max_value=999999)
        .date("returned_at", "退库日期")
        .string("operator", "发放人", max_length=64)
        .text("remark", "备注", max_length=2000)
        .done()
    )


def validate_requisition_return(payload):
    """退库登记：只接收退库数量与退库日期。"""

    return (
        PayloadValidator(payload)
        .number("returned_quantity", "退库数量", required=True, min_value=0.01,
                max_value=999999)
        .date("returned_at", "退库日期", required=True)
        .done()
    )


def validate_application(payload):
    return (
        PayloadValidator(payload)
        .integer("pesticide_id", "施用药剂", required=True, min_value=1)
        .integer("green_space_id", "施药区域", required=True, min_value=1)
        .integer("maintenance_record_id", "关联养护记录", min_value=1)
        .date("application_date", "施药日期", required=True)
        .string("target_pest", "防治对象", required=True, max_length=128)
        .number("apply_area", "施药面积（㎡）", min_value=0.01, max_value=99999999)
        .string("dilution_ratio", "稀释浓度", required=True, max_length=64)
        .number("dosage", "用药量", required=True, min_value=0.01, max_value=999999)
        .string("operator", "施药人员", required=True, max_length=64)
        .string("equipment", "施药器械", max_length=64)
        .text("remark", "备注", max_length=2000)
        .done()
    )
