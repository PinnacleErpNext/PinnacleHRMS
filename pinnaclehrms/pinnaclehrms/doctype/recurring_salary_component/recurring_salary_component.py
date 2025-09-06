# Copyright (c) 2025, OTPL and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
import calendar
from frappe.utils import getdate
from frappe.model.document import Document
import frappe, json, calendar
from frappe.utils import getdate, add_months, formatdate, cint, flt, get_last_day
from datetime import datetime


class RecurringSalaryComponent(Document):
    pass


@frappe.whitelist() 
def create_rsc(data):
    
    try:
        # Parse incoming JSON
        if isinstance(data, str):
            data = json.loads(data)
        
        employee = data.get("employee")
        salary_component = data.get("salary_component")
        total_amount = flt(str(data.get("total_amount") or "0").replace(",", ""))
        number_of_months = cint(data.get("number_of_months") or 0)
        start_date = data.get("start_date")
        schedule = data.get("schedule", [])
        
        # Validation
        if not employee or not salary_component or not total_amount or not number_of_months or not start_date:
            frappe.throw("Missing required fields: Employee, Salary Component, Total Amount, Number of Months, Start Date")

        if not schedule:
            frappe.throw("Schedule data is missing. Please generate preview before saving.")

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
                frappe.throw(f"Invalid month format: {month_label}. Expected 'Month-Year' like 'September-2025'")

            # Get last day of that month
            due_date = get_last_day(schedule_date)
            
            # Create document
            rsc = frappe.get_doc({
                "doctype": "Recurring Salary Component",
                "employee": employee,
                "component": salary_component,
                "amount": amount,
                "month": schedule_date.strftime("%B"),
                "due_date": due_date.strftime("%Y-%m-%d")
            })
            rsc.insert(ignore_permissions=True)
            created_docs.append(rsc.name)

        # Commit once at the end
        frappe.db.commit()
        return {
            "status": "success",
            "message": {
                "created": created_docs,
                "total_created": len(created_docs)
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Recurring Salary Component Creation Error")
        return {
            "status": "error",
            "message": str(e)
        }
