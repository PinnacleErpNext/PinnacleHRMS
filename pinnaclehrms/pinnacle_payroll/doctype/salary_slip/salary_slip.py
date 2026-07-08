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

        additional_salary = frappe.get_doc(
            "Additional Salary", row.additional_salary
        )

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