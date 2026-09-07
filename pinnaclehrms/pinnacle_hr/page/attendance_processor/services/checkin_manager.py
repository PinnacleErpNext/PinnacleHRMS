import frappe


def count_existing_employee_checkins(
    employees,
    from_time,
    to_time,
):
    """
    Count Employee Checkin records that will be deleted.
    """

    if not employees:
        return 0

    filters = {
        "employee": [
            "in",
            employees,
        ],
        "time": [
            "between",
            [
                from_time,
                f"{to_time} 23:59:59",
            ],
        ],
    }

    return frappe.db.count(
        "Employee Checkin",
        filters,
    )


def delete_existing_employee_checkins(
    employees,
    from_time,
    to_time,
):
    """
    Delete Employee Checkin records for the
    specified employees and payroll period.
    """

    if not employees:
        return 0

    filters = {
        "employee": [
            "in",
            employees,
        ],
        "time": [
            "between",
            [
                from_time,
                f"{to_time} 23:59:59",
            ],
        ],
    }

    total = frappe.db.count(
        "Employee Checkin",
        filters,
    )

    if total:

        frappe.db.delete(
            "Employee Checkin",
            filters,
        )

    frappe.db.commit()

    return total
