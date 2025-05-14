import frappe
from hrms.hr.doctype.attendance.attendance import Attendance


def custom_before_save(self, method):
    if self.employee is None:
        empId = frappe.db.get_value(
            "Attendance Device ID Allotment",
            {
                "device_id": self.custom_attendance_device_id,
                "device": self.custom_attendance_device,
            },
            "parent",
        )
        if empId is None:
            empId = frappe.db.get_value(
                "Employee",
                {"attendance_device_id": self.custom_attendance_device_id},
                "employee",
            )
        d_shift, company = frappe.db.get_value(
            "Employee", empId, ["default_shift", "company"]
        )
        self.employee = empId
        self.shift = d_shift
        self.company = company
