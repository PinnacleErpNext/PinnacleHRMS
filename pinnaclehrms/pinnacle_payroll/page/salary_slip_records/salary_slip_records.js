frappe.pages["salary-slip-records"].on_page_load = function (wrapper) {
  // =========================================================
  // Create Page
  // =========================================================
  var page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Pay Slip Report",
    single_column: true,
  });

  const currentYear = new Date().getFullYear();

  // =========================================================
  // Build Form & Table Skeleton
  // =========================================================
  const $form = $(`
    <div class="row">

      <!-- Company -->
      <div class="col-md-3 form-group">
        <label for="company">Company</label>
        <select id="company_list" class="form-control">
          <option value="">Select Company</option>
        </select>
      </div>

      <!-- Year -->
      <div class="col-md-1 form-group">
        <label for="year">Year</label>
        <input
          type="number"
          id="year"
          class="form-control"
          min="1900"
          max="2099"
          value="${currentYear}"
        >
      </div>

      <!-- Month -->
      <div class="col-md-2 form-group">
        <label for="month">Month</label>
        <select id="month" class="form-control">
          <option value="">Select month</option>

          ${[...Array(12)]
            .map(
              (_, i) =>
                `<option value="${i + 1}">
                  ${new Date(0, i).toLocaleString("default", {
                    month: "long",
                  })}
                </option>`,
            )
            .join("")}

        </select>
      </div>

      <!-- Fetch -->
      <div class="col-md-3 form-group d-flex align-items-end">
        <button
          id="fetch_records"
          class="btn btn-primary"
        >
          Get Records
        </button>
      </div>

      <!-- Actions -->
      <div class="col-md-3 form-group d-flex align-items-end">

        <div
          id="action_button"
          class="btn-group"
          style="display:none;"
        >

          <button
            class="btn btn-primary dropdown-toggle"
            data-toggle="dropdown"
          >
            Actions
          </button>

          <ul class="dropdown-menu">

            <li>
              <a
                id="email_pay_slips"
                class="dropdown-item"
              >
                Email Pay Slips
              </a>
            </li>

            <li>
              <a
                id="print_pay_slips"
                class="dropdown-item"
              >
                Print Pay Slips
              </a>
            </li>

            <li>
              <a
                id="download_report"
                class="dropdown-item"
              >
                Download Report
              </a>
            </li>

            <li>
              <a
                id="download_idfc_blkpay"
                class="dropdown-item"
              >
                Download IDFC Bank Bulk Payment Format
              </a>
            </li>

          </ul>

        </div>

      </div>

    </div>

    <!-- =====================================================
         TABLE CONTAINER
         ===================================================== -->

    <div
      id="salary_slip_table_container"
      style="
        max-height:800px;
        overflow-x:auto;
        overflow-y:auto;
        position:relative;
        width:100%;
      "
    >

      <table
        id="record_table"
        class="table table-bordered mt-3"
        style="
          margin-bottom:0;
          width:max-content;
          min-width:100%;
        "
      >

        <thead></thead>

        <tbody id="pay_slip_table_body"></tbody>

      </table>

    </div>

  `).appendTo(page.body);

  const $table = $form.find("#record_table");
  const $tbody = $form.find("#pay_slip_table_body");

  // =========================================================
  // Sticky Table CSS
  // =========================================================
  //
  // Fixed columns:
  //
  // 1. Select
  // 2. Salary Slip
  // 3. Status
  // 4. Employee Name
  // 5. Email
  // 6. Joining Date
  //
  // Header is also fixed during vertical scrolling.
  // =========================================================

  $("#salary-slip-records-sticky-style").remove();

  const stickyStyle = `
  <style>

    /* =====================================================
       TABLE BASE
       ===================================================== */

    #salary_slip_table_container {
      position: relative;
      width: 100%;
      max-width: 100%;
      overflow-x: auto;
      overflow-y: auto;
    }

    #record_table {
      border-collapse: separate !important;
      border-spacing: 0;
      width: max-content !important;
      min-width: 100%;
      margin-bottom: 0 !important;
    }

    #record_table th,
    #record_table td {
      white-space: nowrap;
      vertical-align: middle;
    }


    /* =====================================================
       HEADER
       ===================================================== */

    #record_table thead th {
      position: sticky;
      top: 0;

      background: #f8f9fa !important;

      z-index: 10;

      border-top: 1px solid #ddd;
      border-bottom: 2px solid #ddd;

      height: 42px;

      vertical-align: middle;

      font-weight: 600;
    }


    /* =====================================================
       FIXED COLUMN 1
       SELECT
       ===================================================== */

    #record_table th:nth-child(1),
    #record_table td:nth-child(1) {

      position: sticky;
      left: 0;

      width: 70px;
      min-width: 70px;
      max-width: 70px;

      background: #f1f3f5 !important;

      z-index: 20;
    }


    /* =====================================================
       FIXED COLUMN 2
       SALARY SLIP
       ===================================================== */

    #record_table th:nth-child(2),
    #record_table td:nth-child(2) {

      position: sticky;
      left: 70px;

      width: 180px;
      min-width: 180px;
      max-width: 180px;

      background: #f1f3f5 !important;

      z-index: 20;
    }


    /* =====================================================
       FIXED COLUMN 3
       STATUS
       ===================================================== */

    #record_table th:nth-child(3),
    #record_table td:nth-child(3) {

      position: sticky;
      left: 250px;

      width: 90px;
      min-width: 90px;
      max-width: 90px;

      background: #f1f3f5 !important;

      z-index: 20;
    }


    /* =====================================================
       FIXED COLUMN 4
       EMPLOYEE NAME
       ===================================================== */

    #record_table th:nth-child(4),
    #record_table td:nth-child(4) {

      position: sticky;
      left: 340px;

      width: 160px;
      min-width: 160px;
      max-width: 160px;

      background: #f1f3f5 !important;

      z-index: 20;
    }


    /* =====================================================
       FIXED COLUMN 5
       EMAIL
       ===================================================== */

    #record_table th:nth-child(5),
    #record_table td:nth-child(5) {

      position: sticky;
      left: 500px;

      width: 105px;
      min-width: 105px;
      max-width: 105px;

      background: #f1f3f5 !important;

      z-index: 20;
    }


    /* =====================================================
       FIXED COLUMN 6
       JOINING DATE
       ===================================================== */

    #record_table th:nth-child(6),
    #record_table td:nth-child(6) {

      position: sticky;
      left: 605px;

      width: 115px;
      min-width: 115px;
      max-width: 115px;

      background: #f1f3f5 !important;

      z-index: 20;

      box-shadow:
        4px 0 7px rgba(0, 0, 0, 0.15);
    }


    /* =====================================================
       FIXED HEADER + FIXED COLUMN INTERSECTION
       ===================================================== */

    #record_table thead th:nth-child(1),
    #record_table thead th:nth-child(2),
    #record_table thead th:nth-child(3),
    #record_table thead th:nth-child(4),
    #record_table thead th:nth-child(5),
    #record_table thead th:nth-child(6) {

      position: sticky;

      top: 0;

      z-index: 30;

      background: #e9ecef !important;

      font-weight: 600;
    }


    /* =====================================================
       FIXED BODY COLUMNS
       ===================================================== */

    #record_table tbody td:nth-child(1),
    #record_table tbody td:nth-child(2),
    #record_table tbody td:nth-child(3),
    #record_table tbody td:nth-child(4),
    #record_table tbody td:nth-child(5),
    #record_table tbody td:nth-child(6) {

      background: #f1f3f5 !important;
    }


    /* =====================================================
       FIXED AREA RIGHT BORDER / SHADOW
       ===================================================== */

    #record_table th:nth-child(6),
    #record_table td:nth-child(6) {

      border-right: 2px solid #c8cdd2 !important;

      box-shadow:
        4px 0 7px rgba(0, 0, 0, 0.15);
    }


    /* =====================================================
       HEADER
       ===================================================== */

    #record_table thead th {

      border-bottom:
        2px solid #c8cdd2 !important;
    }


    /* =====================================================
       SALARY SLIP LINK
       ===================================================== */

    #record_table td:nth-child(2) a {

      display: block;

      max-width: 170px;

      overflow: hidden;

      text-overflow: ellipsis;

      white-space: nowrap;
    }


    /* =====================================================
       EMPLOYEE NAME
       ===================================================== */

    #record_table td:nth-child(4) {

      overflow: hidden;

      text-overflow: ellipsis;
    }


    /* =====================================================
       EMAIL
       ===================================================== */

    #record_table td:nth-child(5) {

      text-align: left;
    }

  </style>
`;

  $("#salary-slip-records-sticky-style").remove();

  $("head").append(stickyStyle);

  $("head").append(stickyStyle);

  // =========================================================
  // Populate Company Dropdown
  // =========================================================

  frappe.call({
    method: "frappe.client.get_list",

    args: {
      doctype: "Company",
      fields: ["name"],
      limit_page_length: 999,
    },

    callback: function (res) {
      if (res.message) {
        const $sel = $form.find("#company_list");

        res.message.forEach((c) => {
          $sel.append(
            `<option value="${c.name}">
              ${c.name}
            </option>`,
          );
        });
      }
    },
  });

  // =========================================================
  // Main Fetch Button
  // =========================================================

  $form.find("#fetch_records").click(function () {
    const year = parseInt($form.find("#year").val(), 10);

    const month = parseInt($form.find("#month").val(), 10);

    const company = $form.find("#company_list").val();

    // -----------------------------------------------------
    // Validate Year
    // -----------------------------------------------------

    if (!year || year < 1900 || year > 2099) {
      frappe.throw("Please enter a valid 4-digit year.");

      return;
    }

    // -----------------------------------------------------
    // Validate Month
    // -----------------------------------------------------

    if (!month) {
      frappe.msgprint("Please select both year and month", "Warning");

      return;
    }

    // -----------------------------------------------------
    // Hide Actions
    // -----------------------------------------------------

    $form.find("#action_button").hide();

    frappe.dom.freeze("Loading...");

    // =====================================================
    // Fetch Records
    // =====================================================

    frappe.call({
      method:
        "pinnaclehrms.pinnacle_payroll.page.salary_slip_records.salary_slip_records.getSalarySlipRecords",

      args: {
        year,
        month,
        curr_user: frappe.session.user_email,
        company,
      },

      callback: function (res) {
        frappe.dom.unfreeze();

        const records = res.message || [];

        // -------------------------------------------------
        // No Records
        // -------------------------------------------------

        if (!records.length) {
          $tbody.empty();

          $table.find("thead").empty();

          frappe.msgprint("No records found.");

          return;
        }

        // =================================================
        // Other Earnings Keys
        // =================================================

        const otherKeys = Array.from(
          new Set(
            records.flatMap((r) =>
              (r.other_earnings || []).map((earning) => earning.component),
            ),
          ),
        ).filter(Boolean);

        console.log("Unique Other Earnings keys:", otherKeys);

        // =================================================
        // Deduction Keys
        // =================================================

        const deductionKeys = Array.from(
          new Set(
            records.flatMap((r) =>
              (r.deductions || []).map((deduction) => deduction.component),
            ),
          ),
        ).filter(Boolean);

        console.log("Unique Deduction keys:", deductionKeys);

        // =================================================
        // Static Headers
        // =================================================

        const staticHeaders = [
          '<input type="checkbox" id="select_all_rows"> Select All',

          "Salary Slip",

          "Status",

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

        // =================================================
        // Tail Headers
        // =================================================

        const tailHeaders = ["Total Deduction", "Deductions Total", "Net Pay"];

        // =================================================
        // All Headers
        // =================================================

        const allHeaders = [
          ...staticHeaders,

          ...otherKeys,

          ...deductionKeys,

          ...tailHeaders,
        ];

        // =================================================
        // Render Header
        // =================================================

        const thead = `
            <tr>

              ${allHeaders
                .map(
                  (h) =>
                    `<th
                      style="
                        border:2px solid #ddd;
                        background:#f8f9fa;
                        white-space:nowrap;
                      "
                    >
                      ${h}
                    </th>`,
                )
                .join("")}

            </tr>
          `;

        $table.find("thead").html(thead);

        // =================================================
        // Sort Records
        // =================================================

        records.sort((a, b) => {
          const nameA = (a.employee_name || "").toLowerCase();

          const nameB = (b.employee_name || "").toLowerCase();

          return nameA.localeCompare(nameB);
        });

        // =================================================
        // Render Rows
        // =================================================

        $tbody.empty();

        records.forEach((rec) => {
          // ---------------------------------------------
          // Email
          // ---------------------------------------------

          const emailLink = rec.email
            ? `<span
                       title="${rec.email}"
                       style="
                         color:blue;
                         cursor:pointer;
                       "
                     >
                       Available
                     </span>`
            : "N/A";

          // ---------------------------------------------
          // Salary Breakup
          // ---------------------------------------------

          const info = rec.salary_info || {};

          // ---------------------------------------------
          // Other Earnings
          // ---------------------------------------------

          const other = rec.other_earnings || [];

          const earningsMap = {};

          other.forEach((earning) => {
            if (earning.component) {
              earningsMap[earning.component] = earning.amount || 0;
            }
          });

          // ---------------------------------------------
          // Other Earnings Cells
          // ---------------------------------------------

          const otherCells = otherKeys

            .map(
              (key) =>
                `<td>
                        ${earningsMap[key] ?? 0}
                      </td>`,
            )

            .join("");

          // ---------------------------------------------
          // Deductions
          // ---------------------------------------------

          const deductions = rec.deductions || [];

          const deductionsMap = {};

          deductions.forEach((deduction) => {
            if (deduction.component) {
              deductionsMap[deduction.component] = deduction.amount || 0;
            }
          });

          // ---------------------------------------------
          // Deduction Cells
          // ---------------------------------------------

          const deductionCells = deductionKeys

            .map(
              (key) =>
                `<td>
                        ${deductionsMap[key] ?? 0}
                      </td>`,
            )

            .join("");

          // =================================================
          // Row
          // =================================================

          const row = `

                <tr>

                  <!-- Select -->
                  <td>
                    <input
                      type="checkbox"
                      class="row_checkbox"
                      value="${rec.pay_slip_name}"
                    >
                  </td>


                  <!-- Salary Slip -->
                  <td>

                    <a
                      href="/app/salary-slip/${rec.pay_slip_name}"
                      target="_blank"
                    >
                      ${rec.pay_slip_name}
                    </a>

                  </td>


                  <!-- Status -->
                  <td
                    style="
                      color: ${
                        rec.status === "Draft"
                          ? "#ff9800"
                          : rec.status === "Submitted"
                            ? "#4caf50"
                            : rec.status === "Cancelled"
                              ? "#f44336"
                              : "#000"
                      };

                      font-weight:600;
                    "
                  >

                    ${rec.status}

                  </td>


                  <!-- Employee Name -->
                  <td>
                    ${rec.employee_name || ""}
                  </td>


                  <!-- Email -->
                  <td>
                    ${emailLink}
                  </td>


                  <!-- Joining Date -->
                  <td>
                    ${rec.date_of_joining || ""}
                  </td>


                  <!-- Basic Salary -->
                  <td>
                    ${rec.basic_salary || 0}
                  </td>


                  <!-- Standard Days -->
                  <td>
                    ${rec.standard_working_days || 0}
                  </td>


                  <!-- Actual Days -->
                  <td>
                    ${rec.actual_working_days || 0}
                  </td>


                  <!-- Full Day -->
                  <td>
                    ${info["Full Day"]?.days || 0}
                  </td>


                  <!-- Sundays -->
                  <td>
                    ${info["Sunday Workings"]?.days || 0}
                  </td>


                  <!-- Half Day -->
                  <td>
                    ${info["Half Day"]?.days || 0}
                  </td>


                  <!-- 3/4 Day -->
                  <td>
                    ${info["3/4 Quarter Day"]?.days || 0}
                  </td>


                  <!-- Quarter Day -->
                  <td>
                    ${info["Quarter Day"]?.days || 0}
                  </td>


                  <!-- Lates -->
                  <td>
                    ${info["Lates"]?.days || 0}
                  </td>


                  <!-- Absent -->
                  <td>
                    ${rec.absent || 0}
                  </td>


                  <!-- Total -->
                  <td>
                    ${rec.total || 0}
                  </td>


                  <!-- Other Earnings -->
                  ${otherCells}


                  <!-- Individual Deductions -->
                  ${deductionCells}


                  <!-- Total Deduction -->
                  <td>
                    ${rec.total_deduction || 0}
                  </td>


                  <!-- Deductions Total -->
                  <td>
                    ${rec.deductions_total || 0}
                  </td>


                  <!-- Net Pay -->
                  <td>
                    ${rec.net_payable_amount || 0}
                  </td>

                </tr>

              `;

          $tbody.append(row);
        });

        // =================================================
        // Select All
        // =================================================

        $table.find("#select_all_rows").on("change", function () {
          const checked = $(this).is(":checked");

          $tbody.find(".row_checkbox").prop("checked", checked);

          $form
            .find("#action_button")
            .toggle(checked || $tbody.find(".row_checkbox:checked").length > 0);
        });

        // =================================================
        // Show Actions
        // =================================================

        $form.find("#fetch_records").hide();

        $form.find("#action_button").show();

        // =================================================
        // Checkbox Change
        // =================================================

        $tbody.find(".row_checkbox").on("change", function () {
          const anyChecked = $tbody.find(".row_checkbox:checked").length > 0;

          $form.find("#action_button").toggle(anyChecked);
        });
      },
    });
  });

  // =========================================================
  // Filters Changed
  // =========================================================

  $form.find("#year, #month, #company_list").on("change", function () {
    $form.find("#fetch_records").show();

    $form.find("#action_button").hide();

    $table.find("thead").empty();

    $tbody.empty();
  });

  // =========================================================
  // Email Pay Slips
  // =========================================================

  $form.on("click", "#email_pay_slips", function () {
    const selected = get_selected();

    if (!selected.length) {
      frappe.msgprint("Please select at least one pay slip to email.");

      return;
    }

    const employees = [];

    $tbody.find(".row_checkbox:checked").each(function () {
      const $row = $(this).closest("tr");

      /*
       * Current column positions:
       *
       * 1 = Checkbox
       * 2 = Salary Slip
       * 3 = Status
       * 4 = Employee Name
       * 5 = Email
       */

      const empName = $row.find("td:nth-child(4)").text().trim();

      const empEmail = $row.find("td:nth-child(5) span").attr("title") || "N/A";

      employees.push({
        name: empName,

        email: empEmail,
      });
    });

    // =====================================================
    // Confirmation List
    // =====================================================

    const listHtml = `

        <ul
          style="
            max-height:200px;
            overflow-y:auto;
            padding-left:20px;
          "
        >

          ${employees
            .map(
              (e) =>
                `<li>
                  <strong>
                    ${e.name}
                  </strong>

                  (
                    ${e.email || "No Email"}
                  )

                </li>`,
            )
            .join("")}

        </ul>

      `;

    frappe.confirm(
      `
          <div>

            <p>
              Are you sure you want to send pay slips
              to the following employees?
            </p>

            ${listHtml}

          </div>
        `,

      // ---------------------------------------------------
      // Yes
      // ---------------------------------------------------

      function () {
        frappe.call({
          method:
            "pinnaclehrms.pinnacle_payroll.page.salary_slip_records.salary_slip_records.email_pay_slips",

          args: {
            pay_slips: selected,
          },

          callback: function (res) {
            if (res.message?.message === "success") {
              frappe.msgprint("Pay slips emailed successfully!");
            } else {
              frappe.msgprint("Failed to send email. Please try again.");
            }
          },
        });
      },

      // ---------------------------------------------------
      // No
      // ---------------------------------------------------

      function () {
        frappe.msgprint("Email sending cancelled.");
      },
    );
  });

  // =========================================================
  // Print Pay Slips
  // =========================================================

  $form.on("click", "#print_pay_slips", function () {
    const paySlips = get_selected();

    const y = parseInt($form.find("#year").val(), 10);

    const m = parseInt($form.find("#month").val(), 10);

    window.location.href = `/api/method/pinnaclehrms.pinnacle_payroll.page.salary_slip_records.salary_slip_records.print_pay_slip?year=${y}&month=${m}&pay_slips=${encodeURIComponent(
      JSON.stringify(paySlips),
    )}`;
  });

  // =========================================================
  // Download Pay Slip Report
  // =========================================================

  $form.on("click", "#download_report", function () {
    const y = parseInt($form.find("#year").val(), 10);

    const m = parseInt($form.find("#month").val(), 10);

    const c = $form.find("#company_list").val();

    const encodedCompany = btoa(c);

    window.location.href = `/api/method/pinnaclehrms.pinnacle_payroll.page.salary_slip_records.salary_slip_records.download_pay_slip_report?year=${y}&month=${m}&encodedCompany=${encodedCompany}`;
  });

  // =========================================================
  // Download SFT Report
  // =========================================================

  $form.on("click", "#download_sft_report", function () {
    const y = parseInt($form.find("#year").val(), 10);

    const m = parseInt($form.find("#month").val(), 10);

    const c = $form.find("#company_list").val();

    const encodedCompany = btoa(c);

    window.location.href = `/api/method/pinnaclehrms.pinnacle_payroll.page.salary_slip_records.salary_slip_records.download_sft_report?month=${m}&year=${y}&encodedCompany=${encodedCompany}`;
  });

  // =========================================================
  // Download Bank Upload Bulk Report
  // =========================================================

  $form.on("click", "#download_bank_upld_bulk_report", function () {
    try {
      const y = parseInt($form.find("#year").val(), 10);

      const m = parseInt($form.find("#month").val(), 10);

      const c = $form.find("#company_list").val();

      if (!y || !m || !c) {
        throw new Error("Year, Month, or Company is missing!");
      }

      const encodedCompany = btoa(c);

      const url = `/api/method/pinnaclehrms.pinnacle_payroll.page.salary_slip_records.salary_slip_records.download_bank_upld_bulk_report?month=${m}&year=${y}&encodedCompany=${encodedCompany}`;

      window.location.href = url;
    } catch (err) {
      console.error("❌ Failed to redirect:", err);

      frappe.msgprint({
        title: "Download Failed",

        message:
          err.message || "Something went wrong while downloading the report.",

        indicator: "red",
      });
    }
  });

  // =========================================================
  // Download IDFC BLKPAY
  // =========================================================

  $form.on("click", "#download_idfc_blkpay", function () {
    try {
      const y = parseInt($form.find("#year").val(), 10);

      const m = parseInt($form.find("#month").val(), 10);

      const c = $form.find("#company_list").val();

      if (!y || !m || !c) {
        throw new Error("Year, Month, or Company is missing!");
      }

      const encodedCompany = btoa(c);

      const url = `/api/method/pinnaclehrms.pinnacle_payroll.page.salary_slip_records.salary_slip_records.download_idfc_blkpay?month=${m}&year=${y}&encodedCompany=${encodedCompany}`;

      window.location.href = url;
    } catch (err) {
      console.error("❌ Failed to redirect:", err);

      frappe.msgprint({
        title: "Download Failed",

        message:
          err.message || "Something went wrong while downloading the report.",

        indicator: "red",
      });
    }
  });
};

// ===========================================================
// Helper: Collect Selected Pay Slip Names
// ===========================================================

function get_selected() {
  return $(".row_checkbox:checked")
    .map(function () {
      return this.value;
    })

    .get();
}
