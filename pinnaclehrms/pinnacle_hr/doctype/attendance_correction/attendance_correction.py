# Copyright (c) 2026, Opticode Technologies Pvt. Ltd.
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime
from erpnext.accounts.utils import get_fiscal_year


class AttendanceCorrection(Document):

    def validate(self):
        if not check_attendance_correction_eligibility(self):
            frappe.throw(
                "You have exceeded the maximum limit of attendance correction requests for this fiscal year."
            )

    def on_submit(self):
        new_att = correct_attendance(self)
        frappe.db.set_value(
            "Attendance Correction",
            self.name,
            {
                "corrected_attendance_value": new_att,
                "status": "Approved",
            },
        )


def check_attendance_correction_eligibility(doc):
    """
    Checks if the employee has made fewer than 6 attendance
    corrections in the current fiscal year.
    """
    allowed_corrections = frappe.db.get_single_value(
        "HR Settings",
        "max_attendance_corrections_per_fiscal_year",
    )
    try:
        if frappe.session.user == "Administrator":
            return True

        # Get current fiscal year date range
        fiscal_year = get_fiscal_year()
        fiscal_start = fiscal_year[1]
        fiscal_end = fiscal_year[2]

        correction_count = frappe.db.count(
            "Attendance Correction",
            filters={
                "employee": doc.employee,
                "creation": ["between", [fiscal_start, fiscal_end]],
                "docstatus": 1,
            },
        )

        return correction_count < allowed_corrections

    except Exception:
        frappe.log_error(
            frappe.get_traceback(), "Attendance Correction Eligibility Error"
        )
        return False


def correct_attendance(doc):
    attendance_date = getdate(doc.attendance_date)

    # 1. Fetch existing attendance
    existing_attendance_name = frappe.db.get_value(
        "Attendance",
        {
            "employee": doc.employee,
            "attendance_date": attendance_date,
            "docstatus": 1,
        },
        "name",
    )

    old_in_time = None
    old_out_time = None

    # 2. Cancel existing attendance (if any)
    if existing_attendance_name:
        existing_attendance = frappe.get_doc("Attendance", existing_attendance_name)
        old_in_time = existing_attendance.in_time
        old_out_time = existing_attendance.out_time
        existing_attendance.cancel()

    # 3. Determine corrected times
    final_in_time = old_in_time
    final_out_time = old_out_time

    if doc.log_type and doc.time:
        time_value = get_datetime(f"{doc.attendance_date} {doc.time}")

        if doc.log_type.upper() == "IN":
            final_in_time = time_value
        elif doc.log_type.upper() == "OUT":
            final_out_time = time_value

    # 4. Create new attendance
    new_attendance = frappe.get_doc(
        {
            "doctype": "Attendance",
            "employee": doc.employee,
            "attendance_date": attendance_date,
            "status": "Present",
            "shift": doc.shift,
            "in_time": final_in_time,
            "out_time": final_out_time,
        }
    )

    new_attendance.insert(ignore_permissions=True)
    new_attendance.submit()

    return new_attendance.name


@frappe.whitelist()
def get_attendance(emp, att_date):
    records = frappe.get_list(
        "Attendance",
        filters={
            "employee": emp,
            "attendance_date": att_date,
            "docstatus": 1,
        },
        fields=["name"],
        limit=1,
        ignore_permissions=True,
    )

    if not records:
        return {}

    doc = frappe.get_doc("Attendance", records[0].name)
    return {
        "in_time": doc.in_time,
        "out_time": doc.out_time,
    }


def get_permission_query_conditions(user):
    if not user or user == "Administrator":
        return ""

    # Get employee linked to user
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")

    conditions = []

    if employee:
        conditions.append(f"`tabAttendance Correction`.employee = '{employee}'")

    conditions.append(f"`tabAttendance Correction`.leave_approver = '{user}'")

    return " OR ".join(conditions)
