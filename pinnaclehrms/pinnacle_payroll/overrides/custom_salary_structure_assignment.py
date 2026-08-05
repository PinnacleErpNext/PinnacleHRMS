import frappe
from frappe.utils import date_diff

from hrms.payroll.utils import get_component_eval_context
from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
    SalaryStructureAssignment,
)
from pinnaclehrms.pinnacle_payroll.overrides.custom_salary_slip import (
    get_custom_attendance_context,
)


def _custom_get_component_eval_context(self):
    from hrms.payroll.doctype.payroll_entry.payroll_entry import get_start_end_dates

    data = get_component_eval_context(self.employee, self.as_dict())

    frequency = frappe.get_cached_value(
        "Salary Structure",
        self.salary_structure,
        "payroll_frequency",
    )

    dates = get_start_end_dates(
        frequency,
        self.from_date,
        self.company,
    )

    period_days = date_diff(dates.end_date, dates.start_date) + 1

    data.start_date = dates.start_date
    data.end_date = dates.end_date
    data.payment_days = period_days
    data.total_working_days = period_days
    data.leave_without_pay = 0
    data.absent_days = 0
    data.unmarked_days = 0

    ctx = get_custom_attendance_context(
        employee=self.employee,
        start_date=dates.start_date,
        end_date=dates.end_date,
    )

    data.update(ctx)

    return data


# Monkey patch
SalaryStructureAssignment._get_component_eval_context = (
    _custom_get_component_eval_context
)
