import frappe

from frappe.utils import date_diff, getdate

from hrms.payroll.utils import get_component_eval_context
from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
    SalaryStructureAssignment,
)
from hrms.payroll.doctype.payroll_entry.payroll_entry import (
    get_start_end_dates,
)

from pinnaclehrms.pinnacle_payroll.overrides.custom_salary_slip import (
    get_custom_attendance_context,
)


def _custom_get_component_eval_context(self):
    """
    Build Salary Structure Assignment evaluation context.

    Two situations are supported:

    1. Salary Structure Assignment is being saved:
       Use the Salary Structure payroll frequency and
       Salary Structure Assignment.from_date.

    2. Salary Slip is calculating salary:
       Use the current payroll period supplied through
       frappe.flags.custom_payroll_period.
    """

    # ---------------------------------------------------------
    # Standard HRMS evaluation context
    # ---------------------------------------------------------

    data = get_component_eval_context(
        self.employee,
        self.as_dict(),
    )

    # ---------------------------------------------------------
    # Check whether Salary Slip supplied the CURRENT
    # payroll period.
    # ---------------------------------------------------------

    payroll_period = getattr(
        frappe.flags,
        "custom_payroll_period",
        None,
    )

    # ---------------------------------------------------------
    # CASE 1:
    # Salary Slip / Payroll Entry is evaluating components.
    #
    # Use the actual CURRENT payroll period.
    # ---------------------------------------------------------

    if payroll_period:
        start_date, end_date = payroll_period

        start_date = getdate(start_date)
        end_date = getdate(end_date)

    # ---------------------------------------------------------
    # CASE 2:
    # Salary Structure Assignment itself is being saved.
    #
    # There is no Salary Slip period available.
    #
    # Therefore use the standard HRMS mechanism to determine
    # the salary period.
    # ---------------------------------------------------------

    else:
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

        start_date = getdate(dates.start_date)
        end_date = getdate(dates.end_date)

    # ---------------------------------------------------------
    # Number of days in evaluation period
    # ---------------------------------------------------------

    period_days = (
        date_diff(
            end_date,
            start_date,
        )
        + 1
    )

    # ---------------------------------------------------------
    # Always provide variables required by Salary Structure
    # formulas.
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
    # Custom attendance context
    #
    # This is useful both when evaluating the SSA and when
    # evaluating components during Salary Slip calculation.
    # ---------------------------------------------------------

    ctx = get_custom_attendance_context(
        employee=self.employee,
        start_date=start_date,
        end_date=end_date,
    )

    # ---------------------------------------------------------
    # Merge custom variables
    # ---------------------------------------------------------

    data.update(ctx)

    return data


# ---------------------------------------------------------
# Monkey Patch
# ---------------------------------------------------------

SalaryStructureAssignment._get_component_eval_context = (
    _custom_get_component_eval_context
)
