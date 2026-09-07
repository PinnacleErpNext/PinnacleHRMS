import io
import json

import frappe
import openpyxl

from openpyxl import Workbook
from werkzeug.wrappers import Response

from frappe.utils.file_manager import save_file


def create_attendance_excel(
    validated_data,
):
    """
    Create attendance Excel file in the format
    required by Employee Checkin Data Import.
    """

    wb = Workbook()

    ws = wb.active
    ws.title = "Attendance List"

    headers = [
        "Employee",
        "Employee Name",
        "Shift",
        "Log Type",
        "Time",
        "Punch From",
    ]

    ws.append(headers)

    for employee in sorted(validated_data):

        for row in validated_data[employee]:

            ws.append(
                [
                    row["employee"],
                    row["employee_name"],
                    row.get("shift"),
                    row.get("log_type"),
                    (f"{row.get('attendance_date', '')} " f"{row.get('time', '')}"),
                    row.get("punch_from"),
                ]
            )

    output = io.BytesIO()

    wb.save(output)

    output.seek(0)

    return output


def create_data_import(
    validated_data,
):
    """
    Create Frappe Data Import document
    for Employee Checkin.
    """

    if not validated_data:
        frappe.throw("No validated records found.")

    output = create_attendance_excel(validated_data)

    data_import = frappe.get_doc(
        {
            "doctype": "Data Import",
            "reference_doctype": "Employee Checkin",
            "import_type": "Insert New Records",
            "submit_after_import": 0,
            "mute_emails": 1,
        }
    )

    data_import.insert(ignore_permissions=True)

    file_doc = save_file(
        "attendance_import.xlsx",
        output.getvalue(),
        "Data Import",
        data_import.name,
        is_private=1,
    )

    data_import.import_file = file_doc.file_url

    data_import.save(ignore_permissions=True)

    return data_import


def download_final_attendance_excel(
    logs,
):
    """
    Generate downloadable Final Attendance Excel.
    """

    if isinstance(logs, str):
        raw_data = json.loads(logs)
    else:
        raw_data = logs

    rows = []

    # Case A:
    # {
    #     "HR-EMP-00001": [...]
    # }
    if isinstance(
        raw_data,
        dict,
    ):

        for employee_rows in raw_data.values():

            if isinstance(
                employee_rows,
                list,
            ):
                rows.extend(employee_rows)

    # Case B:
    # [
    #     {...},
    #     {...}
    # ]
    elif isinstance(
        raw_data,
        list,
    ):

        rows = raw_data

    else:

        frappe.throw("Unsupported attendance data format")

    if not rows:
        frappe.throw("No attendance data found")

    rows = sorted(
        rows,
        key=lambda row: (
            row.get("employee")
            or row.get(
                "employee_name",
                "",
            ),
            str(
                row.get(
                    "attendance_date",
                    "",
                )
            ),
            row.get("time", ""),
        ),
    )

    wb = Workbook()

    ws = wb.active
    ws.title = "Final Attendance"

    ws.append(
        [
            "Employee",
            "Employee Name",
            "Attendance Date",
            "Shift",
            "Log Type",
            "Time",
            "Punch From",
        ]
    )

    for row in rows:

        attendance_date = row.get("attendance_date")

        if hasattr(
            attendance_date,
            "strftime",
        ):
            attendance_date = attendance_date.strftime("%Y-%m-%d")
        else:
            attendance_date = str(attendance_date or "")

        ws.append(
            [
                row.get(
                    "employee",
                    "",
                ),
                row.get(
                    "employee_name",
                    "",
                ),
                attendance_date,
                row.get(
                    "shift",
                    "",
                ),
                row.get(
                    "log_type",
                    "",
                ),
                row.get(
                    "time",
                    "",
                ),
                row.get(
                    "punch_from",
                    "",
                ),
            ]
        )

    output = io.BytesIO()

    wb.save(output)

    output.seek(0)

    return Response(
        output,
        mimetype=(
            "application/vnd.openxmlformats-" "officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": "attachment; " "filename=Final_Attendance.xlsx"
        },
    )
