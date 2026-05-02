// Copyright (c) 2026, Opticode Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Correction", {
	refresh(frm) {
		frm.toggle_display(
			"corrected_attendance",
			frm.doc.docstatus === 1 && frm.doc.corrected_attendance_value
		);
	},

	attendance_date(frm) {
		if (!frm.doc.employee || !frm.doc.attendance_date) {
			return;
		}

		console.log("Attendance Date Changed");

		frappe.db.get_value(
			"Attendance",
			{
				employee: frm.doc.employee,
				attendance_date: frm.doc.attendance_date,
				docstatus: 1,
			},
			["name", "in_time", "out_time"],
			(r) => {
				if (r.in_time || r.out_time) {
					frm.set_value("actual_in_time", r.in_time);
					frm.set_value("actual_out_time", r.out_time);
				} else {
					frappe.msgprint(__("No Attendance record found for the selected date."));
					frm.set_value("actual_in_time", null);
					frm.set_value("actual_out_time", null);
				}
			}
		);
	},
	corrected_attendance(frm) {
		frappe.set_route("Form", "Attendance", frm.doc.corrected_attendance_value);
	},
});
