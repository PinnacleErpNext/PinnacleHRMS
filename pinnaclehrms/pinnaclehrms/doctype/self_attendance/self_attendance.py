# Copyright (c) 2025, OTPL and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate
from frappe.model.document import Document

class SelfAttendance(Document):
    pass

@frappe.whitelist(allow_guest=True)
def approve_self_attendance(doc_id):
    try:
        # Fetch the Self Attendance document
        doc = frappe.get_doc("Self Attendance", doc_id)
        
        # Ensure mandatory fields are present
        if not doc.employee or not doc.check_in or not doc.check_out:
            frappe.throw("Employee, Check In, and Check Out are required to mark attendance.")

        # Extract date from Check-in
        attendance_date = getdate(doc.check_in)
        
        # Check if attendance already exists for this employee on the same date
        attendance_exists = frappe.db.exists(
            "Attendance",
            {
                "employee": doc.employee,
                "attendance_date": attendance_date
            }
        )
        
        if attendance_exists:
            return {"status":"Conflicted"}  

        # Create Check-in record
        checkin_doc = frappe.get_doc({
            "doctype": "Employee Checkin",
            "employee": doc.employee,
            "shift": doc.shift,
            "log_type": "IN",
            "time": doc.check_in
        })
        checkin_doc.insert(ignore_permissions=True)

        # Create Check-out record
        checkout_doc = frappe.get_doc({
            "doctype": "Employee Checkin",
            "employee": doc.employee,
            "shift": doc.shift,
            "log_type": "OUT",
            "time": doc.check_out
        })
        checkout_doc.insert(ignore_permissions=True)

        frappe.db.commit()
        return {"status":"Approved"}  # Successfully marked attendance

    except Exception as e:
        # Log the error for debugging
        frappe.log_error(message=str(e), title="mark_attendance Error")
        # Raise a user-friendly error message
        frappe.throw("An error occurred while marking attendance: " + str(e))
