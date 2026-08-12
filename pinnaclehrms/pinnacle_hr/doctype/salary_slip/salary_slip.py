import frappe

from frappe.utils import (
    add_months,
    get_first_day,
    get_last_day,
    formatdate,
    now_datetime,
    get_datetime,
)

# ==========================================================
# CONFIGURATION
# ==========================================================

LATE_ACKNOWLEDGMENT_THRESHOLD = 14
LATE_HIGH_ALERT_THRESHOLD = 20

LATE_EARLY_STATUSES = [
    "Late/Early",
    "Late & Early",
]

LATE_START_TIME = "10:30:00"
LATE_END_TIME = "11:00:00"


# ==========================================================
# CURRENT USER EMPLOYEE
# ==========================================================


def get_employee_for_current_user():
    """
    Return Employee linked with the logged-in user.
    """

    return frappe.db.get_value(
        "Employee",
        {
            "user_id": frappe.session.user,
        },
        "name",
    )


# ==========================================================
# VALIDATE SALARY SLIP EMPLOYEE
# ==========================================================


def validate_salary_slip_employee(salary_slip):
    """
    Make sure the logged-in user is the employee
    associated with the Salary Slip.
    """

    salary_slip_doc = frappe.get_doc(
        "Salary Slip",
        salary_slip,
    )

    employee = get_employee_for_current_user()

    if not employee:
        frappe.throw("No Employee record is linked with your user.")

    if salary_slip_doc.employee != employee:
        frappe.throw("You are not authorized to access this Salary Slip.")

    return salary_slip_doc, employee


# ==========================================================
# PREVIOUS ATTENDANCE PERIOD
# ==========================================================


def get_previous_month_period(salary_slip):
    """
    Calculate the attendance period.

    Example:

    Salary Slip:
        01-07-2026 to 31-07-2026

    Attendance period:
        01-06-2026 to 31-07-2026
    """

    salary_slip_doc = frappe.get_doc(
        "Salary Slip",
        salary_slip,
    )

    previous_month = add_months(
        salary_slip_doc.start_date,
        -1,
    )

    previous_month_start = get_first_day(previous_month)

    previous_month_end = get_last_day(salary_slip_doc.end_date)

    return (
        previous_month_start,
        previous_month_end,
    )


# ==========================================================
# CHECK IN-TIME
# ==========================================================


def is_late_in_time(in_time):
    """
    Return True only when:

        in_time > 10:30 AM
        AND
        in_time < 11:00 AM

    Boundaries are intentionally strict.

    10:30 AM  -> NOT counted
    10:31 AM  -> counted
    10:59 AM  -> counted
    11:00 AM  -> NOT counted
    """

    if not in_time:
        return False

    try:
        attendance_datetime = get_datetime(in_time)

        if not attendance_datetime:
            return False

        attendance_time = attendance_datetime.time()

        start_time = get_datetime(f"2000-01-01 {LATE_START_TIME}").time()

        end_time = get_datetime(f"2000-01-01 {LATE_END_TIME}").time()

        return attendance_time > start_time and attendance_time < end_time

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Late Attendance Time Parsing Error",
        )

        return False


# ==========================================================
# GET LATE ATTENDANCE DATA
# ==========================================================


def get_late_early_attendance_data(
    employee,
    salary_slip,
):
    """
    Fetch relevant Attendance records first.

    Only Attendance records having:

        Late/Early
        OR
        Late & Early

    are fetched.

    The actual in_time comparison is then performed
    in Python.

    Counted record:

        in_time > 10:30 AM
        AND
        in_time < 11:00 AM
    """

    (
        attendance_start,
        attendance_end,
    ) = get_previous_month_period(salary_slip)

    # ------------------------------------------------------
    # Fetch relevant attendance records in ONE DB call
    # ------------------------------------------------------

    attendance_records = frappe.get_all(
        "Attendance",
        filters={
            "employee": employee,
            "attendance_date": [
                "between",
                [
                    attendance_start,
                    attendance_end,
                ],
            ],
            "particulars": [
                "in",
                LATE_EARLY_STATUSES,
            ],
            "docstatus": 1,
        },
        fields=[
            "name",
            "attendance_date",
            "particulars",
            "in_time",
        ],
        order_by="attendance_date asc",
    )

    # ------------------------------------------------------
    # Perform timing check in Python
    # ------------------------------------------------------

    matching_attendance = []

    for attendance in attendance_records:

        if not attendance.in_time:
            continue

        if is_late_in_time(attendance.in_time):
            matching_attendance.append(attendance)

    # ------------------------------------------------------
    # Final count
    # ------------------------------------------------------

    count = len(matching_attendance)

    return {
        "count": 20,
        "from_date": attendance_start,
        "to_date": attendance_end,
        "records": matching_attendance,
    }


# ==========================================================
# GET SALARY SLIP ACCESS
# ==========================================================


@frappe.whitelist()
def get_salary_slip_access(salary_slip):
    """
    Determine whether attendance acknowledgement
    is required before viewing salary details.

    Final flow:

        Administrator
            -> Always allowed

        Employee:
            enable_late_acknowledgment = 0
                -> Normal salary

            enable_late_acknowledgment = 1
                -> Fetch Late/Early attendance
                -> Check in_time in Python

            < 14
                -> Normal salary

            14 to 20
                -> Blue Urgent Notice

            > 20
                -> Red High Alert

    Both acknowledgement levels use:

        late_acknowledgment
    """

    # ======================================================
    # ADMINISTRATOR BYPASS
    # ======================================================

    if frappe.session.user == "Administrator":

        return {
            "allowed": True,
            "required": False,
            "acknowledged": True,
            "acknowledgment_type": None,
        }

    # ======================================================
    # VALIDATE EMPLOYEE
    # ======================================================

    (
        salary_slip_doc,
        employee,
    ) = validate_salary_slip_employee(salary_slip)

    # ======================================================
    # GET EMPLOYEE SETTING
    # ======================================================

    enable_late_acknowledgment = frappe.db.get_value(
        "Employee",
        employee,
        "enable_late_acknowledgment",
    )

    enable_late_acknowledgment = bool(enable_late_acknowledgment)

    # ======================================================
    # FEATURE DISABLED
    # ======================================================

    if not enable_late_acknowledgment:

        return {
            "allowed": True,
            "required": False,
            "acknowledged": False,
            "acknowledgment_type": None,
        }

    # ======================================================
    # GET ATTENDANCE DATA
    # ======================================================

    attendance_data = get_late_early_attendance_data(
        employee,
        salary_slip,
    )

    count = attendance_data["count"]

    # ======================================================
    # ALREADY ACKNOWLEDGED
    # ======================================================

    if salary_slip_doc.late_acknowledgment:

        if count > LATE_HIGH_ALERT_THRESHOLD:

            acknowledgment_type = "high_alert"

        elif count >= LATE_ACKNOWLEDGMENT_THRESHOLD:

            acknowledgment_type = "late"

        else:

            acknowledgment_type = None

        return {
            "allowed": True,
            "required": False,
            "acknowledged": True,
            "acknowledgment_type": acknowledgment_type,
            "count": count,
            "from_date": attendance_data["from_date"],
            "to_date": attendance_data["to_date"],
        }

    # ======================================================
    # MORE THAN 20
    # ======================================================

    if count > LATE_HIGH_ALERT_THRESHOLD:

        return {
            "allowed": False,
            "required": True,
            "acknowledged": False,
            "acknowledgment_type": "high_alert",
            "count": count,
            "from_date": attendance_data["from_date"],
            "to_date": attendance_data["to_date"],
        }

    # ======================================================
    # 14 TO 20
    # ======================================================

    if count >= LATE_ACKNOWLEDGMENT_THRESHOLD:

        return {
            "allowed": False,
            "required": True,
            "acknowledged": False,
            "acknowledgment_type": "late",
            "count": count,
            "from_date": attendance_data["from_date"],
            "to_date": attendance_data["to_date"],
        }

    # ======================================================
    # LESS THAN 14
    # ======================================================

    return {
        "allowed": True,
        "required": False,
        "acknowledged": False,
        "acknowledgment_type": None,
        "count": count,
        "from_date": attendance_data["from_date"],
        "to_date": attendance_data["to_date"],
    }


# ==========================================================
# ACKNOWLEDGE SALARY SLIP
# ==========================================================


@frappe.whitelist()
def acknowledge_salary_slip(
    salary_slip,
    acknowledgment_type=None,
):
    """
    Record attendance acknowledgement.

    Valid acknowledgement types:

        late
        high_alert

    Both update:

        Salary Slip.late_acknowledgment = 1

    A detailed Comment is also added to the Salary Slip.
    """

    # ======================================================
    # ADMINISTRATOR
    # ======================================================

    if frappe.session.user == "Administrator":

        return {
            "success": True,
            "administrator": True,
        }

    # ======================================================
    # VALIDATE ACKNOWLEDGEMENT TYPE
    # ======================================================

    if acknowledgment_type not in [
        "late",
        "high_alert",
    ]:

        frappe.throw("Invalid acknowledgement type.")

    # ======================================================
    # VALIDATE EMPLOYEE
    # ======================================================

    (
        salary_slip_doc,
        employee,
    ) = validate_salary_slip_employee(salary_slip)

    # ======================================================
    # CHECK EMPLOYEE SETTING
    # ======================================================

    enable_late_acknowledgment = frappe.db.get_value(
        "Employee",
        employee,
        "enable_late_acknowledgment",
    )

    if not enable_late_acknowledgment:

        frappe.throw("Late Acknowledgement is not enabled for this employee.")

    # ======================================================
    # RE-CHECK ATTENDANCE
    # ======================================================

    attendance_data = get_late_early_attendance_data(
        employee,
        salary_slip,
    )

    count = attendance_data["count"]

    # ======================================================
    # VALIDATE CURRENT ACKNOWLEDGEMENT LEVEL
    # ======================================================

    if acknowledgment_type == "high_alert":

        if count <= LATE_HIGH_ALERT_THRESHOLD:

            frappe.throw(
                "The Late/Early count no longer requires High Alert acknowledgement."
            )

    elif acknowledgment_type == "late":

        if count < LATE_ACKNOWLEDGMENT_THRESHOLD:

            frappe.throw("The Late/Early count no longer requires acknowledgement.")

        if count > LATE_HIGH_ALERT_THRESHOLD:

            frappe.throw(
                "The Late/Early count now requires High Alert acknowledgement."
            )

    # ======================================================
    # ALREADY ACKNOWLEDGED
    # ======================================================

    if salary_slip_doc.late_acknowledgment:

        return {
            "success": True,
            "already_acknowledged": True,
            "acknowledgment_type": acknowledgment_type,
            "count": count,
        }

    # ======================================================
    # SET ACKNOWLEDGEMENT
    # ======================================================

    frappe.db.set_value(
        "Salary Slip",
        salary_slip_doc.name,
        "late_acknowledgment",
        1,
        update_modified=True,
    )

    # ======================================================
    # ACKNOWLEDGED BY
    # ======================================================

    acknowledged_by = frappe.db.get_value(
        "User",
        frappe.session.user,
        "full_name",
    )

    if not acknowledged_by:
        acknowledged_by = frappe.session.user

    acknowledged_on = now_datetime()

    # ======================================================
    # ACKNOWLEDGEMENT TYPE TEXT
    # ======================================================

    if acknowledgment_type == "high_alert":

        notice_title = "High Alert"

        notice_description = (
            "The employee acknowledged the High Alert "
            "regarding continuous late reporting and "
            "the applicable salary adjustment."
        )

    else:

        notice_title = "Urgent Notice"

        notice_description = (
            "The employee acknowledged the Urgent Notice "
            "regarding regular late reporting and "
            "understood the possible salary adjustment."
        )

    # ======================================================
    # ADD COMMENT
    # ======================================================

    comment_text = f"""
<b>{notice_title}</b><br><br>

Employee:
<b>{salary_slip_doc.employee_name}</b><br>

Employee ID:
<b>{salary_slip_doc.employee}</b><br>

Attendance Period:
<b>
{formatdate(attendance_data["from_date"])}
to
{formatdate(attendance_data["to_date"])}
</b><br>

Late Attendance Occurrences:
<b>{count}</b><br><br>

Acknowledged by:
<b>{acknowledged_by}</b><br>

Acknowledged on:
<b>
{formatdate(acknowledged_on.date())}
{acknowledged_on.strftime("%I:%M %p")}
</b><br><br>

{notice_description}
"""

    salary_slip_doc.add_comment(
        "Comment",
        comment_text,
    )

    frappe.db.commit()

    # ======================================================
    # RESPONSE
    # ======================================================

    return {
        "success": True,
        "acknowledged": True,
        "acknowledgment_type": acknowledgment_type,
        "count": count,
    }
