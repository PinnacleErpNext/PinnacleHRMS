# Copyright (c) 2025, OTPL and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import json
import calendar
from datetime import datetime, time, timedelta, date
from dateutil.relativedelta import relativedelta
from pinnaclehrms.utility.salary_calculator import getSalaryDetails
from frappe.model.document import Document


class LeaveEncashmentTool(Document):
    pass  # No method inside the class


@frappe.whitelist(allow_guest=True)
def eligible_employee_for_leave_encashment(data):
    data = json.loads(data)
    year = data.get("year")
    month = data.get("month")

    # Ensure valid year and month values
    if not year or not month:
        frappe.throw("Year and Month are required!")

    # Set reference date (1st day of given month and year)
    reference_date = datetime(
        int(year), int(month), calendar.monthrange(year, month)[1]
    )

    eligible_employee_list = []

    emp_list = frappe.db.get_list(
        "Employee",
        filters={"status": "Active"},
        fields=["employee", "employee_name", "date_of_joining"],
    )

    for emp in emp_list:
        date_of_joining = emp.get("date_of_joining")

        if date_of_joining:
            # Calculate difference in years
            years_difference = relativedelta(reference_date, date_of_joining).years
            last_encashment = frappe.get_all(
                "Pinnacle Leave Encashment",
                filters={"employee": emp.get("employee")},
                fields=["encashment_date", "next_encashment_date"],
                order_by="encashment_date desc",
                limit_page_length=1,
            )

            last_encashment_date = (
                last_encashment[0]["encashment_date"] if last_encashment else None
            )

            next_encashment_date = (
                last_encashment[0]["next_encashment_date"] if last_encashment else None
            )
            eligibility = "Yes" if years_difference >= 1 else "No"
            if years_difference >= 1:
                if next_encashment_date:
                    if (
                        next_encashment_date.month == month
                        and next_encashment_date.year == year
                    ):
                        eligibility = "Yes"
                    else:
                        eligibility = "No"
                else:
                    eligibility = "Yes"
            else:
                eligibility = "No"
            eligible_employee_list.append(
                {
                    "employee": emp.get("employee"),
                    "employee_name": emp.get("employee_name"),
                    "date_of_joining": str(date_of_joining),
                    "last_encashment_date": (last_encashment_date),
                    "next_encashment_date": (next_encashment_date),
                    "eligible": eligibility,
                }
            )

    return eligible_employee_list


@frappe.whitelist(allow_guest=True)
def generate_leave_encashment(data):

    try:
        data = frappe.parse_json(data)

        emp_list = data.get("selected_emp", [])
        year = int(data.get("year", 0))
        month = int(data.get("month", 0))

        if not emp_list or not year or not month:
            frappe.throw(
                _("Invalid input data. Please provide employee list, year, and month.")
            )

        encashment_records = []

        for emp in emp_list:
            employee_id = emp.get("employee")

            if emp.get("eligible") != "Yes":
                frappe.msgprint(
                    _("{0} is not eligible for leave encashment.").format(employee_id)
                )
                continue

            average_salary = calAvgSalary(employee_id, year, month)

            paid_leaves = (
                frappe.db.get_value(
                    "Assign Salary", {"employee_id": employee_id}, "paid_leaves"
                )
                or 0
            )
            paid_leaves = paid_leaves / (24 * 60 * 60)  # Convert to days

            last_encashment_date = frappe.db.get_list(
                "Pinnacle Leave Encashment",
                filters={"employee": employee_id},
                fields=["encashment_date"],
                order_by="encashment_date desc",
                limit=1,
            )

            if data.get("from_date"):
                cal_from_date = datetime.strptime(data.get("from_date"), "%Y-%m-%d")
            elif last_encashment_date:
                cal_from_date = last_encashment_date[0].get("encashment_date")
            else:
                cal_from_date = frappe.db.get_value(
                    "Employee", {"name": employee_id}, "date_of_joining"
                )
                if not cal_from_date:
                    frappe.throw(
                        _("Joining date not found for Employee {0}").format(employee_id)
                    )

            if data.get("to_date"):
                end_date = datetime.strptime(data.get("to_date"), "%Y-%m-%d")
            else:
                last_day_of_month = calendar.monthrange(year, month)[1]
                end_date = datetime(year, month, last_day_of_month)

            difference = relativedelta(end_date, cal_from_date)
            leave_encashment_months = difference.years * 12 + difference.months + 1

            if data.get("next_encashment_date"):
                next_encashment_date = datetime.strptime(
                    data["next_encashment_date"], "%Y-%m-%d"
                )
            else:
                today = end_date
                if today.month >= 4:
                    next_encashment_date = datetime(today.year + 1, 3, 31)
                else:
                    next_encashment_date = datetime(today.year, 3, 31)

            leave_encashment_amount = (
                (paid_leaves / 12) * leave_encashment_months
            ) * average_salary

            doc = frappe.get_doc(
                {
                    "doctype": "Pinnacle Leave Encashment",
                    "employee": employee_id,
                    "from": cal_from_date.strftime("%Y-%m-%d"),
                    "upto": end_date.strftime("%Y-%m-%d"),
                    "encashment_date": end_date.strftime("%Y-%m-%d"),
                    "next_encashment_date": next_encashment_date,
                    "amount": round(leave_encashment_amount, 2),
                }
            )
            doc.insert(ignore_permissions=True)
            encashment_records.append(doc)

        return encashment_records

    except Exception:
        frappe.log_error(
            frappe.get_traceback(), _("Error in generate_leave_encashment")
        )
        frappe.throw(
            _(
                "An error occurred while generating leave encashment. Please check the logs."
            )
        )


# function to calculate average salary
def calAvgSalary(empID, year, month):

    endDate = date(year, month, calendar.monthrange(year, month)[1] - 1)
    startDate = date(
        endDate.year - 1, endDate.month, calendar.monthrange(year, month)[1]
    )

    salaryData = frappe.db.sql(
        """
                            SELECT 
                                tsh.from_date,
                                tsh.salary
                            FROM 
                                `tabSalary History` AS tsh
                            JOIN 
                                `tabAssign Salary` AS tas
                            ON 
                                tsh.parent = tas.name
                            WHERE 
                                tas.employee_id = %s
                                AND tsh.from_date BETWEEN %s AND %s;
                               """,
        (empID, startDate, endDate),
        as_dict=True,
    )
    salaryStructure = {}

    for data in salaryData:
        salaryStructure[data.get("from_date")] = data.get("salary")

    salary = salaryStructure.get(startDate)

    if not salary:
        salaryDetails = getSalaryDetails(empID, startDate.year, startDate.month)
        salary = salaryDetails.get("basicSalary")

    total_salary = 0
    day_count = 0

    current_date = startDate
    while current_date <= endDate:
        newSalary = salaryStructure.get(current_date)
        if newSalary:
            salary = newSalary

        if salary is not None:
            days = calendar.monthrange(current_date.year, current_date.month)[1]
            perDaySalary = round((salary / days), 2)
            total_salary += perDaySalary
            if salary != 0:
                day_count += 1
        current_date += timedelta(days=1)

    return round((total_salary / day_count), 2) if day_count > 0 else 0
