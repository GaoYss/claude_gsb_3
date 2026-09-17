"""日期解析与序列化辅助。"""

from datetime import date, datetime, time


def parse_date(value, field_label="日期"):
    """把 YYYY-MM-DD 或 ISO 字符串解析为 date。"""

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text).date()
        except ValueError as exc:
            raise ValueError(f"{field_label}格式应为 YYYY-MM-DD") from exc
    raise ValueError(f"{field_label}格式应为 YYYY-MM-DD")


def format_date(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return None


def format_datetime(value):
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat(sep=" ")
    return None


def format_datetime_minute(value):
    """分钟精度的日期时间（最早可进入时间等由日期+时刻派生的值）。"""

    if isinstance(value, datetime):
        return value.replace(second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")
    return None


def today():
    return datetime.now().date()


def parse_time(value, field_label="时间"):
    """把 HH:MM 或 HH:MM:SS 解析为 time；date/datetime 直接取时间部分。"""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value.time().replace(second=0, microsecond=0)
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                return datetime.strptime(text, fmt).time().replace(second=0, microsecond=0)
            except ValueError:
                continue
    raise ValueError(f"{field_label}格式应为 HH:MM")


def format_time(value):
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0).strftime("%H:%M")
    return None


def at_time(day, moment=None):
    """把日期与可选时刻合并为 datetime；时刻缺省按当日 00:00 计。"""

    return datetime.combine(day, moment or time.min)
