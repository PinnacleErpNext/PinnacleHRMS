import frappe
from frappe import _
from datetime import datetime, timedelta
from itertools import groupby
from frappe.utils import cint, create_batch

# HRMS imports
from hrms.hr.doctype.shift_type.shift_type import ShiftType
from hrms.hr.doctype.employee_checkin.employee_checkin import (
    calculate_working_hours,
    skip_attendance_in_checkins,
    update_attendance_in_checkins,
    get_existing_half_day_attendance,
    handle_attendance_exception,
)
from hrms.hr.doctype.shift_assignment.shift_assignment import (
    get_employee_shift,
    get_shift_details,
)
from hrms.hr.doctype.attendance.attendance import Attendance


EMPLOYEE_CHUNK_SIZE = 50


# --------------------------------------------------
# Time Slab Helpers
# --------------------------------------------------

def create_time_slabs(shift_start, shift_end):
    ideal_working_time = shift_end - shift_start
    total_minutes = ideal_working_time.total_seconds() / 60 or 1

    return {
        "check_in": [
            (shift_start, shift_start + timedelta(minutes=round(total_minutes * 0.112)), 0.10),
            (shift_start + timedelta(minutes=round(total_minutes * 0.112)),
             shift_start + timedelta(minutes=round(total_minutes * 0.334)), 0.25),
            (shift_start + timedelta(minutes=round(total_minutes * 0.334)),
             shift_start + timedelta(minutes=round(total_minutes * 0.667)), 0.50),
            (shift_start + timedelta(minutes=round(total_minutes * 0.667)),
             shift_start + timedelta(minutes=round(total_minutes)), 0.75),
        ],
        "check_out": [
            (shift_end - timedelta(minutes=round(total_minutes)),
             shift_end - timedelta(minutes=round(total_minutes * 0.664)), 0.75),
            (shift_end - timedelta(minutes=round(total_minutes * 0.664)),
             shift_end - timedelta(minutes=round(total_minutes * 0.331)), 0.50),
            (shift_end - timedelta(minutes=round(total_minutes * 0.331)),
             shift_end - timedelta(minutes=round(total_minutes * 0.109)), 0.25),
            (shift_end - timedelta(minutes=round(total_minutes * 0.109)),
             shift_end, 0.10),
        ],
    }


def calculate_deduction(check_in, check_out, slabs):
    deduction = 0.0

    for start, end, rate in slabs["check_in"]:
        if start < check_in <= end:
            deduction += rate
            break

    for start, end, rate in slabs["check_out"]:
        if start <= check_out < end:
            deduction += rate
            break

    return min(deduction, 1.0)


def map_deduction_to_status(deduction):
    if deduction == 0:
        return "Full Day"
    if deduction <= 0.10:
        return "Late/Early"
    if deduction <= 0.20:
        return "Late & Early"
    if deduction <= 0.25:
        return "3/4 Day"
    if deduction <= 0.50:
        return "Half Day"
    if deduction <= 0.75:
        return "Quarter Day"
    return "Absent"


# --------------------------------------------------
# Custom get_attendance
# --------------------------------------------------

def custom_get_attendance(self, logs):
    late_entry = early_exit = False

    total_working_hours, in_time, out_time = calculate_working_hours(
        logs,
        self.determine_check_in_and_check_out,
        self.working_hours_calculation_based_on,
    )

    # ERPNext default status logic
    if (
        getattr(self, "working_hours_threshold_for_absent", None)
        and total_working_hours < self.working_hours_threshold_for_absent
    ):
        erp_status = "Absent"

    elif (
        getattr(self, "working_hours_threshold_for_half_day", None)
        and total_working_hours < self.working_hours_threshold_for_half_day
    ):
        erp_status = "Half Day"

    else:
        erp_status = "Present"

    # CASE 1 → status is Absent → particulars must ALWAYS be Absent
    if erp_status == "Absent":
        particulars = "Absent"
        return (
            erp_status,
            total_working_hours,
            late_entry,
            early_exit,
            in_time,
            out_time,
            particulars,
        )

    # CASE 2 → present or half-day → use slab-based particulars
    if in_time and out_time:
        shift_start = logs[0].shift_start
        shift_end = logs[0].shift_end
        slabs = create_time_slabs(shift_start, shift_end)
        deduction = calculate_deduction(in_time, out_time, slabs)
        particulars = map_deduction_to_status(deduction)
    else:
        particulars = "Absent"

    return (
        erp_status,
        total_working_hours,
        late_entry,
        early_exit,
        in_time,
        out_time,
        particulars,
    )


# --------------------------------------------------
# Custom mark_attendance_and_link_log
# --------------------------------------------------

def custom_mark_attendance_and_link_log(
    logs,
    attendance_status,
    attendance_date,
    working_hours=None,
    late_entry=False,
    early_exit=False,
    in_time=None,
    out_time=None,
    shift=None,
    particulars=None,
):
    log_names = [x.name for x in logs]
    employee = logs[0].employee

    # normalize particulars → Absent if blank
    particulars = particulars if particulars not in [None, "", False] else attendance_status

    try:
        frappe.db.savepoint("attendance_creation")

        existing = get_existing_half_day_attendance(employee, attendance_date)

        if existing:
            frappe.db.set_value(
                "Attendance",
                existing.name,
                {
                    "working_hours": working_hours,
                    "shift": shift,
                    "late_entry": late_entry,
                    "early_exit": early_exit,
                    "in_time": in_time,
                    "out_time": out_time,
                    "half_day_status": ("Absent" if attendance_status == "Absent" else "Present"),
                    "modify_half_day_status": 0,
                    "particulars": particulars,
                },
            )
            attendance = frappe.get_doc("Attendance", existing.name)

        else:
            attendance = frappe.new_doc("Attendance")
            attendance.update(
                {
                    "employee": employee,
                    "attendance_date": attendance_date,
                    "status": attendance_status,
                    "particulars": particulars,
                    "working_hours": working_hours,
                    "shift": shift,
                    "late_entry": late_entry,
                    "early_exit": early_exit,
                    "in_time": in_time,
                    "out_time": out_time,
                    "half_day_status": ("Absent" if attendance_status == "Half Day" else None),
                }
            )
            attendance.insert()
            attendance.submit()

        update_attendance_in_checkins(log_names, attendance.name)
        return attendance

    except frappe.ValidationError as e:
        handle_attendance_exception(log_names, e)
        return None


# --------------------------------------------------
# Custom process_auto_attendance
# --------------------------------------------------

@frappe.whitelist()
def custom_process_auto_attendance(self):

    if (
        not cint(getattr(self, "enable_auto_attendance", 0))
        or not getattr(self, "process_attendance_after", None)
        or not getattr(self, "last_sync_of_checkin", None)
    ):
        frappe.logger().info("Auto attendance disabled; skipping.")
        return

    frappe.logger().info("🔍 custom_process_auto_attendance executed")

    logs = self.get_employee_checkins()
    group_key = lambda x: (x["employee"], x["shift_start"])

    for key, group in groupby(sorted(logs, key=group_key), key=group_key):
        logs_group = list(group)
        attendance_date = key[1].date()
        employee = key[0]

        try:
            if not self.should_mark_attendance(employee, attendance_date):
                continue
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"should_mark_attendance error for {employee}",
            )

        try:
            result = self.get_attendance(logs_group)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"get_attendance error for {employee} on {attendance_date}",
            )
            continue

        if not result:
            continue

        if len(result) == 6:
            attendance_status, working_hours, late_entry, early_exit, in_time, out_time = result
            particulars = None
        else:
            attendance_status, working_hours, late_entry, early_exit, in_time, out_time, particulars = result

        try:
            custom_mark_attendance_and_link_log(
                logs_group,
                attendance_status,
                attendance_date,
                working_hours,
                late_entry,
                early_exit,
                in_time,
                out_time,
                self.name,
                particulars,
            )
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"mark_attendance error for {employee} on {attendance_date}",
            )

    frappe.db.commit()

    # Final post-processing: mark absent etc.
    try:
        assigned_employees = self.get_assigned_employees(self.process_attendance_after, True)
        for batch in create_batch(assigned_employees, EMPLOYEE_CHUNK_SIZE):
            for employee in batch:
                try:
                    self.mark_absent_for_dates_with_no_attendance(employee)
                    self.mark_absent_for_half_day_dates(employee)
                except Exception:
                    frappe.log_error(
                        frappe.get_traceback(),
                        f"mark_absent error for {employee}",
                    )
            frappe.db.commit()
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "post-processing (mark absent) failure in custom_process_auto_attendance",
        )


# --------------------------------------------------
# Apply Monkey Patches
# --------------------------------------------------

ShiftType.get_attendance = custom_get_attendance
ShiftType.process_auto_attendance = custom_process_auto_attendance
ShiftType.mark_attendance_and_link_log = custom_mark_attendance_and_link_log

frappe.logger().info("🔥 Custom attendance system activated (ERP status + custom particulars)")
