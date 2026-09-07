import frappe

from frappe.utils import cint


def backup_employee_checkins(
    employees=None,
    from_time=None,
    to_time=None,
):
    """
    Backup existing Employee Checkin records
    into Backup Checkin Logs.
    """

    filters = {}

    if employees:
        filters["employee"] = [
            "in",
            employees,
        ]

    if from_time and to_time:

        filters["time"] = [
            "between",
            [
                from_time,
                f"{to_time} 23:59:59",
            ],
        ]

    checkins = frappe.get_all(
        "Employee Checkin",
        filters=filters,
        fields=[
            "employee",
            "employee_name",
            "log_type",
            "shift",
            "time",
            "device_id",
            "skip_auto_attendance",
            "attendance",
            "shift_start",
            "shift_end",
            "shift_actual_start",
            "shift_actual_end",
            "geolocation",
            "latitude",
            "longitude",
            "offshift",
            "overtime_type",
        ],
    )

    inserted = 0
    skipped = 0

    for row in checkins:

        try:

            doc = frappe.new_doc("Backup Checkin Logs")

            doc.employee = row.employee
            doc.employee_name = row.employee_name
            doc.log_type = row.log_type
            doc.shift = row.shift
            doc.time = row.time
            doc.device_id = row.device_id

            doc.skip_auto_attendance = cint(row.skip_auto_attendance)

            doc.attendance = row.attendance

            doc.shift_start = row.shift_start
            doc.shift_end = row.shift_end

            doc.shift_actual_start = row.shift_actual_start

            doc.shift_actual_end = row.shift_actual_end

            doc.geolocation = row.geolocation
            doc.latitude = row.latitude
            doc.longitude = row.longitude

            doc.offshift = cint(row.offshift)

            doc.overtime_type = row.overtime_type

            doc.insert(ignore_permissions=True)

            inserted += 1

        except (
            frappe.DuplicateEntryError,
            frappe.UniqueValidationError,
        ):

            skipped += 1

    frappe.db.commit()

    return {
        "inserted": inserted,
        "skipped": skipped,
        "total": len(checkins),
    }


def restore_backup_checkins(
    employees=None,
    from_time=None,
    to_time=None,
):
    """
    Reserved for future restoration functionality.

    This can later be used to restore records from
    Backup Checkin Logs back into Employee Checkin.
    """

    # Intentionally not implemented here.
    # We should implement this only after defining the
    # exact restoration rules.
    return {
        "restored": 0,
        "skipped": 0,
    }
