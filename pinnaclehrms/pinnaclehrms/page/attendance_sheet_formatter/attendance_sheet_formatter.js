frappe.pages["attendance-sheet-formatter"].on_page_load = function (wrapper) {
  frappe.ui.make_app_page({
    parent: wrapper,
    title: "Attendance Sheet Formatter",
    single_column: true,
  });
};

frappe.pages["attendance-sheet-formatter"].on_page_show = function (wrapper) {
  let attendanceData = [];
  rawData = {};
  validatedRecord = {};
  let selectedCompany = null;
  // Load SheetJS if not already loaded
  if (typeof XLSX === "undefined") {
    const script = document.createElement("script");
    script.src =
      "https://cdn.sheetjs.com/xlsx-latest/package/dist/xlsx.full.min.js";
    script.onload = () => {
      setupDownloadButton(); // Call function after XLSX is ready
    };
    document.head.appendChild(script);
  } else {
    setupDownloadButton(); // Already loaded
  }
  function setupDownloadButton() {
    document
      .getElementById("download-template-btn")
      .addEventListener("click", () => {
        const data = [
          [
            "Employee",
            "Employee Name",
            "Attendance Date",
            "Shift",
            "In Time",
            "Out Time",
          ],
        ];

        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.aoa_to_sheet(data);
        XLSX.utils.book_append_sheet(wb, ws, "Attendance Template");
        XLSX.writeFile(wb, "Attendance Template.xlsx");
      });
  }

  const html = `
    <!-- Font Awesome for Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

    <div style="font-family: Inter; line-height: 1.8; display: flex; flex-direction: column; height: 100vh;">
      
      <!-- Sticky Controls -->
      <div style="position: sticky; top: 0; background: #fff; z-index: 1000; padding-bottom: 10px; border-bottom: 1px solid #ddd;">
        
        <!-- Company -->
        <div class="mt-3" id="company-field-wrapper">
          <label>Company:</label>
          <div id="company-link-field" style="max-width: 300px;"></div>
        </div>

        <!-- Payroll Period -->
        <div class="mt-3">
          <h6>Payroll Period</h6>
          <div class="d-flex align-items-center gap-2">
            <div id="payroll-from-field" style="max-width: 200px; margin-right: 20px;"></div>
            <div id="payroll-to-field" style="max-width: 200px;"></div>
          </div>
        </div>

        <!-- Upload Sections -->
        <div class="mt-3">
          <label>1. Upload Zaicom Attendance File:</label>
          <input type="file" id="pinnacle-excel-upload" accept=".xlsx" />
        </div>

        <div class="mt-2">
          <label>2. Upload ESSL Attendance File:</label>
          <input type="file" id="opticode-excel-upload" accept=".xlsx" />
        </div>

        <div class="mt-2">
          <label>3. Upload Mantra Attendance File:</label>
          <input type="file" id="mantra-excel-upload" accept=".xlsx" />
        </div>

        <!-- Other File Upload with Download Template Icon -->
        <div class="mt-2" style="display: flex; align-items: center; gap: 10px;">
          <label style="margin: 0;">4. Upload Other Attendance File:</label>
          <input type="file" id="other-excel-upload" accept=".xlsx" />
          
          <!-- Icon Button -->
          <button id="download-template-btn" 
                  title="Download Excel Template"
                  style="background: none; border: none; cursor: pointer; padding: 4px;">
            <i class="fa fa-file-excel-o" style="font-size: 20px; color: #28a745;"></i>
          </button>
        </div>

        <!-- Action Buttons -->
        <div class="mt-3">
          <button id="preview-btn" class="btn btn-light">Load Raw Data</button>
        </div>

        <div class="mt-3 text-center">
          <button id="validate-btn" class="btn btn-warning mx-2">Validate</button>
          <button id="download-raw-btn" class="btn btn-info mx-2">Download Raw Data</button>
          <button id="download-validated-btn" class="btn btn-success mx-2">Download Validated Data</button>
          <button id="import-validated-btn" class="btn btn-primary mx-2" disabled>Import Validated Records</button>
        </div>

        <!-- Tabs -->
        <ul class="nav nav-tabs mt-3" id="attendance-tabs" role="tablist">
          <li class="nav-item">
            <a class="nav-link active" id="raw-tab" data-target="#raw-tab-pane" role="tab">Raw Data</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" id="non-validated-tab" data-target="#non-validated-tab-pane" role="tab">Non-Validated</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" id="validated-tab" data-target="#validated-tab-pane" role="tab">Validated</a>
          </li>
        </ul>
      </div>

      <!-- Tab Contents -->
      <div class="tab-content mt-3" style="flex: 1; overflow: hidden; padding: 10px;">
        <div class="tab-pane fade show active" id="raw-tab-pane">
          <div id="attendance-preview" class="alert alert-info text-center">
            Upload files & click <strong>Load Raw Data</strong>
          </div>
        </div>

        <div class="tab-pane fade" id="non-validated-tab-pane">
          <div id="non-validated-section" class="alert alert-warning text-center">No records yet.</div>
        </div>

        <div class="tab-pane fade" id="validated-tab-pane">
          <div id="validated-section" class="alert alert-success text-center">No validated records yet.</div>
        </div>
      </div>

      <!-- Styles -->
      <style>
        .table-container {
          max-height: calc(100vh - 300px);
          overflow-y: auto;
          overflow-x: auto;
          border: 1px solid #dee2e6;
        }

        .table-container table thead th {
          position: sticky;
          top: 0;
          background: #f8f9fa;
          z-index: 10;
          border-bottom: 2px solid #dee2e6;
        }

        #attendance-table,
        #non-validated-section table,
        #validated-section table {
          border-collapse: separate;
        }
      </style>
    </div>
  `;

  $(wrapper).find(".page-body").html(html);

  // Create Company Link Field
  const companyControl = frappe.ui.form.make_control({
    df: {
      label: "Company",
      fieldtype: "Link",
      options: "Company",
      reqd: 1,
      onchange: () => (selectedCompany = companyControl.get_value()),
    },
    parent: $("#company-link-field"),
    render_input: true,
  });

  // Payroll Period Date Fields
  let payrollFromField = frappe.ui.form.make_control({
    df: {
      label: "From",
      fieldtype: "Date",
      reqd: 1,
      onchange: () => {
        let from_date = payrollFromField.get_value();
        if (from_date) {
          let date = new Date(from_date);
          let lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
          payrollToField.set_value(lastDay.toISOString().slice(0, 10));
        }
      },
    },
    parent: $("#payroll-from-field"),
    render_input: true,
  });

  let payrollToField = frappe.ui.form.make_control({
    df: { label: "To", fieldtype: "Date", reqd: 1 },
    parent: $("#payroll-to-field"),
    render_input: true,
  });

  // Handle Tabs
  $(document).on("click", "#attendance-tabs .nav-link", function (e) {
    e.preventDefault();
    $("#attendance-tabs .nav-link").removeClass("active");
    $(".tab-pane").removeClass("show active");
    $(this).addClass("active");
    $($(this).data("target")).addClass("show active");
  });

  function ensureCompanySelected() {
    if (!selectedCompany) {
      frappe.msgprint("❌ Please select a company.");
      return false;
    }
    return true;
  }

  // Load Raw Data
  $("#preview-btn").on("click", async function () {
    if (!ensureCompanySelected()) return;

    const pinnacleFile = $("#pinnacle-excel-upload")[0].files[0];
    const opticodeFile = $("#opticode-excel-upload")[0].files[0];
    const mantraFile = $("#mantra-excel-upload")[0].files[0];
    const otherFile = $("#other-excel-upload")[0].files[0];
    const payrollFrom = payrollFromField.get_value();
    const payrollTo = payrollToField.get_value();

    if (!payrollFrom || !payrollTo)
      return frappe.msgprint("Select Payroll Period.");
    if (new Date(payrollFrom) > new Date(payrollTo))
      return frappe.msgprint("Invalid Date Range.");
    if (!pinnacleFile && !opticodeFile && !mantraFile && !otherFile)
      return frappe.msgprint("Upload at least one file.");

    const formData = new FormData();
    formData.append("company", selectedCompany);
    formData.append("from_date", payrollFrom);
    formData.append("to_date", payrollTo);
    if (pinnacleFile) formData.append("pinnacle_file", pinnacleFile);
    if (opticodeFile) formData.append("opticode_file", opticodeFile);
    if (mantraFile) formData.append("mantra_file", mantraFile);
    if (otherFile) formData.append("other_file", otherFile);

    frappe.dom.freeze("Loading...");
    try {
      const res = await fetch(
        "/api/method/pinnaclehrms.utility.attendance_formatter.preview_final_attendance_sheet",
        {
          method: "POST",
          headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
          body: formData,
        }
      );
      frappe.dom.unfreeze();

      const data = await res.json();
      if (!res.ok || !data.message)
        return frappe.msgprint("❌ Error loading data");

      rawData = data.message.data;
      attendanceData = [];

      let tableHtml = `
        <div class="table-container">
          <table id="attendance-table" class="table table-bordered table-sm">
            <thead>
              <tr>
                <th>Sr. No.</th><th>Employee</th><th>Name</th><th>Date</th>
                <th>Shift</th><th>Log In From</th><th>In Time</th>
                <th>Log Out From</th><th>Out Time</th>
              </tr>
            </thead>
            <tbody>`;

      let index = 1;
      for (const empId of Object.keys(rawData).sort()) {
        for (const row of rawData[empId]) {
          attendanceData.push({ ...row, index });
          tableHtml += `<tr data-index="${index}">
            <td>${index}</td>
            <td>${row.employee}</td>
            <td>${row.employee_name}</td>
            <td>${row.attendance_date}</td>
            <td>${row.shift}</td>
            <td>${row.custom_log_in_from || ""}</td>
            <td>${row.in_time}</td>
            <td>${row.custom_log_out_from || ""}</td>
            <td>${row.out_time}</td>
          </tr>`;
          index++;
        }
      }
      tableHtml += "</tbody></table></div>";
      $("#attendance-preview").html(tableHtml);
      $("#raw-tab").click();
    } catch (err) {
      frappe.dom.unfreeze();
      frappe.msgprint("❌ Failed to load data");
    }
  });

  // Validation Button
  $(document).on("click", "#validate-btn", () =>
    validateFromTable("#attendance-table tbody tr")
  );

  // Validation Rules
  function validatePresence(row) {
    return !row.in_time || !row.out_time ? { valid: false } : { valid: true };
  }

  function validateDifferentTimes(row) {
    return row.in_time === row.out_time ? { valid: false } : { valid: true };
  }

  function validateRow(row) {
    for (let c of [validatePresence, validateDifferentTimes]) {
      let r = c(row);
      if (!r.valid) return r;
    }
    return { valid: true };
  }

  // Main Validation Function
  function validateFromTable(selector) {
    let invalidRows = [],
      validRows = [];

    $(selector).each(function () {
      const hasInputs = $(this).find("input").length > 0;

      const row = {
        index: $(this).data("index"),
        employee: $(this).find("td:eq(1)").text(),
        employee_name: $(this).find("td:eq(2)").text(),
        attendance_date: $(this).find("td:eq(3)").text(),
        shift: $(this).find("td:eq(4)").text(),
        custom_log_in_from: hasInputs
          ? $(this).find("td:eq(5) input").val()
          : $(this).find("td:eq(5)").text(),
        in_time: hasInputs
          ? $(this).find("td:eq(6) input").val()
          : $(this).find("td:eq(6)").text(),
        custom_log_out_from: hasInputs
          ? $(this).find("td:eq(7) input").val()
          : $(this).find("td:eq(7)").text(),
        out_time: hasInputs
          ? $(this).find("td:eq(8) input").val()
          : $(this).find("td:eq(8)").text(),
      };

      validateRow(row).valid ? validRows.push(row) : invalidRows.push(row);
    });

    // Non-Validated Table
    if (invalidRows.length) {
      let html = `
        <div class="table-container">
          <table class="table table-bordered table-danger">
            <thead>
              <tr>
                <th>Sr. No.</th><th>Employee</th><th>Name</th><th>Date</th><th>Shift</th>
                <th>Log In From</th><th>In Time</th><th>Log Out From</th><th>Out Time</th>
              </tr>
            </thead>
            <tbody>`;

      invalidRows.forEach((r) => {
        html += `<tr data-index="${r.index}">
          <td>${r.index}</td>
          <td>${r.employee}</td>
          <td>${r.employee_name}</td>
          <td>${r.attendance_date}</td>
          <td>${r.shift}</td>
          <td><input type="text" value="${r.custom_log_in_from}" class="form-control log-in-from"></td>
          <td><input type="time" value="${r.in_time}" class="form-control in-time"></td>
          <td><input type="text" value="${r.custom_log_out_from}" class="form-control log-out-from"></td>
          <td><input type="time" value="${r.out_time}" class="form-control out-time"></td>
        </tr>`;
      });

      html += `</tbody></table></div>
      <div class="text-center mt-2">
        <button id="revalidate-btn" class="btn btn-warning">Validate Again</button>
      </div>`;

      $("#non-validated-section").html(html);
    } else {
      $("#non-validated-section").html(
        `<div class="alert alert-success">No invalid rows!</div>`
      );
    }

    // Validated Table
    if (validRows.length) {
      if (!$("#validated-section table").length) {
        $("#validated-section").html(`
          <div class="table-container">
            <table class="table table-bordered table-success">
              <thead>
                <tr>
                  <th>Sr. No.</th><th>Employee</th><th>Name</th><th>Date</th>
                  <th>Shift</th><th>Log In From</th><th>In Time</th>
                  <th>Log Out From</th><th>Out Time</th>
                </tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>`);
      }

      validRows.forEach((r) => {
        if (!validatedRecord[r.employee]) validatedRecord[r.employee] = [];
        validatedRecord[r.employee].push(r);

        $("#validated-section table tbody").append(`
          <tr>
            <td>${r.index}</td><td>${r.employee}</td><td>${r.employee_name}</td>
            <td>${r.attendance_date}</td><td>${r.shift}</td>
            <td>${r.custom_log_in_from}</td><td>${r.in_time}</td>
            <td>${r.custom_log_out_from}</td><td>${r.out_time}</td>
          </tr>`);
      });
    }

    $("#validated-tab").click();
  }

  // Re-Validate Button
  $(document).on("click", "#revalidate-btn", () =>
    validateFromTable("#non-validated-section tbody tr")
  );

  // Download Raw Data
  $("#download-raw-btn").on("click", async () =>
    downloadExcel(rawData, "Raw_Attendance_Sheet.xlsx")
  );

  // Download Validated Data
  $("#download-validated-btn").on("click", async () =>
    downloadExcel(validatedRecord, "Validated_Attendance_Sheet.xlsx")
  );

  // Import Validated Records
  $("#import-validated-btn").on("click", () => {
    frappe.call({
      method:
        "pinnaclehrms.utility.attendance_formatter.create_data_import_for_attendance",
      args: { attendance_data: validatedRecord },
      callback: (r) => {
        if (!r.exc)
          frappe.msgprint(
            `Data Import created: <a href="/app/data-import/${r.message}">${r.message}</a>`
          );
      },
    });
  });

  async function downloadExcel(data, filename) {
    try {
      frappe.dom.freeze("Generating Excel...");
      const formData = new FormData();
      formData.append("logs", JSON.stringify(data));

      const res = await fetch(
        "/api/method/pinnaclehrms.utility.attendance_formatter.download_final_attendance_excel",
        {
          method: "POST",
          headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
          body: formData,
        }
      );

      const contentType = res.headers.get("Content-Type");
      if (contentType && contentType.includes("spreadsheetml")) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);

        frappe.show_alert({
          message: `✅ ${filename} Downloaded`,
          indicator: "green",
        });
      } else {
        frappe.msgprint("❌ " + (await res.text()));
      }
      frappe.dom.unfreeze();
    } catch (err) {
      frappe.dom.unfreeze();
      frappe.msgprint("❌ Error: " + err.message);
    }
  }
};
