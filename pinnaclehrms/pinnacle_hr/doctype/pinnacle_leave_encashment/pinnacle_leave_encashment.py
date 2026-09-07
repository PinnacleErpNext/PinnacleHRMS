# Copyright (c) 2026, Opticode Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, json, calendar
from frappe import _
from frappe.model.document import Document
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta


class PinnacleLeaveEncashment(Document):

    def validate(self):
        relieving_date = frappe.db.get_value(
            "Employee", self.employee, "relieving_date"
        )

        if relieving_date:
            self.next_encashment_date = ""

            if self.to_date:
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

            if self.next_encashment_date:
                data["next_encashment_date"] = self.next_encashment_date

            encashment = _process_encashment(data)

            self.days_in_above = encashment.get("total_days")
            self.average_salary = encashment.get("average_salary")
            self.eligible_days = encashment.get("eligible_days")
            self.amount = encashment.get("amount")
            self.next_encashment_date = encashment.get("next_encashment_date")
            self.salary_structure = encashment.get("salary_structure")

            # Set encashment date
            self.encashment_date = encashment.get("encashment_date")

    def on_submit(self):

        additional_salary = frappe.new_doc("Additional Salary")
        additional_salary.employee = self.employee
        additional_salary.salary_component = "Leave Encashment"
        additional_salary.amount = self.amount
        additional_salary.payroll_date = self.encashment_date
        additional_salary.company = frappe.db.get_value(
            "Employee", self.employee, "company"
        )

        # Reference linking (important for traceability)
        additional_salary.ref_doctype = self.doctype
        additional_salary.ref_docname = self.name

        additional_salary.insert(ignore_permissions=True)
        additional_salary.submit()

        # Store reference back
        # self.db_set("additional_salary", additional_salary.name)


@frappe.whitelist()
def generate_leave_encashment(data):
    """
    Generates leave encashment records for a list of selected employees
    for a given year and month.

    Args:
        data (str or dict): JSON string or dictionary containing the
        following keys:
            - "selected_emp" (list): List of employee dictionaries
            - "year" (int or str): The year for leave encashment.
            - "month" (str): The month for leave encashment.

    Returns:
        list: List of created "Pinnacle Leave Encashment" documents.

    Raises:
        frappe.ValidationError: If input data is invalid or required
        fields are missing.
    """

    try:
        data = frappe.parse_json(data)

        emp_list = data.get("selected_emp", [])
        year = int(data.get("year", 0))
        month = _get_month_code(data.get("month"))

        if not emp_list or not year or not month:
            frappe.throw(
                _(
                    "Invalid input data. Please provide employee list, "
                    "year, and month."
                )
            )

        encashment_records = []

        for emp in emp_list:

            emp_id = emp.get("employee")

            if emp.get("eligible") != "Yes":
                frappe.msgprint(
                    _("{0} is not eligible for leave encashment.").format(emp_id)
                )
                continue

            # Last date of selected month
            last_day_of_month = calendar.monthrange(year, month)[1]

            doc = frappe.get_doc(
                {
                    "doctype": "Pinnacle Leave Encashment",
                    "employee": emp_id,
                    "from_date": emp.get("from_date"),
                    "to_date": f"{year}-{month}-{last_day_of_month}",
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
                "An error occurred while generating leave encashment. "
                "Please check the logs."
            )
        )


def _process_encashment(data):
    """
    Processes leave encashment for an employee.

    Encashment Date Logic:

    1. If the employee has a relieving date and the relieving date
       falls within the encashment period, the relieving date is used.

    2. Otherwise, the last date of the month of `to_date` is used.

    Example:

        Relieving Date = 2026-08-15
        To Date        = 2026-08-31
        Encashment Date = 2026-08-15

        No Relieving Date
        To Date        = 2026-08-31
        Encashment Date = 2026-08-31
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
        link = (
            f'<a href="/app/pinnacle-leave-encashment/'
            f'{encash_doc}" target="_blank">'
            f'{_("View Existing Leave Encashment")}'
            f"</a>"
        )

        return frappe.msgprint(
            _("Leave Encashment is already created! {0}").format(link),
            indicator="orange",
        )

    # -------------------------------------------------------
    # 1. Determine end date
    # -------------------------------------------------------

    if data.get("to_date"):
        end_date = datetime.strptime(data.get("to_date"), "%Y-%m-%d")
    else:
        frappe.throw(_("To Date is required"))

    # -------------------------------------------------------
    # 2. Fetch the applicable Salary Structure Assignment
    # -------------------------------------------------------

    latest_ssa = frappe.db.get_value(
        "Salary Structure Assignment",
        {
            "employee": emp,
            "docstatus": 1,
            "from_date": ("<=", end_date.date()),
        },
        ["name", "from_date", "paid_leaves"],
        as_dict=True,
        order_by="from_date desc",
    )

    # -------------------------------------------------------
    # 3. Get employee relieving date
    # -------------------------------------------------------

    relieving_date = frappe.db.get_value("Employee", emp, "relieving_date")

    if not latest_ssa:
        frappe.throw(
            _(
                "No submitted Salary Structure Assignment found "
                "for Employee {0} before {1}"
            ).format(emp, end_date.strftime("%Y-%m-%d"))
        )

    paid_leaves = latest_ssa.paid_leaves or 0

    # Convert seconds to days
    paid_leaves = paid_leaves / (24 * 60 * 60)

    # -------------------------------------------------------
    # 4. Get last encashment date
    # -------------------------------------------------------

    last_encashment_date = frappe.db.get_list(
        "Pinnacle Leave Encashment",
        filters={"employee": emp},
        fields=["encashment_date"],
        order_by="encashment_date desc",
        limit=1,
    )

    # -------------------------------------------------------
    # 5. Determine From Date
    # -------------------------------------------------------

    if data.get("from_date"):
        from_date = datetime.strptime(data.get("from_date"), "%Y-%m-%d")

    elif last_encashment_date:
        from_date = last_encashment_date[0].get("encashment_date")

    else:
        from_date = frappe.db.get_value("Employee", {"name": emp}, "date_of_joining")

        if not from_date:
            frappe.throw(_("Joining date not found for Employee {0}").format(emp))

        # Convert date to datetime
        if isinstance(from_date, date) and not isinstance(from_date, datetime):
            from_date = datetime.combine(from_date, datetime.min.time())

    # -------------------------------------------------------
    # 6. Re-confirm To Date
    # -------------------------------------------------------

    if data.get("to_date"):
        end_date = datetime.strptime(data.get("to_date"), "%Y-%m-%d")

    # -------------------------------------------------------
    # 7. Calculate Average Salary
    # -------------------------------------------------------

    average_salary, salary_structure = _calAvgSalary(emp, from_date, end_date)

    # -------------------------------------------------------
    # 8. Calculate Total Days
    # -------------------------------------------------------

    total_days = (end_date - from_date).days + 1

    eligible_days = round((total_days / 365) * paid_leaves, 2)

    # -------------------------------------------------------
    # 9. Determine Next Encashment Date
    # -------------------------------------------------------

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

    # -------------------------------------------------------
    # 10. Calculate Encashment Amount
    # -------------------------------------------------------

    leave_encashment_amount = eligible_days * average_salary

    # -------------------------------------------------------
    # 11. Determine Encashment Date
    #
    # Requirement:
    #
    # If relieving date falls within the encashment period:
    #     Encashment Date = relieving date
    #
    # Otherwise:
    #     Encashment Date = last date of the month of To Date
    # -------------------------------------------------------

    last_day_of_month = date(
        end_date.year,
        end_date.month,
        calendar.monthrange(end_date.year, end_date.month)[1],
    )
    frappe.throw(str(last_day_of_month))
    if relieving_date and from_date.date() <= relieving_date <= end_date.date():
        encashment_date = relieving_date
    else:
        encashment_date = last_day_of_month

    # -------------------------------------------------------
    # 12. Prepare Result
    # -------------------------------------------------------

    encashment = {
        "employee": emp,
        "from": from_date.strftime("%Y-%m-%d"),
        "upto": end_date.strftime("%Y-%m-%d"),
        # Final Encashment Date
        "encashment_date": encashment_date,
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
    Calculate average daily salary using Salary Structure Assignment.
    """

    startDate = from_date.date()
    endDate = end_date.date()

    # -------------------------------------------------------
    # 1. Get salary revisions from Salary Structure Assignment
    # -------------------------------------------------------

    salary_data = frappe.db.sql(
        """
        SELECT
            from_date,
            base
        FROM `tabSalary Structure Assignment`
        WHERE
            employee = %s
            AND docstatus = 1
            AND from_date <= %s
        ORDER BY from_date
        """,
        (empID, endDate),
        as_dict=True,
    )

    if not salary_data:
        return (0, "No Salary Structure Assignment found")

    # -------------------------------------------------------
    # 2. Build salary structure timeline
    # -------------------------------------------------------

    salaryStructure = {}

    for row in salary_data:

        salaryStructure[row.from_date] = row.base or 0

    # Ensure start date has salary

    applicable_salary = None

    for salary_date in sorted(salaryStructure.keys()):

        if salary_date <= startDate:

            applicable_salary = salaryStructure[salary_date]

        else:
            break

    salaryStructure[startDate] = applicable_salary or 0

    salaryStructure = dict(sorted(salaryStructure.items()))

    # -------------------------------------------------------
    # 3. Calculate daily salary across period
    # -------------------------------------------------------

    total_salary = 0
    day_count = 0

    current_salary = salaryStructure[startDate]

    current_date = startDate

    while current_date <= endDate:

        if current_date in salaryStructure:

            current_salary = salaryStructure[current_date]

        if current_salary:

            days_in_month = calendar.monthrange(current_date.year, current_date.month)[
                1
            ]

            per_day_salary = round(current_salary / days_in_month, 2)

            total_salary += per_day_salary
            day_count += 1

        current_date += timedelta(days=1)

    average_salary = round(total_salary / day_count, 2) if day_count > 0 else 0

    # -------------------------------------------------------
    # 4. Salary detail text
    # -------------------------------------------------------

    salary_details_text = "Salary Details:\n"

    salary_details_text += f"{'From Date':<15}" f"{'Salary (₹)':>12}\n"

    salary_details_text += "-" * 27 + "\n"

    for salary_date, salary in salaryStructure.items():

        salary_details_text += (
            f"{salary_date.strftime('%Y-%m-%d'):<15}" f"₹{salary:>10,.2f}\n"
        )

    return (average_salary, salary_details_text)


def _get_month_code(month_name):
    """
    Return the numeric code for a given month name.

    Args:
        month_name (str): Full month name.

    Returns:
        int: Numeric month code.
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
