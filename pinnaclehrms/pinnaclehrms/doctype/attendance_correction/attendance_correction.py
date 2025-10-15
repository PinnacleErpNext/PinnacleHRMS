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
        frappe.db.commit()

    # --- 3. Prepare new values ---
    final_in_time = old_in_time
    final_out_time = old_out_time

    if self.log_type and self.time:
        time_value = get_datetime(self.time)
        if self.log_type.upper() == "IN":
            final_in_time = time_value
        elif self.log_type.upper() == "OUT":
            final_out_time = time_value

    # --- 4. Create and submit new record ---
    new_attendance = frappe.get_doc({
        "doctype": "Attendance",
        "employee": self.employee,
        "attendance_date": attendance_date,
        "status": "Present",
        "shift": self.shift,
        "in_time": final_in_time,
        "out_time": final_out_time,
    })

    new_attendance.insert(ignore_permissions=True)
    new_attendance.submit()
    frappe.db.commit()

    return new_attendance.name
