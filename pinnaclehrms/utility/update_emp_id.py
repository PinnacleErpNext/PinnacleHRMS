import frappe
from hrms.hr.doctype.attendance.attendance import Attendance

def custom_before_save(self, method):
    if self.employee is None:
        empId = frappe.db.get_value('Attendance Device ID Allotment', {'device_id': self.custom_attendance_device_id}, 'parent')
        if(empId is None):
            empId = frappe.db.get_value('Employee', {'attendance_device_id': self.custom_attendance_device_id}, 'employee')
    
        self.employee = empId
