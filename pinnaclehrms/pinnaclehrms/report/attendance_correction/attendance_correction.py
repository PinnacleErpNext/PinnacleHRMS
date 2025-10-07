import frappe
from frappe import _


def execute(filters=None):
    if not filters:
        filters = {}

    company = filters.get("company")

    # ------------------------------
    # Get Fiscal Year
    # ------------------------------
    fiscal_year = filters.get("fiscal_year") or frappe.db.get_value(
        "Fiscal Year", {"is_active": 1}, "name"
    )

    if not fiscal_year:
        frappe.throw(_("No active Fiscal Year found!"))

    fy = frappe.db.get_value(
        "Fiscal Year", fiscal_year, ["year_start_date", "year_end_date"], as_dict=True
    )

    fy_start = fy["year_start_date"]
    fy_end = fy["year_end_date"]

    # ------------------------------
    # Build dynamic WHERE clause
    # ------------------------------
    conditions = ""
    params = [fy_start, fy_end]

    if company:
        conditions += " AND e.company = %s"
        params.append(company)

    # ------------------------------
    # Fetch all employees with correction count
    # ------------------------------
    data = frappe.db.sql(
        f"""
        SELECT
            e.name AS employee,
            e.employee_name,
            COALESCE(COUNT(ac.name), 0) AS corrections_count
        FROM `tabEmployee` e
        LEFT JOIN `tabAttendance Correction` ac
            ON ac.employee = e.name
            AND ac.attendance_date BETWEEN %s AND %s
        WHERE 1=1 {conditions}
        GROUP BY e.name, e.employee_name
        ORDER BY corrections_count DESC
        """,
        tuple(params),
        as_dict=True,
    )

    # ------------------------------
    # Add clickable link for corrections_count
    # ------------------------------
    for row in data:
        row[
            "corrections_count"
        ] = f"""
            <a href="/app/attendance-correction?employee={row['employee']}&from_date={fy_start}&to_date={fy_end}" 
               target="_blank">{row['corrections_count']}</a>
        """

    # ------------------------------
    # Define report columns
    # ------------------------------
    columns = [
        {
            "label": "Employee ID",
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 333,
        },
        {
            "label": "Employee Name",
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 333,
        },
        {
            "label": "No. of Corrections",
            "fieldname": "corrections_count",
            "fieldtype": "HTML",
            "width": 333,
        },
    ]

    return columns, data
