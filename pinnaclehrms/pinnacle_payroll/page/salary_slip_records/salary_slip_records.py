import frappe
import calendar
from datetime import date


@frappe.whitelist()
def getSalarySlipRecords(company, year, month, employee=None):

    year = int(year)
    month = int(month)

    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    filters = {
        "company": company,
        "docstatus": 1,  
        "start_date": [">=", start_date],
        "end_date": ["<=", end_date],
    }

    if employee:
        filters["employee"] = employee

    salary_slips = frappe.get_all("Salary Slip", filters=filters, pluck="name")

    result = []

    for slip_name in salary_slips:
        pay_slip = frappe.get_doc("Salary Slip", slip_name)

        # -------------------------------
        # Salary Breakup (safe)
        # -------------------------------
        salary_info = {}
        for sal in pay_slip.salary_breakup:
            salary_info[sal.particulars] = {"days": sal.days, "amount": sal.amount}

        # -------------------------------
        # Earnings
        # -------------------------------
        basic_salary = 0
        other_earnings_total = 0
        other_earnings_info = []

        for e in pay_slip.earnings:
            if e.salary_component == "Basic":
                basic_salary += e.amount
            else:
                other_earnings_total += e.amount
                other_earnings_info.append(
                    {"component": e.salary_component, "amount": e.amount}
                )

        # -------------------------------
        # Employee info (single fetch)
        # -------------------------------
        emp = (
            frappe.db.get_value(
                "Employee",
                pay_slip.employee,
                ["company_email", "pan_number", "date_of_joining"],
                as_dict=True,
            )
            or {}
        )

        pay_slip_dict = {
            "pay_slip_name": pay_slip.name,
            "year": year,
            "month": month,
            "employee": pay_slip.employee,
            "employee_name": pay_slip.employee_name,
            "company": pay_slip.company,
            "designation": pay_slip.designation,
            "department": pay_slip.department,
            "email": emp.get("company_email"),
            "standard_working_days": pay_slip.total_working_days,
            "pan_number": emp.get("pan_number"),
            "date_of_joining": emp.get("date_of_joining"),
            "basic_salary": basic_salary,
            "per_day_salary": (
                basic_salary / pay_slip.total_working_days
                if pay_slip.total_working_days
                else 0
            ),
            "actual_working_days": pay_slip.payment_days,
            "absent": pay_slip.absent_days,
            "total": pay_slip.gross_pay,
            "net_payable_amount": pay_slip.net_pay,
            "salary_info": salary_info,
            "other_earnings": other_earnings_info,
            "other_earnings_total": other_earnings_total,
        }
        print(pay_slip_dict)
        result.append(pay_slip_dict)

    return result
