frappe.pages["pay-slip-report"].on_page_load = function (wrapper) {
  var page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Pay Slip Report",
    single_column: true,
  });

  const currentYear = new Date().getFullYear();

  // Move $form definition here for global access within this function scope
  const $form = $(
    `<div class="row">
        <!-- Year Field -->
        <div class="col-md-1 form-group">
            <label for="year">Year</label>
            <input type="number" id="year" class="form-control" placeholder="Enter year" min="1900" max="2099" value="${currentYear}">
        </div>

        <!-- Month Field -->
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

        <!-- Fetch Records Button -->
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
                    <li><a class="dropdown-item" id="download_report">Download Report</a></li>
                    <li><a class="dropdown-item" id="download_sft_report">Download SFT Report</a></li>
                    <li><a class="dropdown-item" id="download_sft_upld_report">Download SFT Upload Report</a></li>
                </ul>
            </div>
        </div>
    </div>
    
    <div style="max-height: 400px; overflow-y: auto;">
  <table class="table table-bordered mt-3">
    <thead style="position: sticky; top: 0; z-index: 2; background-color: grey; border-bottom: 2px solid #ddd;">
      <tr>
        ${[
          "Select",
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
          "Sunday Earnings",
          "Other Earnings",
          "Adjustments",
          "Net Pay",
        ]
          .map(
            (header) =>
              `<th style="border: 2px solid #ddd; background: #f8f9fa;">${header}</th>`
          )
          .join("")}
      </tr>
    </thead>
    <tbody id="pay_slip_table_body"></tbody>
  </table>
</div>`
  ).appendTo(page.body);

  frappe.call({
    method: "frappe.client.get_list",
    args: {
      doctype: "Company",
      fields: ["name"],
      limit_page_length: 999,
    },
    callback: function (res) {
      if (res.message) {
        const $companySelect = $form.find("#company_list");
        res.message.forEach((company) => {
          $companySelect.append(
            `<option value="${company.name}">${company.name}</option>`
          );
        });
      }
    },
  });

  // Fetch records when button is clicked
  $form.find("#fetch_records").click(function () {
    const year = parseInt($form.find("#year").val(), 10);
    const month = parseInt($form.find("#month").val());
    const selectedCompany = $form.find("#company_list").val();

    if (!year || year < 1900 || year > 2099) {
      frappe.throw("Please enter a valid 4-digit year.");
      return;
    }

    if (!month) {
      frappe.msgprint("Please select both year and month", "Warning");
      return;
    }

    document.getElementById("action_button").style.display = "none";

    const currUser = frappe.session.user_email;
    frappe.call({
      method: "pinnaclehrms.api.get_pay_slip_report",
      args: { year, month, curr_user: currUser, company: selectedCompany },
      callback: function (res) {
        if (res.message) {
          console.log(res.message);
          pay_slip_list(res.message);
          $form.find("#fetch_records").hide();
          document.getElementById("action_button").style.display =
            "inline-block";
        } else {
          document.getElementById("pay_slip_table_body").innerHTML = "";
          frappe.msgprint("No records found.");
          $form.find("#fetch_records").show();
        }
      },
    });
  });

  // Show fetch button when month changes
  $form.find("#month, #year, #company_list").on("change", function () {
    $form.find("#fetch_records").show();
  });

  $form.on("click", "#email_pay_slips", function () {
    // Ensure get_selected function is available
    const selectedPaySlips = get_selected();

    if (selectedPaySlips.length === 0) {
      frappe.msgprint("Please select at least one pay slip to email.");
      return;
    }

    frappe.call({
      method: "pinnaclehrms.api.email_pay_slips", // Update with correct API method
      args: {
        pay_slips: selectedPaySlips,
      },
      callback: function (res) {
        console.log(res.message.message);
        if (res.message.message === "success") {
          frappe.msgprint("Pay slips emailed successfully!");
        } else {
          frappe.msgprint("Failed to send email. Please try again.");
        }
      },
    });
  });

  $form.on("click", "#download_sft_report", function () {
    let month = parseInt($form.find("#month").val());
    window.location.href = `/api/method/pinnaclehrms.api.download_sft_report?month=${month}`;
  });

  $form.on("click", "#download_sft_upld_report", function () {
    let month = parseInt($form.find("#month").val());
    window.location.href = `/api/method/pinnaclehrms.api.download_sft_upld_report?month=${month}`;
  });

  $form.on("click", "#download_report", function () {
    const year = parseInt($form.find("#year").val(), 10);
    const month = parseInt($form.find("#month").val());
    const selectedCompany = $form.find("#company_list").val();
  
    window.location.href = `/api/method/pinnaclehrms.api.download_pay_slip_report?year=${year}&month=${month}&company=${selectedCompany}`;
  });
  
};

// Function to populate table with pay slip data
function pay_slip_list(records) {
  let tableBody = document.getElementById("pay_slip_table_body");
  tableBody.innerHTML = "";

  records.forEach((record) => {
    let emailLink = record.personal_email
      ? `<span style="text-decoration: none; color: blue; cursor: pointer;" title="${record.personal_email}">Available</span>`
      : "N/A";

    // Handle nested salary_info
    let salary_info = record.salary_info || {};
    let other_earnings = record.other_earnings || {};

    const getAmount = (obj, key) => (obj[key] ? obj[key].amount || 0 : 0);

    let rowHTML = `
      <tr>
          <td><input type="checkbox" class="row_checkbox" value="${
            record.pay_slip_name
          }" /></td>
          <td><a href="/app/pay-slips/${
            record.pay_slip_name
          }" target="_blank">${record.pay_slip_name}</a></td>
          <td>${record.employee_name}</td>
          <td>${emailLink}</td>
          <td>${record.date_of_joining || ""}</td>
          <td>${record.basic_salary || 0}</td>
          <td>${record.standard_working_days || 0}</td>
          <td>${record.actual_working_days || 0}</td>
          <td>${salary_info["Full Day"]?.day || 0}</td>
          <td>${salary_info["Sunday Workings"]?.day || 0}</td>
          <td>${salary_info["Half Day"]?.day || 0}</td>
          <td>${salary_info["3/4 Quarter Day"]?.day || 0}</td>
          <td>${salary_info["Quarter Day"]?.day || 0}</td>
          <td>${salary_info["Lates"]?.day || 0}</td>
          <td>${record.absent || 0}</td>
          <td>${record.total || 0}</td>
          <td>${getAmount(other_earnings, "Sunday Workings")}</td>
          <td>${Object.keys(other_earnings)
            .filter((key) => key !== "Sunday Workings")
            .reduce((sum, key) => sum + getAmount(other_earnings, key), 0)}</td>
          <td>${record.adjustments || 0}</td>
          <td>${record.net_payable_amount || 0}</td>
      </tr>
    `;
    tableBody.innerHTML += rowHTML;
  });

  document
    .getElementById("pay_slip_table_body")
    .addEventListener("change", updateActionButtonVisibility);
}

// Function to get selected pay slips
function get_selected() {
  const selected = [];
  document
    .querySelectorAll('input[type="checkbox"].row_checkbox:checked')
    .forEach((checkbox) => {
      selected.push(checkbox.value);
    });
  return selected;
}

// Show action button if any checkbox is selected
function updateActionButtonVisibility() {
  document.getElementById("action_button").style.display =
    document.querySelectorAll('input[type="checkbox"]:checked').length > 0
      ? "inline-block"
      : "none";
}
