import frappe
from frappe import _
import json
import calendar
from datetime import datetime, date
from frappe.utils import flt, cint, get_last_day
from frappe.utils import relativedelta


@frappe.whitelist()
def create_additional_salary_components(data):
    """
    Create Additional Salary Components using Recurring Salary Component logic
    """

    try:
        if isinstance(data, str):
            data = json.loads(data)

        created_docs = []

        employee = data.get("employee")
        salary_component = data.get("salary_component")
        company = data.get("company")
        schedule = data.get("schedule", [])

        if not employee or not salary_component or not company:
            frappe.throw(_("Missing required fields"))

        if not schedule:
            frappe.throw(_("Schedule data is missing"))

        for entry in schedule:
            month_label = entry.get("month")
            amount = flt(entry.get("amount") or 0)
            override = cint(entry.get("override") or 0)

            if not month_label or amount <= 0:
                continue

            # Month-Year → datetime
            try:
                schedule_date = datetime.strptime(month_label, "%B-%Y")
            except ValueError:
                frappe.throw(
                    _(f"Invalid month format: {month_label}. Expected 'Month-Year'")
                )

            payroll_date = get_last_day(schedule_date)

            # 🔍 Check existing Additional Salary Component (safe + silent)
            existing = frappe.db.get_value(
                "Additional Salary",
                {
                    "employee": employee,
                    "salary_component": salary_component,
                    "payroll_date": payroll_date,
                },
                "name",
            )

            if existing:
                if override:
                    doc = frappe.get_doc("Additional Salary", existing)
                    doc.amount = amount
                    doc.is_recurring = 1
                    doc.save(ignore_permissions=True)
                    created_docs.append(doc.name)
                else:
                    # Existing record found but override not allowed → skip
                    continue
            else:
                doc = frappe.get_doc(
                    {
                        "doctype": "Additional Salary",
                        "employee": employee,
                        "salary_component": salary_component,
                        "company": company,
                        "amount": amount,
                        "payroll_date": payroll_date,
                    }
                )
                doc.insert(ignore_permissions=True)
                created_docs.append(doc.name)
        print(created_docs)
        return {
            "status": "success",
            "created": created_docs,
            "total_created": len(created_docs),
        }

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Additional Salary Component (Recurring) Creation Error",
        )
        raise


@frappe.whitelist()
def get_existing_additional_salaries(
    employee, salary_component, start_date, num_months
):
    """
    Fetch existing Additional Salary Components for given employee & component.
    Used to mark preview rows as Existing / New.
    Returns month labels like ['September-2025', 'October-2025']
    """

    try:
        existing_periods = []

        # Convert start date
        start = datetime.strptime(start_date, "%Y-%m-%d")

        for i in range(int(num_months)):
            current_date = start + relativedelta(months=i)

            # Get last day of the month
            last_day = calendar.monthrange(current_date.year, current_date.month)[1]
            payroll_date = current_date.replace(day=last_day)

            month_label = current_date.strftime("%B-%Y")

            exists = frappe.db.exists(
                "Additional Salary",
                {
                    "employee": employee,
                    "salary_component": salary_component,
                    "payroll_date": payroll_date.strftime("%Y-%m-%d"),
                },
            )

            if exists:
                existing_periods.append(month_label)

        return existing_periods

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Error in get_existing_additional_salaries",
        )
        return []
