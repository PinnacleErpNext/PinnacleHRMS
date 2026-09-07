import json

import frappe
from werkzeug.wrappers import Response

from .processors import (
    mantra,
    opticode,
    other,
    pinnacle,
)

from .services.app_attendance import (
    convert_app_attendance_to_records,
    get_app_attendance,
)

from .services.attendance_generator import (
    generate_final_sheet,
)

from .services.attendance_validator import (
    validate_attendance_data,
)

from .services.backup import (
    backup_employee_checkins,
)

from .services.checkin_manager import (
    delete_existing_employee_checkins,
)

from .services.data_import import (
    create_data_import,
    download_final_attendance_excel,
)

from .services.employee import (
    get_employee,
)

# ============================================================
# LOAD RAW ATTENDANCE
# ============================================================


@frappe.whitelist()
def load_raw_attendance_data():

    pinnacle_file = frappe.request.files.get("pinnacle_file")

    opticode_file = frappe.request.files.get("opticode_file")

    mantra_file = frappe.request.files.get("mantra_file")

    other_file = frappe.request.files.get("other_file")

    company = frappe.form_dict.get("company") or None

    payroll_from = frappe.form_dict.get("from_date")

    payroll_to = frappe.form_dict.get("to_date")

    if not payroll_from or not payroll_to:

        return Response(
            "❌ Payroll period is required",
            status=400,
        )

    # ---------------------------------------------------------
    # Employees
    # ---------------------------------------------------------

    employee_list = get_employee(company=company)

    if not employee_list:

        return Response(
            "❌ No active employees found.",
            status=404,
        )

    # ---------------------------------------------------------
    # App Attendance
    # ---------------------------------------------------------

    app_attendance = get_app_attendance(
        list(employee_list.keys()),
        payroll_from,
        payroll_to,
    )

    app_records = convert_app_attendance_to_records(app_attendance)

    # ---------------------------------------------------------
    # Biometric files
    # ---------------------------------------------------------

    pinnacle_attendance = []

    opticode_attendance = []

    mantra_attendance = []

    other_attendance = []

    if pinnacle_file:

        pinnacle_attendance = pinnacle.process(pinnacle_file)

    if opticode_file:

        opticode_attendance = opticode.process(opticode_file)

    if mantra_file:

        mantra_attendance = mantra.process(mantra_file)

    if other_file:

        other_attendance = other.process(other_file)

    return {
        "message": "✅ Attendance files processed successfully",
        "status_cd": 200,
        "pinnacle_attendance": pinnacle_attendance,
        "opticode_attendance": opticode_attendance,
        "mantra_attendance": mantra_attendance,
        "other_attendance": other_attendance,
        "app_attendance": app_records,
    }


# ============================================================
# GENERATE / PREVIEW FINAL ATTENDANCE
# ============================================================


@frappe.whitelist()
def preview_final_attendance_sheet(
    raw_data=None,
):
    """
    Generate final attendance preview.

    Expected structure:

    {
        "pinnacle": [],
        "opticode": [],
        "mantra": [],
        "other": [],
        "app": []
    }
    """

    if not raw_data:

        return {
            "message": "No raw data provided",
            "data": [],
            "total_records": 0,
        }

    if isinstance(
        raw_data,
        str,
    ):

        try:
            raw_data = json.loads(raw_data)

        except Exception:

            frappe.throw("Invalid attendance JSON data.")

    records = []

    records.extend(
        raw_data.get(
            "pinnacle",
            [],
        )
    )

    records.extend(
        raw_data.get(
            "opticode",
            [],
        )
    )

    records.extend(
        raw_data.get(
            "mantra",
            [],
        )
    )

    records.extend(
        raw_data.get(
            "other",
            [],
        )
    )

    records.extend(
        raw_data.get(
            "app",
            [],
        )
    )

    result = generate_final_sheet(records)

    final_rows = result.get(
        "data",
        [],
    )

    return {
        "message": "Preview generated successfully",
        "total_records": len(final_rows),
        "data": final_rows,
    }


# ============================================================
# VALIDATION
# ============================================================


@frappe.whitelist()
def validate_attendance(
    attendance_data=None,
):
    """
    Validate generated attendance.
    """

    return validate_attendance_data(attendance_data)


# ============================================================
# CREATE DATA IMPORT
# ============================================================


@frappe.whitelist()
def create_data_import_for_attendance(
    attendance_data=None,
    payroll_from=None,
    payroll_to=None,
):
    """
    Main replacement workflow:

        1. Validate input
        2. Identify employees
        3. Backup existing checkins
        4. Delete existing checkins
        5. Create Data Import
    """

    if isinstance(
        attendance_data,
        str,
    ):

        try:

            validated_data = json.loads(attendance_data)

        except Exception:

            frappe.throw("Invalid attendance data JSON.")

    else:

        validated_data = attendance_data or {}

    if not validated_data:

        frappe.throw("No validated records found.")

    if not payroll_from or not payroll_to:

        frappe.throw("Payroll period " "(from and to dates) " "are required.")

    # ---------------------------------------------------------
    # Prepare employee list
    # ---------------------------------------------------------

    employees = set()

    total_import_records = 0

    for employee_id in validated_data:

        for row in validated_data[employee_id]:

            employee = row.get("employee") or employee_id

            if employee:

                employees.add(employee)

            total_import_records += 1

    employees = list(employees)

    if not employees:

        frappe.throw("No employees found in validated attendance.")

    # ---------------------------------------------------------
    # BACKUP
    # ---------------------------------------------------------

    backup_stats = backup_employee_checkins(
        employees=employees,
        from_time=payroll_from,
        to_time=payroll_to,
    )

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    deleted_count = delete_existing_employee_checkins(
        employees=employees,
        from_time=payroll_from,
        to_time=payroll_to,
    )

    # ---------------------------------------------------------
    # CREATE DATA IMPORT
    # ---------------------------------------------------------

    data_import = create_data_import(validated_data)

    frappe.db.commit()

    return {
        "data_import": data_import.name,
        "backup_inserted": backup_stats.get(
            "inserted",
            0,
        ),
        "backup_skipped": backup_stats.get(
            "skipped",
            0,
        ),
        "deleted_checkins": deleted_count,
        "total_import_records": total_import_records,
    }


# ============================================================
# DOWNLOAD FINAL EXCEL
# ============================================================


@frappe.whitelist()
def download_final_attendance_excel_endpoint(
    logs,
):
    """
    Download final attendance Excel.
    """

    return download_final_attendance_excel(logs)
