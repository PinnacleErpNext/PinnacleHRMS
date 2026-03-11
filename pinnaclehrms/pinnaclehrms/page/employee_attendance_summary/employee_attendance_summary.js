frappe.pages["Employee Attendance Summary"].on_page_load = function (wrapper) {
  let page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Employee Attendance Summary",
    single_column: true,
  });

  // Filters
  let company = page.add_field({
    label: "Company",
    fieldtype: "Link",
    options: "Company",
    fieldname: "company",
  });

  let employee = page.add_field({
    label: "Employee ID",
    fieldtype: "Link",
    options: "Employee",
    fieldname: "employee",
  });

  let from_date = page.add_field({
    label: "From Date",
    fieldtype: "Date",
    fieldname: "from_date",
  });

  let to_date = page.add_field({
    label: "To Date",
    fieldtype: "Date",
    fieldname: "to_date",
  });

  let get_btn = page.add_field({
    label: "Get Records",
    fieldtype: "Button",
    fieldname: "get_records",
  });

  let download_btn = page.add_field({
    label: "Download Report",
    fieldtype: "Button",
    fieldname: "download_report",
  });
	get_btn.$input.removeClass("btn-default").addClass("btn-dark");
	download_btn.$input.removeClass("btn-default").addClass("btn-success");

  let result_area = $('<div class="mt-4"></div>').appendTo(page.body);

  get_btn.$input.on("click", function () {
    if (!from_date.get_value() || !to_date.get_value()) {
      frappe.msgprint("Please select From Date and To Date");
      return;
    }

    frappe.call({
      method:
        "pinnaclehrms.pinnaclehrms.page.employee_attendance_summary.employee_attendance_summary.get_data",
      args: {
        company: company.get_value(),
        employee: employee.get_value(),
        from_date: from_date.get_value(),
        to_date: to_date.get_value(),
      },
      callback: function (r) {
        let table = `
        <table class="table table-bordered table-striped">
        <thead>
          <tr>
            <th></th>
            <th>Employee</th>
            <th>Name</th>
            <th>Full Day</th>
            <th>Lates</th>
            <th>3/4 Quarter Day</th>
            <th>Half Day</th>
            <th>Quarter Day</th>
            <th>Others Day</th>
            <th>Sunday Workings</th>
            <th>Gross Total</th>
            <th>Absents</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
        `;

        if (r.message && r.message.length) {
          r.message.forEach((d) => {
            table += `
            <tr class="emp-row" id="emp-${d.employee}">
              <td>
                <button class="btn btn-xs btn-default expand-row"
                  data-emp="${d.employee}">
                  ▶
                </button>
              </td>
              <td>${d.employee}</td>
              <td>${d.employee_name}</td>
              <td>${d.full_day || 0}</td>
              <td>${d.lates || 0}</td>
              <td>${d.three_quarter_day || 0}</td>
              <td>${d.half_day || 0}</td>
              <td>${d.quarter_day || 0}</td>
              <td>${d.others_day || 0}</td>
              <td>${d.sunday_workings || 0}</td>
              <td>${d.gross_total || 0}</td>
              <td>${d.absent || 0}</td>
              <td>${d.total || 0}</td>
            </tr>
            `;
          });
        } else {
          table += `
          <tr>
            <td colspan="13" style="text-align:center">
              No Data Found
            </td>
          </tr>
          `;
        }

        table += "</tbody></table>";

        result_area.html(table);

        attach_expand_events();
      },
    });
  });

  download_btn.$input.on("click", function () {

	if (!from_date.get_value() || !to_date.get_value()) {
		frappe.msgprint("Please select From Date and To Date");
		return;
	}

	frappe.call({
		method:
		"pinnaclehrms.pinnaclehrms.page.employee_attendance_summary.employee_attendance_summary.download_excel",

		args: {
			company: company.get_value(),
			employee: employee.get_value(),
			from_date: from_date.get_value(),
			to_date: to_date.get_value(),
		},

		callback: function (r) {

			if (r.message) {
				window.open(r.message);
			}

		}
	});

});

  function attach_expand_events() {
    $(".expand-row").click(function () {
      let btn = $(this);
      let emp = btn.data("emp");
      let emp_row = $("#emp-" + emp);

      if (btn.hasClass("open")) {
        $(".month-row-" + emp).remove();
        btn.removeClass("open");
        btn.text("▶");
        return;
      }

      btn.addClass("open");
      btn.text("▼");

      frappe.call({
        method:
          "pinnaclehrms.pinnaclehrms.page.employee_attendance_summary.employee_attendance_summary.get_employee_month_breakdown",
        args: {
          employee: emp,
          company: company.get_value(),
          from_date: from_date.get_value(),
          to_date: to_date.get_value(),
        },
        callback: function (res) {
          let rows = "";

          if (res.message && res.message.length) {
            res.message.forEach((m) => {
              rows += `
              <tr class="month-row-${emp}" style="background:#fafafa">
                <td style="padding-left:25px;font-weight:500">
                  ↳ ${m.month} ${m.year}
                </td>
                <td></td>
                <td></td>
                <td>${m.full_day || 0}</td>
                <td>${m.lates || 0}</td>
                <td>${m.three_quarter_day || 0}</td>
                <td>${m.half_day || 0}</td>
                <td>${m.quarter_day || 0}</td>
                <td>${m.others_day || 0}</td>
                <td>${m.sunday_workings || 0}</td>
                <td>${m.gross_total || 0}</td>
                <td>${m.absents || 0}</td>
                <td>${m.total || 0}</td>
              </tr>
              `;
            });
          } else {
            rows += `
            <tr class="month-row-${emp}">
              <td colspan="13" style="text-align:center">
                No Data
              </td>
            </tr>
            `;
          }

          emp_row.after(rows);
        },
      });
    });
  }
};
