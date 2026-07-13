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
    if frappe.db.exists(
        "Custom Field", {"dt": "Salary Slip", "fieldname": "salary_breakup_section"}
    ):
        field = frappe.get_doc(
            "Custom Field",
            {"dt": "Salary Slip", "fieldname": "salary_breakup_section"},
        )

        field.label = "Salary Breakup"
        field.fieldtype = "Section Break"
        field.insert_after = "deductions"
        field.save(ignore_permissions=True)

    else:
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": "Salary Slip",
                "label": "Salary Breakup",
                "fieldname": "salary_breakup_section",
                "fieldtype": "Section Break",
                "insert_after": "deductions",
            }
        ).insert(ignore_permissions=True)

    # 2) Table field
    if frappe.db.exists(
        "Custom Field", {"dt": "Salary Slip", "fieldname": "salary_breakup"}
    ):
        field = frappe.get_doc(
            "Custom Field",
            {"dt": "Salary Slip", "fieldname": "salary_breakup"},
        )

        field.label = "Salary Breakup Details"
        field.fieldtype = "Table"
        field.options = "Salary Breakdown"
        field.insert_after = "salary_breakup_section"
        field.read_only = 1
        field.save(ignore_permissions=True)

    else:
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": "Salary Slip",
                "label": "Salary Breakup Details",
                "fieldname": "salary_breakup",
                "fieldtype": "Table",
                "options": "Salary Breakdown",
                "insert_after": "salary_breakup_section",
                "read_only": 1,
            }
        ).insert(ignore_permissions=True)

    # 3) Particulars field in Attendance
    particulars_options = "\n".join(
        [
            "",
            "Full Day",
            "Sunday Working",
            "Late/Early",
            "Late & Early",
            "3/4 Day",
            "65% Particular",
            "Half Day",
            "40% Particular",
            "Quarter Day",
            "15% Particular",
            "Absent",
        ]
    )

    if frappe.db.exists(
        "Custom Field", {"dt": "Attendance", "fieldname": "particulars"}
    ):
        field = frappe.get_doc(
            "Custom Field",
            {"dt": "Attendance", "fieldname": "particulars"},
        )

        field.label = "Particulars"
        field.fieldtype = "Select"
        field.insert_after = "early_exit"
        field.options = particulars_options
        field.read_only = 1
        field.in_list_view = 1
        field.save(ignore_permissions=True)

    else:
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": "Attendance",
                "label": "Particulars",
                "fieldname": "particulars",
                "fieldtype": "Select",
                "insert_after": "early_exit",
                "options": particulars_options,
                "read_only": 1,
                "in_list_view": 1,
            }
        ).insert(ignore_permissions=True)

    frappe.clear_cache()


# ---------------------------------------------------------
# ✅ PART 3: ADD HR SETTINGS FIELDS
# ---------------------------------------------------------
def add_hr_settings_fields():
    """
    Adds:
    1. Max Allowed Attendance Correction per Fiscal Year
    2. Allowed Lates
    """

    # 1️⃣ Max Allowed Attendance Correction
    if frappe.db.exists(
        "Custom Field",
        {
            "dt": "HR Settings",
            "fieldname": "max_attendance_corrections_per_fiscal_year",
        },
    ):
        field = frappe.get_doc(
            "Custom Field",
            {
                "dt": "HR Settings",
                "fieldname": "max_attendance_corrections_per_fiscal_year",
            },
        )

        field.label = "Max Allowed Attendance Correction per Fiscal Year"
        field.fieldtype = "Int"
        field.insert_after = "retirement_age"
        field.default = "6"
        field.description = (
            "Maximum number of attendance corrections allowed per fiscal year"
        )

        # IMPORTANT FIX
        field.flags.ignore_version = True

        field.save(ignore_permissions=True)

    else:
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": "HR Settings",
                "label": "Max Allowed Attendance Correction per Fiscal Year",
                "fieldname": "max_attendance_corrections_per_fiscal_year",
                "fieldtype": "Int",
                "insert_after": "retirement_age",
                "default": "6",
                "description": "Maximum number of attendance corrections allowed per fiscal year",
            }
        ).insert(ignore_permissions=True)

    # 2️⃣ Allowed Lates
    if frappe.db.exists(
        "Custom Field", {"dt": "HR Settings", "fieldname": "allowed_lates"}
    ):
        field = frappe.get_doc(
            "Custom Field",
            {"dt": "HR Settings", "fieldname": "allowed_lates"},
        )

        field.label = "Allowed Lates"
        field.fieldtype = "Int"
        field.insert_after = "max_attendance_corrections_per_fiscal_year"
        field.default = "3"
        field.description = "Number of late entries allowed without penalty"

        # IMPORTANT FIX
        field.flags.ignore_version = True

        field.save(ignore_permissions=True)

    else:
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": "HR Settings",
                "label": "Allowed Lates",
                "fieldname": "allowed_lates",
                "fieldtype": "Int",
                "insert_after": "max_attendance_corrections_per_fiscal_year",
                "default": "3",
                "description": "Number of late entries allowed without penalty",
            }
        ).insert(ignore_permissions=True)

    frappe.clear_cache()

def add_paid_leaves_field():
    """
    Adds:
    1. Max Allowed Attendance Correction per Fiscal Year
    2. Allowed Lates
    """

    # 1️⃣ Max Allowed Attendance Correction
    if frappe.db.exists(
        "Custom Field",
        {
            "dt": "Salary Structure Assignment",
            "fieldname": "paid_leaves",
        },
    ):
        field = frappe.get_doc(
            "Custom Field",
            {
                "dt": "Salary Structure Assignment",
                "fieldname": "paid_leaves",
            },
        )

        field.label = "Paid Leaves"
        field.fieldtype = "Duration"
        field.insert_after = "base"
        field.default = ""
        field.allow_on_submit = 1
        field.description = (
            "Number of paid leaves allocated to the employee per year"
        )

        # IMPORTANT FIX
        field.flags.ignore_version = True

        field.save(ignore_permissions=True)

    else:
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": "Salary Structure Assignment",
                "label": "Paid Leaves",
                "fieldname": "paid_leaves",
                "fieldtype": "Duration",
                "insert_after": "base",
                "default": "",
                "allow_on_submit": 1,
                "description": "Number of paid leaves allocated to the employee per year",
            }
        ).insert(ignore_permissions=True)

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
    add_paid_leaves_field()

    frappe.logger().info("✅ Salary Breakup + HR Settings fields added successfully.")
