import frappe
from pinnaclehrms.pinnacle_hr.setup import (
    add_custom_attendance_statuses,
    remove_custom_attendance_statuses,
    add_salary_breakup_field_to_salary_slip,
)


def after_install():
    """
    Runs automatically before app installation.
    Sets up:
    - Custom attendance statuses
    - Salary Breakup section + child table field on Salary Slip
    """
    frappe.logger().info("Running before_install for Pinnacle HRMS...")

    # 1. Add custom attendance statuses
    add_custom_attendance_statuses()

    # 2. Add Salary Breakup field + section in Salary Slip
    add_salary_breakup_field_to_salary_slip()

    frappe.logger().info("Pinnacle HRMS before_install completed successfully.")


def before_uninstall():
    """
    Runs before the app is uninstalled.
    Safely removes only:
    - Custom attendance statuses

    NOTE:
    We do NOT remove Custom Fields or Child Doctypes automatically.
    """
    frappe.logger().info("Running before_uninstall for Pinnacle HRMS...")

    remove_custom_attendance_statuses()

    frappe.logger().info("Pinnacle HRMS before_uninstall completed.")
