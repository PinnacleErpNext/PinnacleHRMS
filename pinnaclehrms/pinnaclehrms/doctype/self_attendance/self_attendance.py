# Copyright (c) 2025, OTPL and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate
from frappe.model.document import Document

class SelfAttendance(Document):
    pass

@frappe.whitelist(allow_guest=True)
def mark_self_attendance(doc_id):
    try:
        # Fetch the Self Attendance document
        doc = frappe.get_doc("Self Attendance", doc_id)

        # Ensure mandatory fields are present
        if not doc.employee or not doc.check_in or not doc.check_out:
            frappe.throw("Employee, Check In, and Check Out are required to mark attendance.")

        # Extract date from Check-in
        attendance_date = getdate(doc.check_in)

        # Check if attendance already exists for this employee on the same date
        existing_attendance = frappe.db.exists(
            "Attendance",
            {
                "employee": doc.employee,
                "attendance_date": attendance_date
            }
        )

        if existing_attendance:
            return {"status": "Conflicted", "attendance": existing_attendance}  

        # Create Attendance record
        attendance_doc = frappe.get_doc({
            "doctype": "Attendance",
            "employee": doc.employee,
            "shift": doc.shift,
            "attendance_date": attendance_date,
            "in_time": doc.check_in,
            "out_time": doc.check_out
        })

        attendance_doc.insert(ignore_permissions=True)
        frappe.db.commit()  # Commit after inserting the document

        return {"status": "Attendance Marked", "attendance": attendance_doc.name}  

    except Exception as e:
        # Log the error for debugging
        frappe.log_error(message=str(e), title="mark_self_attendance Error")
        frappe.throw(f"An error occurred while marking attendance: {str(e)}")
