"""业务字典。

集中维护各模块的枚举选项：模型层用于入库校验与展示文案，
接口层通过 /api/v1/meta/enums 下发给前端，避免前后端重复定义。
"""


class EnumGroup:
    """一组枚举选项：value 入库，label 用于展示。"""

    def __init__(self, name, options):
        self.name = name
        self.options = [{"value": value, "label": label} for value, label in options]
        self._labels = {value: label for value, label in options}

    @property
    def values(self):
        return list(self._labels)

    def label(self, value):
        return self._labels.get(value, value)

    def has(self, value):
        return value in self._labels

    def default(self):
        return self.options[0]["value"]

    def __contains__(self, value):
        return value in self._labels


# ---------------------------------------------------------------- 绿地台账
GREEN_SPACE_TYPE = EnumGroup("green_space_type", [
    ("park", "公园绿地"),
    ("street", "街头游园"),
    ("road", "道路绿地"),
    ("residential", "居住区绿地"),
    ("attached", "单位附属绿地"),
    ("other", "其他绿地"),
])

MAINTENANCE_GRADE = EnumGroup("maintenance_grade", [
    ("level1", "一级养护"),
    ("level2", "二级养护"),
    ("level3", "三级养护"),
])

GREEN_SPACE_STATUS = EnumGroup("green_space_status", [
    ("normal", "正常养护"),
    ("repairing", "整治提升中"),
    ("suspended", "暂停养护"),
    ("archived", "已归档"),
])

# ---------------------------------------------------------------- 养护任务
TASK_TYPE = EnumGroup("task_type", [
    ("prune", "修剪整形"),
    ("water", "浇灌排涝"),
    ("fertilize", "施肥"),
    ("pest", "病虫害防治"),
    ("weed", "除草松土"),
    ("clean", "保洁清扫"),
    ("replant", "补植补种"),
    ("winter", "防寒防冻"),
    ("other", "其他养护"),
])

TASK_PRIORITY = EnumGroup("task_priority", [
    ("low", "低"),
    ("medium", "中"),
    ("high", "高"),
    ("urgent", "紧急"),
])

TASK_STATUS = EnumGroup("task_status", [
    ("pending", "待执行"),
    ("in_progress", "进行中"),
    ("completed", "已完成"),
    ("cancelled", "已取消"),
])

# ---------------------------------------------------------------- 养护记录
QUALITY_RESULT = EnumGroup("quality_result", [
    ("qualified", "合格"),
    ("pending", "待复检"),
    ("unqualified", "不合格"),
])

WEATHER = EnumGroup("weather", [
    ("sunny", "晴"),
    ("cloudy", "多云"),
    ("overcast", "阴"),
    ("rain", "雨"),
    ("snow", "雪"),
    ("windy", "大风"),
])

# ---------------------------------------------------------------- 绿植更换
PLANT_CATEGORY = EnumGroup("plant_category", [
    ("tree", "乔木"),
    ("shrub", "灌木"),
    ("flower", "草本花卉"),
    ("ground", "地被草坪"),
    ("vine", "藤本植物"),
    ("aquatic", "水生植物"),
])

REPLACEMENT_REASON = EnumGroup("replacement_reason", [
    ("dead", "枯死更换"),
    ("disease", "病虫害更换"),
    ("aging", "老化更新"),
    ("upgrade", "品种改造"),
    ("supplement", "补植补种"),
    ("design", "景观调整"),
])

OLD_PLANT_STATUS = EnumGroup("old_plant_status", [
    ("dead", "已枯死"),
    ("dying", "长势衰弱"),
    ("diseased", "感染病虫害"),
    ("aging", "老化退化"),
    ("normal", "长势正常"),
])

MEASURE_UNIT = EnumGroup("measure_unit", [
    ("plant", "株"),
    ("square_meter", "平方米"),
    ("pot", "盆"),
    ("clump", "丛"),
])

# ---------------------------------------------------------------- 药剂管理
PESTICIDE_TYPE = EnumGroup("pesticide_type", [
    ("insecticide", "杀虫剂"),
    ("fungicide", "杀菌剂"),
    ("herbicide", "除草剂"),
    ("acaricide", "杀螨剂"),
    ("plant_growth", "植物生长调节剂"),
    ("biological", "生物农药"),
    ("other", "其他药剂"),
])

PESTICIDE_TOXICITY = EnumGroup("pesticide_toxicity", [
    ("micro", "微毒"),
    ("low", "低毒"),
    ("medium", "中等毒"),
    ("high", "高毒"),
    ("very_high", "剧毒"),
])

PESTICIDE_FORM = EnumGroup("pesticide_form", [
    ("ec", "乳油"),
    ("sc", "悬浮剂"),
    ("wp", "可湿性粉剂"),
    ("wg", "水分散粒剂"),
    ("sl", "水剂"),
    ("gr", "颗粒剂"),
    ("dp", "粉剂"),
    ("ol", "油剂"),
    ("other", "其他剂型"),
])

# 药剂出入库方向：入库补充库存，领用出库扣减库存
STOCK_MOVEMENT_TYPE = EnumGroup("stock_movement_type", [
    ("in", "入库"),
    ("out", "领用出库"),
])

# 药剂计量单位：库存、领用与用药量共用同一口径
PESTICIDE_UNIT = EnumGroup("pesticide_unit", [
    ("bottle", "瓶"),
    ("bag", "袋"),
    ("box", "包"),
    ("can", "桶"),
    ("kg", "千克"),
    ("g", "克"),
    ("liter", "升"),
    ("ml", "毫升"),
])

# 施药方式
APPLICATION_METHOD = EnumGroup("application_method", [
    ("spray", "喷雾"),
    ("dusting", "喷粉"),
    ("soil", "土壤处理"),
    ("injection", "树干注射"),
    ("bait", "毒饵"),
    ("fumigation", "熏蒸"),
    ("other", "其他方式"),
])

# 施药记录的安全状态：用于列表与看板高亮间隔期风险
APPLICATION_STATUS = EnumGroup("application_status", [
    ("within_interval", "安全间隔期内"),
    ("releasable", "可进入"),
])

# 前端下拉与文档共用的一份字典清单
ENUM_GROUPS = {
    "green_space_type": GREEN_SPACE_TYPE,
    "maintenance_grade": MAINTENANCE_GRADE,
    "green_space_status": GREEN_SPACE_STATUS,
    "task_type": TASK_TYPE,
    "task_priority": TASK_PRIORITY,
    "task_status": TASK_STATUS,
    "quality_result": QUALITY_RESULT,
    "weather": WEATHER,
    "plant_category": PLANT_CATEGORY,
    "replacement_reason": REPLACEMENT_REASON,
    "old_plant_status": OLD_PLANT_STATUS,
    "measure_unit": MEASURE_UNIT,
    "pesticide_type": PESTICIDE_TYPE,
    "pesticide_toxicity": PESTICIDE_TOXICITY,
    "pesticide_form": PESTICIDE_FORM,
    "pesticide_unit": PESTICIDE_UNIT,
    "stock_movement_type": STOCK_MOVEMENT_TYPE,
    "application_method": APPLICATION_METHOD,
    "application_status": APPLICATION_STATUS,
}


def all_enums():
    """返回全部字典，供前端下拉初始化。"""

    return {name: group.options for name, group in ENUM_GROUPS.items()}
