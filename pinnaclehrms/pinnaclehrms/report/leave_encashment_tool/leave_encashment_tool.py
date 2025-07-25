# Copyright (c) 2025, OTPL and contributors
# For license information, please see license.txt

import frappe, json, calendar
from frappe import _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta


def execute(filters=None):
    if not filters:
        filters = {}

    year = int(filters.get("year", datetime.today().year))
    month = filters.get("month")
    month_code = _get_month_code(month)
    company = filters.get("company")
    data = eligible_employee_for_leave_encashment(
        json.dumps({"year": year, "month": month_code, "company": company})
    )

    columns = get_columns()

    return columns, data


def get_columns():
    return [
        {
            "label": "Employee",
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 300,
        },
        {
            "label": "Date Of Joining",
            "fieldname": "date_of_joining",
            "fieldtype": "Date",
            "width": 150,
        },
        {
            "label": "Last Encashment Date",
            "fieldname": "last_encashment_date",
            "fieldtype": "Date",
            "width": 150,
        },
        {
            "label": "Next Encashment Date",
            "fieldname": "next_encashment_date",
            "fieldtype": "Date",
            "width": 150,
        },
        {
            "label": "Eligible",
            "fieldname": "eligible",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Encashment",
            "fieldname": "encashment",
            "fieldtype": "HTML",
            "width": 200,
        },
    ]


def _get_month_code(month_name):
    """
    Returns the numerical code for a given month name.
    Args:
        month_name (str): The full name of the month (e.g., "January", "February").
    Returns:
        int: The corresponding month number (1 for January, 2 for February, ..., 12 for December).
             Returns 0 if the month name is not recognized.
    """

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
    return month_map.get(month_name, 0)


def eligible_employee_for_leave_encashment(data):
    """
    Determines the list of employees eligible for leave encashment based on the provided year, month, and optional company.
    Args:
        data (str): A JSON-encoded string containing the following keys:
            - "year" (int or str): The year for eligibility reference.
            - "month" (int or str): The month for eligibility reference.
            - "company" (str, optional): The company to filter employees by.
    Returns:
        list[dict]: A list of dictionaries, each representing an employee with the following keys:
            - "employee": Employee ID.
            - "employee_name": Name of the employee.
            - "date_of_joining": Date the employee joined.
            - "last_encashment_date": Date of the last leave encashment, if any.
            - "next_encashment_date": Date of the next eligible encashment, if any.
            - "eligible": "Yes" if the employee is eligible for leave encashment, "No" otherwise.
            - "generate_encashment": HTML button string for triggering leave encashment generation.
    Raises:
        frappe.ValidationError: If "year" or "month" is not provided in the input data.
    Notes:
        - Employees must have completed at least one year of service to be eligible.
        - If a next encashment date exists, eligibility is further checked against the provided month and year.
        - Only employees with "Active" status (and optionally matching the specified company) are considered.
    """
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
    filters = {"status": "Active"}

    if data.get("company"):
        filters = {"status": "Active", "company": data.get("company")}
    emp_list = frappe.db.get_list(
        "Employee",
        filters=filters,
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
            encashment_data = frappe.db.sql(
                """
                                       SELECT tple.name FROM `tabPinnacle Leave Encashment` tple WHERE tple.employee = %s AND MONTH(encashment_date) = %s AND  YEAR(encashment_date) = %s
                                       """,
                (emp.get("employee"), month, year),
            )
            if encashment_data:
                encashment = f'<a href="/app/pinnacle-leave-encashment/{encashment_data[0][0]}" target="_blank">{encashment_data[0][0]}</a>'
            else:
                encashment = f"<button class='btn btn-sm btn-primary generate-encashment' data-emp='{emp.get('employee')}' data-empname='{emp.get('employee_name')}' data-doj='{emp.get('date_of_joining')}' data-last='{last_encashment_date}' data-next='{next_encashment_date}'>Generate</button>"
                
            eligible_employee_list.append(
                {
                    "employee": emp.get("employee"),
                    "employee_name": emp.get("employee_name"),
                    "date_of_joining": date_of_joining,
                    "last_encashment_date": last_encashment_date,
                    "next_encashment_date": next_encashment_date,
                    "eligible": eligibility,
                    "encashment": encashment,
                }
            )

    return eligible_employee_list
