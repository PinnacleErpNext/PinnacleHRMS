import frappe
from pinnaclehrms.pinnacle_hr.constants import CUSTOM_ATTENDANCE_STATUSES


# ---------------------------------------------------------
# PART 1: ADD / REMOVE CUSTOM ATTENDANCE STATUSES
# ---------------------------------------------------------
def add_custom_attendance_statuses():
    field = frappe.get_doc(
        "DocField",
        {"parent": "Attendance", "fieldname": "status"},
    )

    existing = field.options.split("\n")
    updated = list(existing)

    for s in CUSTOM_ATTENDANCE_STATUSES:
        if s not in updated:
            updated.append(s)

    field.options = "\n".join(updated)
    field.save()
    frappe.clear_cache()


def remove_custom_attendance_statuses():
    field = frappe.get_doc(
        "DocField",
        {"parent": "Attendance", "fieldname": "status"},
    )
    print(field)
    existing = field.options.split("\n")
    updated = [x for x in existing if x not in CUSTOM_ATTENDANCE_STATUSES]

    field.options = "\n".join(updated)
    field.save()
    frappe.clear_cache()


# ---------------------------------------------------------
# PART 2: ADD SALARY BREAKUP SECTION + TABLE + PARTICULARS FIELD
# ---------------------------------------------------------
def add_salary_breakup_field_to_salary_slip():
    """
    Adds the Salary Breakup section + table + particulars field to Salary Slip.
    Child DocType must already exist.
    """

    # 1) Section Break (after deductions)
    if not frappe.db.exists("Custom Field", "Salary Slip-salary_breakup_section"):
        section = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Salary Slip",
            "label": "Salary Breakup",
            "fieldname": "salary_breakup_section",
            "fieldtype": "Section Break",
            "insert_after": "deductions"
        })
        section.insert(ignore_permissions=True)

    # 2) Table field (after section)
    if not frappe.db.exists("Custom Field", "Salary Slip-salary_breakup"):
        table_field = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Salary Slip",
            "label": "Salary Breakup Details",
            "fieldname": "salary_breakup",
            "fieldtype": "Table",
            "options": "Salary Breakdown",    # <-- make sure this matches your child DocType name
            "insert_after": "salary_breakup_section",
            "read_only": 1,
        })
        table_field.insert(ignore_permissions=True)

    # 3) NEW FIELD: Particulars (Select)
    if not frappe.db.exists("Custom Field", "Salary Slip-particulars"):
        particulars_field = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Attendance",
            "label": "Particulars",
            "fieldname": "particulars",
            "fieldtype": "Select",
            "insert_after": "early_exit",
            "options": "\n".join([
                "",
                "Full Day",
                "Late/Early",
                "Late & Early",
                "3/4 Day",
                "Half Day"
                "Quarter Day",
                "Absent",
            ]),
            "reqd": 0,
            "read_only": 1,
            "in_list_view": 1,
        })
        particulars_field.insert(ignore_permissions=True)

    frappe.clear_cache()


# ---------------------------------------------------------
# PART 3: RUN PATCHES
# ---------------------------------------------------------
def setup_salary_breakup_feature():
    """
    Run once from bench console OR during app installation.
    """
    add_custom_attendance_statuses()
    add_salary_breakup_field_to_salary_slip()

    frappe.logger().info("Salary Breakup fields + particulars added successfully.")
