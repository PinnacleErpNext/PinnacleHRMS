# Copyright (c) 2025, Opticode Technologies Pvt. Ltd.
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, formatdate
from frappe.utils.background_jobs import enqueue
from pinnaclehrms.pinnacle_hr.constants import EMPLOYEE_CHUNK_SIZE


class ShiftVariation(Document):

    # -------------------------------------------------------------------------
    # FAILURE LOGGER (Writes to Doc + Error Log)
    # -------------------------------------------------------------------------
    def log_variation_error(self, title, error):
        safe_name = self.name or "(unsaved)"

        failure_html = f"""
		<b>{title}</b><br>
		<pre>{frappe.as_json(str(error), indent=2)}</pre>
		Shift Date: {self.shift_date}<br>
		Company: {self.company}<br>
		Department: {self.department}<br>
		Designation: {self.designation}
		"""

        # save failure details on document
        self.db_set("has_failure", 1, update_modified=False)
        self.db_set("failure_log", failure_html, update_modified=False)

        # write standard error log
        frappe.log_error(
            message=f"Shift Variation: {safe_name}\n{title}\n{str(error)}",
            title=title,
        )

    def clear_failures(self):
        if self.has_failure or self.failure_log:
            self.db_set("has_failure", 0, update_modified=False)
            self.db_set("failure_log", "", update_modified=False)

    # -------------------------------------------------------------------------
    # SUBMIT LOGIC
    # -------------------------------------------------------------------------
    def on_submit(self):
        if self.has_failure:
            frappe.throw(
                _(
                    "This Shift Variation has previously failed. Please review the Failure Details and clear the failure status before resubmitting."
                )
            )
        try:
            self.clear_failures()

            shift_type_name = self.create_special_shift_type()
            employees = self.get_employees_for_variation()

            if len(employees) > EMPLOYEE_CHUNK_SIZE:
                frappe.msgprint(
                    _(
                        "Large employee list detected ({0}). Processing in background."
                    ).format(len(employees)),
                    indicator="blue",
                )
                enqueue(
                    create_shift_requests_background,
                    queue="long",
                    timeout=600,
                    shift_variation_name=self.name,
                    shift_type_name=shift_type_name,
                )
            else:
                self.create_shift_requests(shift_type_name)

        except Exception as e:
            self.log_variation_error("On Submit Failure", e)
            frappe.throw(_("Shift Variation failed. Check Failure Details tab."))

    # -------------------------------------------------------------------------
    # CREATE SPECIAL SHIFT (FORCES NAMING TO AVOID autoname error)
    # -------------------------------------------------------------------------
    def create_special_shift_type(self) -> str:
        try:
            variation_shift_name = (
                f"{self.shift_name} - {formatdate(self.shift_date, 'dd-MM-yyyy')}"
            )
            variation_shift_name = f"{self.shift_name}"

            existing = frappe.db.exists("Shift Type", variation_shift_name)
            if existing:
                return variation_shift_name

            shift = frappe.new_doc("Shift Type")
            shift.name = variation_shift_name  # 👈 force name
            shift.shift_type_name = variation_shift_name
            shift.company = self.company
            shift.start_time = self.start_time
            shift.end_time = self.end_time
            shift.enable_auto_attendance = 1
            shift.is_night_shift = 0

            shift.insert(ignore_permissions=True, ignore_mandatory=True)
            return shift.name

        except Exception as e:
            self.log_variation_error("Shift Creation Failure", e)
            raise

    # -------------------------------------------------------------------------
    # EMPLOYEE FETCHING
    # -------------------------------------------------------------------------
    def get_employees_for_variation(self) -> list:
        try:
            employees = []
            if getattr(self, "shift_variation_for_employee", None):
                employees = [
                    d.employee for d in self.shift_variation_for_employee if d.employee
                ]

            if not employees:
                filters = {"company": self.company, "status": "Active"}

                if self.department:
                    filters["department"] = self.department
                if self.designation:
                    filters["designation"] = self.designation

                employees = frappe.get_all("Employee", filters=filters, pluck="name")

            return list(set(employees))

        except Exception as e:
            self.log_variation_error("Employee Fetch Failure", e)
            frappe.throw(_("Cannot fetch employees. Check Failure Details tab."))

    # -------------------------------------------------------------------------
    # DIRECT CREATION (SMALL SET)
    # -------------------------------------------------------------------------
    def create_shift_requests(self, shift_type_name):
        try:
            _create_shift_requests_core(self.name, shift_type_name)
        except Exception as e:
            self.log_variation_error("Shift Request Creation Failure", e)
            frappe.throw(_("Shift Requests failed. Check Failure Details tab."))


# -------------------------------------------------------------------------
# BACKGROUND JOB
# -------------------------------------------------------------------------
def create_shift_requests_background(shift_variation_name, shift_type_name):
    try:
        _create_shift_requests_core(
            shift_variation_name, shift_type_name, background=True
        )
    except Exception as e:
        frappe.log_error(
            f"Shift Variation Background Failure\n{str(e)}", "Shift Variation Error"
        )
        doc = frappe.get_doc("Shift Variation", shift_variation_name)
        doc.log_variation_error("Background Shift Request Failure", e)


# -------------------------------------------------------------------------
# CORE CREATION
# -------------------------------------------------------------------------
def _create_shift_requests_core(
    shift_variation_name, shift_type_name, background=False
):
    doc = frappe.get_doc("Shift Variation", shift_variation_name)
    employees = doc.get_employees_for_variation()
    shift_date = getdate(doc.shift_date)

    created, skipped = 0, 0

    for emp in employees:
        try:
            exists = frappe.db.exists(
                "Shift Request",
                {
                    "employee": emp,
                    "from_date": shift_date,
                    "to_date": shift_date,
                    "shift_type": shift_type_name,
                },
            )
            if exists:
                skipped += 1
                continue

            req = frappe.new_doc("Shift Request")
            req.employee = emp
            req.company = doc.company
            req.from_date = shift_date
            req.to_date = shift_date
            req.shift_type = shift_type_name
            req.status = "Approved"
            req.shift_request_type = "Assign"

            req.insert(ignore_permissions=True)
            try:
                req.submit()
            except:
                pass

            created += 1

        except Exception as inner_error:
            doc.log_variation_error(
                f"Shift Request Creation Failure for {emp}", inner_error
            )
            continue

    # Background vs UI result
    if not background:
        frappe.msgprint(
            _("{0} created, {1} skipped").format(created, skipped), indicator="green"
        )
    else:
        frappe.log_error(
            f"Background Shift Request Completed | Created: {created}, Skipped: {skipped}",
            "Shift Variation Background Log",
        )
