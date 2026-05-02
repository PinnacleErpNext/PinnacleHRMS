import frappe
from datetime import timedelta
from frappe.utils import get_datetime


def before_save_set_particulars(doc, method=None):  
    #----- Step 1: If no in_time or out_time, particulars = Absent -----
    if not doc.in_time or not doc.out_time:
        doc.particulars = "Absent"
        return

    #----- Step 2: Fetch shift timings from Shift Master -----
    if not doc.shift:
        # No shift -> cannot calculate slabs -> default Full Day
        doc.particulars = "Full Day"
        return

    shift_doc = frappe.get_doc("Shift Type", doc.shift)

    # These are the correct fields used by ERPNext shift type
    shift_start = shift_doc.start_time
    shift_end = shift_doc.end_time

    if not shift_start or not shift_end:
        doc.particulars = "Full Day"
        return

    # Convert shift timings into date + time (combine with attendance date)
    shift_start = frappe.utils.get_datetime(f"{doc.attendance_date} {shift_start}")
    shift_end   = frappe.utils.get_datetime(f"{doc.attendance_date} {shift_end}")

    # Handle overnight shift
    if shift_end < shift_start:
        shift_end += timedelta(days=1)

    #----- Step 3: Calculate ideal working duration -----
    ideal_working_time = shift_end - shift_start
    total_minutes = ideal_working_time.total_seconds() / 60 or 1

    #----- Step 4: Slab definitions -----
    slabs = {
        "check_in": [
            (shift_start,
             shift_start + timedelta(minutes=round(total_minutes * 0.112)), 0.10),

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

    deduction = 0.0

    #----- Step 5: Check-In Slab -----
    for start, end, rate in slabs["check_in"]:
        if start < get_datetime(doc.in_time) <= end:
            deduction += rate
            break

    #----- Step 6: Check-Out Slab -----
    for start, end, rate in slabs["check_out"]:
        if start <= get_datetime(doc.out_time) < end:
            deduction += rate
            break

    deduction = min(deduction, 1.0)

    #----- Step 7: Set particulars -----
    doc.particulars = map_deduction_to_status(deduction)


def map_deduction_to_status(d):
    if d == 0:
        return "Full Day"
    if d <= 0.10:
        return "Late/Early"
    if d <= 0.20:
        return "Late & Early"
    if d <= 0.25:
        return "3/4 Day"
    if d <= 0.50:
        return "Half Day"
    if d <= 0.75:
        return "Quarter Day"
    return "Absent"
