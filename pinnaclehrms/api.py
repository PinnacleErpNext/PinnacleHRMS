import frappe, json, uuid
from pinnaclehrms.utility.salary_calculator import (
    createPaySlips,
    getEmpRecords,
    calculateMonthlySalary,
)
from collections import defaultdict
from frappe.utils.xlsxutils import make_xlsx
from frappe.desk.query_report import build_xlsx_data
from frappe.utils import nowdate, flt
from frappe import _


# API to get pay slips in create pay slips
@frappe.whitelist(allow_guest=True)
def get_pay_slip_list(parent_docname, month, year, company=None, employee=None):
    baseQuery = """
                SELECT
                    name,
                    employee_name,
                    employee_id,
                    net_payble_amount 
                FROM
                    `tabPay Slips` 
                WHERE 
                    month_num = %s AND year = %s
                """
    filters = [month, year]
    if company != "":
        filters.append(company)
        baseQuery += "AND company = %s"
    if employee != "":
        baseQuery += " AND employee_id = %s"
        filters.append(employee)

    pay_slip_list = frappe.db.sql(baseQuery, filters, as_dict=True)

    created_pay_slips = []

    for pay_slip in pay_slip_list:
        generated_name = str(uuid.uuid4())  # Generate a unique ID for the name field
        frappe.db.sql(
            """
            INSERT INTO `tabCreated Pay Slips` (
                `name`, `pay_slip`, `employee`,`employee_id`, `salary`, `parent`, `parenttype`, `parentfield`
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """,
            (
                generated_name,  # name
                pay_slip["name"],  # pay_slip
                pay_slip["employee_name"],  # employee
                pay_slip["employee_id"],  # employee_id
                pay_slip["net_payble_amount"],  # salary
                parent_docname,  # parent
                "Create Pay Slips",  # parenttype
                "created_pay_slips",  # parentfield
            ),
        )
        if not any(item["pay_slip"] == pay_slip["name"] for item in created_pay_slips):
            created_pay_slips.append(
                {
                    "name": generated_name,
                    "pay_slip": pay_slip["name"],
                    "employee": pay_slip["employee_name"],
                    "employee_id": pay_slip["employee_id"],
                    "salary": pay_slip["net_payble_amount"],
                    "parent": parent_docname,
                    "parenttype": "Create Pay Slips",
                    "parentfield": "created_pay_slips",
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
        personal_email = doc.personal_email

        subject = f"Pay Slip for {employee_name} - {month} {year}"

        # HTML email body with dynamic content
        context = {"doc": doc}  # Pass data to the template
        message = frappe.render_template(
            "pinnaclehrms/public/templates/pay_slip.html", context
        )

        # Attach the pay slip PDF
        if personal_email:
            frappe.sendmail(
                recipients=[personal_email],
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
            filters={"personal_email": curr_user},
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
            earning.type: {"amount": earning.amount}
            for earning in pay_slip.other_earnings
        }

        # Prepare combined dict for this pay slip
        pay_slip_dict = {
            "pay_slip_name": pay_slip.name,
            "year": pay_slip.year,
            "month": pay_slip.month_num,
            "employee_id": pay_slip.employee_id,
            "employee_name": pay_slip.employee_name,
            "company": pay_slip.company,
            "designation": pay_slip.designation,
            "department": pay_slip.department,
            "personal_email": pay_slip.personal_email,
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
            "other_earnings_total":pay_slip.other_earnings_total
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


# API to print pay slip
@frappe.whitelist(allow_guest=True)
def print_pay_slip(pay_slips):
    try:
        pay_slips = json.loads(pay_slips)
        for pay_slip in pay_slips:
            frappe.utils.print_format.download_pdf(
                "Pay Slips", pay_slip, format="Pay Slip Format"
            )
    except Exception as e:
        frappe.log_error(message=str(e), title="Pay Slip Printing Error")
        frappe.throw(f"An error occurred while printing pay slips: {str(e)}")


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
    personal_email = paySlip.personal_email
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

    if personal_email:
        frappe.sendmail(
            recipients=[personal_email],
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
def regeneratePaySlip(data):

    data = json.loads(data)
    year = int(data.get("year"))
    month = data.get("month")

    empRecords = getEmpRecords(data)
    employeeData = calculateMonthlySalary(empRecords, year, month)

    # frappe.throw(str(employeeData))

    for emp_id, data in employeeData.items():

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

        full_day_working_amount = round(
            (salaryInfo.get("full_days", 0) * salaryInfo.get("per_day_salary", 0)), 2
        )
        quarter_day_working_amount = round(
            (
                salaryInfo.get("quarter_days", 0)
                * salaryInfo.get("per_day_salary", 0)
                * 0.25
            ),
            2,
        )
        half_day_working_amount = round(
            (
                salaryInfo.get("half_days", 0)
                * 0.5
                * salaryInfo.get("per_day_salary", 0)
            ),
            2,
        )
        three_four_quarter_days_working_amount = round(
            (
                salaryInfo.get("three_four_quarter_days", 0)
                * 0.75
                * salaryInfo.get("per_day_salary", 0)
            ),
            2,
        )
        lates_amount = round(
            (salaryInfo.get("lates", 0) * salaryInfo.get("per_day_salary", 0) * 0.9), 2
        )
        other_earnings_amount = round(
            (salaryInfo.get("overtime", 0)), 2
        ) + salaryInfo.get("holidays", 0)

        # Check if a Pay Slip already exists for the employee
        existing_doc = frappe.get_all(
            "Pay Slips",
            filters={
                "employee_id": data.get("employee"),
                "docstatus": 0,  # Check for open or draft status
            },
            fields=["name"],
        )

        if existing_doc:
            # If a Pay Slip exists, update it
            pay_slip = frappe.get_doc("Pay Slips", existing_doc[0]["name"])
        else:
            # If no Pay Slip exists, create a new one
            pay_slip = frappe.new_doc("Pay Slips")

        # Update the fields
        pay_slip.update(
            {
                "year": year,
                "month": month_name,
                "month_num": month,
                "company": data.get("company"),
                "employee_id": data.get("employee"),
                "employee_name": data.get("employee_name"),
                "personal_email": data.get("personal_email"),
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
                "other_earnings_amount": other_earnings_amount,  # Corrected key alignment
                "total": round(
                    (
                        full_day_working_amount
                        + quarter_day_working_amount
                        + half_day_working_amount
                        + three_four_quarter_days_working_amount
                        + lates_amount
                    ),
                    2,
                ),
            }
        )
        pay_slip.attendance_record = attendanceRecord

        sal_calculations = pay_slip.salary_calculation
        pay_slip.salary_calculation = []
        for sal_cal in sal_calculations:
            print(sal_cal)
            frappe.delete_doc("Salary Calculation", sal_cal.name)
        if salaryInfo.get("full_days"):
            pay_slip.append(
                "salary_calculation",
                {
                    "particulars": "Full Day",
                    "days": salaryInfo.get("full_days"),
                    "rate": salaryInfo.get("per_day_salary"),
                    "effective_percentage": "100",
                    "amount": full_day_working_amount,
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
                    "amount": lates_amount,
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
                    "amount": three_four_quarter_days_working_amount,
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
                    "amount": half_day_working_amount,
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
                    "amount": quarter_day_working_amount,
                    "parent": pay_slip.name,
                },
            )
        if salaryInfo.get("others"):
            pay_slip.append(
                "salary_calculation",
                {
                    "particulars": "Others Day",
                    "days": salaryInfo.get("others"),
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

        pay_slip.append(
            "other_earnings",
            {
                "type": "Incentives",
                "amount": 0,
                "parent": pay_slip.name,
            },
        )
        pay_slip.append(
            "other_earnings",
            {
                "type": "Special Incentives",
                "amount": 0,
                "parent": pay_slip.name,
            },
        )
        pay_slip.append(
            "other_earnings",
            {
                "type": "Leave Encashment",
                "amount": salaryInfo.get("leave_encashment"),
                "parent": pay_slip.name,
            },
        )
        pay_slip.append(
            "other_earnings",
            {
                "type": "Overtime",
                "amount": salaryInfo.get("overtime"),
                "parent": pay_slip.name,
            },
        )
        # pay_slip.append(
        #     "other_earnings",
        #     {
        #         "type": "Holidays",
        #         "amount": salaryInfo.get("holidays"),
        #         "parent": pay_slip.name,
        #     },
        # )

        # Save or submit the document
        pay_slip.save()

        frappe.db.sql(
            """UPDATE `tabCreated Pay Slips` SET salary = %s WHERE pay_slip = %s AND employee_id = %s""",
            (pay_slip.net_payble_amount, pay_slip.name, pay_slip.employee_id),
        )

        # frappe.db.commit()

    return {"message": ("Success")}


# API to download sft report
@frappe.whitelist(allow_guest=False)
def download_sft_report(month=None):
    """
    month: integer 1–12 as string or number
    """
    report_name = "Salary_Beneficiary_List"
    conditions = []

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

    # Validate and use the month parameter
    if month:
        try:
            m = int(month)
            if 1 <= m <= 12:
                # Filter on the month() of your date field
                conditions.append(f"tps.month_num = {m}")
            else:
                frappe.throw("Month must be between 1 and 12")
        except ValueError:
            frappe.throw("Invalid month format")

    where_sql = " AND ".join(conditions) or "1=1"
    query = f"""
        SELECT
            te.ifsc_code   AS IFSC,
            te.bank_ac_no  AS `Beneficiary Account No`,
            te.employee_name AS `Beneficiary Name`,
            tps.net_payble_amount AS `Amount (₹)`
        FROM `tabEmployee` AS te
        JOIN `tabPay Slips` AS tps ON tps.employee_id = te.name
        WHERE {where_sql}
    """
    data = frappe.db.sql(query, as_dict=True)

    # Prepare headers + rows
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
        [[c["header"] for c in columns]] + rows,
        report_name,
        column_widths=[c["width"] for c in columns],
    )

    # Download response
    frappe.response.filename = f"{report_name}.xlsx"
    frappe.response.filecontent = xlsx_file.getvalue()
    frappe.response.type = "binary"


# API to download sft upload report
@frappe.whitelist(allow_guest=False)
def download_sft_upld_report(month=None):
    """
    month: integer 1–12 as string or number
    Generates an SFT upload report for the given month.
    """
    
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
    
    # 1. Validate month
    if not month:
        frappe.throw("Please specify a month (1–12)")
    try:
        m = int(month)
        if m < 1 or m > 12:
            frappe.throw("Month must be between 1 and 12")
    except ValueError:
        frappe.throw("Invalid month format")

    # 2. Build WHERE clause
    where_sql = f"tps.month_num = {m}"

    # 3. Run your custom SQL
    query = f"""
        SELECT
            '192105002170'                        AS `Debit Ac No`,
            te.employee_name                     AS `Beneficiary Name`,
            te.bank_ac_no                        AS `Beneficiary Account No`,
            te.ifsc_code                         AS `IFSC`,
            tps.net_payble_amount                AS `Amount (₹)`,
            'N'                                  AS `Pay Mode`,
            CONCAT(
                DATE_FORMAT(CURDATE(), '%d-'),
                UPPER(DATE_FORMAT(CURDATE(), '%b')),
                DATE_FORMAT(CURDATE(), '-%Y')
            )                                    AS `Date`
        FROM `tabEmployee` AS te
        JOIN `tabPay Slips` AS tps ON tps.employee_id = te.name
        WHERE {where_sql}
    """
    data = frappe.db.sql(query, as_dict=True)
    if not data or len(data) == 0:
        frappe.msgprint(
            title=_("Notification"),
            indicator="green",
            message=_("No data found to update"),
        )
        return
    # 4. Prepare headers and rows
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
    # Build row data in the order of columns
    rows = [[row[col["key"]] for col in columns] for row in data]

    # 5. Generate the XLSX
    # Use .xls extension for compatibility if required, but content is XLSX
    today = nowdate()  # YYYY-MM-DD
    filename = f"sft_upload_report_{today}.xls"
    xlsx_file = make_xlsx(
        [[c["header"] for c in columns]] + rows,
        "SFT Upload",
        column_widths=[c["width"] for c in columns],
    )

    # 6. Send as download response
    frappe.response.filename = filename
    frappe.response.filecontent = xlsx_file.getvalue()
    frappe.response.type = "binary"

#API to download to pay slip records.
@frappe.whitelist()
def download_pay_slip_report(year=None, month=None, company=None):
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

    # Define top-level columns
    columns = [
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

    # Sub-columns under salary_info
    salary_info_keys = [
        "Full Day",
        "Sunday Workings",
        "Half Day",
        "Quarter Day",
        "3/4 Quarter Day",
        "Lates",
    ]
    salary_info_sub_cols = ["Day", "Amount"]

    # Sub-columns under other_earnings
    other_earning_keys = [
        "Incentives",
        "Special Incentives",
        "Leave Encashment",
        "Overtime",
    ]
    other_earning_sub_cols = ["Amount"]

    # Prepare headers
    header_row_1 = (
        columns
        + ["Salary Info"] * (len(salary_info_keys) * len(salary_info_sub_cols))
        + ["Other Earnings"] * (len(other_earning_keys) * len(other_earning_sub_cols))
    )

    header_row_2 = [""] * len(columns)
    for key in salary_info_keys:
        header_row_2 += [f"{key} - Day", f"{key} - Amount"]
    for key in other_earning_keys:
        header_row_2 += [f"{key} - Amount"]

    # Prepare rows
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
            r.get("personal_email"),
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

        # Salary Info breakdown
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

    filename = f"Pay_Slip_Report_{year}_{month}.xlsx"
    frappe.response.filename = filename
    frappe.response.filecontent = xlsx_data.getvalue()
    frappe.response.type = "binary"
