import frappe
from datetime import datetime
from frappe.utils import getdate, flt
from functools import wraps

from hrms.utils.holiday_list import get_holiday_list_for_employee

# -------------------------------------------------------
# FUNCTION 1: Get Attendance + Overtime Context
# -------------------------------------------------------


def get_custom_attendance_context(employee, start_date, end_date):
    """Returns dictionary with attendance counts + overtime hours."""

    start_date = getdate(start_date)
    end_date = getdate(end_date)

    attendance = frappe.get_all(
        "Attendance",
        filters={
            "employee": employee,
            "attendance_date": ["between", [start_date, end_date]],
            "docstatus": 1,
        },
        fields=[
            "attendance_date",
            "status",
            "in_time",
            "out_time",
            "shift",
            "particulars",
        ],
    )

    employee_data = get_employee_payroll_context(
        employee,
        as_on=start_date,
    )

    effective_start = max(
        start_date,
        (
            getdate(employee_data.date_of_joining)
            if employee_data.date_of_joining
            else start_date
        ),
    )

    effective_end = min(
        end_date,
        (
            getdate(employee_data.relieving_date)
            if employee_data.relieving_date
            else end_date
        ),
    )

    if effective_start <= effective_end:
        holiday_count = frappe.db.count(
            "Holiday",
            filters={
                "parent": employee_data.holiday_list,
                "holiday_date": [
                    "between",
                    [effective_start, effective_end],
                ],
            },
        )
    else:
        holiday_count = 0

    # -------------------------------------------------------
    # Attendance Counts
    # -------------------------------------------------------

    full = sum(1 for d in attendance if d.particulars == "Full Day")

    sunday_working = sum(1 for d in attendance if d.particulars == "Sunday Working")

    three_fourth = sum(1 for d in attendance if d.particulars == "3/4 Day")

    sixty_five_particular = sum(
        1 for d in attendance if d.particulars == "65% Particular"
    )

    half = sum(1 for d in attendance if d.particulars == "Half Day")

    forty_particular = sum(1 for d in attendance if d.particulars == "40% Particular")

    quarter = sum(1 for d in attendance if d.particulars == "Quarter Day")

    fifteen_particular = sum(1 for d in attendance if d.particulars == "15% Particular")

    absent = sum(1 for d in attendance if d.particulars == "Absent")

    late_early = sum(1 for d in attendance if d.particulars == "Late/Early")

    late_and_early = sum(1 for d in attendance if d.particulars == "Late & Early")

    # -------------------------------------------------------
    # POINT-BASED LATE GRACE LOGIC
    # -------------------------------------------------------

    hr_settings = frappe.get_single("HR Settings")

    allowed_points = hr_settings.allowed_lates or 0

    remaining_points = allowed_points

    adjusted_late_early = 0
    adjusted_late_and_early = 0

    grace_full_days = 0

    # Late & Early = cost 2 points
    for _ in range(late_and_early):

        if remaining_points >= 2:
            remaining_points -= 2
            grace_full_days += 1

        else:
            adjusted_late_and_early += 1

    # Late/Early = cost 1 point
    for _ in range(late_early):

        if remaining_points >= 1:
            remaining_points -= 1
            grace_full_days += 1

        else:
            adjusted_late_early += 1

    # -------------------------------------------------------
    # Overtime Calculation
    # -------------------------------------------------------

    total_overtime = 0.0

    for att in attendance:

        if not att.in_time or not att.out_time or not att.shift:
            continue

        try:
            shift = frappe.get_cached_doc(
                "Shift Type",
                att.shift,
            )

            shift_start = datetime.combine(
                att.in_time.date(),
                shift.start_time,
            )

            shift_end = datetime.combine(
                att.in_time.date(),
                shift.end_time,
            )

            shift_hours = (shift_end - shift_start).total_seconds() / 3600

            actual_hours = (att.out_time - att.in_time).total_seconds() / 3600

            overtime = max(
                0,
                actual_hours - shift_hours,
            )

            total_overtime += overtime

        except Exception:
            pass

    # -------------------------------------------------------
    # Present Count
    # -------------------------------------------------------

    present = (
        full
        + holiday_count
        + sunday_working
        + grace_full_days
        + adjusted_late_early
        + adjusted_late_and_early
        + three_fourth
        + sixty_five_particular
        + half
        + forty_particular
        + quarter
        + fifteen_particular
    )

    # -------------------------------------------------------
    # Fraction-Based Present Day Calculation
    # -------------------------------------------------------

    fraction_total = (
        (full + holiday_count + grace_full_days) * 1
        + sunday_working * 1
        + adjusted_late_early * 0.90
        + adjusted_late_and_early * 0.80
        + three_fourth * 0.75
        + sixty_five_particular * 0.65
        + half * 0.50
        + forty_particular * 0.40
        + quarter * 0.25
        + fifteen_particular * 0.15
    )

    frappe.logger().info(
        f"Custom attendance context: "
        f"employee={employee}, "
        f"start_date={start_date}, "
        f"end_date={end_date}, "
        f"present={present}, "
        f"fraction_total={fraction_total}, "
        f"holiday_count={holiday_count}, "
        f"overtime={total_overtime}"
    )

    # -------------------------------------------------------
    # Return All Variables
    # -------------------------------------------------------

    return {
        "full_day_count": (full + holiday_count + grace_full_days),
        "sunday_working_count": sunday_working,
        "three_fourth_day_count": three_fourth,
        "sixty_five_particular_count": sixty_five_particular,
        "half_day_count": half,
        "forty_particular_count": forty_particular,
        "quarter_day_count": quarter,
        "fifteen_particular_count": fifteen_particular,
        "absent_day_count": absent,
        "late_early_count": adjusted_late_early,
        "late_and_early_count": adjusted_late_and_early,
        "present_day_count": present,
        "fractional_total_days": fraction_total,
        "total_attendance_records": len(attendance),
        "overtime_hours": total_overtime,
    }


# -------------------------------------------------------
# FUNCTION 2: Push Variables into Salary Slip Context
# -------------------------------------------------------


def apply_custom_attendance_to_context(
    self,
    data,
    default_data,
):
    """Inject custom attendance values into Salary Slip calculation context."""

    ctx = get_custom_attendance_context(
        employee=self.employee,
        start_date=self.start_date,
        end_date=self.end_date,
    )

    for key, value in ctx.items():
        data[key] = value
        default_data[key] = value

    # Populate breakup table
    populate_salary_breakup_table(
        self,
        ctx,
    )


# -------------------------------------------------------
# FUNCTION 3: Populate Salary Slip Child Table
# -------------------------------------------------------


def populate_salary_breakup_table(self, ctx):
    """Populate Salary Slip 'salary_breakup' child table."""

    # Clear table
    self.set(
        "salary_breakup",
        [],
    )

    # ---------------------------------------------------
    # GET BASE FROM SALARY STRUCTURE ASSIGNMENT
    # ---------------------------------------------------

    base = 0

    try:

        salary_structure_assignment_name = frappe.db.get_value(
            "Salary Structure Assignment",
            {
                "employee": self.employee,
                "salary_structure": self.salary_structure,
                "docstatus": 1,
            },
            "name",
            order_by="from_date desc",
        )

        if salary_structure_assignment_name:

            salary_structure_assignment = frappe.get_doc(
                "Salary Structure Assignment",
                salary_structure_assignment_name,
            )

            base = flt(salary_structure_assignment.base)

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "Failed to fetch Salary Structure Assignment Base",
        )

    # ---------------------------------------------------
    # PER DAY RATE
    # ---------------------------------------------------

    rate = 0

    try:

        if base and self.total_working_days:
            rate = base / self.total_working_days

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "Failed to calculate per day rate",
        )

    # ---------------------------------------------------
    # BREAKUP ROWS
    # ---------------------------------------------------

    rows = [
        (
            "Full Day",
            ctx["full_day_count"],
            100,
        ),
        (
            "Sunday Working",
            ctx["sunday_working_count"],
            100,
        ),
        (
            "Late/Early",
            ctx["late_early_count"],
            90,
        ),
        (
            "Late & Early",
            ctx["late_and_early_count"],
            80,
        ),
        (
            "3/4 Day",
            ctx["three_fourth_day_count"],
            75,
        ),
        (
            "65% Particular",
            ctx["sixty_five_particular_count"],
            65,
        ),
        (
            "Half Day",
            ctx["half_day_count"],
            50,
        ),
        (
            "40% Particular",
            ctx["forty_particular_count"],
            40,
        ),
        (
            "Quarter Day",
            ctx["quarter_day_count"],
            25,
        ),
        (
            "15% Particular",
            ctx["fifteen_particular_count"],
            15,
        ),
        (
            "Absent",
            ctx["absent_day_count"],
            0,
        ),
        (
            "Overtime Hours",
            ctx["overtime_hours"],
            0,
        ),
    ]

    # ---------------------------------------------------
    # APPEND ROWS
    # ---------------------------------------------------

    for label, days, percentage in rows:

        if not days:
            continue

        amount = 0

        if percentage > 0:
            amount = days * rate * (percentage / 100)

        self.append(
            "salary_breakup",
            {
                "particulars": label,
                "days": days,
                "rate": rate,
                "effective_percentage": percentage,
                "amount": amount,
            },
        )


# -------------------------------------------------------
# FUNCTION 4: Override get_data_for_eval
# -------------------------------------------------------


def custom_get_data_for_eval(original):
    """Wrapper around standard Salary Slip get_data_for_eval."""

    @wraps(original)
    def wrapper(self, *args, **kwargs):

        # Run original HRMS logic
        data, default_data = original(
            self,
            *args,
            **kwargs,
        )

        # Inject custom attendance context
        apply_custom_attendance_to_context(
            self,
            data,
            default_data,
        )

        frappe.logger().info(
            "Custom attendance context applied " f"to Salary Slip {self.name}."
        )

        return data, default_data

    return wrapper


# -------------------------------------------------------
# FUNCTION 5: Get Employee Payroll Context
# -------------------------------------------------------


def get_employee_payroll_context(
    employee,
    as_on=None,
):
    """
    Return employee payroll information along with
    the applicable Holiday List.

    Holiday List is resolved for the supplied `as_on` date.
    """

    as_on = getdate(as_on) if as_on else getdate()

    employee_data = frappe.db.get_value(
        "Employee",
        employee,
        [
            "name",
            "employee_name",
            "company",
            "date_of_joining",
            "relieving_date",
        ],
        as_dict=True,
    )

    if not employee_data:

        frappe.throw(f"Employee {employee} does not exist.")

    holiday_list = get_holiday_list_for_employee(
        employee,
        raise_exception=True,
        as_on=as_on,
    )

    employee_data.holiday_list = holiday_list

    return employee_data


# -------------------------------------------------------
# FUNCTION 6: Set Current Payroll Period
# -------------------------------------------------------


def custom_set_evaluated_components(original):
    """
    Store the CURRENT Salary Slip payroll period before
    Salary Structure Assignment components are evaluated.

    Salary Structure Assignment evaluation happens before
    Salary Slip.get_data_for_eval() injects custom attendance
    variables.

    Therefore, frappe.flags is used to pass the current
    Salary Slip period into the SSA evaluation context.
    """

    @wraps(original)
    def wrapper(self, *args, **kwargs):

        # -------------------------------------------------
        # Store CURRENT Salary Slip period
        # -------------------------------------------------

        frappe.flags.custom_payroll_period = (
            getdate(self.start_date),
            getdate(self.end_date),
        )

        frappe.logger().info(
            "Custom payroll period set: "
            f"employee={self.employee}, "
            f"start_date={self.start_date}, "
            f"end_date={self.end_date}"
        )

        try:

            # ---------------------------------------------
            # Let standard HRMS evaluate components
            # ---------------------------------------------

            return original(
                self,
                *args,
                **kwargs,
            )

        finally:

            # ---------------------------------------------
            # Always clear the flag
            # ---------------------------------------------

            frappe.flags.custom_payroll_period = None

            frappe.logger().info("Custom payroll period cleared.")

    return wrapper


# -------------------------------------------------------
# FUNCTION 7: Apply Salary Slip Override
# -------------------------------------------------------


def apply_salary_slip_override():
    """Hook to activate Salary Slip overrides."""

    from hrms.payroll.doctype.salary_slip.salary_slip import (
        SalarySlip,
    )

    # ---------------------------------------------------
    # Override get_data_for_eval
    # ---------------------------------------------------

    SalarySlip.get_data_for_eval = custom_get_data_for_eval(
        SalarySlip.get_data_for_eval
    )

    # ---------------------------------------------------
    # Override _set_evaluated_components
    #
    # This is IMPORTANT.
    #
    # It sets the current Salary Slip period BEFORE
    # Salary Structure Assignment evaluates components.
    # ---------------------------------------------------

    SalarySlip._set_evaluated_components = custom_set_evaluated_components(
        SalarySlip._set_evaluated_components
    )

    frappe.logger().info("✅ Custom Salary Slip overrides enabled.")


# -------------------------------------------------------
# Auto-run Override on Import
# -------------------------------------------------------

try:

    apply_salary_slip_override()

    frappe.logger().info("🔥 Salary Slip override auto-loaded at import.")

except Exception as e:

    frappe.logger().error(f"❌ Failed to load Salary Slip override: {e}")
