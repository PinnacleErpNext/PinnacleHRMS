# Copyright (c) 2025, OTPL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today
from erpnext.accounts.utils import get_fiscal_year
from hrms.hr.doctype.attendance.attendance import Attendance
from frappe.utils import get_datetime, getdate


class AttendanceCorrection(Document):
    def validate(self):
        if not check_attendance_correction_eligiblity(self, "validate"):
            frappe.throw(
                "You have exceeded the maximum limit of 6 attendance correction requests for this fiscal year."
            )

    def on_submit(self):
        new_att = correct_attendance(self)
        frappe.db.set_value(
            "Attendance Correction",
            self.name,
            {
                "corrected_attendance": new_att,
                "status": "Approved",
            },
        )


def check_attendance_correction_eligiblity(doc, method):
    if frappe.session.user == "Administrator":
        return True
    """
    Checks if the employee has made 6 or more attendance correction requests
    in the current fiscal year.

    Returns:
        True  -> Eligible (less than 6 corrections)
        False -> Not eligible (6 or more corrections)
    """
    try:
        # Get current fiscal year range
        fiscal_year = get_fiscal_year()
        fiscal_start = fiscal_year.get("year_start_date")
        fiscal_end = fiscal_year.get("year_end_date")
        # Count attendance corrections for this employee within fiscal year
        correction_count = frappe.db.count(
            "Attendance Correction",
            filters={
                "employee": doc.employee,
                "creation": ["between", [fiscal_start, fiscal_end]],
                "docstatus": 1,
            },
        )
        # Eligible only if < 6 corrections
        return correction_count < 6

    except Exception:
        frappe.log_error(
            frappe.get_traceback(), "Attendance Correction Eligibility Error"
        )
        return False


def correct_attendance(self):
    attendance_date = getdate(self.attendance_date)

    # --- 1. Fetch existing attendance record ---
    existing_attendance_name = frappe.db.get_value(
        "Attendance",
        {
            "employee": self.employee,
            "attendance_date": attendance_date,
            "docstatus": 1,
        },
        "name",
    )

    old_in_time = None
    old_out_time = None

    # --- 2. If record exists, cancel and preserve values ---
    if existing_attendance_name:
        existing_attendance_doc = frappe.get_doc("Attendance", existing_attendance_name)
        old_in_time = existing_attendance_doc.in_time
        old_out_time = existing_attendance_doc.out_time
        existing_attendance_doc.cancel()
        existing_attendance_doc.add_comment(
            "Info",
            (
                f"Cancelled via Attendance Correction ({self.name}) | "
                f"Log: {self.log_type} | "
                f"Old: {old_in_time if self.log_type.upper() == 'IN' else old_out_time} | "
                f"New: {self.time} | "
                f"Reason: {self.reason_for_correction}"
            ),
        )
        frappe.db.commit()

    # --- 3. Prepare new values ---
    final_in_time = old_in_time
    final_out_time = old_out_time
    log_in_from = existing_attendance_doc.custom_log_in_from
    log_out_from = existing_attendance_doc.custom_log_out_from

    if self.log_type and self.time:
        time_value = get_datetime(self.time + " " + str(self.attendance_date))
        if self.log_type.upper() == "IN":
            final_in_time = time_value
        elif self.log_type.upper() == "OUT":
            final_out_time = time_value

    # --- 4. Create and submit new record ---
    new_attendance = frappe.get_doc(
        {
            "doctype": "Attendance",
            "employee": self.employee,
            "attendance_date": attendance_date,
            "status": "Present",
            "shift": self.shift,
            "in_time": final_in_time,
            "custom_log_in_from": log_in_from,
            "out_time": final_out_time,
            "custom_log_out_from": log_out_from,
        }
    )

    new_attendance.insert(ignore_permissions=True)
    new_attendance.submit()
    frappe.db.commit()
    old_time = old_in_time if self.log_type.upper() == "IN" else old_out_time

    new_attendance.add_comment(
        "Info",
        (
            f"Created via Attendance Correction ({self.name}) | "
            f"Log: {self.log_type} | "
            f"Old: {old_time} | "
            f"New: {self.time} | "
            f"Reason: {self.reason_for_correction} | "
            f"Attendance: {existing_attendance_name or 'New Attendance Record'}"
        ),
    )

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
        limit=1,
        ignore_permissions=True,  # ✅ FORCE bypass permissions
    )

    if not records:
        return {}

    doc = frappe.get_doc("Attendance", records[0].name)
    return {
        "in_time": doc.in_time,
        "out_time": doc.out_time,
    }
