import frappe
import io
import json
from datetime import datetime, time
from collections import defaultdict
from openpyxl import load_workbook, Workbook
from werkzeug.wrappers import Response

# --- Helpers ---


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

            if not all([device_id, emp_name, date_val, in_time, out_time]):
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
    attendance_logs = defaultdict(list)
    seen = set()

    for data in attendance_data or []:
        try:
            device_id = data.get("device_id")
            device = data.get("device")
            date_val = data.get("attendance_date")
            shift = data.get("shift", "Regular")
            in_time_raw = data.get("in_time")
            out_time_raw = data.get("out_time")

            emp_id = frappe.db.get_value(
                "Attendance Device ID Allotment",
                {"device": device, "device_id": device_id},
                "parent",
            )
            if not emp_id:
                continue

            parsed_date = parse_date_safe(date_val)
            if not parsed_date:
                continue
            if not in_time_raw:
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

            if not out_time_raw:
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

            in_str = format_time_string(in_time_raw)
            out_str = format_time_string(out_time_raw)

            if not in_str and not out_str:
                continue

            key = (emp_id, parsed_date.date(), in_str, out_str)
            if key in seen:
                continue
            seen.add(key)

            attendance_logs[emp_id].append(
                {
                    "date": parsed_date.date(),
                    "shift": shift.strip(),
                    "in_time": in_str,
                    "out_time": out_str,
                    "custom_log_in_from": device,
                    "custom_log_out_from": device,
                }
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Error processing entry: {data}")

    # Aggregate
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

        final_data[emp_id] = [
            {
                "employee": emp_id,
                "employee_name": frappe.db.get_value(
                    "Employee", emp_id, "employee_name"
                ),
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
    if not pinnacle_file and not opticode_file:
        return Response("❌ No files received", status=400)

    records = []
    if pinnacle_file:
        records += process_pinnacle(pinnacle_file)
    if opticode_file:
        records += process_Opticode_final(opticode_file)

    result = generate_final_sheet(records)
    data = result.get("data", {})

    html = '<table class="table table-bordered"><thead><tr>'
    html += "<th>Employee</th><th>Employee Name</th><th>Attendance Date</th><th>Shift</th><th>Log In From</th><th>In Time</th><th>Log Out From</th><th>Out Time</th></tr></thead><tbody>"

    for emp_id in sorted(data):
        for row in data[emp_id]:
            html += f"<tr><td>{row['employee']}</td><td>{row['employee_name']}</td><td>{row['attendance_date']}</td><td>{row['shift']}</td><td>{row['custom_log_in_from']}</td><td>{row['in_time']}</td><td>{row['custom_log_out_from']}</td><td>{row['out_time']}</td></tr>"

    html += "</tbody></table>"

    return Response(html, content_type="text/html")


@frappe.whitelist()
def download_final_attendance_excel():
    pinnacle_file = frappe.request.files.get("pinnacle_file")
    opticode_file = frappe.request.files.get("opticode_file")
    if not pinnacle_file and not opticode_file:
        return Response("❌ No files received", status=400)

    records = []
    if pinnacle_file:
        records += process_pinnacle(pinnacle_file)
    if opticode_file:
        records += process_Opticode_final(opticode_file)

    result = generate_final_sheet(records)
    data = result.get("data", {})

    wb = Workbook()
    ws = wb.active
    ws.title = "Final Attendance"
    ws.append(
        [
            "Employee",
            "Employee Name",
            "Attendance Date",
            "Shift",
            "In Time",
            "Out Time",
            "Log In From",
            "Log Out From",
        ]
    )

    for emp_id in sorted(data):
        for row in data[emp_id]:
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
                    row["in_time"],
                    row["out_time"],
                    row["custom_log_in_from"],
                    row["custom_log_out_from"],
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
