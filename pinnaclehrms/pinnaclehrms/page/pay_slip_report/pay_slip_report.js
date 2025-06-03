// File: public/js/pay_slip_report.js

frappe.pages["pay-slip-report"].on_page_load = function (wrapper) {
  // Create the page container
  var page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Pay Slip Report",
    single_column: true,
  });

  const currentYear = new Date().getFullYear();

  // Build the form & table skeleton
  const $form = $(`
    <div class="row">
      <div class="col-md-1 form-group">
        <label for="year">Year</label>
        <input type="number" id="year" class="form-control"
               min="1900" max="2099" value="${currentYear}">
      </div>
      <div class="col-md-2 form-group">
        <label for="month">Month</label>
        <select id="month" class="form-control">
          <option value="">Select month</option>
          ${[...Array(12)]
            .map(
              (_, i) =>
                `<option value="${i + 1}">${new Date(0, i).toLocaleString(
                  "default",
                  { month: "long" }
                )}</option>`
            )
            .join("")}
        </select>
      </div>
      <div class="col-md-3 form-group">
        <label for="company">Company</label>
        <select id="company_list" class="form-control">
          <option value="">Select Company</option>
        </select>
      </div>
      <div class="col-md-3 form-group d-flex align-items-end">
        <button id="fetch_records" class="btn btn-primary">Get Records</button>
      </div>
      <div class="col-md-3 form-group d-flex align-items-end">
        <div id="action_button" class="btn-group" style="display:none;">
          <button class="btn btn-primary dropdown-toggle" data-toggle="dropdown">
            Actions
          </button>
          <ul class="dropdown-menu">
            <li><a id="email_pay_slips" class="dropdown-item">Email Pay Slips</a></li>
            <li><a id="print_pay_slips" class="dropdown-item">Print Pay Slips</a></li>
            <li><a id="download_report" class="dropdown-item">Download Report</a></li>
            <li><a id="download_sft_report" class="dropdown-item">Download SFT Report</a></li>
            <li><a id="download_sft_upld_report" class="dropdown-item">Download SFT Upload Report</a></li>
          </ul>
        </div>
      </div>
    </div>
    <div style="max-height:400px; overflow-y:auto;">
      <table class="table table-bordered mt-3">
        <!-- dynamic <thead> will be injected here -->
        <thead></thead>
        <tbody id="pay_slip_table_body"></tbody>
      </table>
    </div>
  `).appendTo(page.body);

  const $table = $form.find("table");
  const $tbody = $form.find("#pay_slip_table_body");

  // Populate Company dropdown
  frappe.call({
    method: "frappe.client.get_list",
    args: { doctype: "Company", fields: ["name"], limit_page_length: 999 },
    callback: function (res) {
      if (res.message) {
        const $sel = $form.find("#company_list");
        res.message.forEach((c) => {
          $sel.append(`<option value="${c.name}">${c.name}</option>`);
        });
      }
    },
  });

  // Main fetch button click
  $form.find("#fetch_records").click(function () {
    const year = parseInt($form.find("#year").val(), 10);
    const month = parseInt($form.find("#month").val(), 10);
    const company = $form.find("#company_list").val();

    if (!year || year < 1900 || year > 2099) {
      frappe.throw("Please enter a valid 4-digit year.");
      return;
    }
    if (!month) {
      frappe.msgprint("Please select both year and month", "Warning");
      return;
    }

    // Hide actions until after fetch
    $form.find("#action_button").hide();
    frappe.dom.freeze("Loading...");
    // Fetch report data
    frappe.call({
      method: "pinnaclehrms.api.get_pay_slip_report",
      args: {
        year,
        month,
        curr_user: frappe.session.user_email,
        company,
      },
      callback: function (res) {
        frappe.dom.unfreeze();
        const records = res.message || [];
        if (!records.length) {
          $tbody.empty();
          frappe.msgprint("No records found.");
          return;
        }

        // 1. Determine all unique Other Earnings keys
        const otherKeys = Array.from(
          new Set(records.flatMap((r) => Object.keys(r.other_earnings || {})))
        );

        // 2. Build full header list
        const staticHeaders = [
          '<input type="checkbox" id="select_all_rows"> Select All',
          "Pay Slip",
          "Employee Name",
          "Email",
          "Joining Date",
          "Basic Salary",
          "Standard Days",
          "Actual Days",
          "Full Day",
          "Sundays",
          "Half Day",
          "3/4 Day",
          "Quarter Day",
          "Lates",
          "Absent",
          "Total",
        ];
        const tailHeaders = ["Net Pay"];
        const allHeaders = [...staticHeaders, ...otherKeys, ...tailHeaders];

        // 3. Render <thead>
        const thead = `
          <tr>
            ${allHeaders
              .map(
                (h) =>
                  `<th style="border:2px solid #ddd;
                           background:#f8f9fa;">
                 ${h}
               </th>`
              )
              .join("")}
          </tr>`;
        $table.find("thead").html(thead);

        // 4. Render each row
        $tbody.empty();
        records.forEach((rec) => {
          const emailLink = rec.personal_email
            ? `<span title="${rec.personal_email}"
                     style="color:blue;cursor:pointer">
                 Available
               </span>`
            : "N/A";

          const info = rec.salary_info || {};
          const other = rec.other_earnings || {};

          // Build dynamic Other Earnings cells
          const otherCells = otherKeys
            .map((k) => `<td>${other[k]?.amount || 0}</td>`)
            .join("");

          const row = `
            <tr>
              <td><input type="checkbox"
                         class="row_checkbox"
                         value="${rec.pay_slip_name}"></td>
              <td><a href="/app/pay-slips/${rec.pay_slip_name}"
                     target="_blank">
                   ${rec.pay_slip_name}
                 </a>
              </td>
              <td>${rec.employee_name}</td>
              <td>${emailLink}</td>
              <td>${rec.date_of_joining || ""}</td>
              <td>${rec.basic_salary || 0}</td>
              <td>${rec.standard_working_days || 0}</td>
              <td>${rec.actual_working_days || 0}</td>
              <td>${info["Full Day"]?.day || 0}</td>
              <td>${info["Sunday Workings"]?.day || 0}</td>
              <td>${info["Half Day"]?.day || 0}</td>
              <td>${info["3/4 Quarter Day"]?.day || 0}</td>
              <td>${info["Quarter Day"]?.day || 0}</td>
              <td>${info["Lates"]?.day || 0}</td>
              <td>${rec.absent || 0}</td>
              <td>${rec.total || 0}</td>
              ${otherCells}
              <td>${rec.net_payable_amount || 0}</td>
            </tr>`;
          $tbody.append(row);
        });
        $table.find("#select_all_rows").on("change", function () {
          const checked = $(this).is(":checked");
          $tbody.find(".row_checkbox").prop("checked", checked);
          $form
            .find("#action_button")
            .toggle(checked || $tbody.find(".row_checkbox:checked").length > 0);
        });

        // 5. Show action button and hide fetch
        $form.find("#fetch_records").hide();
        $form.find("#action_button").show();

        // 6. Bind checkbox change to toggle Actions
        $tbody.find(".row_checkbox").on("change", function () {
          const anyChecked = $tbody.find(":checked").length > 0;
          $form.find("#action_button").toggle(anyChecked);
        });
      },
    });
  });

  // Show fetch again if filters change
  $form.find("#year, #month, #company_list").on("change", function () {
    $form.find("#fetch_records").show();
  });

  // Email Pay Slips
  $form.on("click", "#email_pay_slips", function () {
    const selected = get_selected();
    if (!selected.length) {
      frappe.msgprint("Please select at least one pay slip to email.");
      return;
    }
    frappe.call({
      method: "pinnaclehrms.api.email_pay_slips",
      args: { pay_slips: selected },
      callback: function (res) {
        if (res.message?.message === "success") {
          frappe.msgprint("Pay slips emailed successfully!");
        } else {
          frappe.msgprint("Failed to send email. Please try again.");
        }
      },
    });
  });

  $form.on("click", "#print_pay_slips", function () {
    const selected = get_selected();
    if (!selected.length) {
      frappe.msgprint("Please select at least one pay slip to email.");
      return;
    }
  });

  // Download / Print actions
  $form.on("click", "#download_report", function () {
    const y = parseInt($form.find("#year").val(), 10);
    const m = parseInt($form.find("#month").val(), 10);
    const c = $form.find("#company_list").val();
    window.location.href = `/api/method/pinnaclehrms.api.download_pay_slip_report?year=${y}&month=${m}&company=${c}`;
  });
  $form.on("click", "#download_sft_report", function () {
    const m = parseInt($form.find("#month").val(), 10);
    window.location.href = `/api/method/pinnaclehrms.api.download_sft_report?month=${m}`;
  });
  $form.on("click", "#download_sft_upld_report", function () {
    const m = parseInt($form.find("#month").val(), 10);
    window.location.href = `/api/method/pinnaclehrms.api.download_sft_upld_report?month=${m}`;
  });
};

// Helper: collect selected pay slip names
function get_selected() {
  return $(".row_checkbox:checked")
    .map(function () {
      return this.value;
    })
    .get();
}
