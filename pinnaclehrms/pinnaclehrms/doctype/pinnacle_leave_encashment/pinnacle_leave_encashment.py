# Copyright (c) 2025, OTPL and contributors
# For license information, please see license.txt

import frappe, json, calendar
from frappe import _
from frappe.model.document import Document
from datetime import datetime
from pinnaclehrms.utility.salary_calculator import getSalaryDetails
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta


class PinnacleLeaveEncashment(Document):

    def validate(self):
        relieving_date = frappe.db.get_value(
            "Employee", self.employee, "relieving_date"
        )
        if relieving_date:
            self.next_encashment_date = ""
            to_date = datetime.strptime(self.to_date, "%Y-%m-%d").date()
            if to_date > relieving_date:
                frappe.throw(
                    _("To Date cannot be after the employee's relieving date.")
                )

    def before_save(self):
        if self.employee:
            data = {
                "from_date": self.from_date,
                "to_date": self.to_date or self.encashment_date,
                "employee": self.employee,
            }

            encashment = _process_encashment(data)

            self.days_in_above = encashment.get("total_days")
            self.average_salary = encashment.get("average_salary")
            self.eligible_days = encashment.get("eligible_days")
            self.amount = encashment.get("amount")
            self.next_encashment_date = encashment.get("next_encashment_date")
            self.salary_structure = encashment.get("salary_structure")


@frappe.whitelist()
def generate_leave_encashment(data):
    """
    Generates leave encashment records for a list of selected employees for a given year and month.

    Args:
        data (str or dict): JSON string or dictionary containing the following keys:
            - "selected_emp" (list): List of employee dictionaries, each containing:
                - "employee" (str): Employee ID.
                - "eligible" (str): Eligibility status ("Yes" or "No").
                - "from_date" (str): Start date for encashment period.
            - "year" (int or str): The year for leave encashment.
            - "month" (str): The month for leave encashment (to be converted to month code).

    Returns:
        list: List of created "Pinnacle Leave Encashment" document objects.

    Raises:
        frappe.ValidationError: If input data is invalid or required fields are missing.
        frappe.ValidationError: If an error occurs during document creation (with error logged).

    Side Effects:
        - Inserts new "Pinnacle Leave Encashment" documents into the database.
        - Displays a message for employees not eligible for leave encashment.
        - Logs errors and throws a user-friendly error message if an exception occurs.
    """

    try:
        data = frappe.parse_json(data)

        emp_list = data.get("selected_emp", [])
        year = int(data.get("year", 0))
        month = _get_month_code(data.get("month"))

        if not emp_list or not year or not month:
            frappe.throw(
                _("Invalid input data. Please provide employee list, year, and month.")
            )

        encashment_records = []

        for emp in emp_list:

            emp_id = emp.get("employee")
            if emp.get("eligible") != "Yes":
                frappe.msgprint(
                    _("{0} is not eligible for leave encashment.").format(emp_id)
                )
                continue
            doc = frappe.get_doc(
                {
                    "doctype": "Pinnacle Leave Encashment",
                    "employee": emp_id,
                    "from_date": emp.get("from_date"),
                    "to_date": f"{year}-{month}-{calendar.monthrange(year, month)[1]}",
                }
            )
            doc.insert()
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


def _process_encashment(data):
    """
    Processes leave encashment for an employee based on the provided data.

    This function checks if a leave encashment record already exists for the given employee and date range.
    If it exists, it returns a message with a link to the existing record. Otherwise, it calculates the eligible
    leave encashment amount based on the employee's paid leaves, average salary, and the period between the
    specified from and to dates. It also determines the next eligible encashment date and prepares a summary
    of the calculation.

    Args:
        data (dict): A dictionary containing the following keys:
            - "employee" (str): The employee ID.
            - "from_date" (str, optional): The start date for encashment calculation (format: "YYYY-MM-DD").
            - "to_date" (str): The end date for encashment calculation (format: "YYYY-MM-DD").
            - "next_encashment_date" (str, optional): The next eligible encashment date (format: "YYYY-MM-DD").

    Returns:
        dict: A dictionary containing the calculated encashment details, including:
            - "employee": Employee ID.
            - "from": Encashment period start date.
            - "upto": Encashment period end date.
            - "encashment_date": Date of encashment.
            - "amount": Calculated encashment amount.
            - "next_encashment_date": Next eligible encashment date.
            - "encashment_calculation": A summary string of the calculation.

    Raises:
        frappe.ValidationError: If the employee's joining date is not found.
    """

    emp = data.get("employee")
    encash_doc = frappe.db.exists(
        "Pinnacle Leave Encashment",
        {
            "employee": emp,
            "from": data.get("from_date"),
            "upto": data.get("to_date"),
        },
    )
    if encash_doc is not None:
        # encash_doc will be the name (ID) of the document
        link = f'<a href="/app/pinnacle-leave-encashment/{encash_doc}" target="_blank">{_("View Existing Leave Encashment")}</a>'
        return frappe.msgprint(
            _("Leave Encashment is already created! {0}").format(link),
            indicator="orange",
        )

    paid_leaves = (
        frappe.db.get_value("Assign Salary", {"employee_id": emp}, "paid_leaves") or 0
    )
    paid_leaves = paid_leaves / (24 * 60 * 60)  # Convert to days

    last_encashment_date = frappe.db.get_list(
        "Pinnacle Leave Encashment",
        filters={"employee": emp},
        fields=["encashment_date"],
        order_by="encashment_date desc",
        limit=1,
    )

    if data.get("from_date"):
        from_date = datetime.strptime(data.get("from_date"), "%Y-%m-%d")
    elif last_encashment_date:
        from_date = last_encashment_date[0].get("encashment_date")
    else:
        from_date = frappe.db.get_value("Employee", {"name": emp}, "date_of_joining")
        if not from_date:
            frappe.throw(_("Joining date not found for Employee {0}").format(emp))

    if data.get("to_date"):
        end_date = datetime.strptime(data.get("to_date"), "%Y-%m-%d")

    # leave_encashment_months = difference.years * 12 + difference.months + 1

    average_salary, salary_structure = _calAvgSalary(emp, from_date, end_date)
    total_days = (end_date - from_date).days
    eligible_days = round(((total_days / 365) * paid_leaves), 2)

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

    leave_encashment_amount = eligible_days * average_salary

    encashment = {
        "employee": emp,
        "from": from_date.strftime("%Y-%m-%d"),
        "upto": end_date.strftime("%Y-%m-%d"),
        "encashment_date": end_date.strftime("%Y-%m-%d"),
        "amount": round(leave_encashment_amount, 2),
        "next_encashment_date": next_encashment_date,
        "total_days": total_days,
        "average_salary": average_salary,
        "eligible_days": eligible_days,
        "salary_structure": salary_structure,
    }

    return encashment


def _calAvgSalary(empID, from_date, end_date):
    """
    Calculate the average daily salary for an employee within a specified date range.

    This function retrieves the salary history for the given employee (`empID`) between `from_date` and `end_date`.
    It computes the average daily salary over the period, accounting for any salary changes that may have occurred.
    If salary data is missing for the start date, it fetches the basic salary using `getSalaryDetails`.

    Args:
        empID (str): The employee ID for whom the average salary is to be calculated.
        from_date (datetime): The start date of the period.
        end_date (datetime): The end date of the period.

    Returns:
        float: The average daily salary over the specified period. Returns 0 if no salary data is found.
    """
    startDate = from_date.date()
    endDate = end_date.date()

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

    salaryStructure[startDate] = salary
    salaryStructure = dict(sorted(salaryStructure.items()))
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

    average_salary = round((total_salary / day_count), 2) if day_count > 0 else 0

    salary_details_text = "Salary Details:\n"
    salary_details_text += f"{'From Date':<15}{'Salary (₹)':>12}\n"
    salary_details_text += "-" * 27 + "\n"

    for date, salary in salaryStructure.items():
        salary_details_text += f"{date.strftime('%Y-%m-%d'):<15}₹{salary:>10,.2f}\n"

    return average_salary, salary_details_text


def _get_month_code(month_name):
    """
    Return the numeric code for a given month name.
    Args:
        month_name (str): The full name of the month (e.g., "January", "February").
    Returns:
        int: The numeric code of the month (1 for January, 2 for February, ..., 12 for December).
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
