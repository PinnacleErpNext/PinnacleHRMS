import frappe
import calendar
from frappe.utils import getdate, nowdate
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "label": _("Attendance Date"),
            "fieldname": "attendance_date",
            "fieldtype": "Date",
            "width": 200,
        },
        {
            "label": _("Check In"),
            "fieldname": "check_in",
            "fieldtype": "Datetime",
            "width": 200,
        },
        {
            "label": _("Check Out"),
            "fieldname": "check_out",
            "fieldtype": "Datetime",
            "width": 200,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Action"),
            "fieldname": "action",
            "fieldtype": "HTML",
            "width": 110,
        },
    ]


def get_data(filters):
    conditions = ""
    params = {}

    if filters:
        if filters.get("employee"):
            conditions += " AND ec.employee = %(employee)s"
            params["employee"] = filters.get("employee")

        if filters.get("month") and not (
            filters.get("from_date") or filters.get("to_date")
        ):
            month_index = list(calendar.month_name).index(filters.get("month"))
            year = getdate(nowdate()).year
            from_date = f"{year}-{month_index:02d}-01"
            last_day = calendar.monthrange(year, month_index)[1]
            to_date = f"{year}-{month_index:02d}-{last_day}"
            conditions += " AND DATE(ec.time) BETWEEN %(from_date)s AND %(to_date)s"
            params["from_date"] = from_date
            params["to_date"] = to_date

        if (
            filters.get("from_date")
            and filters.get("to_date")
            and not filters.get("month")
        ):
            conditions += " AND DATE(ec.time) BETWEEN %(from_date)s AND %(to_date)s"
            params["from_date"] = filters.get("from_date")
            params["to_date"] = filters.get("to_date")

    # First fetch min/max time per employee per date
    data = frappe.db.sql(
        f"""
        SELECT
            ec.employee,
            e.employee_name,
            DATE(ec.time) AS attendance_date,
            MIN(ec.time) AS check_in,
            MAX(ec.time) AS check_out
        FROM `tabEmployee Checkin` ec
        JOIN `tabEmployee` e ON ec.employee = e.name
        WHERE 1=1 {conditions}
        GROUP BY ec.employee, DATE(ec.time)
        ORDER BY ec.employee, DATE(ec.time) DESC
    """,
        params,
        as_dict=1,
    )

    # Now fetch corresponding document names of min/max times
    result = []
    for row in data:
        checkin_docname = frappe.db.get_value(
            "Employee Checkin",
            {"employee": row["employee"], "time": row["check_in"]},
            "name",
        )
        checkout_docname = frappe.db.get_value(
            "Employee Checkin",
            {"employee": row["employee"], "time": row["check_out"]},
            "name",
        )

        # Get status (assuming workflow_state or custom is_approved field — fallback to empty if not there)
        status = (
            frappe.db.get_value("Employee Checkin", checkin_docname, "workflow_state")
            or ""
        )

        row["status"] = status

        row[
            "action"
        ] = f"""<button class='btn btn-primary btn-xs' onclick="frappe.call({{
            method: 'pinnaclehrms.pinnaclehrms.report.employee_punching_report.employee_punching_report.approve_attendance',
            args: {{ checkin_name: '{checkin_docname}', checkout_name: '{checkout_docname}' }},
            callback: function(r) {{ frappe.msgprint(r.message); }}
        }})">Approve</button>"""

        result.append(row)

    return result


@frappe.whitelist()
def approve_attendance(checkin_name, checkout_name):
    # Approve both checkin and checkout documents

    for docname in [checkin_name, checkout_name]:
        checkin = frappe.get_doc("Employee Checkin", docname)

        # OPTIONAL: Set custom field or workflow_state (adjust as needed)
        frappe.db.set_value("Employee Checkin", docname, "workflow_state", "Approved")

        checkin.add_comment("Comment", "Checkin approved via report action")

    frappe.db.commit()

    return f"Check-in and Check-out records approved ({checkin_name}, {checkout_name})."
