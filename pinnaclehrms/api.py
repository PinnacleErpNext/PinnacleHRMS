import frappe, json, uuid, base64, zipfile, calendar, io
from pinnaclehrms.utility.salary_calculator import (
    createPaySlips,
    getEmpRecords,
    calculateMonthlySalary,
    getEncashment,
)
from collections import defaultdict
from frappe.utils.xlsxutils import make_xlsx
from frappe.desk.query_report import build_xlsx_data
from frappe.utils import nowdate, flt
from frappe import _
from frappe.utils import format_datetime
from frappe.utils.pdf import get_pdf
import calendar
from datetime import date


# API to get pay slips in create pay slips
@frappe.whitelist(allow_guest=True)
def get_pay_slip_list(parent_docname, month, year, company=None, employee=None):
    baseQuery = """
        SELECT
            name,
            employee_name,
            employee,
            net_payble_amount
        FROM
            `tabPay Slips`
        WHERE 
            month_num = %s AND year = %s
    """

    filters = [month, year]

    if company:
        baseQuery += " AND company = %s"
        filters.append(company)

    if employee:
        baseQuery += " AND employee = %s"
        filters.append(employee)

    # ✅ Ensure results are sorted
    baseQuery += " ORDER BY employee_name ASC, employee ASC"

    pay_slip_list = frappe.db.sql(baseQuery, filters, as_dict=True)

    created_pay_slips = []

    for idx, pay_slip in enumerate(pay_slip_list, start=1):
        generated_name = str(uuid.uuid4())  # Generate a unique ID

        # Avoid duplicates
        if not any(item["pay_slip"] == pay_slip["name"] for item in created_pay_slips):
            frappe.db.sql(
                """
                INSERT INTO `tabCreated Pay Slips` (
                    `name`, `pay_slip`, `employee`, `employee_id`, `salary`,
                    `parent`, `parenttype`, `parentfield`, `idx`
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    generated_name,  # name
                    pay_slip["name"],  # pay_slip
                    pay_slip["employee_name"],  # employee (Employee Name)
                    pay_slip["employee"],  # employee_id
                    pay_slip["net_payble_amount"],  # salary
                    parent_docname,  # parent
                    "Create Pay Slips",  # parenttype
                    "created_pay_slips",  # parentfield
                    idx,  # ✅ ensures sorted order in child table
                ),
            )

            created_pay_slips.append(
                {
                    "name": generated_name,
                    "pay_slip": pay_slip["name"],
                    "employee": pay_slip["employee_name"],  # Employee Name
                    "employee_id": pay_slip["employee"],  # Employee ID
                    "salary": pay_slip["net_payble_amount"],
                    "parent": parent_docname,
                    "parenttype": "Create Pay Slips",
                    "parentfield": "created_pay_slips",
                    "idx": idx,  # ✅ same idx for JSON return
                }
            )

    return created_pay_slips


# API to e-mail pay slips
@frappe.whitelist(allow_guest=True)
def email_pay_slips(pay_slips=None, raw_data=None):
    if pay_slips is None:
        pay_slips = []

    if raw_data is not None:
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON data provided in raw_data.")
    elif pay_slips:
        data = json.loads(pay_slips)
    else:
        raise ValueError("Either raw_data or pay_slips must be provided.")

    for item in data:
        record = frappe.db.get_value("Created Pay Slips", item, "pay_slip")
        if record:
            pay_slips.append(record)
        if raw_data:
            data = pay_slips

    for pay_slip_name in data:
        if pay_slip_name == "on":
            continue
        doc = frappe.get_doc("Pay Slips", pay_slip_name)

        employee_name = doc.employee_name
        month = doc.month
        year = doc.year
        doctype = doc.doctype
        docname = doc.name
        email = frappe.db.get_value("Employee", doc.employee, "company_email")

        subject = f"Pay Slip for {employee_name} - {month} {year}"

        # HTML email body with dynamic content
        context = {"doc": doc}  # Pass data to the template
        message = frappe.render_template(
            "pinnaclehrms/public/templates/pay_slip.html", context
        )

        # Attach the pay slip PDF
        if email:
            frappe.sendmail(
                recipients=[email],
                sender="hr@mygstcafe.in",
                cc="records@mygstcafe.in",
                subject=subject,
                message=message,
                # header=["Pay Slip Notification", "green"]
            )

            return {"message": "success"}
        else:
            frappe.throw(f"No email address found for employee {employee_name}")


# API to get pay slip report
@frappe.whitelist(allow_guest=True)
def get_pay_slip_report(year=None, month=None, curr_user=None, company=None):
    user_roles = frappe.get_roles(curr_user)

    # Step 1: Build filters based on role and params
    filters = {
        "year": year,
        "month_num": month,
    }

    if company:
        filters["company"] = company
    elif not set(user_roles).intersection({"All", "HR User", "HR Manager"}):
        # If user is not HR or Admin, restrict by employee
        employee = frappe.get_all(
            "Employee",
            filters={"email": curr_user},
            fields=["name"],
            limit=1,
        )
        if not employee:
            employee = frappe.get_all(
                "Employee",
                filters={"company_email": curr_user},
                fields=["name"],
                limit=1,
            )
        if not employee:
            frappe.throw("No Employee Data found or you don't have access!")
        filters["employee_id"] = employee[0].name

    # Step 2: Get pay slip names matching filters
    pay_slip_names = frappe.get_all("Pay Slips", filters=filters, pluck="name")

    if not pay_slip_names:
        frappe.msgprint(
            "No records found for the specified year and month.", title="Warning!"
        )
        return []

    pay_slips_data = []

    # Step 3: Loop over each pay slip and fetch full document to get child tables
    for name in pay_slip_names:
        pay_slip = frappe.get_doc("Pay Slips", name)

        # Collect salary_calculation data
        salary_info = {
            sal.particulars: {"day": sal.days, "amount": sal.amount}
            for sal in pay_slip.salary_calculation
        }

        # Collect other_earnings data
        other_earnings_info = {
            earning.component: {"amount": earning.amount}
            for earning in pay_slip.other_earnings
        }

        # Prepare combined dict for this pay slip
        pay_slip_dict = {
            "pay_slip_name": pay_slip.name,
            "year": pay_slip.year,
            "month": pay_slip.month_num,
            "employee": pay_slip.employee,
            "employee_name": pay_slip.employee_name,
            "company": pay_slip.company,
            "designation": pay_slip.designation,
            "department": pay_slip.department,
            "email": frappe.db.get_value(
                "Employee", pay_slip.employee, "company_email"
            ),
            "standard_working_days": pay_slip.standard_working_days,
            "pan_number": pay_slip.pan_number,
            "date_of_joining": pay_slip.date_of_joining,
            "basic_salary": pay_slip.basic_salary,
            "per_day_salary": pay_slip.per_day_salary,
            "actual_working_days": pay_slip.actual_working_days,
            "absent": pay_slip.absent,
            "total": pay_slip.total,
            "net_payable_amount": pay_slip.net_payble_amount,
            "salary_info": salary_info,
            "other_earnings": other_earnings_info,
            "other_earnings_total": pay_slip.other_earnings_total,
        }

        pay_slips_data.append(pay_slip_dict)

    return pay_slips_data


# API to get pay slip for pay slip request
@frappe.whitelist(allow_guest=True)
def get_pay_slip_request(date=None, requested_by=None):

    if date is None and requested_by is None:
        return frappe.throw("No date or requested by is not found")

    records = frappe.db.sql(
        """
                            SELECT name 
                            FROM `tabRequest Pay Slip` 
                            WHERE requested_date = %s OR  requested_by = %s;""",
        (date, requested_by),
        as_dict=True,
    )

    if not records:
        return frappe.throw("No requests found")

    return records


@frappe.whitelist()
def print_pay_slip(pay_slips, year=None, month=None):

    # Parse JSON list of Pay Slip names
    pay_slips = json.loads(pay_slips)

    # In-memory zip stream
    zip_stream = io.BytesIO()

    # Create zip file in memory
    with zipfile.ZipFile(
        zip_stream, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as zipf:
        for pay_slip in pay_slips:
            doc = frappe.get_doc("Pay Slips", pay_slip)
            context = {"doc": doc}

            # Render HTML from template
            html = frappe.render_template(
                "pinnaclehrms/public/templates/pay_slip.html", context
            )

            # Generate PDF from HTML
            pdf_bytes = get_pdf(html)

            generated_pay_slips = []
            filename = f"{doc.employee_name}_{doc.month}_{doc.year}.pdf"
            if filename in generated_pay_slips:
                filename = f"{doc.employee}_{doc.month}_{doc.year}.pdf"
            generated_pay_slips.append(filename)
            # Add to zip
            zipf.writestr(filename, pdf_bytes)

    # Reset stream position to start
    zip_stream.seek(0)

    # Send zip file as response
    frappe.response.filename = f"{calendar.month_name[int(month)]}_{year}_pay_slips.zip"
    frappe.response.filecontent = zip_stream.read()
    frappe.response.type = "binary"


# API get pay slip requests
@frappe.whitelist(allow_guest=True)
def getPaySlipRequests():
    records = frappe.db.get_all(
        "Request Pay Slip",
        fields=["name", "requested_date", "employee", "year", "month", "status"],
        filters={"status": "Requested"},
        order_by="creation desc",
    )

    return records


# API to approve pay slip request
@frappe.whitelist(allow_guest=True)
def approvePaySlipRequest(data):
    data = json.loads(data)

    # Check if a Pay Slip exists for the given employee, month, and year
    if frappe.db.exists(
        "Pay Slips",
        {
            "employee_id": data["select_employee"],
            "month_num": data["month"],
            "year": data["year"],
        },
    ):
        # Fetch the Pay Slip document
        paySlip = frappe.get_doc(
            "Pay Slips",
            {
                "employee_id": data["select_employee"],
                "month_num": data["month"],
                "year": data["year"],
            },
        )
    else:
        createPaySlips(data)
        paySlip = frappe.get_doc(
            "Pay Slips",
            {
                "employee_id": data["select_employee"],
                "month_num": data["month"],
                "year": data["year"],
            },
        )

    employee_name = paySlip.employee_name
    month = paySlip.month
    year = paySlip.year
    doctype = paySlip.doctype
    docname = paySlip.name
    email = paySlip.email
    subject = f"Pay Slip for {employee_name} - {month} {year}"
    message = f"""
    Dear {employee_name},
    Please find attached your pay slip for {month} {year}.
    Best regards,
    Your Company
    """
    pdf_attachment = frappe.attach_print(
        doctype, docname, file_name=f"Pay Slip {docname}"
    )

    if email:
        frappe.sendmail(
            recipients=[email],
            subject=subject,
            message=message,
            attachments=[
                {"fname": f"Pay Slip - {employee_name}.pdf", "fcontent": pdf_attachment}
            ],
        )
        return {"message": ("Success")}
    else:
        frappe.throw(f"No email address found for employee {employee_name}")


# API to regenerate pay slip
@frappe.whitelist(allow_guest=True)
def regeneratePaySlip(data, parent=None):

    data = json.loads(data)

    year = int(data.get("year"))
    month = data.get("month")

    empRecords = getEmpRecords(data)

    employeeData = calculateMonthlySalary(empRecords, year, month)

    # frappe.throw(str(employeeData))

    for emp_id, data in employeeData.items():
        otherEarningsAmount = 0.0
        month_mapping = {
            1: "January",
            2: "February",
            3: "March",
            4: "April",
            5: "May",
            6: "June",
            7: "July",
            8: "August",
            9: "September",
            10: "October",
            11: "November",
            12: "December",
        }
        month_name = month_mapping.get(month)
        salaryInfo = data.get("salary_information", {})
        attendanceRecord = frappe.render_template(
            "pinnaclehrms/public/templates/attendance_record.html",
            {"attendance_record": data.get("attendance_records")},
        )

        fullDayWorkingAmount = round(
            (salaryInfo.get("full_days", 0) * salaryInfo.get("per_day_salary", 0)),
            2,
        )
        earlyCheckoutWorkingAmount = round(
            (
                salaryInfo.get("early_checkout_days", 0)
                * salaryInfo.get("per_day_salary", 0)
            ),
            2,
        )
        quarterDayWorkingAmount = round(
            (
                salaryInfo.get("quarter_days", 0)
                * salaryInfo.get("per_day_salary", 0)
                * 0.25
            ),
            2,
        )
        halfDayWorkingAmount = round(
            (
                salaryInfo.get("half_days", 0)
                * 0.5
                * salaryInfo.get("per_day_salary", 0)
            ),
            2,
        )
        threeFourQuarterDaysWorkingAmount = round(
            (
                salaryInfo.get("three_four_quarter_days", 0)
                * 0.75
                * salaryInfo.get("per_day_salary", 0)
            ),
            2,
        )
        latesAmount = round(
            (salaryInfo.get("lates", 0) * salaryInfo.get("per_day_salary", 0) * 0.9),
            2,
        )
        othersDayAmount = salaryInfo.get("others_day_salary")

        # Check if a Pay Slip already exists for the employee
        existing_doc = frappe.get_all(
            "Pay Slips",
            filters={
                "employee": data.get("employee"),
                "month_num": month,
                "year": year,
                "docstatus": 0,
            },
            fields=["name"],
        )

        if existing_doc:
            # If a Pay Slip exists, update it
            pay_slip = frappe.get_doc("Pay Slips", existing_doc[0]["name"])
        else:
            # If no Pay Slip exists, create a new one
            pay_slip = frappe.new_doc("Pay Slips")
        if salaryInfo.get("other_earnings"):
            otherEarnings = salaryInfo.get("other_earnings")
            for earning in otherEarnings:
                earning = otherEarnings.get(earning)
                if earning.get("type") == "Earning":
                    otherEarningsAmount += earning.get("amount")
                else:
                    otherEarningsAmount -= earning.get("amount")

        # Update the fields
        pay_slip.update(
            {
                "year": year,
                "month": month_name,
                "month_num": month,
                "company": data.get("company"),
                "employee": data.get("employee"),
                "employee_name": data.get("employee_name"),
                "email": data.get("email"),
                "designation": data.get("designation"),
                "department": data.get("department"),
                "pan_number": data.get("pan_number"),
                "date_of_joining": data.get("date_of_joining"),
                "attendance_device_id": data.get("attendance_device_id"),
                "basic_salary": data.get("basic_salary"),
                "per_day_salary": salaryInfo.get("per_day_salary"),
                "standard_working_days": salaryInfo.get("standard_working_days"),
                "others_days": salaryInfo.get("others"),
                "absent": salaryInfo.get("absent"),
                "actual_working_days": salaryInfo.get("actual_working_days"),
                "net_payble_amount": salaryInfo.get("total_salary"),
                "other_earnings_total": otherEarningsAmount,
                "total": round(
                    (
                        fullDayWorkingAmount
                        + quarterDayWorkingAmount
                        + halfDayWorkingAmount
                        + threeFourQuarterDaysWorkingAmount
                        + latesAmount
                        + salaryInfo.get("sundays_salary")
                        + earlyCheckoutWorkingAmount
                        + othersDayAmount
                    ),
                    2,
                ),
            }
        )
        pay_slip.attendance_record = attendanceRecord

        sal_calculations = pay_slip.salary_calculation
        pay_slip.salary_calculation = []
        for sal_cal in sal_calculations:

            frappe.delete_doc("Salary Calculation", sal_cal.name)
        if salaryInfo.get("full_days"):
            pay_slip.append(
                "salary_calculation",
                {
                    "particulars": "Full Day",
                    "days": salaryInfo.get("full_days"),
                    "rate": salaryInfo.get("per_day_salary"),
                    "effective_percentage": "100",
                    "amount": fullDayWorkingAmount,
                    "parent": pay_slip.name,
                },
            )
        if salaryInfo.get("lates"):
            pay_slip.append(
                "salary_calculation",
                {
                    "particulars": "Lates",
                    "days": salaryInfo.get("lates"),
                    "rate": salaryInfo.get("per_day_salary"),
                    "effective_percentage": "10",
                    "amount": latesAmount,
                    "parent": pay_slip.name,
                },
            )
        if salaryInfo.get("three_four_quarter_days"):
            pay_slip.append(
                "salary_calculation",
                {
                    "particulars": "3/4 Quarter Day",
                    "days": salaryInfo.get("three_four_quarter_days"),
                    "rate": salaryInfo.get("per_day_salary"),
                    "effective_percentage": "75",
                    "amount": threeFourQuarterDaysWorkingAmount,
                    "parent": pay_slip.name,
                },
            )
        if salaryInfo.get("half_days"):
            pay_slip.append(
                "salary_calculation",
                {
                    "particulars": "Half Day",
                    "days": salaryInfo.get("half_days"),
                    "rate": salaryInfo.get("per_day_salary"),
                    "effective_percentage": "50",
                    "amount": halfDayWorkingAmount,
                    "parent": pay_slip.name,
                },
            )
        if salaryInfo.get("quarter_days"):
            pay_slip.append(
                "salary_calculation",
                {
                    "particulars": "Quarter Day",
                    "days": salaryInfo.get("quarter_days"),
                    "rate": salaryInfo.get("per_day_salary"),
                    "effective_percentage": "25",
                    "amount": quarterDayWorkingAmount,
                    "parent": pay_slip.name,
                },
            )
        if salaryInfo.get("others_day"):
            pay_slip.append(
                "salary_calculation",
                {
                    "particulars": "Others Day",
                    "days": salaryInfo.get("others"),
                    "rate": salaryInfo.get("per_day_salary"),
                    "amount": othersDayAmount,
                    "effective_percentage": "-",
                    "parent": pay_slip.name,
                },
            )
        if salaryInfo.get("sundays_working_days"):
            pay_slip.append(
                "salary_calculation",
                {
                    "particulars": "Sunday Workings",
                    "days": salaryInfo.get("sundays_working_days"),
                    "rate": salaryInfo.get("per_day_salary"),
                    "amount": salaryInfo.get("sundays_salary"),
                    "parent": pay_slip.name,
                },
            )

        # Update child table for "other_earnings"
        pay_slip.other_earnings = []

        if salaryInfo.get("other_earnings"):
            for component, earning in salaryInfo.get("other_earnings").items():
                if component != "Leave Encashment":
                    pay_slip.append(
                        "other_earnings",
                        {
                            "component": component,
                            "type": earning.get("type"),
                            "amount": earning.get("amount"),
                            "component_reference": "Recurring Salary Component",
                            "reference_name": earning.get("doc_no"),
                        },
                    )
                else:
                    pay_slip.append(
                        "other_earnings",
                        {
                            "component": component,
                            "type": earning.get("type"),
                            "amount": earning.get("amount"),
                            "component_reference": "Pinnacle Leave Encashment",
                            "reference_name": earning.get("doc_no"),
                        },
                    )

        # Save or submit the document
        pay_slip.save()
        encashment = getEncashment(emp_id, year, month)

        if salaryInfo.get("other_earnings"):
            for component, earning in salaryInfo.get("other_earnings").items():
                if component != "Leave Encashment":
                    frappe.db.set_value(
                        "Recurring Salary Component",
                        earning.get("doc_no"),
                        {"status": "Cleared", "pay_slip": pay_slip.name},
                    )
                else:
                    frappe.db.set_value(
                        "Pinnacle Leave Encashment",
                        earning.get("doc_no"),
                        {"status": "Paid", "pay_slip": pay_slip.name},
                    )

        createdPaySlip = frappe.db.sql(
            """
                                       select name from `tabCreated Pay Slips`
                                       where employee_id = %s and pay_slip = %s
                                       """,
            (data.get("employee"), pay_slip.name),
            as_dict=True,
        )

        if createdPaySlip:
            frappe.db.sql(
                """UPDATE `tabCreated Pay Slips` 
                SET salary = %s, parent = %s 
                WHERE pay_slip = %s AND employee_id = %s""",
                (
                    pay_slip.net_payble_amount,
                    parent,
                    pay_slip.name,
                    pay_slip.employee,
                ),
            )
        else:
            frappe.db.sql(
                """
                INSERT INTO `tabCreated Pay Slips` 
                (name, pay_slip, employee, employee_id, salary, parent, parenttype, parentfield)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    pay_slip.name,
                    pay_slip.employee_name,
                    pay_slip.employee,
                    pay_slip.net_payble_amount,
                    parent,
                    "Create Pay Slips",
                    "created_pay_slips",
                ),
            )

        # frappe.db.commit()

    return {"message": ("Success")}


# API to download sft report
@frappe.whitelist(allow_guest=False)
def download_bank_upld_bulk_report(year=None, month=None, encodedCompany=None):
    company = base64.b64decode(encodedCompany).decode("utf-8")
    """
    month: integer 1–12 as string or number
    """

    report_name = ""
    conditions = []
    params = {}

    curr_user = frappe.session.user
    allowed_roles = ["All", "HR User", "HR Manager", "System Manager"]
    user_roles = frappe.get_roles(curr_user)

    # Allow access only if user has allowed roles or is Administrator
    if not (
        any(role in user_roles for role in allowed_roles)
        or curr_user == "Administrator"
    ):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app/home"
        return

    # Validate inputs
    if not month or not year:
        frappe.throw("Please specify a month and year")

    try:
        m = int(month)
        if 1 <= m <= 12:
            conditions.append("tps.month_num = %(month)s AND tps.year = %(year)s")
            params.update({"month": m, "year": int(year)})
            report_name = f"{company.replace(' ', '_')}_ICICI_SFTP_{calendar.month_name[m]}_{year}"
        else:
            frappe.throw("Month must be between 1 and 12")
    except ValueError:
        frappe.throw("Invalid month format")

    if company:
        conditions.append("tps.company = %(company)s")
        params["company"] = company

    where_sql = " AND ".join(conditions) or "1=1"

    query = f"""
        SELECT
            te.ifsc_code AS IFSC,
            te.bank_ac_no AS `Beneficiary Account No`,
            te.employee_name AS `Beneficiary Name`,
            tps.net_payble_amount AS `Amount (₹)`
        FROM `tabEmployee` AS te
        JOIN `tabPay Slips` AS tps ON tps.employee = te.name
        WHERE {where_sql}
    """

    data = frappe.db.sql(query, params, as_dict=True)

    # Define columns and rows for export
    columns = [
        {"header": "IFSC", "key": "IFSC", "width": 20},
        {
            "header": "Beneficiary Account No",
            "key": "Beneficiary Account No",
            "width": 25,
        },
        {"header": "Beneficiary Name", "key": "Beneficiary Name", "width": 30},
        {"header": "Amount (₹)", "key": "Amount (₹)", "width": 15},
    ]
    rows = [[r[col["key"]] for col in columns] for r in data]

    xlsx_file = make_xlsx(
        [[col["header"] for col in columns]] + rows,
        report_name,
        column_widths=[col["width"] for col in columns],
    )

    # Return file as response
    frappe.response.filename = f"{report_name}.xlsx"
    frappe.response.filecontent = xlsx_file.getvalue()
    frappe.response.type = "binary"


# API to download sft upload report
@frappe.whitelist(allow_guest=False)
def download_sft_report(year=None, month=None, encodedCompany=None):

    company = base64.b64decode(encodedCompany).decode("utf-8")
    curr_user = frappe.session.user
    allowed_roles = ["All", "HR User", "HR Manager", "System Manager"]
    user_roles = frappe.get_roles(curr_user)

    if not (
        any(role in user_roles for role in allowed_roles)
        or curr_user == "Administrator"
    ):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app/home"
        return

    if not month or not year:
        frappe.throw("Please specify a month and year")

    try:
        m = int(month)
        if m < 1 or m > 12:
            frappe.throw("Month must be between 1 and 12")

    except ValueError:
        frappe.throw("Invalid month format")

    # Prepare parameters
    params = {"month": m, "year": int(year)}
    report_name = (
        f"{company.replace(' ', '_')}_ICICI_BulkPayment_{calendar.month_name[m]}_{year}"
    )
    conditions = ["tps.month_num = %(month)s", "tps.year = %(year)s"]

    if company:
        conditions.append("tps.company = %(company)s")
        params["company"] = company

    where_sql = " AND ".join(conditions)

    # DO NOT use f-string here
    query = """
        SELECT
            '192105002170' AS `Debit Ac No`,
            te.employee_name AS `Beneficiary Name`,
            te.bank_ac_no AS `Beneficiary Account No`,
            te.ifsc_code AS `IFSC`,
            tps.net_payble_amount AS `Amount (₹)`,
            'N' AS `Pay Mode`,
            CONCAT(
                DATE_FORMAT(CURDATE(), '%%d-'),
                UPPER(DATE_FORMAT(CURDATE(), '%%b')),
                DATE_FORMAT(CURDATE(), '-%%Y')
            ) AS `Date`
        FROM `tabEmployee` AS te
        JOIN `tabPay Slips` AS tps ON tps.employee = te.name
        WHERE {where_conditions}
    """.format(
        where_conditions=where_sql
    )

    data = frappe.db.sql(query, params, as_dict=True)

    if not data:
        frappe.msgprint(
            _("No data found to update"), title=_("Notification"), indicator="green"
        )
        return

    columns = [
        {"header": "Debit Ac No", "key": "Debit Ac No", "width": 20},
        {"header": "Beneficiary Name", "key": "Beneficiary Name", "width": 30},
        {
            "header": "Beneficiary Account No",
            "key": "Beneficiary Account No",
            "width": 25,
        },
        {"header": "IFSC", "key": "IFSC", "width": 15},
        {"header": "Amount (₹)", "key": "Amount (₹)", "width": 15},
        {"header": "Pay Mode", "key": "Pay Mode", "width": 10},
        {"header": "Date", "key": "Date", "width": 15},
    ]

    rows = [[row[col["key"]] for col in columns] for row in data]

    xlsx_file = make_xlsx(
        [[col["header"] for col in columns]] + rows,
        report_name,
        column_widths=[col["width"] for col in columns],
    )

    frappe.response.filename = f"{report_name}.xlsx"
    frappe.response.filecontent = xlsx_file.getvalue()
    frappe.response.type = "binary"


# API to download to pay slip records.
# @frappe.whitelist()
# def download_pay_slip_report(year=None, month=None, encodedCompany=None):
#     company = base64.b64decode(encodedCompany).decode("utf-8")
#     curr_user = frappe.session.user
#     allowed_roles = ["All", "HR User", "HR Manager", "System Manager"]
#     user_roles = frappe.get_roles(curr_user)

#     if (
#         any(role in user_roles for role in allowed_roles)
#         and curr_user != "Administrator"
#     ):
#         frappe.local.response["type"] = "redirect"
#         frappe.local.response["location"] = "/app/home"
#         return

#     if not year or not month:
#         frappe.throw(_("Year and Month are required"))

#     records = get_pay_slip_report(
#         year=year, month=month, curr_user=curr_user, company=company
#     )

#     if not records:
#         frappe.throw(_("No data found for the given filters."))

#     # Define top-level columns
#     columns = [
#         "Pay Slip Name",
#         "Year",
#         "Month",
#         "Employee ID",
#         "Employee Name",
#         "Company",
#         "Designation",
#         "Department",
#         "Personal Email",
#         "Standard Working Days",
#         "PAN Number",
#         "Date of Joining",
#         "Basic Salary",
#         "Per Day Salary",
#         "Actual Working Days",
#         "Absent",
#         "Total",
#         "Net Payable Amount",
#     ]

#     # Sub-columns under salary_info
#     salary_info_keys = [
#         "Full Day",
#         "Sunday Workings",
#         "Half Day",
#         "Quarter Day",
#         "3/4 Quarter Day",
#         "Lates",
#     ]
#     salary_info_sub_cols = ["Day", "Amount"]

#     # Sub-columns under other_earnings
#     other_earning_keys = [
#         "Incentives",
#         "Special Incentives",
#         "Leave Encashment",
#         "Overtime",
#     ]
#     other_earning_sub_cols = ["Amount"]

#     # Prepare headers
#     header_row_1 = (
#         columns
#         + ["Salary Info"] * (len(salary_info_keys) * len(salary_info_sub_cols))
#         + ["Other Earnings"] * (len(other_earning_keys) * len(other_earning_sub_cols))
#     )

#     header_row_2 = [""] * len(columns)
#     for key in salary_info_keys:
#         header_row_2 += [f"{key} - Day", f"{key} - Amount"]
#     for key in other_earning_keys:
#         header_row_2 += [f"{key} - Amount"]

#     # Prepare rows
#     data_rows = []
#     for r in records:
#         row = [
#             r.get("pay_slip_name"),
#             r.get("year"),
#             r.get("month"),
#             r.get("employee_id"),
#             r.get("employee_name"),
#             r.get("company"),
#             r.get("designation"),
#             r.get("department"),
#             r.get("email"),
#             r.get("standard_working_days"),
#             r.get("pan_number"),
#             r.get("date_of_joining"),
#             r.get("basic_salary"),
#             r.get("per_day_salary"),
#             r.get("actual_working_days"),
#             r.get("absent"),
#             r.get("total"),
#             r.get("net_payable_amount"),
#         ]

#         # Salary Info breakdown
#         salary_info = r.get("salary_info", {})
#         for key in salary_info_keys:
#             info = salary_info.get(key, {})
#             row.append(info.get("day", 0))
#             row.append(info.get("amount", 0))

#         # Other Earnings
#         other_earnings = r.get("other_earnings", {})
#         for key in other_earning_keys:
#             earning = other_earnings.get(key, {})
#             row.append(earning.get("amount", 0))

#         data_rows.append(row)

#     # Generate Excel
#     xlsx_data = make_xlsx(
#         data=[header_row_1, header_row_2] + data_rows, sheet_name="Pay Slip Report"
#     )

#     filename = f"{company.replace(' ', '_')}_Pay_Slip_Report_{calendar.month_name[int(month)]}_{year}.xlsx"
#     frappe.response.filename = filename
#     frappe.response.filecontent = xlsx_data.getvalue()
#     frappe.response.type = "binary"


@frappe.whitelist()
def download_pay_slip_report(year=None, month=None, encodedCompany=None):
    company = base64.b64decode(encodedCompany).decode("utf-8")
    curr_user = frappe.session.user
    allowed_roles = ["All", "HR User", "HR Manager", "System Manager"]
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

    records = get_pay_slip_report(
        year=year, month=month, curr_user=curr_user, company=company
    )

    if not records:
        frappe.throw(_("No data found for the given filters."))

    # Define static columns
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

    # Dynamically gather all unique keys for salary_info and other_earnings
    salary_info_keys = set()
    other_earning_keys = set()

    for r in records:
        salary_info = r.get("salary_info", {})
        other_earnings = r.get("other_earnings", {})

        for key in salary_info.keys():
            salary_info_keys.add(key)

        for key in other_earnings.keys():
            other_earning_keys.add(key)

    salary_info_keys = sorted(list(salary_info_keys))
    other_earning_keys = sorted(list(other_earning_keys))

    # Build headers
    header_row_1 = (
        static_columns
        + ["Salary Info"] * (len(salary_info_keys) * 2)
        + ["Other Earnings"] * len(other_earning_keys)
    )

    header_row_2 = [""] * len(static_columns)
    for key in salary_info_keys:
        header_row_2 += [f"{key} - Day", f"{key} - Amount"]
    for key in other_earning_keys:
        header_row_2.append(f"{key} - Amount")

    # Prepare data rows
    data_rows = []

    for r in records:
        row = [
            r.get("pay_slip_name"),
            r.get("year"),
            r.get("month"),
            r.get("employee_id"),
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

        # Salary Info
        salary_info = r.get("salary_info", {})
        for key in salary_info_keys:
            info = salary_info.get(key, {})
            row.append(info.get("day", 0))
            row.append(info.get("amount", 0))

        # Other Earnings
        other_earnings = r.get("other_earnings", {})
        for key in other_earning_keys:
            earning = other_earnings.get(key, {})
            row.append(earning.get("amount", 0))

        data_rows.append(row)

    # Generate Excel
    xlsx_data = make_xlsx(
        data=[header_row_1, header_row_2] + data_rows, sheet_name="Pay Slip Report"
    )

    filename = f"{company.replace(' ', '_')}_Pay_Slip_Report_{calendar.month_name[int(month)]}_{year}.xlsx"
    frappe.response.filename = filename
    frappe.response.filecontent = xlsx_data.getvalue()
    frappe.response.type = "binary"


# API to send attendance notification
def attendance_notification(doc, method):
    try:
        hr_email = "hr@mygstcafe.in"

        subject = (
            f"Attendance Notification – {doc.employee}:{doc.employee_name} - {doc.time}"
        )
        status = "In" if doc.log_type == "IN" else "Out"
        time = format_datetime(doc.time)

        message = f"""
        Dear HR Team,<br><br>
        This is to notify that the following employee has checked {status}:<br><br>
        <b>Employee ID:</b> {doc.employee}<br>
        <b>Name:</b> {doc.employee_name}<br>
        <b>Status:</b> Checked {status}<br>
        <b>Time:</b> {time}<br><br>
        Regards,<br>
        PinnacleHRMS
        """

        frappe.sendmail(recipients=[hr_email], subject=subject, message=message)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Attendance Notification Error")


@frappe.whitelist()
def download_idfc_blkpay(year=None, month=None, encodedCompany=None):
    company = base64.b64decode(encodedCompany).decode("utf-8")
    """
    month: integer 1–12 as string or number
    """

    report_name = ""
    conditions = []
    params = {}

    curr_user = frappe.session.user
    allowed_roles = ["All", "HR User", "HR Manager", "System Manager"]
    user_roles = frappe.get_roles(curr_user)

    # Allow access only if user has allowed roles or is Administrator
    if not (
        any(role in user_roles for role in allowed_roles)
        or curr_user == "Administrator"
    ):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app/home"
        return

    # Validate inputs
    if not month or not year:
        frappe.throw("Please specify a month and year")

    try:
        m = int(month)
        if 1 <= m <= 12:
            conditions.append("tps.month_num = %(month)s AND tps.year = %(year)s")
            params.update({"month": m, "year": int(year)})
            report_name = f"{company.replace(' ', '_')}_IDFC_BLKPAY_{calendar.month_name[m]}_{year}"
        else:
            frappe.throw("Month must be between 1 and 12")
    except ValueError:
        frappe.throw("Invalid month format")

    if company:
        conditions.append("tps.company = %(company)s")
        params["company"] = company

    where_sql = " AND ".join(conditions) or "1=1"

    query = f"""
        SELECT
            te.ifsc_code AS IFSC,
            te.bank_ac_no AS `Beneficiary Account No`,
            te.employee_name AS `Beneficiary Name`,
            te.company,
            tps.net_payble_amount AS `Amount (₹)`
        FROM `tabEmployee` AS te
        JOIN `tabPay Slips` AS tps ON tps.employee = te.name
        WHERE {where_sql}
    """

    data = frappe.db.sql(query, params, as_dict=True)

    # Mapping for company debit accounts
    company_debit_map = {
        "Opticodes Technologies Private Limited": "10238672140",
        "Pinnacle Finserv Advisors Pvt. Ltd.": "10237782223",
    }

    today_str = date.today().strftime("%Y-%m-%d")  # current date

    # Define columns and rows for export
    columns = [
        {"header": "Beneficiary Name", "key": "Beneficiary Name", "width": 30},
        {
            "header": "Beneficiary Account No",
            "key": "Beneficiary Account No",
            "width": 25,
        },
        {"header": "IFSC", "key": "IFSC", "width": 20},
        {"header": "Transaction Type", "key": "Transaction Type", "width": 30},
        {"header": "Debit Account Number", "key": "Debit Account Number", "width": 30},
        {"header": "Transaction Date", "key": "Transaction Date", "width": 30},
        {"header": "Amount (₹)", "key": "Amount (₹)", "width": 15},
        {"header": "Currency", "key": "Currency", "width": 15},
    ]

    rows = []
    for r in data:
        debit_account = company_debit_map.get(r["company"], "N/A")
        row = [
            r["Beneficiary Name"],
            r["Beneficiary Account No"],
            r["IFSC"],
            "NEFT",  # assuming transaction type is NEFT
            debit_account,
            today_str,
            r["Amount (₹)"],
            "INR",  # assuming currency INR
        ]
        rows.append(row)

    xlsx_file = make_xlsx(
        [[col["header"] for col in columns]] + rows,
        report_name,
        column_widths=[col["width"] for col in columns],
    )

    # Return file as response
    frappe.response.filename = f"{report_name}.xlsx"
    frappe.response.filecontent = xlsx_file.getvalue()
    frappe.response.type = "binary"
