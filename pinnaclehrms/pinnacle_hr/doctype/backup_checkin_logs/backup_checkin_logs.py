import frappe
from frappe import _
from frappe.model.document import Document


class BackupCheckinLogs(Document):

    def before_insert(self):
        if self.employee and self.time and self.log_type:
            self.unique_key = (
                f"{self.employee}_"
                f"{self.time.strftime('%Y%m%d%H%M%S')}_"
                f"{self.log_type}"
            )


def restore_checkin(backup_checkin):
    """
    Restore a single Backup Checkin Logs record into Employee Checkin
    and delete the backup record after successful restoration.
    """

    if not backup_checkin:
        frappe.throw(_("Backup Checkin Log is required."))

    backup = frappe.get_doc(
        "Backup Checkin Logs",
        backup_checkin,
    )

    if not backup.employee:
        frappe.throw(_("Employee is required."))

    if not backup.time:
        frappe.throw(_("Time is required."))

    # Check whether the Employee Checkin already exists
    existing = frappe.db.exists(
        "Employee Checkin",
        {
            "employee": backup.employee,
            "time": backup.time,
            "log_type": backup.log_type,
        },
    )

    if existing:
        frappe.throw(
            _(
                "Employee Checkin already exists for employee {0} "
                "at {1}. Existing record: {2}"
            ).format(
                backup.employee,
                backup.time,
                existing,
            )
        )

    # Create Employee Checkin
    checkin = frappe.new_doc("Employee Checkin")

    checkin.employee = backup.employee
    checkin.time = backup.time
    checkin.log_type = backup.log_type

    # Copy optional fields
    optional_fields = [
        "employee_name",
        "shift",
        "shift_start",
        "shift_end",
        "shift_actual_start",
        "shift_actual_end",
        "device_id",
    ]

    for fieldname in optional_fields:
        if backup.meta.has_field(fieldname) and checkin.meta.has_field(fieldname):
            checkin.set(
                fieldname,
                backup.get(fieldname),
            )

    # First create Employee Checkin
    checkin.insert(ignore_permissions=True)

    # Delete backup ONLY after successful insertion
    frappe.delete_doc(
        "Backup Checkin Logs",
        backup.name,
        ignore_permissions=True,
    )

    return {
        "success": True,
        "name": checkin.name,
    }


@frappe.whitelist()
def restore_checkin_logs(backup_checkins):
    """
    Restore selected Backup Checkin Logs records.
    """

    if isinstance(backup_checkins, str):
        backup_checkins = frappe.parse_json(backup_checkins)

    if not backup_checkins:
        frappe.throw(_("Please select at least one Backup Checkin Log."))

    success_count = 0
    failed_count = 0

    restored = []
    failed = []

    for backup_checkin in backup_checkins:
        try:
            result = restore_checkin(backup_checkin)

            success_count += 1

            restored.append(
                {
                    "backup_checkin": backup_checkin,
                    "employee_checkin": result["name"],
                }
            )

        except Exception as e:
            failed_count += 1

            failed.append(
                {
                    "backup_checkin": backup_checkin,
                    "error": str(e),
                }
            )

    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "restored": restored,
        "failed": failed,
    }
