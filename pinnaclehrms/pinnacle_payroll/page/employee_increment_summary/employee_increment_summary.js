frappe.pages["employee-increment-summary"].on_page_load = function (wrapper) {
  let page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Employee Increment Summary",
    single_column: true,
  });

  let filters = {};

  frappe.dom.set_style(`
		.employee-increment-page {
			padding: 10px;
		}

		.filters-section {
			position: sticky;
			top: 0;
			z-index: 1000;
			background: #fff;
			padding: 10px 0;
			margin-bottom: 15px;
		}

		.increment-table-wrapper {
			overflow: auto;
			max-height: calc(100vh - 180px);
			border: 1px solid #d1d8dd;
			border-radius: 8px;
		}

		.increment-table table {
			min-width: 1400px;
			margin-bottom: 0;
		}

		.increment-table thead th {
			position: sticky;
			top: 0;
			z-index: 50;
			background: #f8f9fa;
			white-space: nowrap;
		}

		.sticky-col-1 {
			position: sticky;
			left: 0;
			z-index: 60;
			background: white !important;
			min-width: 50px;
			max-width: 50px;
		}

		.sticky-col-2 {
			position: sticky;
			left: 50px;
			z-index: 60;
			background: white !important;
			min-width: 180px;
		}

		.sticky-col-3 {
			position: sticky;
			left: 230px;
			z-index: 60;
			background: white !important;
			min-width: 240px;
		}

		.main-row:hover td {
			background: #f5f7fa !important;
		}

		.overdue-row td {
			background: #fff5f5 !important;
		}

		.history-wrapper {
			padding: 10px;
			background: #fafafa;
		}

		.history-table th {
			background: #f1f3f5;
		}

		.summary-cards {
			display: flex;
			gap: 12px;
			margin-bottom: 15px;
			flex-wrap: wrap;
		}

		.summary-card {
			flex: 1;
			min-width: 180px;
			padding: 15px;
			border-radius: 8px;
			background: #f8f9fa;
			border: 1px solid #d1d8dd;
		}

		.summary-card .count {
			font-size: 24px;
			font-weight: bold;
			margin-top: 5px;
		}
	`);

  let body = $(`
		<div class="employee-increment-page">

			<div class="filters-section row">

				<div class="col-md-3">
					<select class="form-control company">
						<option value="">Select Company</option>
					</select>
				</div>

				<div class="col-md-3">
					<input type="text"
						class="form-control employee"
						placeholder="Employee">
				</div>

				<div class="col-md-3">
					<select class="form-control status">
						<option value="">All Status</option>
						<option value="Eligible">Eligible</option>
						<option value="Upcoming">Upcoming</option>
						<option value="Overdue">Overdue</option>
						<option value="Active">Active</option>
					</select>
				</div>

				<div class="col-md-3 text-right">

					<button class="btn btn-primary get-records">
						Get Records
					</button>

					<button class="btn btn-success download-report">
						Download
					</button>

				</div>

			</div>

			<div class="summary-cards"></div>

			<div class="increment-table-wrapper">
				<div class="increment-table"></div>
			</div>

		</div>
	`);

  $(wrapper).find(".layout-main-section").append(body);

  load_companies();

  body.find(".get-records").on("click", function () {
    get_records();
  });

  body.find(".download-report").on("click", function () {
    frappe.msgprint({
      title: __("Coming Soon"),
      message: __("Download functionality will be added soon."),
      indicator: "blue",
    });
  });

  function load_companies() {
    frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "Company",
        fields: ["name"],
        limit_page_length: 500,
      },
      callback: function (r) {
        let options = `<option value="">Select Company</option>`;

        (r.message || []).forEach((company) => {
          options += `
						<option value="${company.name}">
							${company.name}
						</option>
					`;
        });

        body.find(".company").html(options);
      },
    });
  }

  function get_records() {
    filters = {
      company: body.find(".company").val(),
      employee: body.find(".employee").val(),
      status: body.find(".status").val(),
    };

    frappe.call({
      method:
        "pinnaclehrms.pinnacle_payroll.page.employee_increment_summary.employee_increment_summary.get_data",
      args: {
        filters: filters,
      },
      freeze: true,
      callback: function (r) {
        let data = r.message || [];

        render_summary_cards(data);

        render_table(data);
      },
    });
  }

  function render_summary_cards(data) {
    let total = data.length;

    let eligible = data.filter((d) => d.status === "Eligible").length;

    let upcoming = data.filter((d) => d.status === "Upcoming").length;

    let overdue = data.filter((d) => d.status === "Overdue").length;

    let html = `
			<div class="summary-card">
				<div>Total Employees</div>
				<div class="count">${total}</div>
			</div>

			<div class="summary-card">
				<div>Eligible</div>
				<div class="count text-success">${eligible}</div>
			</div>

			<div class="summary-card">
				<div>Upcoming</div>
				<div class="count text-warning">${upcoming}</div>
			</div>

			<div class="summary-card">
				<div>Overdue</div>
				<div class="count text-danger">${overdue}</div>
			</div>
		`;

    body.find(".summary-cards").html(html);
  }

  function render_table(data) {
    let html = `
			<table class="table table-bordered">

				<thead>
					<tr>
						<th class="sticky-col-1" style="width:50px;"></th>
						<th class="sticky-col-2">Employee</th>
						<th class="sticky-col-3">Name</th>
						<th>Department</th>
						<th>Current Salary</th>
						<th>Last Increment</th>
						<th>Next Increment</th>
						<th>Status</th>
						<th>Action</th>
					</tr>
				</thead>

				<tbody>
		`;

    data.forEach((row, index) => {
      let badge_class =
        {
          Eligible: "badge-success",
          Upcoming: "badge-warning",
          Overdue: "badge-danger",
          Active: "badge-secondary",
        }[row.status] || "badge-secondary";

      let action_btn = "";

      if (row.status === "Eligible" || row.status === "Overdue") {
        action_btn = `
					<button
						class="btn btn-sm btn-primary assign-increment"
						data-employee="${row.employee}">
						Assign Increment
					</button>
				`;
      }

      html += `
				<tr class="
					main-row
					${row.status === "Overdue" ? "overdue-row" : ""}
				">

					<td class="sticky-col-1">
						<button
							class="btn btn-xs btn-default toggle-row">
							▶
						</button>
					</td>

					<td class="sticky-col-2">
						${row.employee}
					</td>

					<td class="sticky-col-3">
						${row.employee_name}
					</td>

					<td>${row.department || ""}</td>

					<td>
						${format_currency(row.current_salary)}
					</td>

					<td>
						${row.last_increment || ""}
					</td>

					<td>
						${row.next_increment || ""}
					</td>

					<td>
						<span class="badge ${badge_class}">
							${row.status}
						</span>
					</td>

					<td>
						${action_btn}
					</td>

				</tr>
			`;

      html += `
				<tr class="history-row" style="display:none;">

					<td colspan="9">

						<div class="history-wrapper">

							<table class="
								table
								table-bordered
								table-sm
								history-table
							">

								<thead>
									<tr>
										<th>Effective Date</th>
										<th>Salary Structure</th>
										<th>Previous Salary</th>
										<th>Current Salary</th>
										<th>Increment</th>
									</tr>
								</thead>

								<tbody>
			`;

      (row.history || []).forEach((history) => {
        html += `
					<tr>

						<td>${history.from_date}</td>

						<td>${history.salary_structure}</td>

						<td>
							${format_currency(history.previous_salary || 0)}
						</td>

						<td>
							${format_currency(history.current_salary || 0)}
						</td>

						<td>
							${format_currency(history.increment || 0)}
						</td>

					</tr>
				`;
      });

      html += `
								</tbody>

							</table>

						</div>

					</td>

				</tr>
			`;
    });

    html += `
				</tbody>
			</table>
		`;

    body.find(".increment-table").html(html);

    body.find(".toggle-row").on("click", function () {
      let row = $(this).closest("tr");

      let history_row = row.next(".history-row");

      history_row.toggle();

      $(this).text(history_row.is(":visible") ? "▼" : "▶");
    });

    body.find(".assign-increment").on("click", function () {
      let employee = $(this).attr("data-employee");

      let row = data.find((d) => d.employee === employee);

      if (!row) {
        frappe.msgprint(__("Employee data not found"));
        return;
      }

      frappe.new_doc("Salary Structure Assignment", {
        employee: row.employee,

        company: row.company,

        salary_structure: row.salary_structure,

        from_date: frappe.datetime.add_days(row.next_increment, 1),

        base: row.current_salary,
      });
    });
  }

  get_records();
};
