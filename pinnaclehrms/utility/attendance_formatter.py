import frappe
import io
import json
from datetime import datetime, time
from collections import defaultdict
from openpyxl import load_workbook, Workbook
from werkzeug.wrappers import Response
from collections import defaultdict
from datetime import time
import openpyxl
from io import BytesIO
from frappe.utils.file_manager import save_file
from collections import defaultdict


# --- Helpers ---


def format_date_safe(date_value):
    """
    Safely format a date value to 'YYYY-MM-DD'.
    Handles datetime objects, strings, or None.
    Returns an empty string if the date is invalid.
    """
    if not date_value:
        return ""

    # If already a datetime or date object
    if isinstance(date_value, (datetime,)):
        return date_value.strftime("%Y-%m-%d")

    # If it's a string, try to parse it
    try:
        parsed_date = datetime.strptime(str(date_value), "%Y-%m-%d")
        return parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        # If parsing fails, just return the original string
        return str(date_value)


def convert_app_attendance_to_records(app_attendance):
    """Convert app_attendance dict into records list matching final sheet format."""
    converted_records = []
    for emp_id, records in app_attendance.items():
        for rec in records:
            converted_records.append(
                {
                    "device_id": "",  # App logs don't have device_id
                    "device": "App",  # Mark source as App
                    "employee_name": rec.get("employee_name"),
                    "employee_id": emp_id,
                    "attendance_date": rec.get("attendance_date"),
                    "shift": rec.get("shift") or "Regular",
                    "in_time": rec.get("in_time"),
                    "out_time": rec.get("out_time"),
                }
            )
    return converted_records


def parse_date_safe(date_val):
    if isinstance(date_val, datetime):
        return date_val
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(date_val), fmt)
        except Exception:
            continue
    return None


def parse_time_safe(value):
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        value = value.strip()
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).time()
            except:
                continue
    return None


def format_time_string(t):
    if isinstance(t, datetime):
        return t.strftime("%H:%M:%S")
    elif t:
        return str(t).strip()
    return None


def get_employee(company):

    employees = frappe.get_all(
        "Employee",
        filters={"company": company, "status": "Active"},
        fields=["name", "employee_name"],
    )
    return {emp.name: emp.employee_name for emp in employees}


def get_app_attendance(employee_list, payrollFrom, payrollTo):
    """
    Fetch attendance data for a list of employees within a given date range.
    Groups by employee and date, returning in_time, out_time, and status.

    Args:
        employee_list (list): List of employee IDs
        payrollFrom (str): Start date (YYYY-MM-DD)
        payrollTo (str): End date (YYYY-MM-DD)

    Returns:
        dict: { employee_id: [attendance_records] }
    """
    # Ensure employee list is not empty
    if not employee_list:
        return {}

    # Build dynamic condition string
    condition_str = """
        WHERE employee IN %(employee_list)s
        AND DATE(`time`) BETWEEN %(from_date)s AND %(to_date)s
    """

    # SQL Query
    query = f"""
        SELECT  
            employee,
            employee_name,
            shift, 
            DATE(`time`) AS attendance_date, 
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
            employee, attendance_date
    """

    # Execute query safely with parameters
    attendance = frappe.db.sql(
        query,
        {
            "employee_list": tuple(employee_list),
            "from_date": payrollFrom,
            "to_date": payrollTo,
        },
        as_dict=True,
    )

    # Convert to structured dictionary { employee_id: [records] }
    attendance_dict = defaultdict(list)
    for record in attendance:
        attendance_dict[record["employee"]].append(record)

    return dict(attendance_dict)


# --- Processors ---


def process_pinnacle(file):
    file_stream = file.stream.read()
    wb = load_workbook(filename=io.BytesIO(file_stream), data_only=True)

    if "Att.log report" not in wb.sheetnames:
        frappe.throw("Sheet 'Att.log report' not found.")

    ws = wb["Att.log report"]
    raw_period = ws["C3"].value
    start_date_str = raw_period.split("~")[0].strip()
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    formatted_period = start_date.strftime("%b-%Y")
    dates = [cell.value for cell in ws[4] if isinstance(cell.value, int)]

    records = []
    row = 5
    while ws.cell(row=row, column=1).value:
        if ws.cell(row=row, column=1).value == "ID:":
            device_id = str(ws.cell(row=row, column=3).value or "").strip()
            emp_name = str(ws.cell(row=row, column=11).value or "").strip()
            time_log_row = row + 1

            for col_index, day in enumerate(dates, start=1):
                time_log = ws.cell(row=time_log_row, column=col_index).value
                if isinstance(time_log, str):
                    time_log = time_log.strip()
                    in_time = time_log[:5]
                    out_time = time_log[-5:] if len(time_log) >= 10 else ""

                    date_obj = datetime.strptime(
                        f"{day:02d}-{formatted_period}", "%d-%b-%Y"
                    )
                    records.append(
                        {
                            "device_id": device_id,
                            "device": "Zicom Regal",
                            "employee_name": emp_name,
                            "attendance_date": date_obj.strftime("%d-%b-%Y"),
                            "shift": "Regular",
                            "in_time": in_time,
                            "out_time": out_time,
                        }
                    )
            row += 2
        else:
            row += 1
    return records


def process_Opticode_final(file):
    file_stream = file.stream.read()
    wb = load_workbook(filename=io.BytesIO(file_stream), data_only=True)
    records = []
    seen = set()

    if "Final" not in wb.sheetnames:
        frappe.throw("Sheet 'Final' not found in the workbook.")

    sheet = wb["Final"]
    if sheet.max_row < 2:
        return []

    header_row = [
        cell.value.strip() if isinstance(cell.value, str) else cell.value
        for cell in sheet[1]
    ]
    col_index = {header: idx for idx, header in enumerate(header_row)}

    required_fields = ["ID", "G", "Date", "In Time", "Out Time"]
    for field in required_fields:
        if field not in col_index:
            frappe.throw(f"Missing required column: {field}")

    for row in sheet.iter_rows(min_row=2, values_only=True):
        try:
            device_id = row[col_index["ID"]]
            emp_name = row[col_index["G"]]
            date_val = row[col_index["Date"]]
            in_time = row[col_index["In Time"]]
            out_time = row[col_index["Out Time"]]

            if not all([device_id, emp_name, date_val]):
                continue

            if isinstance(date_val, datetime):
                date_key = date_val.date()
                date_str = date_val.strftime("%d-%b-%Y")
            else:
                date_obj = datetime.strptime(str(date_val), "%Y-%m-%d")
                date_key = date_obj.date()
                date_str = date_obj.strftime("%d-%b-%Y")

            in_time_str = str(in_time).strip()
            out_time_str = str(out_time).strip()

            unique_key = (str(device_id), date_key, in_time_str, out_time_str)
            if unique_key in seen:
                continue
            seen.add(unique_key)

            records.append(
                {
                    "device_id": str(device_id),
                    "device": "ESSL Westcott",
                    "employee_name": emp_name.strip(),
                    "attendance_date": date_str,
                    "shift": "Regular",
                    "in_time": in_time_str,
                    "out_time": out_time_str,
                }
            )
        except Exception as e:
            frappe.log_error(
                f"Error processing Opticode row: {e}", "Opticode Formatter"
            )

    return records


# --- Core Final Generator ---


@frappe.whitelist()
def generate_final_sheet(attendance_data=None):
    """Generate final attendance sheet from raw attendance logs."""
    attendance_logs = defaultdict(list)
    seen = set()

    # --- Preload Employee Names for later ---
    emp_name_cache = {}

    for data in attendance_data or []:
        device_in = device_out = None  # reset each record

        try:
            device_id = data.get("device_id")
            device = data.get("device")
            date_val = data.get("attendance_date")
            shift = data.get("shift", "Regular").strip()
            in_time_raw = data.get("in_time")
            out_time_raw = data.get("out_time")

            # --- Get employee from device allotment ---
            if device == "App":
                emp_id = data.get("employee_id")
            else:
                emp_id = frappe.db.get_value(
                    "Attendance Device ID Allotment",
                    {"device": device, "device_id": device_id},
                    "parent",
                )

            if not emp_id:
                continue

            # --- Parse date safely ---
            parsed_date = parse_date_safe(date_val)
            if not parsed_date:
                continue

            # --- If IN missing, fetch from Employee Checkin ---
            if not in_time_raw or in_time_raw in ["None", "00:00:00", "00:00"]:
                in_time = frappe.db.get_value(
                    "Employee Checkin",
                    {
                        "employee": emp_id,
                        "log_type": "IN",
                        "time": ["like", f"{parsed_date.date()}%"],
                    },
                    "time",
                )
                in_time_raw = in_time.time() if in_time else None
                if in_time_raw:
                    device_in = "App"

            # --- If OUT missing, fetch from Employee Checkin ---
            if not out_time_raw or out_time_raw in ["None", "00:00:00", "00:00"]:
                out_time = frappe.db.get_value(
                    "Employee Checkin",
                    {
                        "employee": emp_id,
                        "log_type": "OUT",
                        "time": ["like", f"{parsed_date.date()}%"],
                    },
                    "time",
                )
                out_time_raw = out_time.time() if out_time else None
                if out_time_raw:
                    device_out = "App"

            # --- Format times ---
            in_str = format_time_string(in_time_raw)
            out_str = format_time_string(out_time_raw)

            if not in_str and not out_str:
                continue

            # --- Deduplicate per employee + date ---
            key = (emp_id, parsed_date.date())
            if key in seen:
                continue
            seen.add(key)

            # --- Append log ---
            attendance_logs[emp_id].append(
                {
                    "date": parsed_date.date(),
                    "shift": shift,
                    "in_time": in_str,
                    "out_time": out_str,
                    "custom_log_in_from": device_in or device,
                    "custom_log_out_from": device_out or device,
                }
            )

        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Error processing entry: {data}")

    # --- Aggregate Final Data ---
    final_data = {}
    for emp_id, logs in attendance_logs.items():
        summary = {}

        for log in logs:
            date = str(log["date"])
            in_t = parse_time_safe(log["in_time"]) or time(0, 0, 0)
            out_t = parse_time_safe(log["out_time"]) or time(0, 0, 0)

            if date not in summary:
                summary[date] = {
                    "date": log["date"],
                    "shift": log["shift"],
                    "min_in_time": in_t,
                    "max_out_time": out_t,
                    "custom_log_in_from": log["custom_log_in_from"],
                    "custom_log_out_from": log["custom_log_out_from"],
                }
            else:
                summary[date]["min_in_time"] = min(summary[date]["min_in_time"], in_t)
                summary[date]["max_out_time"] = max(
                    summary[date]["max_out_time"], out_t
                )
                # Keep first non-empty device info
                if not summary[date]["custom_log_in_from"]:
                    summary[date]["custom_log_in_from"] = log["custom_log_in_from"]
                if not summary[date]["custom_log_out_from"]:
                    summary[date]["custom_log_out_from"] = log["custom_log_out_from"]

        # Cache employee name
        if emp_id not in emp_name_cache:
            emp_name_cache[emp_id] = frappe.db.get_value(
                "Employee", emp_id, "employee_name"
            )

        final_data[emp_id] = [
            {
                "employee": emp_id,
                "employee_name": emp_name_cache[emp_id],
                "attendance_date": entry["date"],
                "shift": entry["shift"],
                "in_time": (
                    entry["min_in_time"].strftime("%H:%M:%S")
                    if entry["min_in_time"]
                    else ""
                ),
                "out_time": (
                    entry["max_out_time"].strftime("%H:%M:%S")
                    if entry["max_out_time"]
                    else ""
                ),
                "custom_log_in_from": entry.get("custom_log_in_from", ""),
                "custom_log_out_from": entry.get("custom_log_out_from", ""),
            }
            for entry in summary.values()
        ]
   
    return {
        "message": "✅ Attendance extracted successfully",
        "total_employees": len(final_data),
        "total_records": sum(len(x) for x in final_data.values()),
        "data": final_data,
    }


# --- Preview and Download Endpoints ---


@frappe.whitelist()
def preview_final_attendance_sheet():
    pinnacle_file = frappe.request.files.get("pinnacle_file")
    opticode_file = frappe.request.files.get("opticode_file")

    company = frappe.form_dict.get("company")
    payrollFrom = frappe.form_dict.get("from_date")
    payrollTo = frappe.form_dict.get("to_date")

    if not company or not payrollFrom or not payrollTo:
        return Response("❌ Company and Payroll Period are required", status=400)

    # Fetch employees for the selected company
    employeeList = get_employee(company)

    if not employeeList:
        return Response("❌ No active employees found for this company", status=404)

    # Fetch attendance from the app for given employees and period
    app_attendance = get_app_attendance(
        list(employeeList.keys()), payrollFrom, payrollTo
    )

    # Convert app_attendance to same structure as other records
    app_records = convert_app_attendance_to_records(app_attendance)

    # Combine all records
    records = []
    if pinnacle_file:
        records += process_pinnacle(pinnacle_file)
    if opticode_file:
        records += process_Opticode_final(opticode_file)
    records += app_records

    result = generate_final_sheet(records)
    print(result)
    data = result.get("data", {})

    # Build HTML preview
    html = '<table class="table table-bordered"><thead><tr>'
    html += (
        "<th>Employee</th><th>Employee Name</th><th>Attendance Date</th>"
        "<th>Shift</th><th>Log In From</th><th>In Time</th>"
        "<th>Log Out From</th><th>Out Time</th></tr></thead><tbody>"
    )

    for emp_id in sorted(data):
        for row in data[emp_id]:
            html += (
                f"<tr><td>{row['employee']}</td>"
                f"<td>{row['employee_name']}</td>"
                f"<td>{format_date_safe(row['attendance_date'])}</td>"
                f"<td>{row['shift']}</td>"
                f"<td>{row['custom_log_in_from']}</td>"
                f"<td>{row['in_time']}</td>"
                f"<td>{row['custom_log_out_from']}</td>"
                f"<td>{row['out_time']}</td></tr>"
            )

    html += "</tbody></table>"

    return {
        "message": "Preview generated successfully",
        "data": data,
        "html": html,
        "total_employees": len(data),
        "total_records": sum(len(x) for x in data.values()),
    }


@frappe.whitelist()
def download_final_attendance_excel(logs):

    data = json.loads(logs)
    # frappe.throw(str(data))
    wb = Workbook()
    ws = wb.active
    ws.title = "Final Attendance"
    ws.append(
        [
            "Employee",
            "Employee Name",
            "Attendance Date",
            "Shift",
            "Log In From",
            "In Time",
            "Log Out From",
            "Out Time",
        ]
    )

    for emp_id in sorted(data):
        for row in data[emp_id]:
            print(row)
            ws.append(
                [
                    row["employee"],
                    row["employee_name"],
                    (
                        row["attendance_date"].strftime("%d-%b-%Y")
                        if isinstance(row["attendance_date"], datetime)
                        else str(row["attendance_date"])
                    ),
                    row["shift"],
                    row["custom_log_in_from"],
                    row["in_time"],
                    row["custom_log_out_from"],
                    row["out_time"],
                ]
            )

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return Response(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Final_Attendance.xlsx"},
    )


@frappe.whitelist()
def create_data_import_for_attendance(attendance_data=None):
    """
    Creates a Data Import record with an Excel file for Attendance List
    and starts the import process.
    """
    # 1. Fetch validated records
    validated_data = json.loads(attendance_data or "[]")
    if not validated_data:
        frappe.throw("No validated records found.")

    # 2. Create Excel file in memory
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance List"

    headers = [
        "Employee",
        "Employee Name",
        "Attendance Date",
        "Shift",
        "Log In From",
        "In Time",
        "Log Out From",
        "Out Time",
    ]
    ws.append(headers)

    for emp_id in sorted(validated_data):
        for row in validated_data[emp_id]:
            ws.append(
                [
                    row["employee"],
                    row["employee_name"],
                    (
                        row["attendance_date"].strftime("%Y-%m-%d")
                        if isinstance(row["attendance_date"], datetime)
                        else str(row["attendance_date"])
                    ),
                    row.get("shift"),
                    row.get("custom_log_in_from"),
                    row.get("in_time"),
                    row.get("custom_log_out_from"),
                    row.get("out_time"),
                ]
            )

    # Save to bytes
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    # 3. Create Data Import record first
    data_import = frappe.get_doc(
        {
            "doctype": "Data Import",
            "import_type": "Insert New Records",
            "reference_doctype": "Attendance",
            "submit_after_import": 0,
            "mute_emails": 1,
        }
    )
    data_import.insert(ignore_permissions=True)

    # 4. Attach the Excel file to Data Import
    file_doc = save_file(
        "attendance_import.xlsx",
        output.getvalue(),
        "Data Import",
        data_import.name,
        is_private=1,
    )
    data_import.import_file = file_doc.file_url
    data_import.save(ignore_permissions=True)

    # 5. Start the import
    frappe.enqueue(
        "frappe.core.doctype.data_import.data_import.start_import",
        data_import=data_import.name,
        import_type="Insert New Records",
    )

    return data_import.name
