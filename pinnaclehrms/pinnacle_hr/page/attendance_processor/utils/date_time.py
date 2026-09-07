from datetime import datetime, time

from frappe.utils import getdate


def parse_date_safe(value):
    """
    Parse common date formats safely.

    Returns:
        date/datetime object or None
    """
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    for fmt in (
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ):
        try:
            return datetime.strptime(str(value), fmt)
        except (ValueError, TypeError):
            continue

    return None


def format_date_safe(date_value):
    """
    Safely format date to YYYY-MM-DD.
    """
    if not date_value:
        return ""

    if isinstance(date_value, datetime):
        return date_value.strftime("%Y-%m-%d")

    try:
        parsed_date = datetime.strptime(str(date_value), "%Y-%m-%d")
        return parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        return str(date_value)


def parse_time_safe(value):
    """
    Parse various time/datetime formats safely.

    Returns:
        datetime.time or None
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.time()

    if isinstance(value, time):
        return value

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

        formats = [
            # 24-hour
            "%H:%M:%S",
            "%H:%M",
            "%H:%M:%S.%f",
            # 12-hour
            "%I:%M:%S %p",
            "%I:%M %p",
            "%I:%M:%S.%f %p",
            # Date + time
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %I:%M:%S %p",
            "%Y-%m-%d %I:%M %p",
            "%Y-%m-%d %I:%M:%S.%f %p",
            # Slash date
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y/%m/%d %H:%M:%S.%f",
            "%Y/%m/%d %I:%M:%S %p",
            "%Y/%m/%d %I:%M %p",
            "%Y/%m/%d %I:%M:%S.%f %p",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue

    return None


def format_time_string(value):
    """
    Convert datetime/time values to HH:MM:SS.
    """
    if isinstance(value, datetime):
        return value.strftime("%H:%M:%S")

    if isinstance(value, time):
        return value.strftime("%H:%M:%S")

    if value:
        return str(value).strip()

    return None


def to_date(value):
    """
    Convert a value to a Frappe date.
    """
    if not value:
        return None

    try:
        return getdate(value)
    except Exception:
        return None


def is_empty_or_zero(value):
    """
    Used by attendance validation.
    """
    if value is None:
        return True

    value = str(value).strip()

    return value in (
        "",
        "0",
        "00",
        "00:00",
        "00:00:00",
    )
