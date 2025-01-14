// Copyright (c) 2024, OTPL and contributors
// For license information, please see license.txt

frappe.ui.form.on("Shift Variation", {
	refresh(frm) {},
	month(frm) {
		const monthName = frm.doc.month;

		const months = {
			January: 1,
			February: 2,
			March: 3,
			April: 4,
			May: 5,
			June: 6,
			July: 7,
			August: 8,
			September: 9,
			October: 10,
			November: 11,
			December: 12,
		};

		let monthNum = months[monthName];

		if (!monthNum) {
			frappe.msgprint("Invalid month name.");
			return;
		}

		frm.set_value("month_num", monthNum);
		console.log(frm.doc.month_num);
	},
});
