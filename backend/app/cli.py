"""命令行工具：初始化数据表与写入演示数据。

    flask --app wsgi init-db
    flask --app wsgi seed --reset
"""

import random
from datetime import date, timedelta

import click
from flask.cli import with_appcontext

from .extensions import db
from .models import GreenSpace
from .services import (
    GreenSpaceService,
    MaintenanceRecordService,
    MaintenanceTaskService,
    PesticideApplicationService,
    PesticideRequisitionService,
    PesticideService,
    PlantReplacementService,
)

SPACE_SEEDS = [
    {
        "name": "武林广场中轴绿地",
        "district": "拱墅区",
        "address": "环城北路武林广场南侧",
        "green_type": "street",
        "maintenance_grade": "level1",
        "area_sqm": 8600,
        "manager": "沈建国",
        "contact_phone": "0571-85112233",
        "plant_summary": "香樟 86 株、红叶石楠球 42 株、时令花坛 420 平方米",
        "established_date": date(2008, 4, 18),
        "remark": "市中心重点窗口绿地，重大活动前需专项保障。",
    },
    {
        "name": "运河文化公园",
        "district": "拱墅区",
        "address": "运河东路 128 号沿河两侧",
        "green_type": "park",
        "maintenance_grade": "level1",
        "area_sqm": 46200,
        "manager": "俞晓慧",
        "contact_phone": "0571-88221009",
        "plant_summary": "垂柳 120 株、黄山栾树 68 株、鸢尾与麦冬混植地被 12000 平方米",
        "established_date": date(2012, 9, 28),
        "remark": "沿河防汛通道，汛期作业需同步报备。",
    },
    {
        "name": "文一西路沿线绿地",
        "district": "余杭区",
        "address": "文一西路（荆长大道—良睦路段）两侧",
        "green_type": "road",
        "maintenance_grade": "level2",
        "area_sqm": 31500,
        "manager": "陈立群",
        "contact_phone": "0571-86331177",
        "plant_summary": "银杏 210 株、金森女贞色块 3400 平方米、马尼拉草坪 9800 平方米",
        "established_date": date(2016, 3, 12),
        "remark": "快速路两侧，作业须避开早高峰。",
    },
    {
        "name": "西溪里小区附属绿地",
        "district": "西湖区",
        "address": "文二西路 788 号西溪里小区内",
        "green_type": "residential",
        "maintenance_grade": "level3",
        "area_sqm": 12400,
        "manager": "周雯",
        "contact_phone": "0571-88132456",
        "plant_summary": "桂花 76 株、垂丝海棠 54 株、八角金盘与南天竹组团 1800 平方米",
        "established_date": date(2005, 6, 1),
        "remark": "业主投诉集中区域，修剪作业需提前公示。",
    },
    {
        "name": "滨江公园樱花大道",
        "district": "滨江区",
        "address": "江南大道滨江公园东段",
        "green_type": "park",
        "maintenance_grade": "level1",
        "area_sqm": 23800,
        "manager": "林轶",
        "contact_phone": "0571-86608812",
        "plant_summary": "染井吉野樱 180 株、紫藤廊架 46 米、时令花卉 3600 平方米",
        "established_date": date(2018, 3, 20),
        "remark": "樱花季人流密集，需加强保洁与草坪养护。",
    },
    {
        "name": "之江路立体绿化试点",
        "district": "上城区",
        "address": "之江路 66 号高架桥墩立体绿化",
        "green_type": "other",
        "maintenance_grade": "level2",
        "area_sqm": 4200,
        "manager": "郑潮",
        "contact_phone": "0571-87790011",
        "plant_summary": "爬藤月季、常春藤与花叶络石立体种植 1400 平方米",
        "established_date": date(2021, 5, 6),
        "status": "repairing",
        "remark": "立体绿化试点，滴灌系统改造中。",
    },
    {
        "name": "临丁路老苗圃绿地",
        "district": "余杭区",
        "address": "临丁路 289 号（原苗圃用地）",
        "green_type": "other",
        "maintenance_grade": "level3",
        "area_sqm": 6800,
        "manager": "戴伟民",
        "contact_phone": "0571-86221144",
        "plant_summary": "迁移后保留香樟 24 株，其余为待改造空地",
        "established_date": date(1998, 3, 10),
        "status": "archived",
        "remark": "地块已移交储备，台账归档留档。",
    },
]

TASK_SEEDS = [
    ("prune", "行道树整形修剪", "high", "绿化一班",
     "对行道树进行疏枝整形，清理枯枝与影响视线的下垂枝。"),
    ("water", "夏季抗旱浇灌", "medium", "浇水二班",
     "连续高温天气，按早晚两班次对新栽苗木与花境浇透水。"),
    ("fertilize", "春季返青施肥", "medium", "绿化二班",
     "对草坪与色块追施复合肥，施肥后及时浇水。"),
    ("pest", "蚜虫与网蝽防治", "high", "植保班",
     "采用低毒药剂对香樟、红叶石楠进行蚜虫与网蝽防治。"),
    ("weed", "绿篱与树穴除草", "low", "绿化三班",
     "清除绿篱内杂草与树穴杂草，保持树穴整洁。"),
    ("clean", "景观节点保洁", "low", "保洁班",
     "清理落叶、白色垃圾与花坛残花，保洁面积约 5000 平方米。"),
    ("replant", "枯死苗木补植", "high", "绿化一班",
     "补植越冬枯死的麦冬与色块苗木，恢复景观连续性。"),
    ("winter", "乔木防寒裹干", "medium", "绿化二班",
     "对新栽乔木主干裹干防冻，根颈培土并浇足防冻水。"),
]

RECORD_CONTENTS = {
    "prune": ["修剪香樟下垂枝 32 株，清运枝条 2 车", "整形修剪黄山栾树 18 株，清理枯枝 1.2 吨"],
    "water": ["对花境与草坪浇灌 4 车次，累计浇水 36 吨", "早晚两班次浇灌新栽苗木 260 株"],
    "fertilize": ["草坪追施复合肥 180 公斤，施肥后浇透水", "色块灌木施用缓释肥 60 公斤"],
    "pest": ["喷施生物药剂防治蚜虫，作业面积 3200 平方米", "悬挂黄板 60 张，诱杀网蝽成虫"],
    "weed": ["清除绿篱内杂草约 800 平方米", "树穴松土除草 140 个，清运杂草 1.5 吨"],
    "clean": ["清理落叶与白色垃圾 6 车，清洗园路 800 米", "花坛残花清理与补花 120 平方米"],
    "replant": ["补植麦冬 460 平方米，浇透定根水", "补植红叶石楠球 24 株并支撑固定"],
    "winter": ["乔木裹干 96 株，根颈培土 96 处", "浇灌防冻水 28 吨，覆盖防寒布 400 平方米"],
}

PLANT_POOL = [
    ("香樟", "tree", "胸径 25-30cm", "plant"),
    ("黄山栾树", "tree", "胸径 18-20cm", "plant"),
    ("垂丝海棠", "tree", "地径 10-12cm", "plant"),
    ("红叶石楠", "shrub", "冠幅 80-100cm", "plant"),
    ("金森女贞", "shrub", "H40cm", "square_meter"),
    ("麦冬", "ground", "3-5 芽/丛", "square_meter"),
    ("马尼拉草坪", "ground", "满铺", "square_meter"),
    ("时令花卉", "flower", "杯苗", "pot"),
    ("爬藤月季", "vine", "H120cm", "plant"),
    ("常春藤", "vine", "H80cm", "clump"),
]

REASONS = ["dead", "disease", "aging", "upgrade", "supplement", "design"]
OLD_STATUS = ["dead", "dying", "diseased", "aging", "normal"]
WEATHERS = ["sunny", "cloudy", "overcast", "rain", "windy"]
WORKERS = ["王海涛", "李建民", "张凤英", "吴国强", "何丽萍", "赵春生", "孙明华", "许娟"]
SUPPLIERS = ["萧山苗木合作社", "临安绿源苗圃", "余杭花卉基地", "杭州城西园艺公司"]

PESTICIDE_SEEDS = [
    {
        "name": "10% 吡虫啉可湿性粉剂",
        "registration_no": "PD20181234",
        "pesticide_type": "insecticide",
        "toxicity": "low",
        "active_ingredient": "吡虫啉 10%",
        "formulation": "可湿性粉剂",
        "manufacturer": "浙江新农化工股份有限公司",
        "safety_interval_days": 7,
        "stock_quantity": 48000,
        "unit": "gram",
    },
    {
        "name": "4.5% 高效氯氰菊酯乳油",
        "registration_no": "PD20154321",
        "pesticide_type": "insecticide",
        "toxicity": "medium",
        "active_ingredient": "高效氯氰菊酯 4.5%",
        "formulation": "乳油",
        "manufacturer": "江苏扬农化工股份有限公司",
        "safety_interval_days": 14,
        "stock_quantity": 12000,
        "unit": "milliliter",
    },
    {
        "name": "70% 甲基硫菌灵可湿性粉剂",
        "registration_no": "PD20120876",
        "pesticide_type": "fungicide",
        "toxicity": "low",
        "active_ingredient": "甲基硫菌灵 70%",
        "formulation": "可湿性粉剂",
        "manufacturer": "山东海讯生物科技有限公司",
        "safety_interval_days": 10,
        "stock_quantity": 26000,
        "unit": "gram",
    },
    {
        "name": "1.8% 阿维菌素乳油",
        "registration_no": "PD20162288",
        "pesticide_type": "acaricide",
        "toxicity": "medium",
        "active_ingredient": "阿维菌素 1.8%",
        "formulation": "乳油",
        "manufacturer": "河北威远生物化工有限公司",
        "safety_interval_days": 14,
        "stock_quantity": 8600,
        "unit": "milliliter",
    },
    {
        "name": "苏云金杆菌可湿性粉剂",
        "registration_no": "PD20190666",
        "pesticide_type": "biological",
        "toxicity": "micro",
        "active_ingredient": "苏云金杆菌 16000IU/mg",
        "formulation": "可湿性粉剂",
        "manufacturer": "武汉科诺生物科技股份有限公司",
        "safety_interval_days": 3,
        "stock_quantity": 15000,
        "unit": "gram",
    },
    {
        "name": "41% 草甘膦异丙胺盐水剂",
        "registration_no": "PD20103455",
        "pesticide_type": "herbicide",
        "toxicity": "low",
        "active_ingredient": "草甘膦异丙胺盐 41%",
        "formulation": "水剂",
        "manufacturer": "浙江新安化工集团股份有限公司",
        "safety_interval_days": 21,
        "stock_quantity": 0,
        "unit": "milliliter",
        "status": "phase_out",
    },
]

PEST_TARGETS = ["蚜虫", "网蝽", "红蜘蛛", "白粉病", "蚧壳虫", "食叶害虫"]
DILUTION_RATIOS = ["1:1000", "1:1500", "1:2000", "800 倍液", "1000 倍液"]
EQUIPMENTS = ["背负式电动喷雾器", "车载式喷雾机", "超低容量喷雾器"]


def register_cli(app):
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_command)
    app.cli.add_command(reset_db_command)


@click.command("init-db")
@with_appcontext
def init_db_command():
    """按模型创建数据表（幂等）。"""

    db.create_all()
    click.echo("数据表已就绪")


@click.command("reset-db")
@with_appcontext
def reset_db_command():
    """删除并重建全部数据表。"""

    db.drop_all()
    db.create_all()
    click.echo("数据表已重建")


@click.command("seed")
@click.option("--reset", is_flag=True, help="先清空数据库再写入演示数据")
@click.option("--seed", "seed_value", default=20260913, help="随机种子，保证可复现")
@with_appcontext
def seed_command(reset, seed_value):
    """写入一批演示数据，便于本地联调与验收。"""

    if reset:
        db.drop_all()
        db.create_all()
    elif db.session.query(GreenSpace.id).first() is not None:
        click.echo("数据库已有数据，如需重建请执行：flask --app wsgi seed --reset")
        return

    summary = generate_demo_data(random.Random(seed_value))
    click.echo(
        "演示数据写入完成：绿地 {green_space} 处、养护任务 {maintenance_task} 条、"
        "养护记录 {maintenance_record} 条、绿植更换 {plant_replacement} 条、"
        "药剂档案 {pesticide} 个、药剂领用 {pesticide_requisition} 条、"
        "施药记录 {pesticide_application} 条".format(**summary)
    )


def generate_demo_data(rng):
    """按真实业务节奏生成演示数据，并复用 service 层以触发编号与状态联动。"""

    today_ = date.today()
    counts = {
        "green_space": 0,
        "maintenance_task": 0,
        "maintenance_record": 0,
        "plant_replacement": 0,
        "pesticide": 0,
        "pesticide_requisition": 0,
        "pesticide_application": 0,
    }

    pesticides = []
    for seed in PESTICIDE_SEEDS:
        pesticides.append(PesticideService.create(dict(seed)))
        counts["pesticide"] += 1
    in_use_pesticides = [item for item in pesticides if item.status == "in_use"]
    active_spaces = []

    for index, space_seed in enumerate(SPACE_SEEDS):
        payload = dict(space_seed)
        space = GreenSpaceService.create(payload)
        counts["green_space"] += 1

        # 已归档绿地不允许再登记任务与记录，仅保留台账
        if space.status == "archived":
            continue
        active_spaces.append(space)
        pest_records = []

        for _ in range(rng.randint(2, 4)):
            task_type, title, priority, executor, description = rng.choice(TASK_SEEDS)
            planned_ahead = rng.random() < 0.25
            plan_date = (
                today_ + timedelta(days=rng.randint(1, 18))
                if planned_ahead
                else today_ - timedelta(days=rng.randint(5, 170))
            )
            task = MaintenanceTaskService.create({
                "green_space_id": space.id,
                "title": title,
                "task_type": task_type,
                "plan_date": plan_date,
                "priority": priority,
                "executor": executor,
                "description": description,
            })
            counts["maintenance_task"] += 1

            # 未来任务保持待执行；历史任务少量遗留为逾期未办
            if planned_ahead or rng.random() < 0.2:
                continue

            record_date = plan_date + timedelta(days=rng.randint(0, 3))
            quality = "qualified" if rng.random() < 0.82 else rng.choice(["pending", "unqualified"])
            record = MaintenanceRecordService.create({
                "task_id": task.id,
                "record_date": record_date,
                "work_content": rng.choice(RECORD_CONTENTS[task_type]),
                "worker": rng.choice(WORKERS),
                "work_hours": rng.choice([3, 4, 5, 6, 8, 10]),
                "weather": rng.choice(WEATHERS),
                "materials": rng.choice(["复合肥 180kg", "低毒药剂 12L", "支撑杆 60 根", "无", "防寒布 400㎡"]),
                "quality_result": quality,
                "issue_found": "局部色块缺株，已列入下月补植计划" if quality == "unqualified" else None,
            })
            counts["maintenance_record"] += 1
            if task_type == "pest":
                pest_records.append(record)

            replace_chance = 0.85 if task_type in {"replant", "pest", "prune"} else 0.35
            if rng.random() < replace_chance:
                for _ in range(rng.randint(1, 2)):
                    plant_name, category, spec, unit = rng.choice(PLANT_POOL)
                    unit_price = round(rng.uniform(8, 220), 2)
                    PlantReplacementService.create({
                        "green_space_id": space.id,
                        "maintenance_record_id": record.id,
                        "plant_name": plant_name,
                        "plant_category": category,
                        "spec": spec,
                        "quantity": rng.choice([20, 45, 60, 120, 260, 400]),
                        "unit": unit,
                        "reason": rng.choice(REASONS),
                        "old_plant_status": rng.choice(OLD_STATUS),
                        "replace_date": record_date + timedelta(days=rng.randint(0, 5)),
                        "supplier": rng.choice(SUPPLIERS),
                        "unit_price": unit_price,
                        "operator": rng.choice(WORKERS),
                    })
                    counts["plant_replacement"] += 1

        # 日常巡查类记录（不挂任务），保留独立录入场景
        for _ in range(rng.randint(1, 3)):
            MaintenanceRecordService.create({
                "green_space_id": space.id,
                "record_date": today_ - timedelta(days=rng.randint(1, 40)),
                "work_content": rng.choice([
                    "日常巡查，清理零星垃圾与倒伏草本",
                    "巡查发现一处树穴积水，已开沟排水",
                    "巡查记录：色块长势正常，无明显病虫害",
                ]),
                "worker": rng.choice(WORKERS),
                "work_hours": rng.choice([1, 2, 3]),
                "weather": rng.choice(WEATHERS),
                "quality_result": "qualified",
            })
            counts["maintenance_record"] += 1

        # 药剂施用与领用：约六成绿地生成 1~2 条施药记录，领用先于施药登记
        space_applications = []
        for _ in range(rng.choice([0, 1, 1, 2])):
            pesticide = rng.choice(in_use_pesticides)
            app_date = today_ - timedelta(days=rng.randint(20, 120))
            linked_record = (
                rng.choice(pest_records) if pest_records and rng.random() < 0.7 else None
            )
            dosage = float(rng.choice([200, 300, 400, 500, 600, 800]))
            requisition = PesticideRequisitionService.create({
                "pesticide_id": pesticide.id,
                "quantity": dosage,
                "recipient": rng.choice(WORKERS),
                "issue_date": app_date - timedelta(days=rng.randint(0, 2)),
                "purpose": f"{space.name}{rng.choice(PEST_TARGETS)}防治用药",
                "operator": "仓管员 " + rng.choice(WORKERS),
            })
            counts["pesticide_requisition"] += 1
            application = PesticideApplicationService.create({
                "pesticide_id": pesticide.id,
                "green_space_id": space.id,
                "maintenance_record_id": linked_record.id if linked_record else None,
                "application_date": app_date,
                "target_pest": rng.choice(PEST_TARGETS),
                "apply_area": rng.choice([1200, 2400, 3200, 4800, 6000]),
                "dilution_ratio": rng.choice(DILUTION_RATIOS),
                "dosage": dosage,
                "operator": rng.choice(WORKERS),
                "equipment": rng.choice(EQUIPMENTS),
                "remark": "避开人流高峰时段作业，设置警示标识。",
            }, force=True)
            counts["pesticide_application"] += 1
            space_applications.append(application)

    # 选两处绿地补登近期施药（间隔期内），供看板与列表展示安全管控状态
    for space in active_spaces[:2]:
        pesticide = in_use_pesticides[0]
        app_date = today_ - timedelta(days=rng.randint(1, 3))
        PesticideRequisitionService.create({
            "pesticide_id": pesticide.id,
            "quantity": 400,
            "recipient": rng.choice(WORKERS),
            "issue_date": app_date,
            "purpose": f"{space.name}蚜虫应急补防用药",
            "operator": "仓管员 沈慧",
        })
        counts["pesticide_requisition"] += 1
        PesticideApplicationService.create({
            "pesticide_id": pesticide.id,
            "green_space_id": space.id,
            "application_date": app_date,
            "target_pest": "蚜虫",
            "apply_area": 3200,
            "dilution_ratio": "1:1500",
            "dosage": 400,
            "operator": rng.choice(WORKERS),
            "equipment": rng.choice(EQUIPMENTS),
            "remark": "巡查发现蚜虫虫口回升，间隔期内补防，已现场确认风险并设置围挡。",
        }, force=True)
        counts["pesticide_application"] += 1

    # 一条已退库领用记录（先走发放再办理退库），覆盖领用全生命周期
    if in_use_pesticides and active_spaces:
        issue_date = today_ - timedelta(days=18)
        returned_requisition = PesticideRequisitionService.create({
            "pesticide_id": in_use_pesticides[2].id,
            "quantity": 300,
            "recipient": WORKERS[2],
            "issue_date": issue_date,
            "purpose": f"{active_spaces[-1].name}白粉病防治备药（未用完退库）",
            "operator": "仓管员 沈慧",
        })
        PesticideRequisitionService.register_return(returned_requisition.id, {
            "returned_quantity": 80,
            "returned_at": issue_date + timedelta(days=1),
        })
        counts["pesticide_requisition"] += 1

    # 一条已取消任务，覆盖全部状态场景
    first_space = db.session.query(GreenSpace).order_by(GreenSpace.id.asc()).first()
    if first_space is not None:
        MaintenanceTaskService.create({
            "green_space_id": first_space.id,
            "title": "台风前乔木加固（已取消）",
            "task_type": "other",
            "plan_date": today_ - timedelta(days=12),
            "priority": "urgent",
            "executor": "应急班组",
            "description": "台风路径外移，作业取消。",
            "status": "cancelled",
        })
        counts["maintenance_task"] += 1

    db.session.commit()
    return counts
