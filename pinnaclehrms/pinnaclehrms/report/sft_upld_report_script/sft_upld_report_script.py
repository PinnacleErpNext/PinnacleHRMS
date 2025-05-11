# Copyright (c) 2025
# License: MIT. See license.txt

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data()
    return columns, data


def get_columns():
    return [
        {
            "label": _("Debit Ac No"),
            "fieldname": "debit_ac_no",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Beneficiary Name"),
            "fieldname": "beneficiary_name",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Beneficiary Account No"),
            "fieldname": "beneficiary_account_no",
            "fieldtype": "Data",
            "width": 200,
        },
        {"label": _("IFSC"), "fieldname": "ifsc", "fieldtype": "Data", "width": 120},
        {
            "label": _("Amount (₹)"),
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": _("Pay Mode"),
            "fieldname": "pay_mode",
            "fieldtype": "Data",
            "width": 80,
        },
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Data", "width": 120},
    ]


def get_data():
    return frappe.db.sql(
        """
        SELECT 
            '192105002170' AS debit_ac_no,
            te.employee_name AS beneficiary_name,
            te.bank_ac_no AS beneficiary_account_no,
            te.ifsc_code AS ifsc,
            tps.net_payble_amount AS amount,
            'N' AS pay_mode,
            CONCAT(DATE_FORMAT(CURDATE(), '%%d-'), UPPER(DATE_FORMAT(CURDATE(), '%%b')), DATE_FORMAT(CURDATE(), '-%%Y')) AS date
        FROM `tabEmployee` AS te
        JOIN `tabPay Slips` AS tps ON tps.employee_id = te.name
    """,
        as_dict=1,
    )

def get_report_file_name(filters):
    # Custom logic to define filename
    custom_name = "My_Custom_Report_Name"
    return custom_name
