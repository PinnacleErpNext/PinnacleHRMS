import frappe

from frappe.utils import add_years, date_diff, getdate, today


@frappe.whitelist()
def get_data(filters=None):

    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    conditions = ""

    if filters.get("company"):
        conditions += f" AND ssa.company = '{filters.get('company')}' "

    if filters.get("employee"):
        conditions += f"""
			AND (
				ssa.employee LIKE '%{filters.get("employee")}%'
				OR emp.employee_name LIKE '%{filters.get("employee")}%'
			)
		"""

    data = frappe.db.sql(
        f"""
		SELECT
			ssa.name,
			ssa.employee,
			emp.employee_name,
			emp.department,
			ssa.salary_structure,
			ssa.from_date,
			ssa.base,
			ssa.company
		FROM `tabSalary Structure Assignment` ssa
		LEFT JOIN `tabEmployee` emp
			ON emp.name = ssa.employee
		WHERE
			ssa.docstatus = 1
			AND emp.status = 'Active'
			{conditions}
		ORDER BY
			ssa.employee,
			ssa.from_date DESC
	""",
        as_dict=1,
    )

    grouped = {}

    for row in data:

        if row.employee not in grouped:
            grouped[row.employee] = []

        grouped[row.employee].append(row)

    final_data = []

    today_date = getdate(today())

    for employee, records in grouped.items():

        latest = records[0]

        last_increment = latest.from_date

        next_increment = add_years(last_increment, 1)

        status = "Active"

        diff = date_diff(next_increment, today_date)

        if today_date > getdate(next_increment):
            status = "Overdue"

        elif today_date == getdate(next_increment):
            status = "Eligible"

        elif diff <= 30:
            status = "Upcoming"

        if filters.get("status") and filters.get("status") != status:
            continue

        history = []

        for index, row in enumerate(records):

            previous_salary = 0

            if index + 1 < len(records):
                previous_salary = records[index + 1].base or 0

            current_salary = row.base or 0

            history.append(
                {
                    "from_date": row.from_date,
                    "salary_structure": row.salary_structure,
                    "previous_salary": previous_salary,
                    "current_salary": current_salary,
                    "increment": current_salary - previous_salary,
                }
            )

        final_data.append(
            {
                "employee": latest.employee,
                "employee_name": latest.employee_name,
                "department": latest.department,
                "current_salary": latest.base,
                "last_increment": last_increment,
                "next_increment": next_increment,
                "status": status,
                "history": history,
            }
        )

    return final_data
