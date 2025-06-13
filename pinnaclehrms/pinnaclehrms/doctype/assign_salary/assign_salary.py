# Copyright (c) 2025, OTPL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AssignSalary(Document):
    def onload(self):
        salary_history = self.salary_history[-1]
        curr_salary = salary_history.salary
        applicable_from = salary_history.from_date
        self.current_salary = curr_salary
        self.applicable_from = applicable_from
