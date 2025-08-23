# Copyright (c) 2025, OTPL and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
import calendar
from frappe.utils import getdate
from frappe.model.document import Document
import frappe, json, calendar
from frappe.utils import getdate, add_months, formatdate, cint, flt
from datetime import datetime


class RecurringSalaryComponent(Document):
    pass


@frappe.whitelist()
def create_rsc(data):
    """
    Creates Recurring Salary Component entries in bulk

    Args:
        data (json): {
            "employee": "EMP-0001",
            "rows": [
                {
                    "salary_component": "Basic Salary",
                    "total_amount": "12000",
                    "number_of_months": 12,
                    "start_date": "2025-09-30"
                }
            ]
        }
    """
    frappe.logger().info(f"Creating Recurring Salary Components with data: {data}")
    data = json.loads(data)
    emp_id = data.get("employee")

    if not emp_id:
        frappe.throw(_("Employee ID is required."))

    rows = data.get("rows", [])
    if not rows:
        frappe.throw(_("At least one salary component is required."))

    created_docs = []

    for row in rows:
        component = row.get("salary_component")
        amount = flt(str(row.get("total_amount") or 0).replace(",", ""))
        num_months = cint(row.get("number_of_months") or 0)
        start_date = getdate(row.get("start_date")) if row.get("start_date") else None

        if not component or not amount or not num_months or not start_date:
            continue

        # divide equally
        per_month_amount = amount / num_months

        for i in range(num_months):
            schedule_date = add_months(start_date, i)

            month_name = schedule_date.strftime("%B")
            year = schedule_date.year
            month_num = schedule_date.month
            last_day = calendar.monthrange(year, month_num)[1]
            recurring_schedule = f"{year}-{month_num:02d}-{last_day:02d}"

            rsc = frappe.get_doc(
                {
                    "doctype": "Recurring Salary Component",
                    "employee": emp_id,
                    "component": component,
                    "amount": per_month_amount,
                    "month": month_name,
                    "recurring_schedule": recurring_schedule,
                }
            )
            rsc.insert(ignore_permissions=True)
            created_docs.append(rsc.name)

    frappe.db.commit()

    return {"created": created_docs}
