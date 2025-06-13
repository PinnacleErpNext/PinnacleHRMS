# Copyright (c) 2024, mygstcafe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from collections import defaultdict
from pinnaclehrms.utility.salary_calculator import createPaySlips


class CreatePaySlips(Document):
    def autoname(self):
        if self.genrate_for_all:
            self.name = f"For-all-pay-slip-{self.year}-{self.month}"

    def before_save(self):
        data = {}
        year = self.year
        month = int(self.month) if self.month else None
        employee_list = []

        if not year or not month:
            frappe.throw("Select year and month")

        data["year"] = year
        data["month"] = month

        autoCalculateLeaveEncashment = self.auto_calculate_leave_encashment
        lates = self.allowed_lates
        generateForAll = self.genrate_for_all

        data["auto_calculate_leave_encashment"] = autoCalculateLeaveEncashment
        data["allowed_lates"] = lates
        data["generate_for_all"] = generateForAll

        if not generateForAll:
            if not self.select_company and not self.employee_list:
                frappe.throw("Please Select Company or Employee!")

            if self.select_company:
                company = self.select_company
                data["select_company"] = company

            # if self.select_employee:
            #     employee = self.select_employee
            #     data["select_employee"] = employee

            if self.employee_list:
                for employee in self.employee_list:
                    employee_list.append(employee.select_employee)
                data["employee_list"] = employee_list

        createPaySlips(data)

    def on_trash(self):
        for pay_slip in self.created_pay_slips:
            exist = frappe.db.exists("Pay Slips", pay_slip.pay_slip)
            if exist:
                doc = frappe.get_doc("Pay Slips", pay_slip.pay_slip)
                doc.delete()

    # def on_submit(self):
    #     self.add_regenrate_button = 0
    #     pay_slip_list = self.created_pay_slips

    #     for item in pay_slip_list:
    #         docname = item.pay_slip
    #         pay_slip = frappe.get_doc("Pay Slips", docname)

    #         pay_slip.submit()
