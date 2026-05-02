import frappe
import calendar
import base64
import json

from datetime import date, timedelta
from io import BytesIO

from frappe import _
from frappe.utils import get_datetime
from frappe.utils.xlsxutils import make_xlsx

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font


@frappe.whitelist()
def getSalarySlipRecords(company, year, month, employee=None):
    year = int(year)
    month = int(month)

    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)

    filters = {
        "company": company,
        "docstatus": 1,
        "start_date": [">=", start_date],
        "end_date": ["<=", end_date],
    }

    if employee:
        filters["employee"] = employee

    salary_slips = frappe.get_all("Salary Slip", filters=filters, pluck="name")

    result = []

    for slip_name in salary_slips:
        pay_slip = frappe.get_doc("Salary Slip", slip_name)

        # Salary Breakup
        salary_info = {}
        for sal in pay_slip.salary_breakup:
            salary_info[sal.particulars] = {
                "days": sal.days,
                "amount": sal.amount,
            }

        # Earnings
        basic_salary = 0
        other_earnings_total = 0
        other_earnings_info = []

        for e in pay_slip.earnings:
            if e.salary_component == "Basic":
                basic_salary += e.amount
            else:
                other_earnings_total += e.amount
                other_earnings_info.append(
                    {"component": e.salary_component, "amount": e.amount}
                )

        # Employee info
        emp = (
            frappe.db.get_value(
                "Employee",
                pay_slip.employee,
                ["company_email", "pan_number", "date_of_joining"],
                as_dict=True,
            )
            or {}
        )

        pay_slip_dict = {
            "pay_slip_name": pay_slip.name,
            "year": year,
            "month": month,
            "employee": pay_slip.employee,
            "employee_name": pay_slip.employee_name,
            "company": pay_slip.company,
            "designation": pay_slip.designation,
            "department": pay_slip.department,
            "email": emp.get("company_email"),
            "standard_working_days": pay_slip.total_working_days,
            "pan_number": emp.get("pan_number"),
            "date_of_joining": emp.get("date_of_joining"),
            "basic_salary": basic_salary,
            "per_day_salary": (
                basic_salary / pay_slip.total_working_days
                if pay_slip.total_working_days
                else 0
            ),
            "actual_working_days": pay_slip.payment_days,
            "absent": pay_slip.absent_days,
            "total": pay_slip.gross_pay,
            "net_payable_amount": pay_slip.net_pay,
            "salary_info": salary_info,
            "other_earnings": other_earnings_info,
            "other_earnings_total": other_earnings_total,
        }

        print(pay_slip_dict)
        result.append(pay_slip_dict)

    return result


@frappe.whitelist()
def download_pay_slip_report(year=None, month=None, encodedCompany=None):
    company = base64.b64decode(encodedCompany).decode("utf-8")

    curr_user = frappe.session.user
    allowed_roles = ["System Manager"]
    user_roles = frappe.get_roles(curr_user)

    if (
        any(role in user_roles for role in allowed_roles)
        and curr_user != "Administrator"
    ):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app/home"
        return

    if not year or not month:
        frappe.throw(_("Year and Month are required"))

    records = getSalarySlipRecords(company=company, year=year, month=month)

    if not records:
        frappe.throw(_("No data found for the given filters."))

    static_columns = [
        "Pay Slip Name",
        "Year",
        "Month",
        "Employee ID",
        "Employee Name",
        "Company",
        "Designation",
        "Department",
        "Personal Email",
        "Standard Working Days",
        "PAN Number",
        "Date of Joining",
        "Basic Salary",
        "Per Day Salary",
        "Actual Working Days",
        "Absent",
        "Total",
        "Net Payable Amount",
    ]

    salary_info_keys = set()
    other_earning_keys = set()

    for r in records:
        for key in r.get("salary_info", {}).keys():
            if key:
                salary_info_keys.add(key)

        for earning in r.get("other_earnings", []):
            if earning.get("component"):
                other_earning_keys.add(earning.get("component"))

    salary_info_keys = sorted(salary_info_keys)
    other_earning_keys = sorted(other_earning_keys)

    header_row_1 = (
        static_columns
        + ["Salary Info"] * (len(salary_info_keys) * 2)
        + ["Other Earnings"] * len(other_earning_keys)
    )

    header_row_2 = [""] * len(static_columns)

    for key in salary_info_keys:
        header_row_2 += [f"{key} - Days", f"{key} - Amount"]

    for key in other_earning_keys:
        header_row_2.append(f"{key} - Amount")

    data_rows = []

    for r in records:
        row = [
            r.get("pay_slip_name"),
            r.get("year"),
            r.get("month"),
            r.get("employee"),
            r.get("employee_name"),
            r.get("company"),
            r.get("designation"),
            r.get("department"),
            r.get("email"),
            r.get("standard_working_days"),
            r.get("pan_number"),
            r.get("date_of_joining"),
            r.get("basic_salary"),
            r.get("per_day_salary"),
            r.get("actual_working_days"),
            r.get("absent"),
            r.get("total"),
            r.get("net_payable_amount"),
        ]

        salary_info = r.get("salary_info", {})
        for key in salary_info_keys:
            info = salary_info.get(key, {})
            row.append(info.get("days", 0))
            row.append(info.get("amount", 0))

        earnings_map = {
            e.get("component"): e.get("amount")
            for e in r.get("other_earnings", [])
            if e.get("component")
        }

        for key in other_earning_keys:
            row.append(earnings_map.get(key, 0))

        data_rows.append(row)

    xlsx_data = make_xlsx(
        data=[header_row_1, header_row_2] + data_rows,
        sheet_name="Pay Slip Report",
    )

    filename = f"{company.replace(' ', '_')}_Pay_Slip_Report_{calendar.month_name[int(month)]}_{year}.xlsx"

    frappe.response.filename = filename
    frappe.response.filecontent = xlsx_data.getvalue()
    frappe.response.type = "binary"
