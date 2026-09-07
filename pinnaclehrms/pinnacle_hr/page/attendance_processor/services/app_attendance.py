from collections import defaultdict

import frappe


def get_app_attendance(
    employee_list,
    payroll_from,
    payroll_to,
):
    """
    Fetch raw Employee Checkin punches for employees
    within the payroll period.

    Only records with skip_auto_attendance = 0 are included.
    """

    if not employee_list:
        return {}

    query = """
        SELECT
            employee,
            employee_name,
            shift,
            DATE(`time`) AS attendance_date,
            `time`,
            log_type,
            skip_auto_attendance
        FROM
            `tabEmployee Checkin`
        WHERE
            employee IN %(employee_list)s
            AND DATE(`time`) BETWEEN %(from_date)s AND %(to_date)s
            AND skip_auto_attendance = 0
        ORDER BY
            employee,
            `time`
    """

    rows = frappe.db.sql(
        query,
        {
            "employee_list": tuple(employee_list),
            "from_date": payroll_from,
            "to_date": payroll_to,
        },
        as_dict=True,
    )

    attendance_dict = defaultdict(list)

    for row in rows:
        attendance_dict[row["employee"]].append(row)

    return dict(attendance_dict)


def convert_app_attendance_to_records(app_attendance):
    """
    Convert Employee Checkin data into the same raw punch
    structure used by biometric processors.
    """

    converted_records = []

    for employee_id, records in app_attendance.items():
        for record in records:

            punch_time = record.get("time")

            if not punch_time:
                continue

            converted_records.append(
                {
                    "employee": employee_id,
                    "employee_id": employee_id,
                    "employee_name": record.get("employee_name"),
                    "device_id": "",
                    "device": "App",
                    "device_name": "App",
                    "attendance_date": record.get("attendance_date"),
                    "time": punch_time,
                    "source": "App",
                }
            )

    return converted_records
