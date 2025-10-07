import frappe
import json
import io
from frappe import _
from frappe.utils.xlsxutils import make_xlsx
from frappe.utils import format_datetime


def execute(filters=None):
    columns = [
        {
            "label": f"<input type='checkbox' id='select-all-checkbox'>",
            "fieldname": "select",
            "fieldtype": "HTML",
            "width": 40,
        },
        {
            "label": "Employee",
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 300,
        },
        {"label": "Shift", "fieldname": "shift", "fieldtype": "Data", "width": 120},
        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 120},
        {
            "label": "IN Time",
            "fieldname": "in_time",
            "fieldtype": "Datetime",
            "width": 300,
        },
        {
            "label": "OUT Time",
            "fieldname": "out_time",
            "fieldtype": "Datetime",
            "width": 300,
        },
        {"label": "Status", "fieldname": "status", "fieldtype": "HTML", "width": 120},
    ]

    conditions = []
    values = []

    if filters.get("shift"):
        conditions.append("shift = %s")
        values.append(filters.get("shift"))

    if filters.get("employee"):
        conditions.append("employee = %s")
        values.append(filters.get("employee"))

    if filters.get("date"):
        conditions.append("DATE(`time`) = %s")
        values.append(filters.get("date"))
    else:
        if filters.get("year"):
            conditions.append("YEAR(`time`) = %s")
            values.append(filters.get("year"))

        if filters.get("month"):
            month_map = {
                "January": 1,
                "February": 2,
                "March": 3,
                "April": 4,
                "May": 5,
                "June": 6,
                "July": 7,
                "August": 8,
                "September": 9,
                "October": 10,
                "November": 11,
                "December": 12,
            }
            month_num = month_map.get(filters.get("month"))
            if month_num:
                conditions.append("MONTH(`time`) = %s")
                values.append(month_num)

    condition_str = " AND ".join(conditions)
    if condition_str:
        condition_str = "WHERE " + condition_str

    query = f"""
        SELECT  
            employee,
            employee_name,
            shift, 
            DATE(`time`) AS date, 
            MIN(CASE WHEN log_type = 'IN'  THEN `time` END)  AS in_time,  
            MAX(CASE WHEN log_type = 'OUT' THEN `time` END)  AS out_time,
            CASE 
                WHEN SUM(CASE WHEN skip_auto_attendance = 1 THEN 1 ELSE 0 END) > 0 THEN 'Pending'
                ELSE 'Approved'
            END AS raw_status
        FROM  
            `tabEmployee Checkin`
        {condition_str}
        GROUP BY  
            employee, DATE(`time`)
        ORDER BY  
            employee, date
    """

    data = frappe.db.sql(query, values, as_dict=True)

    for row in data:
        disabled_attr = "disabled" if row["raw_status"] == "Approved" else ""
        row[
            "select"
        ] = f"""
            <input type='checkbox' class='approve-checkbox' 
                data-employee='{row['employee']}' 
                data-date='{row['date']}' {disabled_attr}>
        """
        if row["raw_status"] == "Pending":
            row["status"] = "<span style='color:red;font-weight:bold;'>Pending</span>"
        else:
            row["status"] = (
                "<span style='color:green;font-weight:bold;'>Approved</span>"
            )

    return columns, data


@frappe.whitelist()
def bulk_approve_attendance(records):
    records = json.loads(records)
    for rec in records:

        employee = rec.get("employee")
        date = rec.get("date")

        logs = frappe.db.sql(
            """
            SELECT name
            FROM `tabEmployee Checkin`
            WHERE employee = %s AND DATE(`time`) = %s
        """,
            (employee, date),
            as_dict=True,
        )
        
        for log in logs:
            frappe.db.set_value(
                "Employee Checkin", log["name"], "skip_auto_attendance", 0
            )
            attendance_notification(log["name"])
    frappe.db.commit()
    return {"status": "success"}


@frappe.whitelist()
def download_final_attendance_excel(filters):
    if isinstance(filters, str):
        filters = json.loads(filters)

    conditions = []
    values = []

    # Filters
    if filters.get("shift"):
        conditions.append("shift = %s")
        values.append(filters.get("shift"))

    if filters.get("employee"):
        conditions.append("employee = %s")
        values.append(filters.get("employee"))

    if filters.get("date"):
        conditions.append("DATE(`time`) = %s")
        values.append(filters.get("date"))
    else:
        if filters.get("year"):
            conditions.append("YEAR(`time`) = %s")
            values.append(filters.get("year"))

        if filters.get("month"):
            month_map = {
                "January": 1,
                "February": 2,
                "March": 3,
                "April": 4,
                "May": 5,
                "June": 6,
                "July": 7,
                "August": 8,
                "September": 9,
                "October": 10,
                "November": 11,
                "December": 12,
            }
            month_num = month_map.get(filters.get("month"))
            if month_num:
                conditions.append("MONTH(`time`) = %s")
                values.append(month_num)

    conditions.append("skip_auto_attendance = 0")

    # Combine conditions
    condition_str = " AND ".join(conditions)
    if condition_str:
        condition_str = "WHERE " + condition_str

    # SQL Query
    query = f"""
        SELECT  
            employee,
            employee_name,
            shift, 
            DATE(`time`) AS date, 
            MIN(CASE WHEN log_type = 'IN'  THEN `time` END)  AS in_time,  
            MAX(CASE WHEN log_type = 'OUT' THEN `time` END)  AS out_time,
            CASE 
                WHEN SUM(CASE WHEN skip_auto_attendance = 1 THEN 1 ELSE 0 END) > 0 THEN 'Pending'
                ELSE 'Approved'
            END AS raw_status
        FROM  
            `tabEmployee Checkin`
        {condition_str}
        GROUP BY  
            employee, DATE(`time`)
        ORDER BY  
            employee, date
    """

    data = frappe.db.sql(query, values, as_dict=True)

    # Prepare Excel rows
    rows = [["Employee", "Employee Name", "Date", "In Time", "Out Time"]]
    for row in data:
        rows.append(
            [
                row.get("employee"),
                row.get("employee_name"),
                str(row.get("date")),
                str(row.get("in_time") or ""),
                str(row.get("out_time") or ""),
            ]
        )

    # Generate Excel file (returns BytesIO)
    xlsx_file = make_xlsx(rows, "Attendance Approval")

    # File name formatting
    filename = f"Attendance_Approval_{filters.get('month') or ''}_{filters.get('year') or ''}.xlsx"

    # Send as download
    frappe.response.filename = filename
    frappe.response.filecontent = xlsx_file.getvalue()
    frappe.response.type = "binary"


@frappe.whitelist()
def attendance_notification(log):
    try:
        # Fetch Employee Checkin document
        doc = frappe.get_doc("Employee Checkin", log)

        hr_email = "hr@mygstcafe.in"

        # Prepare subject
        subject = f"Attendance Approval – {doc.employee}: {doc.employee_name} - {format_datetime(doc.time)}"

        # Determine status
        status = "In" if doc.log_type == "IN" else "Out"

        # Format the message
        message = f"""
        Dear HR Team,<br><br>
        This is to notify that the following employee's attendance has been approved:<br><br>
        <b>Employee ID:</b> {doc.employee}<br>
        <b>Name:</b> {doc.employee_name}<br>
        <b>Status:</b> Checked {status}<br>
        <b>Time:</b> {format_datetime(doc.time)}<br><br>
        Regards,<br>
        PinnacleHRMS
        """

        # Send email
        frappe.sendmail(
            recipients=[hr_email],
            subject=subject,
            message=message
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Attendance Notification Error")
