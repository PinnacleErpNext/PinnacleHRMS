// Copyright (c) 2024, OTPL and contributors
// For license information, please see license.txt
var preventSubmission;
frappe.ui.form.on("Create Pay Slips", {
	refresh(frm) {
		if (frm.doc.created_pay_slips) {
			employeeId = [""];
			paySlipList = frm.doc.created_pay_slips;
			paySlipList.forEach((paySlip) => {
				employeeId.push(paySlip.employee_id);
			});
		}
		add_email_btn(frm);
		if (frm.genrate_for_all) {
			frm.set_df_property("select_company", "hidden", 1);
			frm.set_df_property("company_abbr", "hidden", 1);
		}
		frm.select_company = frappe.defaults.get_user_default("company");
		let currentYear = new Date().getFullYear();
		if (!frm.doc.year) {
			frm.set_value("year", currentYear);
		}
		if (frm.doc.add_regenrate_button) {
			frm.add_custom_button("Regenerate Pay Slip", () => {
				let details = new frappe.ui.Dialog({
					title: "Enter details",
					fields: [
						{
							label: "Year",
							fieldname: "year",
							fieldtype: "Data",
							default: frm.doc.year,
							read_only: 1,
							reqd: true,
						},
						{
							label: "Month",
							fieldname: "month",
							fieldtype: "Data",
							default: frm.doc.select_month,
							read_only: 1,
							reqd: true,
						},
						{
							label: "Company",
							fieldname: "select_company",
							fieldtype: "Link",
							default: frm.doc.select_company,
							read_only: 1,
							options: "Company",
						},
						{
							label: "Employee",
							fieldname: "select_employee",
							fieldtype: "Select",
							default: frm.doc.select_employee,
							options: employeeId,
						},
						{
							label: "Allowed Lates",
							fieldname: "allowed_lates",
							fieldtype: "Int",
							default: 3,
							reqd: true,
						},
						{
							label: "Auto Calculate Leave Encashment",
							fieldname: "auto_calculate_leave_encashment",
							default: 0,
							fieldtype: "Check",
						},
					],
					primary_action_label: "Submit",
					primary_action(values) {
						const monthName =
							values.month.charAt(0).toUpperCase() +
							values.month.slice(1).toLowerCase();
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

						values.month = months[monthName];

						if (!values.month) {
							frappe.msgprint("Invalid month name.");
							return;
						}

						// Call the server-side method
						frappe.call({
							method: "pinnacle.api.regeneratePaySlip",
							args: { data: values },
							callback: function (res) {
								console.log(res.message.message);
								if (res.message.message === "Success") {
									frm.reload_doc();
								}
							},
						});

						details.hide(); // Hide the dialog after submission
					},
				});

				// Show the dialog
				details.show();
			});
		}
	},

	before_save(frm) {
		frm.set_value("add_regenrate_button", 1);
	},

	after_save(frm) {
		createPaySlipList(frm);
	},

	select_month(frm) {
		const monthName = frm.doc.select_month;
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

		frm.set_value("month", monthNum);

		const currentDate = new Date();
		const currentMonth = currentDate.getMonth() + 1;

		if (monthNum && currentMonth < monthNum) {
			frappe.validated = false;
			frappe.throw({
				message: "Pay Slips cannot be generated for future months!",
				title: "Warning",
				indicator: "orange",
			});
		}
	},

	validate: function (frm) {
		if (preventSubmission) {
			frappe.validate = false;
		}
	},

	genrate_for_all(frm) {
		frm.set_df_property("select_company", "hidden", frm.doc.genrate_for_all ? 1 : 0);
		frm.set_value("select_company", "");
		frm.set_df_property("company_abbr", "hidden", frm.doc.genrate_for_all ? 1 : 0);
		frm.set_value("company_abbr");
		frm.set_df_property("select_employee", "hidden", frm.doc.genrate_for_all ? 1 : 0);
		frm.set_value("select_employee", "");
		frm.set_df_property("select_employee", "disabled", frm.doc.genrate_for_all ? 1 : 0);
	},
});

function add_email_btn(frm) {
	frm.fields_dict["created_pay_slips"].grid.wrapper.find(".grid-add-row").hide();
	frm.fields_dict["created_pay_slips"].grid.wrapper.find(".grid-remove-rows").hide();
	frm.fields_dict["created_pay_slips"].grid.add_custom_button(
		"Email Pay Slips",
		function () {
			let selected_rows = frm.fields_dict["created_pay_slips"].grid.get_selected();

			if (selected_rows.length > 0) {
				frappe.call({
					method: "pinnacle.api.email_pay_slip",
					args: {
						raw_data: selected_rows,
					},
					callback: function (res) {
						frappe.msgprint("Pay slip emailed successfully!");
					},
					error: function (r) {
						frappe.msgprint(r.message);
					},
				});
			} else {
				frappe.msgprint("No row selected!");
			}
		},
		"Actions"
	);
}

function createPaySlipList(frm) {
	frappe.call({
		method: "pinnacle.api.get_pay_slip_list",
		args: {
			month: frm.doc.month,
			year: frm.doc.year,
			parent_docname: frm.docname,
			company: frm.doc.select_company,
			employee: frm.doc.select_employee,
		},
		callback: function (res) {
			frm.reload_doc();
		},
		error: function (r) {
			frappe.msgprint(r.message);
		},
	});
}
