import json

from .date_time import parse_time_safe, to_date


def coerce_json_arg(arg):
    """
    Convert a JSON string into Python data.

    If arg is already a Python object, return it unchanged.
    """
    if not arg:
        return None

    if isinstance(arg, str):
        try:
            return json.loads(arg)
        except Exception:
            return None

    return arg


def normalize_punch_record(row):
    """
    Convert a source attendance row into the common attendance structure.

    Canonical structure:

    {
        "employee": ...,
        "employee_name": ...,
        "device_id": ...,
        "device": ...,
        "attendance_date": ...,
        "time": ...,
        "source": ...
    }
    """

    if not row:
        return None

    employee = row.get("employee") or row.get("employee_id")

    employee_name = row.get("employee_name") or row.get("name") or ""

    device = (
        row.get("device_name") or row.get("device") or row.get("punch_from") or "N/A"
    )

    device_id = str(row.get("device_id") or "").strip()

    attendance_date = to_date(row.get("attendance_date"))

    punch_time = row.get("time")

    if punch_time:
        parsed_time = parse_time_safe(punch_time)

        if parsed_time:
            punch_time = parsed_time

    return {
        "employee": employee,
        "employee_name": str(employee_name).strip(),
        "device_id": device_id,
        "device": str(device).strip(),
        "attendance_date": attendance_date,
        "time": punch_time,
        "source": row.get("source") or row.get("device") or "",
    }


def normalize_records(records):
    """
    Normalize a list of attendance records.
    """
    normalized = []

    for row in records or []:
        record = normalize_punch_record(row)

        if record:
            normalized.append(record)

    return normalized


def merge_header_cells(header_cells):
    """
    Merge multi-cell headers such as:

        Attendance | Device | ID

    into:

        Attendance Device ID
    """

    merged = []
    temp = []

    ending_words = {
        "id",
        "name",
        "date",
        "shift",
        "time",
    }

    recognized_words = {
        "attendance",
        "device",
        "id",
        "employee",
        "name",
        "date",
        "shift",
        "in",
        "out",
        "time",
    }

    for val in header_cells:
        if val is None:
            continue

        text = str(val).strip()

        if not text:
            continue

        if text.lower() in recognized_words:
            temp.append(text)

            if text.lower() in ending_words:
                merged.append(" ".join(temp))
                temp = []
        else:
            if temp:
                merged.append(" ".join(temp))
                temp = []

            merged.append(text)

    if temp:
        merged.append(" ".join(temp))

    return merged
