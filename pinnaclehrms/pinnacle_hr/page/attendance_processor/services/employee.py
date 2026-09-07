import frappe


def get_employee(company=None):
    """
    Fetch active employees.

    If company is provided, only employees from that company
    are returned.

    Returns:

        {
            "HR-EMP-00001": "Employee One",
            "HR-EMP-00002": "Employee Two"
        }
    """

    filters = {"status": "Active"}

    if company:
        filters["company"] = company

    employees = frappe.get_all(
        "Employee",
        filters=filters,
        fields=[
            "name",
            "employee_name",
        ],
    )

    return {employee.name: employee.employee_name for employee in employees}


def get_employee_name(employee):
    """
    Fetch employee name.
    """
    if not employee:
        return None

    return frappe.db.get_value(
        "Employee",
        employee,
        "employee_name",
    )


def get_employee_shift_map(employees):
    """
    Fetch default_shift for all employees in one query.

    Returns:

        {
            "HR-EMP-00001": "Manager",
            "HR-EMP-00002": "Developer"
        }
    """

    if not employees:
        return {}

    employees = list(set(employees))

    rows = frappe.get_all(
        "Employee",
        filters={"name": ["in", employees]},
        fields=[
            "name",
            "default_shift",
        ],
    )

    return {row.name: row.default_shift for row in rows}


def get_employee_id_from_device(device, device_id):
    """
    Resolve Employee from biometric device + device ID.
    """

    if not device or not device_id:
        return None

    return frappe.db.get_value(
        "Attendance Device ID Allotment",
        {
            "device": device,
            "device_id": device_id,
        },
        "parent",
    )
