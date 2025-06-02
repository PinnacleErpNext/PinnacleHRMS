import frappe
from hrms.hr.doctype.attendance.attendance import Attendance
from datetime import datetime
from frappe import _


def custom_before_save(self, method):
    # Determine employee based on custom device mapping or directly from field
    if not self.employee:
        empId = frappe.db.get_value(
            "Attendance Device ID Allotment",
            {
                "device_id": self.custom_attendance_device_id,
                "device": self.custom_attendance_device,
            },
            "parent",
        )
        
        if not empId:
            frappe.throw(_("Employee could not be identified from device details."))
    else:   
        empId = self.employee

    # Fetch shift and company info
    d_shift, company = frappe.db.get_value(
        "Employee", empId, ["default_shift", "company"]
    )
    self.employee = empId
    self.shift = d_shift
    self.company = company

    # Ensure in_time and out_time are combined properly with date
    if self.attendance_date:
        if self.in_time:
            if isinstance(self.in_time, datetime):
                check_in = self.in_time.time()
            else:
                check_in = datetime.strptime(str(self.in_time), "%H:%M:%S").time()
            self.in_time = datetime.combine(self.attendance_date, check_in)

        if self.out_time:
            if isinstance(self.out_time, datetime):
                check_out = self.out_time.time()
            else:
                check_out = datetime.strptime(str(self.out_time), "%H:%M:%S").time()
            self.out_time = datetime.combine(self.attendance_date, check_out)

        # Set status
        if not self.in_time or not self.out_time:
            self.status = "Absent"
