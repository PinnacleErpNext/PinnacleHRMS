from collections import defaultdict

import frappe

from ..constants import (
    LOG_TYPE_IN,
    LOG_TYPE_OUT,
    MSG_ATTENDANCE_GENERATED,
)
from ..utils.date_time import parse_time_safe, to_date
from ..utils.normalization import normalize_punch_record
from .employee import (
    get_employee_id_from_device,
    get_employee_name,
    get_employee_shift_map,
)


def generate_final_sheet(attendance_data=None):
    """
    Generate final punch-style attendance.

    Input:
        Raw attendance records from:

        - Pinnacle
        - Opticode
        - Mantra
        - Other
        - App

    Output:

        Employee
        Employee Name
        Date
        Shift
        Log Type
        Time
        Punch From
    """

    attendance_data = attendance_data or []

    punch_map = defaultdict(lambda: defaultdict(list))

    # ---------------------------------------------------------
    # NORMALIZE AND BUILD PUNCH MAP
    # ---------------------------------------------------------

    for row in attendance_data:

        try:
            record = normalize_punch_record(row)

            if not record:
                continue

            employee = record.get("employee")

            employee_name = record.get("employee_name")

            device = record.get("device") or "N/A"

            device_id = record.get("device_id") or ""

            # -------------------------------------------------
            # Resolve employee from biometric mapping
            # -------------------------------------------------

            if not employee:
                employee = get_employee_id_from_device(
                    device,
                    device_id,
                )

            if not employee:
                continue

            # -------------------------------------------------
            # Resolve employee name
            # -------------------------------------------------

            if not employee_name:
                employee_name = get_employee_name(employee)

            if not employee_name:
                continue

            # -------------------------------------------------
            # Date
            # -------------------------------------------------

            punch_date = to_date(record.get("attendance_date"))

            if not punch_date:
                continue

            # -------------------------------------------------
            # CASE 1: Raw punch
            # -------------------------------------------------

            if record.get("time"):

                punch_time = parse_time_safe(record.get("time"))

                if not punch_time:
                    continue

                punch_map[employee][punch_date].append(
                    {
                        "employee": employee,
                        "employee_name": employee_name,
                        "time": punch_time,
                        "device": device,
                        "device_id": device_id,
                    }
                )

        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "Punch parsing error",
            )

    # ---------------------------------------------------------
    # BUILD FINAL ROWS
    # ---------------------------------------------------------

    final_rows = []

    employee_shift_map = get_employee_shift_map(punch_map.keys())

    for employee, dates in punch_map.items():

        for date_key, punches in dates.items():

            if not punches:
                continue

            punches.sort(key=lambda x: x["time"])

            first_punch = punches[0]
            last_punch = punches[-1]

            employee_name = first_punch.get("employee_name") or get_employee_name(
                employee
            )

            shift = employee_shift_map.get(employee)

            # -------------------------------------------------
            # IN
            # -------------------------------------------------

            final_rows.append(
                {
                    "employee": employee,
                    "employee_name": employee_name,
                    "attendance_date": date_key,
                    "shift": shift,
                    "log_type": LOG_TYPE_IN,
                    "time": first_punch["time"].strftime("%H:%M:%S"),
                    "punch_from": first_punch["device"],
                }
            )

            # -------------------------------------------------
            # OUT
            # -------------------------------------------------

            if first_punch["time"] != last_punch["time"]:

                final_rows.append(
                    {
                        "employee": employee,
                        "employee_name": employee_name,
                        "attendance_date": date_key,
                        "shift": shift,
                        "log_type": LOG_TYPE_OUT,
                        "time": last_punch["time"].strftime("%H:%M:%S"),
                        "punch_from": last_punch["device"],
                    }
                )

    # ---------------------------------------------------------
    # IMPORTANT:
    # Sorting MUST happen after ALL employees are processed.
    # ---------------------------------------------------------

    final_rows = sorted(
        final_rows,
        key=lambda row: (
            row.get("employee") or "",
            str(row.get("attendance_date") or ""),
            row.get("time") or "",
        ),
    )

    return {
        "message": MSG_ATTENDANCE_GENERATED,
        "total_records": len(final_rows),
        "data": final_rows,
    }
