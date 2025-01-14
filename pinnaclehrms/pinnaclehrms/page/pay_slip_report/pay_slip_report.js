frappe.pages["pay-slip-report"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Pay Slip Report",
		single_column: true,
	});

	const currentYear = new Date().getFullYear();

	const $form = $(`
    <div class="row">
        <!-- Year Field -->
        <div class="col-md-3 form-group">
            <label for="year">Year</label>
            <input type="number" id="year" class="form-control" placeholder="Enter year" min="1000" max="9999" value="${currentYear}">
        </div>

        <!-- Month Field -->
        <div class="col-md-3 form-group">
            <label for="month">Month</label>
            <select id="month" class="form-control">
                <option value="">Select month</option>
                ${[...Array(12)]
					.map(
						(_, i) =>
							`<option value="${i + 1}">${new Date(0, i).toLocaleString("default", {
								month: "long",
							})}</option>`
					)
					.join("")}
            </select>
        </div>

        <!-- Button to Fetch Records -->
        <div class="col-md-3 form-group d-flex align-items-end">
            <button id="fetch_records" class="btn btn-primary">Get Records</button>
        </div>

        <!-- Actions Button (Initially Hidden) -->
        <div class="col-md-3 form-group d-flex align-items-end">
            <div id="action_button" class="btn-group" style="display: none;">
                <button class="btn btn-primary dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                    Actions
                </button>
                <ul class="dropdown-menu">
                    <li><a class="dropdown-item" id="email_pay_slips">Email Pay Slips</a></li>
                    <li><a class="dropdown-item" id="print_pay_slips">Print Pay Slips</a></li>
                </ul>
            </div>
        </div>
    </div>
    <div id="pay_slip_table"></div>
  `).appendTo(page.body);
	// Fetch records on button click
	$form.find("#fetch_records").click(function () {
		const year = $form.find("#year").val();
		if (year < 1000 || year > 9999) {
			frappe.throw("Invalid Year!");
			return;
		}
		const actionButton = document.getElementById("action_button");
		actionButton.style.display = "none";

		const month = $form.find("#month").val();
		if (year && month) {
			const currUser = frappe.session.user_email;
			frappe.call({
				method: "pinnaclehrms.api.get_pay_slip_report",
				args: {
					year: year,
					month: month,
					curr_user: currUser,
				},
				callback: function (res) {
					if (res.message && res.message.length) {
						pay_slip_list(res.message);
						$form.find("#fetch_records").hide();
					} else {
						document.getElementById("pay_slip_table").innerHTML = "";
						frappe.msgprint("No records found.");
						$form.find("#fetch_records").show();
					}
				},
			});
		} else {
			frappe.msgprint((msg = "Please select both year and month"), (title = "Warning"));
		}
	});

	// Detect change in the month dropdown
	$form.find("#month").on("change", function () {
		$form.find("#fetch_records").show();
	});
};

function pay_slip_list(records) {
	let table = `
                <div style="overflow-x: auto; max-width: 100%;">
                <table class="table table-bordered scrollable-table">
                    <thead>
                        <tr>
                            <th style="position: sticky; background: #888; color: black; left: 0px; z-index: 2;"><input type="checkbox" id="select_all" />Select All</th>
                            <th style="position: sticky; background: #888; color: black; left: 60px; z-index: 2;">Pay Slip</th>
                            <th style="position: sticky; background: #888; color: black; left: 160px; z-index: 2;">Employee Name</th>
                            <th style="position: sticky; background: #888; color: black; left: 245px; z-index: 2;">Email</th>
                            <th style="position: sticky; background: #888; color: black; left: 450px; z-index: 2;">Date Of Joining</th>
                            <th style="position: sticky; background: #888; color: black; left: 550px; z-index: 2;">Basic Salary</th>
                            <th>Standard Working Day</th>
                            <th>Actual Days Of Working</th>
                            <th>Full Day Working</th>
                            <th>Sunday Working</th>
                            <th>Half Day Working</th>
                            <th>3/4 Day Working</th>
                            <th>Quarter Day Working</th>
                            <th>Late Coming Penalty -1 Hour</th>
                            <th>Leaves</th>
                            <th>Total Monthly Salary</th>
                            <th>Sunday Workings</th>
                            <th>Total Other Earnings</th>
                            <th>Other Adjustments - Less</th>
                            <th>Takeaway Salary</th>
                        </tr>
                    </thead>
                    <tbody>
  `;

	records.forEach((record) => {
		table += `<tr>
                    <td style="position: sticky; background: #888; color: black; left: 0px; z-index: 2;"><input type="checkbox" class="row_checkbox" value="${record.name}" /></td>
                    <td style="position: sticky; background: #888; color: black; left: 60px; z-index: 2;"><a href="/app/pay-slips/${record.name}" target="blank" style="color: black;">${record.name}</a></td>
                    <td style="position: sticky; background: #888; color: black; left: 160px; z-index: 2;">${record.employee_name}</td>
                    <td style="position: sticky; background: #888; color: black; left: 245px; z-index: 2;">${record.personal_email}</td>
                    <td style="position: sticky; background: #888; color: black; left: 450px; z-index: 2;">${record.date_of_joining}</td>
                    <td style="position: sticky; background: #888; color: black; left: 550px; z-index: 2;">${record.basic_salary}</td>
                    <td>${record.standard_working_days}</td>
                    <td>${record.actual_working_days}</td>
                    <td>${record.full_day_working_days}</td>
                    <td>${record.sundays_working_days}</td>
                    <td>${record.half_day_working_days}</td>
                    <td>${record.three_four_quarter_days_working_days}</td>
                    <td>${record.quarter_day_working_days}</td>
                    <td>${record.lates_days}</td>
                    <td>${record.absent}</td>
                    <td>${record.total}</td>
                    <td>${record.sunday_working_amount}</td>
                    <td>${record.other_earnings_amount}</td>
                    <td>${record.adjustments}</td>
                    <td>${record.net_payble_amount}</td>
                    </tr>`;
	});

	table += `</tbody></table></div>`;
	document.getElementById("pay_slip_table").innerHTML = table;

	// Add "Select All" functionality
	const selectAllCheckbox = document.getElementById("select_all");
	selectAllCheckbox.addEventListener("change", function () {
		const isChecked = selectAllCheckbox.checked;
		document
			.querySelectorAll('.row_checkbox') // Row checkboxes
			.forEach((checkbox) => (checkbox.checked = isChecked));
		updateActionButtonVisibility(); // Update action button visibility
	});

	// Update action button visibility based on checkbox selection
	updateActionButtonVisibility();
	// Email Pay Slips Action
	document.getElementById("email_pay_slips").addEventListener("click", function () {
		const selectedRows = get_selected();
		if (selectedRows.length === 0) {
			frappe.msgprint("No Pay Slips selected to email.");
			return;
		}

		console.log(selectedRows)

		// Convert selected rows to JSON string
		const paySlips = JSON.stringify(selectedRows);

		// Call server-side method
		frappe.call({
			method: "pinnaclehrms.api.email_pay_slip",
			args: {
				pay_slips: paySlips,
			},
			callback: function (res) {
				if (res.message) {
					frappe.msgprint("Pay slips emailed successfully.");
				}
			},
			error: function (res) {
				frappe.msgprint("Failed to email pay slips: " + (res.message || "Unknown error."));
			},
		});
	});

	// Print Pay Slips Action
	document.getElementById("print_pay_slips").addEventListener("click", function () {
		const selectedRows = get_selected();
		if (!selectedRows.length) {
			frappe.msgprint("No Pay Slips selected to print.");
			return;
		}
		selectedRows.forEach((pay_slip) => {
			frappe.call({
				method: "pinnaclehrms.api.print_pay_slip",
				args: {
					pay_slips: JSON.stringify(selectedRows),
				},
				callback: function (r) {
					if (!r.exc) {
						console.log("PDF successfully downloaded for Pay Slip:", pay_slip);
					}
				},
				error: function (error) {
					console.error("AJAX request failed:", error);
					frappe.msgprint("Failed to download the pay slip PDF. Please check the logs.");
				},
			});
		});
	});
}
function updateActionButtonVisibility() {
	document.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
		checkbox.addEventListener("change", (event) => {
			const actionButton = document.getElementById("action_button");
			const anyChecked =
				document.querySelectorAll('input[type="checkbox"]:checked').length > 0;

			actionButton.style.display = anyChecked ? "inline-block" : "none";
		});
	});
}

function get_selected() {
	const selected = [];
	document.querySelectorAll('input[type="checkbox"]:checked').forEach((checkbox) => {
		selected.push(checkbox.value);
	});
	return selected;
}
