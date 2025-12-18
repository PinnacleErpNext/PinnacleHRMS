# Copyright (c) 2025, OTPL and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
import calendar
from frappe.utils import getdate, relativedelta
from frappe.model.document import Document
import frappe, json, calendar
from frappe.utils import getdate, add_months, formatdate, cint, flt, get_last_day
from datetime import datetime
from datetime import date


class RecurringSalaryComponent(Document):
    def before_save(self):
        if not self.due_date:
            self.due_date = _get_last_date_of_month(self.month, self.year)


def _get_last_date_of_month(month_name, year):
    """Return the last date of the given month name for the specified year."""

    # Convert month name to month number (1–12)
    try:
        month_number = list(calendar.month_name).index(month_name.strip().capitalize())
    except ValueError:
        raise ValueError(f"Invalid month name: {month_name}")

    if month_number == 0:
        raise ValueError(f"Invalid month name: {month_name}")

    # Get the number of days in the given month and year
    last_day = calendar.monthrange(year, month_number)[1]

    # Return the last date of the month
    return date(year, month_number, last_day)


@frappe.whitelist()
def create_rsc(data):

    try:
        # Parse incoming JSON
        if isinstance(data, str):
            data = json.loads(data)
        print("Data received in create_rsc:", data)

        employee = data.get("employee")
        salary_component = data.get("salary_component")
        total_amount = flt(str(data.get("total_amount") or "0").replace(",", ""))
        number_of_months = cint(data.get("number_of_months") or 0)
        start_date = data.get("start_date")
        schedule = data.get("schedule", [])

        # Validation
        if (
            not employee
            or not salary_component
            or not total_amount
            or not number_of_months
            or not start_date
        ):
            frappe.throw(
                "Missing required fields: Employee, Salary Component, Total Amount, Number of Months, Start Date"
            )

        if not schedule:
            frappe.throw(
                "Schedule data is missing. Please generate preview before saving."
            )

        created_docs = []

        # Process each month in schedule
        for entry in schedule:
            month_label = entry.get("month")
            amount = flt(entry.get("amount") or 0)

            if not month_label or amount <= 0:
                continue

            # Extract year and month safely from "MonthName-Year" format
            try:
                schedule_date = datetime.strptime(month_label, "%B-%Y")
            except ValueError:
                frappe.throw(
                    f"Invalid month format: {month_label}. Expected 'Month-Year' like 'September-2025'"
                )

            # Get last day of that month
            due_date = get_last_day(schedule_date)
            if entry.get("override"):
                exists = frappe.db.exists(
                    "Recurring Salary Component",
                    {
                        "employee": employee,
                        "component": salary_component,
                        "due_date": due_date,
                    },
                )
                if exists:
                    rsc_doc = frappe.get_doc("Recurring Salary Component", exists)
                    rsc_doc.employee = employee
                    rsc_doc.component = salary_component
                    rsc_doc.amount = amount
                    rsc_doc.month = schedule_date.strftime("%B")
                    rsc_doc.due_date = due_date.strftime("%Y-%m-%d")
                    rsc_doc.save(ignore_permissions=True)
                    created_docs.append(rsc_doc.name)
            else:
                # Create document
                rsc = frappe.get_doc(
                    {
                        "doctype": "Recurring Salary Component",
                        "employee": employee,
                        "component": salary_component,
                        "amount": amount,
                        "month": schedule_date.strftime("%B"),
                        "due_date": due_date.strftime("%Y-%m-%d"),
                    }
                )
                rsc.insert(ignore_permissions=True)
                created_docs.append(rsc.name)

        # Commit once at the end
        frappe.db.commit()
        return {
            "status": "success",
            "message": {"created": created_docs, "total_created": len(created_docs)},
        }

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(), "Recurring Salary Component Creation Error"
        )
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_existing_records(employee, salary_component, start_date, num_months):
    """
    Fetch existing recurring salary components for given employee and component
    to mark preview rows as 'Existing' or 'New'.
    Returns a list of month labels like ['January-2025', 'February-2025'].
    """

    try:
        existing_periods = []

        # Convert start_date string (YYYY-MM-DD) to datetime object
        start = datetime.strptime(start_date, "%Y-%m-%d")

        for i in range(int(num_months)):
            # Move to next month
            next_date = start + relativedelta(months=i)

            # Set date to last day of that month
            last_day = calendar.monthrange(next_date.year, next_date.month)[1]
            final_date = next_date.replace(day=last_day)

            # Format final date as DD-MM-YYYY
            formatted_final_date = final_date.strftime("%d-%m-%Y")

            # For frontend comparison like "September-2025"
            month_label = next_date.strftime("%B-%Y")

            # Debug logging
            frappe.logger().debug(
                f"Checking existence for {month_label} ({formatted_final_date})"
            )

            print(f"Checking existence for {formatted_final_date}")

            # Check if a record already exists for this employee, component, and due date
            exists = frappe.db.exists(
                "Recurring Salary Component",
                {
                    "employee": employee,
                    "component": salary_component,
                    "due_date": datetime.strptime(
                        formatted_final_date, "%d-%m-%Y"
                    ).strftime("%Y-%m-%d"),
                },
            )
            print(f"cheking for {formatted_final_date} : {exists}")
            if exists:
                existing_periods.append(month_label)

        return existing_periods

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error in get_existing_records")
        return []
