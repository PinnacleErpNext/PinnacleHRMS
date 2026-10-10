import frappe
from frappe.utils import flt


def update_leave_encashment_status(doc, method=None):
    """
    On Salary Slip submit:
    - Loop through Earnings table
    - Find linked Additional Salary
    - If Additional Salary is against Pinnacle Leave Encashment
    - Mark Leave Encashment as Paid
    """

    processed_docs = set()

    for row in doc.earnings:
        if not row.additional_salary:
            continue

        additional_salary = frappe.get_doc("Additional Salary", row.additional_salary)

        if (
            additional_salary.ref_doctype == "Pinnacle Leave Encashment"
            and additional_salary.ref_docname
        ):
            # Avoid updating same document multiple times
            if additional_salary.ref_docname in processed_docs:
                continue

            frappe.db.set_value(
                "Pinnacle Leave Encashment",
                additional_salary.ref_docname,
                "status",
                "Paid",
                update_modified=False,
            )

            processed_docs.add(additional_salary.ref_docname)


def before_save(salary_slip, method=None):
    """
    Before saving the Salary Slip:
    1. Fetch the Salary Structure Assignment base into base_salary.
    2. Set loyalty_bonus from the Salary Slip earnings.
    3. If the loyalty component is not present in earnings yet,
       fetch its amount from the applicable Salary Structure.
    """

    # ---------------------------------------------------------
    # 1. Fetch Salary Structure Assignment
    # ---------------------------------------------------------

    salary_structure_assignment = None

    if salary_slip.employee and salary_slip.salary_structure:
        salary_structure_assignment = frappe.db.get_value(
            "Salary Structure Assignment",
            {
                "employee": salary_slip.employee,
                "salary_structure": salary_slip.salary_structure,
                "docstatus": 1,
                "from_date": ["<=", salary_slip.start_date],
            },
            ["name", "base"],
            order_by="from_date desc",
            as_dict=True,
        )

    if salary_structure_assignment:
        salary_slip.base_salary = flt(salary_structure_assignment.base)

    # ---------------------------------------------------------
    # 2. Get Loyalty Bonus from Salary Slip Earnings
    # ---------------------------------------------------------

    loyalty_bonus = 0
    loyalty_component_found = False
    
    for earning in salary_slip.get("earnings") or []:

        if earning.salary_component == "Loyalty Incentive and Contribution":
            loyalty_bonus += flt(earning.amount)
            loyalty_component_found = True

    # ---------------------------------------------------------
    # 3. Fallback: Fetch from Salary Structure Assignment's
    #    Salary Structure when the component is missing
    # ---------------------------------------------------------

    if not loyalty_component_found and salary_structure_assignment:
        salary_structure = frappe.get_doc(
            "Salary Structure",
            salary_slip.salary_structure,
        )

        for earning in salary_structure.get("earnings") or []:
            if earning.salary_component == "Loyalty Incentive and Contribution":
                loyalty_bonus += flt(earning.amount)

    salary_slip.loyalty_bonus = loyalty_bonus
    
    salary_slip.total = flt(salary_slip.base_salary) + flt(loyalty_bonus)
