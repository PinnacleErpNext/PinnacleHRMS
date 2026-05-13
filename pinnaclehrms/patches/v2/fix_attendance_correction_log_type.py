import frappe


def execute():
    """
    Normalize Attendance Correction log_type values.

    In  -> IN
    Out -> OUT
    """

    updates = {
        "In": "IN",
        "Out": "OUT",
    }

    for old_value, new_value in updates.items():

        records = frappe.get_all(
            "Attendance Correction",
            filters={"log_type": old_value},
            pluck="name",
        )

        if not records:
            continue

        frappe.db.set_value(
            "Attendance Correction",
            {"name": ["in", records]},
            "log_type",
            new_value,
            update_modified=False,
        )

        print(
            f"Updated {len(records)} Attendance Correction records "
            f"from '{old_value}' to '{new_value}'"
        )

    frappe.db.commit()
