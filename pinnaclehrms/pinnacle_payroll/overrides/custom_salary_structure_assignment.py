import frappe
from frappe.utils import date_diff, getdate

from hrms.payroll.utils import get_component_eval_context
from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
    SalaryStructureAssignment,
)

from pinnaclehrms.pinnacle_payroll.overrides.custom_salary_slip import (
    get_custom_attendance_context,
)


def _custom_get_component_eval_context(self):
    """
    Build Salary Structure Assignment evaluation context.

    IMPORTANT:
    Attendance/payroll calculations must use the CURRENT
    Salary Slip / Payroll Entry period.

    Do NOT use self.from_date here because self.from_date
    represents the Salary Structure Assignment effective date,
    not the current payroll period.
    """

    # ---------------------------------------------------------
    # Get standard salary component evaluation context
    # ---------------------------------------------------------
    data = get_component_eval_context(
        self.employee,
        self.as_dict(),
    )

    # ---------------------------------------------------------
    # Get CURRENT payroll period
    #
    # This is populated by the Salary Slip override before
    # Salary Structure Assignment components are evaluated.
    # ---------------------------------------------------------
    payroll_period = getattr(
        frappe.flags,
        "custom_payroll_period",
        None,
    )

    # ---------------------------------------------------------
    # Safety fallback
    #
    # If this method is called outside Salary Slip calculation,
    # don't attempt custom attendance calculation using
    # Salary Structure Assignment.from_date.
    # ---------------------------------------------------------
    if not payroll_period:
        return data

    start_date, end_date = payroll_period

    start_date = getdate(start_date)
    end_date = getdate(end_date)

    # ---------------------------------------------------------
    # Number of days in CURRENT payroll period
    # ---------------------------------------------------------
    period_days = (
        date_diff(
            end_date,
            start_date,
        )
        + 1
    )

    # ---------------------------------------------------------
    # Add payroll-period variables to evaluation context
    #
    # Use dictionary keys explicitly because these values are
    # consumed by salary structure formulas.
    # ---------------------------------------------------------
    data.update(
        {
            "start_date": start_date,
            "end_date": end_date,
            "payment_days": period_days,
            "total_working_days": period_days,
            "leave_without_pay": 0,
            "absent_days": 0,
            "unmarked_days": 0,
        }
    )

    # ---------------------------------------------------------
    # Get custom attendance context
    #
    # IMPORTANT:
    # Use CURRENT payroll period, NOT Salary Structure
    # Assignment.from_date.
    # ---------------------------------------------------------
    ctx = get_custom_attendance_context(
        employee=self.employee,
        start_date=start_date,
        end_date=end_date,
    )

    # ---------------------------------------------------------
    # Merge custom attendance variables
    # ---------------------------------------------------------
    data.update(ctx)

    return data


# ---------------------------------------------------------
# Monkey Patch
# ---------------------------------------------------------

SalaryStructureAssignment._get_component_eval_context = (
    _custom_get_component_eval_context
)
