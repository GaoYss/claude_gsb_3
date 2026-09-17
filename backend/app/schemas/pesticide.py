"""药剂管理校验规则：药剂档案、出入库流水、施药记录。"""

from ..constants import (
    APPLICATION_METHOD,
    PESTICIDE_FORM,
    PESTICIDE_TOXICITY,
    PESTICIDE_TYPE,
    PESTICIDE_UNIT,
    STOCK_MOVEMENT_TYPE,
    WEATHER,
)
from .common import PayloadValidator


def validate_pesticide(payload):
    return (
        PayloadValidator(payload)
        .string("name", "药剂名称", required=True, max_length=128)
        .enum("pesticide_type", "药剂类别", group=PESTICIDE_TYPE, required=True)
        .enum("toxicity", "毒性", group=PESTICIDE_TOXICITY, default="low")
        .enum("form", "剂型", group=PESTICIDE_FORM, default="ec")
        .string("active_ingredient", "有效成分", max_length=128)
        .string("registration_no", "农药登记证号", max_length=64)
        .string("manufacturer", "生产企业", max_length=128)
        .enum("unit", "计量单位", group=PESTICIDE_UNIT, default="bottle")
        .number("stock_quantity", "期初库存", min_value=0, max_value=99999999)
        .number("stock_low_threshold", "库存预警阈值", min_value=0, max_value=99999999)
        .integer("safety_interval_days", "安全间隔期（天）", required=True, min_value=0, max_value=365)
        .string("target_pests", "防治对象", max_length=255)
        .string("storage_condition", "储存条件", max_length=255)
        .text("remark", "备注", max_length=2000)
        .done()
    )


def validate_stock_movement(payload):
    return (
        PayloadValidator(payload)
        .integer("pesticide_id", "药剂", required=True, min_value=1)
        .enum("movement_type", "出入库类型", group=STOCK_MOVEMENT_TYPE, required=True)
        .number("quantity", "数量", required=True, min_value=0.01, max_value=99999999)
        .date("movement_date", "出入库日期", required=True)
        .string("receiver", "领用人 / 经办人", max_length=64)
        .integer("green_space_id", "领用绿地", min_value=1)
        .string("purpose", "用途", max_length=255)
        .string("operator", "登记人", max_length=64)
        .text("remark", "备注", max_length=2000)
        .done()
    )


def validate_application(payload):
    return (
        PayloadValidator(payload)
        .integer("green_space_id", "施药区域（绿地）", required=True, min_value=1)
        .integer("pesticide_id", "使用药剂", required=True, min_value=1)
        .string("location", "具体位置", max_length=128)
        .date("application_date", "施药日期", required=True)
        .time("application_time", "施药时刻")
        .string("target_pest", "防治对象", required=True, max_length=128)
        .enum("application_method", "施药方式", group=APPLICATION_METHOD)
        .string("dilution_ratio", "稀释浓度", max_length=64)
        .number("dosage", "用药量", required=True, min_value=0.01, max_value=99999999)
        .number("treated_area", "作业面积（㎡）", min_value=0.01, max_value=99999999)
        .string("operator", "施药人员", required=True, max_length=64)
        .enum("weather", "天气", group=WEATHER)
        .text("remark", "备注", max_length=2000)
        .done()
    )
