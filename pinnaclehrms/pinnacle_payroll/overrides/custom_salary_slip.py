import frappe
from datetime import datetime
from functools import wraps
from frappe.utils import flt


# -------------------------------------------------------
# 🔥 FUNCTION 1: Get Attendance + Overtime Context
# -------------------------------------------------------
def get_custom_attendance_context(employee, start_date, end_date):
    """Returns dictionary with attendance counts + overtime hours."""

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
    print(len(attendance))
    for d in attendance:
        print(
            f"attendance={d.attendance_date}, particulars={d.particulars}, in_time={d.in_time}, out_time={d.out_time}, shift={d.shift}"
        )

    holiday_list = frappe.get_value("Employee", employee, "holiday_list")

    holidays = frappe.db.sql(
        """
        SELECT COUNT(holiday_date) as total_holidays
        FROM `tabHoliday`
        WHERE holiday_date BETWEEN %s AND %s
        AND parent = %s
    """,
        (start_date, end_date, holiday_list),
        as_dict=True,
    )

    holiday_count = holidays[0].total_holidays if holidays else 0

    full = sum(1 for d in attendance if d.particulars == "Full Day")
    sunday_working = sum(1 for d in attendance if d.particulars == "Sunday Working")
    half = sum(1 for d in attendance if d.particulars == "Half Day")
    three_fourth = sum(1 for d in attendance if d.particulars == "3/4 Day")
    quarter = sum(1 for d in attendance if d.particulars == "Quarter Day")
    absent = sum(1 for d in attendance if d.particulars == "Absent")

    late = sum(1 for d in attendance if d.particulars == "Late")
    late_early = sum(1 for d in attendance if d.particulars == "Late/Early")
    late_and_early = sum(1 for d in attendance if d.particulars == "Late & Early")

    print(
        f"full={full}, holiday_count={holiday_count}, sunday_working={sunday_working}, half={half}, three_fourth={three_fourth}, quarter={quarter}, absent={absent}, late={late}, late_early={late_early}, late_and_early={late_and_early}"
    )

    # -------------------------------------------------------
    # 🔥 POINT-BASED LATE GRACE LOGIC (UPDATED)
    # -------------------------------------------------------
    hr_settings = frappe.get_single("HR Settings")
    allowed_points = hr_settings.allowed_lates or 0

    remaining_points = allowed_points

    adjusted_late_early = 0
    adjusted_late_and_early = 0

    grace_full_days = 0

    # Consume points for Late & Early (cost = 2)
    for _ in range(late_and_early):
        if remaining_points >= 2:
            remaining_points -= 2
            grace_full_days += 1
        else:
            adjusted_late_and_early += 1

    # Consume points for Late/Early (cost = 1)
    for _ in range(late_early):
        if remaining_points >= 1:
            remaining_points -= 1
            grace_full_days += 1
        else:
            adjusted_late_early += 1

    # -------------------------------------------------------
    # 🔥 Correct Overtime Calculation
    # -------------------------------------------------------
    total_overtime = 0.0

    for att in attendance:
        if not att.in_time or not att.out_time or not att.shift:
            continue

        try:
            shift = frappe.get_cached_doc("Shift Type", att.shift)

            shift_start = datetime.combine(att.in_time.date(), shift.start_time)
            shift_end = datetime.combine(att.in_time.date(), shift.end_time)

            shift_hours = (shift_end - shift_start).total_seconds() / 3600
            actual_hours = (att.out_time - att.in_time).total_seconds() / 3600

            overtime = max(0, actual_hours - shift_hours)
            total_overtime += overtime

        except Exception:
            pass
    present = (
        full
        + holiday_count
        + sunday_working
        + grace_full_days
        + adjusted_late_early
        + adjusted_late_and_early
        + half
        + three_fourth
        + quarter
    )
    # -------------------------------------------------------
    # 🔥 Fraction-based present day calculation
    # -------------------------------------------------------
    fraction_total = (
        (full + holiday_count + grace_full_days) * 1
        + sunday_working * 1
        + three_fourth * 0.75
        + half * 0.50
        + quarter * 0.25
        + adjusted_late_early * 0.90
        + adjusted_late_and_early * 0.80
    )
    print(
        f"present={present}, fraction_total={fraction_total}, total_overtime={total_overtime}"
    )
    # -------------------------------------------------------
    # RETURN ALL VARIABLES
    # -------------------------------------------------------
    return {
        "full_day_count": full + holiday_count + grace_full_days,
        "sunday_working_count": sunday_working,
        "three_fourth_day_count": three_fourth,
        "half_day_count": half,
        "quarter_day_count": quarter,
        "absent_day_count": absent,
        "late_day_count": late,  # unchanged
        "late_early_count": adjusted_late_early,  # UPDATED
        "late_and_early_count": adjusted_late_and_early,  # UPDATED
        "present_day_count": present,
        "fractional_total_days": fraction_total,
        "total_attendance_records": len(attendance),
        "overtime_hours": total_overtime,
    }


# -------------------------------------------------------
# 🔥 FUNCTION 2: Push Variables into Salary Slip Context
# -------------------------------------------------------
def apply_custom_attendance_to_context(self, data, default_data):
    """Inject custom attendance values into Salary Slip calculation context."""

    ctx = get_custom_attendance_context(
        employee=self.employee,
        start_date=self.start_date,
        end_date=self.end_date,
    )
    # frappe.throw(str(ctx))
    for key, value in ctx.items():
        data[key] = value
        default_data[key] = value

    # ALSO populate breakup table
    populate_salary_breakup_table(self, ctx)


# -------------------------------------------------------
# 🔥 FUNCTION 3: Populate Salary Slip Child Table
# -------------------------------------------------------
def populate_salary_breakup_table(self, ctx):
    """Populate Salary Slip 'salary_breakup' child table with new structure."""

    print("Populating salary breakup table with attendance context...")

    # Clear existing table
    self.set("salary_breakup", [])

    # ------------------------------------------
    # GET BASE FROM SALARY STRUCTURE ASSIGNMENT
    # ------------------------------------------
    base = 0

    try:
        # Fetch Salary Structure Assignment using
        # employee + salary structure
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

            print(f"Salary Structure Assignment: {salary_structure_assignment.name}")

            # Fetch base salary
            base = flt(salary_structure_assignment.base)

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Failed to fetch Salary Structure Assignment Base",
        )

    print(f"Base Salary: {base}")
    print(f"Total Working Days: {self.total_working_days}")

    # ------------------------------------------
    # CALCULATE PER DAY RATE
    # ------------------------------------------
    rate = 0

    try:
        if base and self.total_working_days:
            rate = base / self.total_working_days
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Failed to calculate per day rate",
        )

    print(f"Per Day Rate: {rate}")

    # ------------------------------------------
    # BREAKUP ROWS
    # ------------------------------------------
    rows = [
        ("Full Day", ctx["full_day_count"], 100),
        ("Sunday Working", ctx["sunday_working_count"], 100),
        ("3/4 Day", ctx["three_fourth_day_count"], 75),
        ("Half Day", ctx["half_day_count"], 50),
        ("Quarter Day", ctx["quarter_day_count"], 25),
        ("Absent", ctx["absent_day_count"], 0),
        ("Late/Early", ctx["late_early_count"], 90),
        ("Late & Early", ctx["late_and_early_count"], 80),
        ("Overtime Hours", ctx["overtime_hours"], 0),
    ]

    # ------------------------------------------
    # APPEND ROWS
    # ------------------------------------------
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
# 🔥 FUNCTION 4: Clean Override of get_data_for_eval
# -------------------------------------------------------
def custom_get_data_for_eval(original):
    """Wrapper around ERPNext's get_data_for_eval to inject attendance variables."""

    @wraps(original)
    def wrapper(self, *args, **kwargs):

        # Run original ERPNext logic
        data, default_data = original(self, *args, **kwargs)

        # Inject custom attendance variables afterward
        apply_custom_attendance_to_context(self, data, default_data)

        frappe.logger().info("Custom attendance context applied to Salary Slip.")

        return data, default_data

    return wrapper


# -------------------------------------------------------
# 🔥 Apply Monkey-Patch Override
# -------------------------------------------------------
def apply_salary_slip_override():
    """Hook to activate override; add in hooks.py"""

    from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip

    SalarySlip.get_data_for_eval = custom_get_data_for_eval(
        SalarySlip.get_data_for_eval
    )

    frappe.logger().info("✅ Custom Salary Slip get_data_for_eval override enabled.")


# -------------------------------------------------------
# 🔥 Auto-run override on import
# -------------------------------------------------------
try:
    apply_salary_slip_override()
    frappe.logger().info("🔥 Salary Slip override auto-loaded at import.")
except Exception as e:
    frappe.logger().error(f"❌ Failed to load Salary Slip override: {e}")
