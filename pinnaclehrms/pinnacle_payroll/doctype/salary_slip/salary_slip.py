import frappe


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


def before_save(doc, method=None):
    """
    Fetch Base Salary from Salary Structure Assignment
    and set it in Salary Slip's base_salary field.
    """

    if not doc.employee:
        return

    # Get the Salary Structure Assignment applicable to the Salary Slip
    assignment = frappe.get_all(
        "Salary Structure Assignment",
        filters={
            "employee": doc.employee,
            "company": doc.company,
            "from_date": ["<=", doc.start_date],
            "docstatus": 1,
        },
        fields=["name", "base"],
        order_by="from_date desc",
        limit=1,
    )

    if not assignment:
        doc.base_salary = 0
        return

    # Set Base Salary from Salary Structure Assignment
    doc.base_salary = assignment[0].base
