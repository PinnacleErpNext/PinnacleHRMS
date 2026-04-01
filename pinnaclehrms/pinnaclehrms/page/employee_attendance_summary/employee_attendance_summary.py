import frappe
from collections import defaultdict
from frappe.utils import get_datetime, getdate
from datetime import timedelta
from openpyxl import Workbook
from frappe.utils.file_manager import save_file
from io import BytesIO


def load_shifts():
    global shifts

    shift_docs = frappe.get_all("Shift Type", fields=["name", "start_time", "end_time"])
    shifts = {}

    for s in shift_docs:
        shifts[s.name] = {"start_time": s.start_time, "end_time": s.end_time}
    return shifts

load_shifts()

@frappe.whitelist()
def get_data(company=None, employee=None, from_date=None, to_date=None):

    filters = {"attendance_date": ["between", [from_date, to_date]], "docstatus": 1}

    if company:
        filters["company"] = company

    if employee:
        filters["employee"] = employee

    attendances = frappe.get_all(
        "Attendance",
        fields=[
            "employee",
            "employee_name",
            "attendance_date",
            "in_time",
            "out_time",
            "shift",
            "company",
        ],
        filters=filters,
    )

    result = defaultdict(
        lambda: {
            "employee": "",
            "employee_name": "",
            "full_day": 0,
            "lates": 0,
            "three_quarter_day": 0,
            "half_day": 0,
            "quarter_day": 0,
            "others_day": 0,
            "sunday_workings": 0,
            "absent": 0,
            "gross_total": 0,
            "total": 0,
        }
    )

    for att in attendances:

        emp = att.employee
        result[emp]["employee"] = att.employee
        result[emp]["employee_name"] = att.employee_name

        date = getdate(att.attendance_date)

        if date.weekday() == 6:
            result[emp]["sunday_workings"] += 1
            continue

        particulars = calculate_particulars(att)

        if particulars == "Full Day":
            result[emp]["full_day"] += 1

        elif particulars == "Late/Early":
            result[emp]["lates"] += 1

        elif particulars == "3/4 Day":
            result[emp]["three_quarter_day"] += 1

        elif particulars == "Half Day":
            result[emp]["half_day"] += 1

        elif particulars == "Quarter Day":
            result[emp]["quarter_day"] += 1

        elif particulars == "Absent":
            result[emp]["absent"] += 1

        else:
            result[emp]["others_day"] += 1

    for emp in result:

        r = result[emp]

        r["gross_total"] = (
            r["full_day"]
            + r["lates"]
            + r["three_quarter_day"]
            + r["half_day"]
            + r["quarter_day"]
            + r["others_day"]
            + r["sunday_workings"]
        )

        r["total"] = r["gross_total"] + r["absent"]

    return list(result.values())


def calculate_particulars(att):

    if not att.get("in_time") or not att.get("out_time"):
        return "Absent"

    if not att.get("shift"):
        return "Full Day"

    shift_doc = shifts.get(att.shift)

    shift_start = shift_doc.get("start_time")
    shift_end = shift_doc.get("end_time")
    if not shift_start or not shift_end:
        return "Full Day"

    shift_start = get_datetime(f"{att.attendance_date} {shift_start}")
    shift_end = get_datetime(f"{att.attendance_date} {shift_end}")

    if shift_end < shift_start:
        shift_end += timedelta(days=1)

    ideal_working_time = shift_end - shift_start
    total_minutes = ideal_working_time.total_seconds() / 60 or 1

    in_time = get_datetime(att.in_time)
    out_time = get_datetime(att.out_time)

    late_minutes = (in_time - shift_start).total_seconds() / 60
    early_minutes = (shift_end - out_time).total_seconds() / 60

    if late_minutes > total_minutes * 0.75 or early_minutes > total_minutes * 0.75:
        return "Quarter Day"

    if late_minutes > total_minutes * 0.50 or early_minutes > total_minutes * 0.50:
        return "Half Day"

    if late_minutes > total_minutes * 0.25 or early_minutes > total_minutes * 0.25:
        return "3/4 Day"

    if late_minutes > 0 and early_minutes > 0:
        return "Late/Early"

    if late_minutes > 0 or early_minutes > 0:
        return "Late/Early"

    return "Full Day"


@frappe.whitelist()
def get_employee_month_breakdown(employee, company=None, from_date=None, to_date=None):

    filters = {
        "employee": employee,
        "attendance_date": ["between", [from_date, to_date]],
        "docstatus": 1,
    }

    if company:
        filters["company"] = company

    attendances = frappe.get_all(
        "Attendance",
        fields=["attendance_date", "in_time", "out_time", "shift"],
        filters=filters,
    )

    result = defaultdict(
        lambda: {
            "month": "",
            "year": "",
            "full_day": 0,
            "lates": 0,
            "three_quarter_day": 0,
            "half_day": 0,
            "quarter_day": 0,
            "others_day": 0,
            "sunday_workings": 0,
            "absents": 0,
            "gross_total": 0,
            "total": 0,
        }
    )

    for att in attendances:

        date = getdate(att.attendance_date)
        key = f"{date.year}-{date.month}"

        if not result[key]["month"]:
            result[key]["month"] = date.strftime("%B")
            result[key]["year"] = date.year

        if date.weekday() == 6:
            result[key]["sunday_workings"] += 1
            continue

        particulars = calculate_particulars(att)

        if particulars == "Full Day":
            result[key]["full_day"] += 1

        elif particulars == "Late/Early":
            result[key]["lates"] += 1

        elif particulars == "3/4 Day":
            result[key]["three_quarter_day"] += 1

        elif particulars == "Half Day":
            result[key]["half_day"] += 1

        elif particulars == "Quarter Day":
            result[key]["quarter_day"] += 1

        elif particulars == "Absent":
            result[key]["absents"] += 1

        else:
            result[key]["others_day"] += 1

    for key in result:

        r = result[key]

        r["gross_total"] = (
            r["full_day"]
            + r["lates"]
            + r["three_quarter_day"]
            + r["half_day"]
            + r["quarter_day"]
            + r["others_day"]
            + r["sunday_workings"]
        )

        r["total"] = r["gross_total"] + r["absents"]

    return list(result.values())


@frappe.whitelist()
def download_excel(company=None, employee=None, from_date=None, to_date=None):

    data = get_data(company, employee, from_date, to_date)

    wb = Workbook()
    ws = wb.active
    ws.title = "Employee Attendance Summary"

    headers = [
        "Employee",
        "Employee Name",
        "Full Day",
        "Lates",
        "3/4 Quarter Day",
        "Half Day",
        "Quarter Day",
        "Others Day",
        "Sunday Workings",
        "Gross Total",
        "Absents",
        "Total",
    ]

    ws.append(headers)

    for d in data:
        ws.append(
            [
                d.get("employee"),
                d.get("employee_name"),
                d.get("full_day", 0),
                d.get("lates", 0),
                d.get("three_quarter_day", 0),
                d.get("half_day", 0),
                d.get("quarter_day", 0),
                d.get("others_day", 0),
                d.get("sunday_workings", 0),
                d.get("gross_total", 0),
                d.get("absent", 0),
                d.get("total", 0),
            ]
        )

    # Save workbook to memory
    file_stream = BytesIO()
    wb.save(file_stream)

    file_name = "Employee_Attendance_Summary.xlsx"

    file_doc = save_file(
        file_name, file_stream.getvalue(), "File", "Home", is_private=0
    )

    return file_doc.file_url
