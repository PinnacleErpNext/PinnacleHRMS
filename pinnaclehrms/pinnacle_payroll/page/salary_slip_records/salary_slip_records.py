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
from frappe.utils import flt
from pinnaclehrms.utility.permission import is_user_allowed_for_report


import io
import zipfile


from frappe.utils.pdf import get_pdf


@frappe.whitelist()
def getSalarySlipRecords(company, year, month, employee=None):
    # --- User access check ---
    if not is_user_allowed_for_report(
        source_name="Salary Register", source_type="Report"
    ):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app/home"
        return
    year = int(year)
    month = int(month)

    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)

    filters = {
        "company": company,
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

        # Deductions
        deductions_total = 0
        deductions_info = []

        for d in pay_slip.deductions:
            amount = flt(d.amount)

            deductions_total += amount

            deductions_info.append(
                {
                    "component": d.salary_component,
                    "amount": amount,
                }
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
            "status": pay_slip.status,
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
            "deductions": deductions_info,
            "deductions_total": deductions_total,
            "total_deduction": pay_slip.total_deduction,
        }

        # print(pay_slip_dict)
        result.append(pay_slip_dict)

    return result


@frappe.whitelist()
def download_pay_slip_report(year=None, month=None, encodedCompany=None):

    company = base64.b64decode(encodedCompany).decode("utf-8")

    curr_user = frappe.session.user

    allowed_roles = ["System Manager"]

    user_roles = frappe.get_roles(curr_user)

    # --- User access check ---
    if not is_user_allowed_for_report(
        source_name="Salary Register", source_type="Report"
    ):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app/home"
        return

    if not year or not month:
        frappe.throw(_("Year and Month are required"))

    records = getSalarySlipRecords(company=company, year=year, month=month)

    if not records:
        frappe.throw(_("No data found for the given filters."))

    # Attendance columns in the required order
    attendance_keys = [
        "Full Day",
        "Sundays",
        "Half Day",
        "3/4 Day",
        "Quarter Day",
        "Lates",
        "Absent",
    ]

    salary_info_keys = set()
    earnings_keys = set()
    other_earning_keys = set()
    deduction_keys = set()

    for r in records:

        for key in r.get("salary_info", {}).keys():
            if key:
                salary_info_keys.add(key)

        for earning in r.get("earnings", []):
            if earning.get("component"):
                earnings_keys.add(earning.get("component"))

        for earning in r.get("other_earnings", []):
            if earning.get("component"):
                other_earning_keys.add(earning.get("component"))

        for deduction in r.get("deductions", []):
            if deduction.get("component"):
                deduction_keys.add(deduction.get("component"))

    # Keep attendance columns in the specified order
    attendance_columns = [key for key in attendance_keys if key in salary_info_keys]

    # Include any additional attendance particulars
    attendance_columns += sorted(salary_info_keys - set(attendance_columns))

    earnings_keys = sorted(earnings_keys)
    other_earning_keys = sorted(other_earning_keys)
    deduction_keys = sorted(deduction_keys)

    static_columns = [
        "Salary Slip",
        "Status",
        "Employee Name",
        "Email",
        "Joining Date",
        "Basic Salary",
        "Standard Days",
        "Actual Days",
    ]

    header_row_1 = (
        static_columns
        + attendance_columns
        + ["Total"]
        + ["Earnings"] * len(earnings_keys)
        + ["Other Earnings"] * len(other_earning_keys)
        + ["Deductions"] * len(deduction_keys)
        + ["Total Deduction", "Deductions Total", "Net Pay"]
    )

    header_row_2 = (
        [""] * (len(static_columns) + len(attendance_columns) + 1)
        + earnings_keys
        + other_earning_keys
        + deduction_keys
        + ["", "", ""]
    )

    data_rows = []

    for r in records:

        row = [
            r.get("pay_slip_name"),
            r.get("status"),
            r.get("employee_name"),
            r.get("email"),
            r.get("date_of_joining"),
            r.get("basic_salary"),
            r.get("standard_working_days"),
            r.get("actual_working_days"),
        ]

        # Attendance days
        salary_info = r.get("salary_info", {})

        for key in attendance_columns:
            info = salary_info.get(key, {})
            row.append(info.get("days", 0))

        # Total
        row.append(r.get("total"))

        # Earnings
        earnings_map = {
            e.get("component"): e.get("amount")
            for e in r.get("earnings", [])
            if e.get("component")
        }

        for key in earnings_keys:
            row.append(earnings_map.get(key, 0))

        # Other Earnings
        other_earnings_map = {
            e.get("component"): e.get("amount")
            for e in r.get("other_earnings", [])
            if e.get("component")
        }

        for key in other_earning_keys:
            row.append(other_earnings_map.get(key, 0))

        # Deductions
        deductions_map = {
            d.get("component"): d.get("amount")
            for d in r.get("deductions", [])
            if d.get("component")
        }

        for key in deduction_keys:
            row.append(deductions_map.get(key, 0))

        # Deduction totals and Net Pay
        row.append(r.get("total_deduction"))
        row.append(r.get("deductions_total"))
        row.append(r.get("net_payable_amount"))

        data_rows.append(row)

    xlsx_data = make_xlsx(
        data=[header_row_1, header_row_2] + data_rows,
        sheet_name="Pay Slip Report",
    )

    filename = f"{company.replace(' ', '_')}_Pay_Slip_Report_{calendar.month_name[int(month)]}_{year}.xlsx"

    frappe.response.filename = filename

    frappe.response.filecontent = xlsx_data.getvalue()

    frappe.response.type = "binary"


@frappe.whitelist()
def download_idfc_blkpay(year=None, month=None, encodedCompany=None):
    import base64
    import calendar
    from datetime import date
    from io import BytesIO

    import frappe
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    # --- Decode and validate company ---
    company = base64.b64decode(encodedCompany).decode("utf-8")
    company_abbr = frappe.db.get_value("Company", company, "abbr")

    # --- User access check ---
    if not is_user_allowed_for_report(
        source_name="Salary Register", source_type="Report"
    ):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app/home"
        return

    # --- Validate input month & year ---
    if not month or not year:
        frappe.throw("Please specify a month and year")

    try:
        m = int(month)
        year = int(year)

        if not (1 <= m <= 12):
            frappe.throw("Month must be between 1 and 12")

    except ValueError:
        frappe.throw("Invalid month format")

    last_day = calendar.monthrange(year, m)[1]
    last_date = date(year, m, last_day)

    formatted_date_for_filename = last_date.strftime("%d%m%Y")

    # ---------------------------------------------------
    # FETCH DATA FROM SALARY SLIP INSTEAD OF PAY SLIPS
    # ---------------------------------------------------
    query = """
        SELECT
            emp.ifsc_code AS ifsc,
            emp.bank_ac_no AS beneficiary_account_no,
            ss.employee_name AS beneficiary_name,
            ss.company,
            ss.net_pay AS amount
        FROM `tabSalary Slip` ss
        INNER JOIN `tabEmployee` emp
            ON emp.name = ss.employee
        WHERE
            MONTH(ss.end_date) = %(month)s
            AND YEAR(ss.end_date) = %(year)s
            AND ss.company = %(company)s
            AND IFNULL(ss.net_pay, 0) > 0
    """

    params = {
        "month": m,
        "year": year,
        "company": company,
    }

    data = frappe.db.sql(query, params, as_dict=True)

    if not data:
        frappe.throw("No submitted Salary Slips found for selected month and company")

    # --- Debit account map ---
    company_debit_map = {
        "Opticodes Technologies Private Limited": "10238672140",
        "Pinnacle Finserv Advisors Pvt. Ltd.": "10237782223",
    }

    today = date.today()

    # --- Column configuration ---
    columns = [
        {"header": "Beneficiary Name", "width": 30},
        {"header": "Beneficiary Account No", "width": 25},
        {"header": "IFSC", "width": 20},
        {"header": "Transaction Type", "width": 20},
        {"header": "Debit Account Number", "width": 30},
        {"header": "Transaction Date", "width": 20},
        {"header": "Amount (₹)", "width": 15},
        {"header": "Currency", "width": 10},
    ]

    # --- Prepare row data ---
    rows = []

    for r in data:
        debit_account = company_debit_map.get(r.company, "")

        rows.append(
            [
                r.beneficiary_name or "",
                str(r.beneficiary_account_no or ""),
                r.ifsc or "",
                "NEFT",
                debit_account,
                today.strftime("%d/%m/%Y"),
                flt(r.amount, 2),
                "INR",
            ]
        )

    # --- Build Excel file ---
    wb = Workbook()
    ws = wb.active
    ws.title = "IDFC BLKPAY"

    # --- Header Row ---
    for col_num, col in enumerate(columns, 1):
        col_letter = ws.cell(row=1, column=col_num).column_letter

        ws.merge_cells(f"{col_letter}1:{col_letter}2")

        cell = ws.cell(row=1, column=col_num, value=col["header"])

        ws.column_dimensions[col_letter].width = col["width"]

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

        cell.font = Font(bold=True)

    # --- Write data rows ---
    start_row = 3

    for row_idx, row_data in enumerate(rows, start_row):

        for col_idx, value in enumerate(row_data, 1):

            header = columns[col_idx - 1]["header"]

            cell = ws.cell(
                row=row_idx,
                column=col_idx,
                value=value,
            )

            # Keep account numbers as text
            if header in ["Beneficiary Account No", "IFSC"]:
                cell.number_format = "@"

            elif header == "Amount (₹)":
                cell.number_format = "0.00"
                cell.alignment = Alignment(horizontal="right")

            else:
                cell.alignment = Alignment(horizontal="left")

    # --- Save workbook to memory ---
    output = BytesIO()

    wb.save(output)

    output.seek(0)

    # --- Set response ---
    frappe.response.filename = f"{company_abbr}{formatted_date_for_filename}.xlsx"

    frappe.response.filecontent = output.getvalue()
    frappe.response.type = "binary"


@frappe.whitelist()
def email_pay_slips(pay_slips=None):

    # --- User access check ---
    if not is_user_allowed_for_report(
        source_name="Salary Register", source_type="Report"
    ):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app/home"
        return

    if not pay_slips:
        frappe.throw(_("Please select at least one Salary Slip."))

    # Handle JSON string or Python list
    if isinstance(pay_slips, str):
        try:
            pay_slips = json.loads(pay_slips)
        except json.JSONDecodeError:
            frappe.throw(_("Invalid Salary Slip data."))

    if not isinstance(pay_slips, list):
        frappe.throw(_("Invalid Salary Slip selection."))

    sent_count = 0
    failed_emails = []

    for salary_slip_name in pay_slips:

        if salary_slip_name == "on":
            continue

        # Fetch standard ERPNext Salary Slip
        doc = frappe.get_doc("Salary Slip", salary_slip_name)

        employee_name = doc.employee_name
        employee = doc.employee

        # Fetch Employee Email
        email = frappe.db.get_value("Employee", employee, "company_email")

        if not email:
            failed_emails.append(employee_name)
            continue

        # Salary Slip Period
        start_date = doc.start_date
        end_date = doc.end_date

        subject = f"Salary Slip for {employee_name} ({start_date} to {end_date})"

        # Render Email Template
        context = {"doc": doc}

        message = frappe.render_template("templates/salary_slip.html", context)

        # Generate Salary Slip PDF using the same custom template as print_pay_slip
        html = frappe.render_template("templates/salary_slip.html", {"doc": doc})
        pdf_bytes = get_pdf(html)

        pdf_data = {
            "fname": f"Salary_Slip_{salary_slip_name}.pdf",
            "fcontent": pdf_bytes,
        }

        # Send Email
        frappe.sendmail(
            recipients=[email],
            cc=["records@mygstcafe.in"],
            subject=subject,
            message=message,
            attachments=[pdf_data],
        )

        sent_count += 1

    return {
        "message": "success" if sent_count else "failed",
        "sent_count": sent_count,
        "failed_emails": failed_emails,
    }


@frappe.whitelist()
def print_pay_slip(pay_slips, year=None, month=None):

    # --- User access check ---
    if not is_user_allowed_for_report(
        source_name="Salary Register", source_type="Report"
    ):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app/home"
        return

    # Parse JSON list of Salary Slip names
    if isinstance(pay_slips, str):
        try:
            pay_slips = json.loads(pay_slips)
        except json.JSONDecodeError:
            frappe.throw(_("Invalid Salary Slip selection."))

    if not isinstance(pay_slips, list) or not pay_slips:
        frappe.throw(_("Please select at least one Salary Slip."))

    # In-memory ZIP stream
    zip_stream = io.BytesIO()

    # Track generated filenames to avoid duplicates
    generated_pay_slips = []

    with zipfile.ZipFile(
        zip_stream, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as zipf:

        for pay_slip in pay_slips:

            # Fetch standard ERPNext Salary Slip
            doc = frappe.get_doc("Salary Slip", pay_slip)

            context = {"doc": doc}

            # Render HTML using the same template used for emailing
            html = frappe.render_template("templates/salary_slip.html", context)

            # Generate PDF
            pdf_bytes = get_pdf(html)

            # Generate filename
            filename = f"{doc.employee_name}_{doc.start_date}_{doc.end_date}.pdf"

            # Avoid duplicate filenames
            if filename in generated_pay_slips:
                filename = f"{doc.name}.pdf"

            generated_pay_slips.append(filename)

            # Add PDF to ZIP
            zipf.writestr(filename, pdf_bytes)

    # Reset stream position
    zip_stream.seek(0)

    # Set ZIP response
    month_name = calendar.month_name[int(month)] if month else "Salary_Slips"

    frappe.response.filename = f"{month_name}_{year or ''}_pay_slips.zip"
    frappe.response.filecontent = zip_stream.read()
    frappe.response.type = "download"
    frappe.response.content_type = "application/zip"
