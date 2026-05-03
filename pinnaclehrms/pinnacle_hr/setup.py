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

    existing = field.options.split("\n")
    updated = [x for x in existing if x not in CUSTOM_ATTENDANCE_STATUSES]

    field.options = "\n".join(updated)
    field.save()
    frappe.clear_cache()


# ---------------------------------------------------------
# PART 2: ADD SALARY BREAKUP + PARTICULARS FIELD
# ---------------------------------------------------------
def add_salary_breakup_field_to_salary_slip():

    # 1) Section Break
    if not frappe.db.exists("Custom Field", {"dt": "Salary Slip", "fieldname": "salary_breakup_section"}):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Salary Slip",
            "label": "Salary Breakup",
            "fieldname": "salary_breakup_section",
            "fieldtype": "Section Break",
            "insert_after": "deductions"
        }).insert(ignore_permissions=True)

    # 2) Table field
    if not frappe.db.exists("Custom Field", {"dt": "Salary Slip", "fieldname": "salary_breakup"}):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Salary Slip",
            "label": "Salary Breakup Details",
            "fieldname": "salary_breakup",
            "fieldtype": "Table",
            "options": "Salary Breakdown",
            "insert_after": "salary_breakup_section",
            "read_only": 1,
        }).insert(ignore_permissions=True)

    # 3) Particulars field in Attendance
    if not frappe.db.exists("Custom Field", {"dt": "Attendance", "fieldname": "particulars"}):
        frappe.get_doc({
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
                "Half Day",
                "Quarter Day",
                "Absent",
            ]),
            "read_only": 1,
            "in_list_view": 1,
        }).insert(ignore_permissions=True)

    frappe.clear_cache()


# ---------------------------------------------------------
# ✅ PART 3: ADD HR SETTINGS FIELDS (NEW)
# ---------------------------------------------------------
def add_hr_settings_fields():
    """
    Adds:
    1. Max Allowed Attendance Correction per Fiscal Year
    2. Allowed Lates
    """

    # 1️⃣ Max Allowed Attendance Correction
    if not frappe.db.exists("Custom Field", {
        "dt": "HR Settings",
        "fieldname": "max_attendance_corrections_per_fiscal_year"
    }):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "HR Settings",
            "label": "Max Allowed Attendance Correction per Fiscal Year",
            "fieldname": "max_attendance_corrections_per_fiscal_year",
            "fieldtype": "Int",
            "insert_after": "retirement_age",
            "default": 6,
            "description": "Maximum number of attendance corrections allowed per fiscal year"
        }).insert(ignore_permissions=True)

    # 2️⃣ Allowed Lates
    if not frappe.db.exists("Custom Field", {
        "dt": "HR Settings",
        "fieldname": "allowed_lates"
    }):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "HR Settings",
            "label": "Allowed Lates",
            "fieldname": "allowed_lates",
            "fieldtype": "Int",
            "insert_after": "max_attendance_corrections_per_fiscal_year",
            "default": 3,
            "description": "Number of late entries allowed without penalty"
        }).insert(ignore_permissions=True)

    frappe.clear_cache()


# ---------------------------------------------------------
# PART 4: RUN PATCHES
# ---------------------------------------------------------
def setup_salary_breakup_feature():
    """
    Run once from bench console OR during app installation.
    """
    add_custom_attendance_statuses()
    add_salary_breakup_field_to_salary_slip()
    add_hr_settings_fields()

    frappe.logger().info("✅ Salary Breakup + HR Settings fields added successfully.")