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
                <input type="number" id="year" class="form-control" placeholder="Enter year" min="1900" max="2099" value="${currentYear}">
            </div>

            <!-- Month Field -->
            <div class="col-md-3 form-group">
                <label for="month">Month</label>
                <select id="month" class="form-control">
                    <option value="">Select month</option>
                    ${[...Array(12)]
                      .map(
                        (_, i) =>
                          `<option value="${i + 1}">${new Date(
                            0,
                            i
                          ).toLocaleString("default", {
                            month: "long",
                          })}</option>`
                      )
                      .join("")}
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
                    </ul>
                </div>
            </div>
        </div>
        
        <table class="table table-bordered mt-3">
            <thead>
                <tr>
                    <th>Select</th>
                    <th>Pay Slip</th>
                    <th>Employee Name</th>
                    <th>Email</th>
                    <th>Joining Date</th>
                    <th>Basic Salary</th>
                    <th>Standard Days</th>
                    <th>Actual Days</th>
                    <th>Full Day</th>
                    <th>Sundays</th>
                    <th>Half Day</th>
                    <th>3/4 Day</th>
                    <th>Quarter Day</th>
                    <th>Lates</th>
                    <th>Absent</th>
                    <th>Total</th>
                    <th>Sunday Earnings</th>
                    <th>Other Earnings</th>
                    <th>Adjustments</th>
                    <th>Net Pay</th>
                </tr>
            </thead>
            <tbody id="pay_slip_table_body"></tbody>
        </table>
    `).appendTo(page.body);

  // Fetch records when button is clicked
  $form.find("#fetch_records").click(function () {
    const year = parseInt($form.find("#year").val(), 10);
    const month = $form.find("#month").val();

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
      args: { year, month, curr_user: currUser },
      callback: function (res) {
        if (res.message) {
          console.log(res.message);
          pay_slip_list(res.message);
          $form.find("#fetch_records").hide();
        } else {
          document.getElementById("pay_slip_table_body").innerHTML = "";
          frappe.msgprint("No records found.");
          $form.find("#fetch_records").show();
        }
      },
    });
  });

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

  // Handle "Email Pay Slips" button click
  $form.find("#email_pay_slips").click(function () {
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
        if (res.message === "success") {
          frappe.msgprint("Pay slips emailed successfully!");
        } else {
          frappe.msgprint("Failed to send emails. Please try again.");
        }
      },
    });
  });

  // Show fetch button when month changes
  $form.find("#month").on("change", function () {
    $form.find("#fetch_records").show();
  });
};

// Function to populate table with pay slip data
function pay_slip_list(records) {
  let tableBody = document.getElementById("pay_slip_table_body");
  tableBody.innerHTML = "";

  records.forEach((record) => {
    let full_day = 0,
      sundays = 0,
      half_day = 0,
      three_four_day = 0,
      quarter_day = 0,
      late_days = 0;

    if (record.salary_calculation) {
      record.salary_calculation.forEach((entry) => {
        switch (entry.salary_particulars) {
          case "Full Day":
            full_day = entry.salary_days;
            break;
          case "Sundays":
            sundays = entry.salary_days;
            break;
          case "Half Day":
            half_day = entry.salary_days;
            break;
          case "3/4 Quarter Day":
            three_four_day = entry.salary_days;
            break;
          case "Quarter Day":
            quarter_day = entry.salary_days;
            break;
          default:
            if (entry.salary_particulars.includes("Lates"))
              late_days = entry.salary_days;
        }
      });
    }

    let other_earnings_amount = (record.other_earnings || []).reduce(
      (sum, earning) => sum + (earning.earnings_amount || 0),
      0
    );
    let sunday_working_amount = sundays * (record.per_day_salary || 0);

    let rowHTML = `
            <tr>
                <td><input type="checkbox" class="row_checkbox" value="${
                  record.pay_slip_name
                }" /></td>
                <td><a href="/app/pay-slips/${
                  record.pay_slip_name
                }" target="blank">${record.pay_slip_name}</a></td>
                <td>${record.employee_name}</td>
                <td>${record.personal_email || "N/A"}</td>
                <td>${record.date_of_joining}</td>
                <td>${record.basic_salary || 0}</td>
                <td>${record.standard_working_days || 0}</td>
                <td>${record.actual_working_days || 0}</td>
                <td>${full_day}</td>
                <td>${sundays}</td>
                <td>${half_day}</td>
                <td>${three_four_day}</td>
                <td>${quarter_day}</td>
                <td>${late_days}</td>
                <td>${record.absent || 0}</td>
                <td>${record.total || 0}</td>
                <td>${sunday_working_amount}</td>
                <td>${other_earnings_amount}</td>
                <td>${record.adjustments || 0}</td>
                <td>${record.net_payble_amount || 0}</td>
            </tr>`;

    tableBody.innerHTML += rowHTML;
  });

  // Attach event listener for checkbox selection
  document
    .getElementById("pay_slip_table_body")
    .addEventListener("change", updateActionButtonVisibility);
}

// Show action button if any checkbox is selected
function updateActionButtonVisibility() {
  document.getElementById("action_button").style.display =
    document.querySelectorAll('input[type="checkbox"]:checked').length > 0
      ? "inline-block"
      : "none";
}
