import frappe
import calendar
from datetime import datetime, time
from collections import defaultdict
from openpyxl import Workbook, load_workbook
from openpyxl.utils.datetime import from_excel
from datetime import datetime
from werkzeug.wrappers import Response
import io


def extract_attendance_records(file_stream, excel_type):
    wb = load_workbook(filename=io.BytesIO(file_stream), data_only=True)

    if excel_type == "Pinnacle":
        if "Att.log report" not in wb.sheetnames:
            frappe.throw("Sheet 'Att.log report' not found in the workbook.")
        sheet = wb["Att.log report"]
        return process_Pinnacle(sheet)

    elif excel_type == "Opticode":
        if "Final" not in wb.sheetnames:
            frappe.throw("Sheet 'Final' not found in the workbook.")
        sheet = wb["Final"]
        return process_Opticode_final(sheet)

    else:
        frappe.throw("Invalid Excel Type. Choose either 'Pinnacle' or 'Opticode'.")


@frappe.whitelist()
def upload_excel():
    try:
        uploaded_file = frappe.request.files.get("file")
        excel_type = frappe.form_dict.get("excel_type")

        if not uploaded_file:
            return Response("No file received", status=400)

        file_stream = uploaded_file.stream.read()
        records = extract_attendance_records(file_stream, excel_type)

        if not records:
            return Response("No valid attendance records found.", status=204)

        headers = [
            "Attendance Device Id",
            "Attendance Device",
            "Employee Name",
            "Attendance Date",
            "Shift",
            "In Time",
            "Out Time",
        ]

        html = "<table class='table table-bordered'><thead><tr>"
        html += "".join(f"<th>{h}</th>" for h in headers)
        html += "</tr></thead><tbody>"
        for row in records:
            html += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        html += "</tbody></table>"

        return Response(html, content_type="text/html")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Upload Excel Failed")
        return Response(f"Server Error: {str(e)}", status=500)


@frappe.whitelist()
def download_excel():
    try:
        uploaded_file = frappe.request.files.get("file")
        excel_type = frappe.form_dict.get("excel_type")

        if not uploaded_file:
            return Response("No file received", status=400)

        file_stream = uploaded_file.stream.read()
        records = extract_attendance_records(file_stream, excel_type)

        out_wb = Workbook()
        out_ws = out_wb.active
        out_ws.title = "Formatted Attendance"

        headers = [
            "Attendance Device Id",
            "Attendance Device",
            "Employee Name",
            "Attendance Date",
            "Shift",
            "In Time",
            "Out Time",
        ]
        out_ws.append(headers)

        for row in records:
            out_ws.append(row)

        output = io.BytesIO()
        out_wb.save(output)
        output.seek(0)

        return Response(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=Formatted_Attendance.xlsx"
            },
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Download Excel Failed")
        return Response(f"Server Error: {str(e)}", status=500)


def process_Opticode_final(sheet):
    records = []
    seen = set()  # Track unique records

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

            # Convert times
            in_time_str = in_time
            out_time_str = out_time

            unique_key = (str(device_id), date_key, in_time_str, out_time_str)
            if unique_key in seen:
                continue
            seen.add(unique_key)

            records.append(
                [
                    str(device_id),
                    "ESSL",
                    emp_name.strip(),
                    date_str,
                    "Regular",
                    in_time_str,
                    out_time_str,
                ]
            )

        except Exception as e:
            frappe.log_error(
                f"Error processing Opticode row: {e}", "Opticode Formatter"
            )

    return records


def process_Pinnacle(sheet):
    ws = sheet
    raw_period = ws["C3"].value
    start_date_str = raw_period.split("~")[0].strip()
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    formatted_period = start_date.strftime("%b-%Y")
    dates = [cell.value for cell in ws[4] if isinstance(cell.value, int)]

    records = []
    row = 5
    while True:
        if not ws.cell(row=row, column=1).value:
            break
        if ws.cell(row=row, column=1).value == "ID:":
            device_id = str(ws.cell(row=row, column=3).value or "").strip()
            emp_name = str(ws.cell(row=row, column=11).value or "").strip()
            time_log_row = row + 1

            for col_index, day in enumerate(dates, start=1):
                time_log = ws.cell(row=time_log_row, column=col_index).value
                if isinstance(time_log, str):
                    time_log = time_log.strip()
                    if len(time_log) >= 10:
                        in_time = time_log[:5]
                        out_time = time_log[-5:]
                    elif len(time_log) == 5:
                        in_time = time_log
                        out_time = ""
                    else:
                        continue

                    date_obj = datetime.strptime(
                        f"{day:02d}-{formatted_period}", "%d-%b-%Y"
                    )
                    formatted_date = date_obj.strftime("%d-%b-%Y")
                    records.append(
                        [
                            device_id,
                            "zicom",
                            emp_name,
                            formatted_date,
                            "Regular",
                            in_time,
                            out_time,
                        ]
                    )
            row += 2
        else:
            row += 1

    return records


def parse_date_safe(date_val):
    if isinstance(date_val, datetime):
        return date_val
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(date_val), fmt)
        except Exception:
            continue
    return None


def format_time_string(t):
    if isinstance(t, datetime):
        return t.strftime("%H:%M:%S")
    elif t:
        return str(t).strip()
    return None


def parse_time_safe(value):
    """Ensure time is parsed and returned in HH:MM:SS format."""
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        value = value.strip()
        # Handle formats like "09:45", "9:45", "19:18"
        for fmt in ("%H:%M:%S", "%H:%M", "%H:%M:%S %p"):
            try:
                return datetime.strptime(value, fmt).time()
            except:
                continue
    return None


@frappe.whitelist()
def generate_final_sheet():
    attendance_logs = defaultdict(list)
    seen_entries = set()
    files = frappe.request.files.getlist("files[]")

    if not files:
        return Response("❌ No files received", status=400)

    for file in files:
        try:
            file_stream = file.stream.read()
            wb = load_workbook(filename=io.BytesIO(file_stream), data_only=True)
            sheet = wb.active

            header_row = [
                cell.value.strip() if isinstance(cell.value, str) else cell.value
                for cell in sheet[1]
            ]
            col_index = {header: idx for idx, header in enumerate(header_row)}

            required_fields = [
                "Attendance Device Id",
                "Attendance Device",
                "Employee Name",
                "Attendance Date",
                "Shift",
                "In Time",
                "Out Time",
            ]
            missing = [f for f in required_fields if f not in col_index]
            if missing:
                frappe.log_error(
                    f"Missing columns in {file.filename}: {missing}",
                    "generate_final_sheet",
                )
                continue

            for row in sheet.iter_rows(min_row=2, values_only=True):
                try:
                    device = row[col_index["Attendance Device"]]
                    device_id = row[col_index["Attendance Device Id"]]
                    emp_id = frappe.db.get_value(
                        "Attendance Device ID Allotment",
                        {"device": device, "device_id": device_id},
                        "parent",
                    )
                    if not emp_id:
                        continue

                    date_val = row[col_index["Attendance Date"]]

                    shift = row[col_index["Shift"]]
                    in_time_raw = row[col_index["In Time"]]
                    if in_time_raw is None:
                        in_time = frappe.db.sql(
                            """
                                                    SELECT time(time) FROM `tabEmployee Checkin`
                                                    WHERE employee = %s AND date(time) = %s AND log_type = 'IN'
                                                """,
                            (emp_id, (parse_date_safe(date_val)).date()),
                            as_dict=True,
                        )
                        in_time_raw = in_time[0]["time(time)"] if in_time else None
                    out_time_raw = row[col_index["Out Time"]]
                    if out_time_raw is None:
                        out_time = frappe.db.sql(
                            """
                                                    SELECT time(time) FROM `tabEmployee Checkin`
                                                    WHERE employee = %s AND date(time) = %s AND log_type = 'OUT'
                                                """,
                            (emp_id, (parse_date_safe(date_val)).date()),
                            as_dict=True,
                        )
                        out_time_raw = out_time[0]["time(time)"] if out_time else None
                    date_obj = parse_date_safe(date_val)
                    if not date_obj:
                        continue

                    date_key = date_obj.date()
                    in_str = format_time_string(in_time_raw)
                    out_str = format_time_string(out_time_raw)

                    if not in_str and not out_str:
                        continue

                    unique_key = (emp_id, date_key, in_str, out_str)
                    if unique_key in seen_entries:
                        continue
                    seen_entries.add(unique_key)

                    attendance_logs[emp_id].append(
                        {
                            "date": date_key,
                            "shift": (
                                shift.strip() if isinstance(shift, str) else "Regular"
                            ),
                            "in_time": in_str,
                            "out_time": out_str,
                        }
                    )
                    print(f"Processed: {emp_id}, {date_key}, {in_str}, {out_str}")
                except Exception as row_err:
                    frappe.log_error(f"Row error: {row_err}", "generate_final_sheet")

        except Exception as file_err:
            frappe.log_error(frappe.get_traceback(), f"File error: {file.filename}")

    final_attendance = {}
    today = datetime.today().date()

    for emp_id, logs in attendance_logs.items():
        daily_summary = {}
        for log in logs:
            date = log["date"]
            key = str(date)

            in_time = parse_time_safe(log.get("in_time"))
            out_time = parse_time_safe(log.get("out_time"))

            if key not in daily_summary:
                daily_summary[key] = {
                    "date": date,
                    "shift": log["shift"],
                    "min_in_time": in_time,
                    "max_out_time": out_time,
                }
            else:
                daily_summary[key]["min_in_time"] = min(
                    daily_summary[key]["min_in_time"], in_time
                )
                daily_summary[key]["max_out_time"] = max(
                    daily_summary[key]["max_out_time"], out_time
                )

        if str(today) not in daily_summary:
            checkins = frappe.db.sql(
                """
                SELECT time(time) FROM `tabEmployee Checkin`
                WHERE employee = %s AND date(time) = %s
            """,
                (emp_id, today),
                as_dict=True,
            )

            parsed_times = [
                parse_time_safe(str(r["time(time)"]))
                for r in checkins
                if r.get("time(time)")
            ]
            if parsed_times:
                daily_summary[str(today)] = {
                    "date": today,
                    "shift": "Regular",
                    "min_in_time": min(parsed_times),
                    "max_out_time": max(parsed_times),
                }

        final_attendance[emp_id] = [
            {
                "employee": emp_id,
                "attendance_date": entry["date"],
                "shift": entry["shift"],
                "in_time": entry["min_in_time"].strftime("%H:%M:%S"),
                "out_time": entry["max_out_time"].strftime("%H:%M:%S"),
            }
            for entry in daily_summary.values()
        ]

    return {
        "message": "✅ Attendance extracted successfully",
        "total_employees": len(final_attendance),
        "total_records": sum(len(logs) for logs in final_attendance.values()),
        "data": final_attendance,
    }


@frappe.whitelist()
def download_final_attendance_excel():
    """
    Downloads the final formatted attendance sheet generated by `generate_final_sheet()`.
    """
    try:
        result = generate_final_sheet()
        data = result.get("data", {})

        wb = Workbook()
        ws = wb.active
        ws.title = "Final Attendance"

        # Write headers
        headers = ["Employee", "Date", "Shift", "In Time", "Out Time"]
        ws.append(headers)

        # Write rows
        for emp_id, records in data.items():
            for rec in records:
                ws.append(
                    [
                        rec.get("employee"),
                        (
                            rec.get("attendance_date").strftime("%d-%b-%Y")
                            if isinstance(rec.get("attendance_date"), (str, datetime))
                            else str(rec.get("attendance_date"))
                        ),
                        rec.get("shift"),
                        rec.get("in_time"),
                        rec.get("out_time"),
                    ]
                )

        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return Response(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=Final_Attendance.xlsx"
            },
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Download Final Attendance Failed")
        return Response(f"Server Error: {str(e)}", status=500)


@frappe.whitelist()
def preview_final_attendance_sheet():
    """
    Calls `generate_final_sheet()` and returns an HTML preview
    of the final formatted attendance data.
    """
    from frappe.utils.response import Response

    try:
        result = generate_final_sheet()
        data = result.get("data", {})

        # Start building HTML table
        html = '<table class="table table-bordered table-sm"><thead><tr>'
        headers = ["Employee", "Date", "Shift", "In Time", "Out Time"]
        html += "".join(f"<th>{col}</th>" for col in headers)
        html += "</tr></thead><tbody>"

        for emp_id in sorted(data.keys()):
            for record in data[emp_id]:
                html += "<tr>"
                html += f"<td>{record.get('employee')}</td>"
                html += f"<td>{record.get('attendance_date')}</td>"
                html += f"<td>{record.get('shift')}</td>"
                html += f"<td>{record.get('in_time')}</td>"
                html += f"<td>{record.get('out_time')}</td>"
                html += "</tr>"

        html += "</tbody></table>"

        return Response(html, content_type="text/html")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Preview Final Attendance Error")
        return Response("❌ Failed to generate preview", status=500)
