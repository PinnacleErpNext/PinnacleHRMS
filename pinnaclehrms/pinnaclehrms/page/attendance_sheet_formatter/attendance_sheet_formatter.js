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

  const html = `
    <div style="font-family: Inter; line-height: 1.8; display: flex; flex-direction: column; height: 100vh;">

      <!-- Sticky Controls -->
      <div style="position: sticky; top: 0; background: #fff; z-index: 1000; padding-bottom: 10px; border-bottom: 1px solid #ddd;">
        <div>
          <label>1. Upload Zaicom Attendance File:</label>
          <input type="file" id="pinnacle-excel-upload" accept=".xlsx" />
        </div>
        <div>
          <label>2. Upload ESSL Attendance File:</label>
          <input type="file" id="opticode-excel-upload" accept=".xlsx" />
        </div>
        <div>
          <button id="preview-btn" class="btn btn-light">Load Raw Data</button>
        </div>

        <!-- Action Buttons -->
        <div class="mt-3 text-center">
          <button id="validate-btn" class="btn btn-warning mx-2">Validate</button>
          <button id="download-raw-btn" class="btn btn-info mx-2">Download Raw Data</button>
          <button id="download-validated-btn" class="btn btn-success mx-2">Download Validated Data</button>
          <button id="import-validated-btn" class="btn btn-primary mx-2">Import Validated Records</button>
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

      <!-- Scrollable Tab Contents -->
      <div class="tab-content mt-3" style="flex: 1; overflow-y: auto; padding: 10px;">
      <!-- Raw Data Tab -->
      <div class="tab-pane fade show active" id="raw-tab-pane" role="tabpanel">
        <div id="attendance-preview" style="overflow-y: auto; max-height: 70vh;">
          <div class="alert alert-info text-center shadow-sm rounded">
            <i class="bi bi-upload"></i> Upload files and click 
            <strong>"Load Raw Data"</strong> to preview attendance records here.
          </div>
        </div>
      </div>

      <!-- Non-Validated Tab -->
      <div class="tab-pane fade" id="non-validated-tab-pane" role="tabpanel">
        <div style="max-height: 70vh; overflow-y: auto;">
          <div id="non-validated-section">
            <div class="alert alert-warning text-center shadow-sm rounded">
              <i class="bi bi-exclamation-triangle"></i> 
              No records to validate yet. Click <strong>"Validate"</strong> to start.
            </div>
          </div>
        </div>
      </div>

      <!-- Validated Tab -->
      <div class="tab-pane fade" id="validated-tab-pane" role="tabpanel">
        <div style="max-height: 70vh; overflow-y: auto;">
          <div id="validated-section">
            <div class="alert alert-success text-center shadow-sm rounded">
              <i class="bi bi-check-circle"></i> 
              No validated records yet. Valid records will appear here after validation.
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <style>
      /* Sticky Table Header */
      #attendance-table thead th,
      #non-validated-section table thead th,
      #validated-section table thead th {
        position: sticky;
        top: 0;
        background: #f8f9fa;
        z-index: 10;
      }
    </style>
  `;

  $(wrapper).find(".page-body").html(html);

  // 🔀 Handle Tab Switching manually
  $(document).on("click", "#attendance-tabs .nav-link", function (e) {
    e.preventDefault();
    $("#attendance-tabs .nav-link").removeClass("active");
    $(".tab-pane").removeClass("show active");
    $(this).addClass("active");
    const target = $(this).data("target");
    $(target).addClass("show active");
  });

  // 🔍 Load Raw Data
  $("#preview-btn").on("click", async function () {
    const pinnacleFile = document.getElementById("pinnacle-excel-upload")
      .files[0];
    const opticodeFile = document.getElementById("opticode-excel-upload")
      .files[0];

    if (!pinnacleFile && !opticodeFile) {
      frappe.msgprint("Please upload at least one file.");
      return;
    }

    const formData = new FormData();
    if (pinnacleFile) formData.append("pinnacle_file", pinnacleFile);
    if (opticodeFile) formData.append("opticode_file", opticodeFile);

    frappe.dom.freeze("Loading raw data...");
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
      if (!res.ok || !data.message) {
        frappe.msgprint("❌ Error loading data");
        return;
      }

      attendanceData = [];
      rawData = data.message;

      let tableHtml = `
        <table id="attendance-table" class="table table-bordered table-sm">
          <thead>
            <tr>
              <th>Sr. No.</th>
              <th>Employee</th>
              <th>Employee Name</th>
              <th>Attendance Date</th>
              <th>Shift</th>
              <th>Log In From</th>
              <th>In Time</th>
              <th>Log Out From</th>
              <th>Out Time</th>
            </tr>
          </thead>
          <tbody>
      `;

      let index = 1;
      const sortedKeys = Object.keys(data.message).sort();
      for (const empId of sortedKeys) {
        const rows = data.message[empId];
        for (const row of rows) {
          attendanceData.push({ ...row, index });
          tableHtml += `
            <tr data-index="${index}">
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

      tableHtml += "</tbody></table>";
      $("#attendance-preview").html(tableHtml);
      // $("#non-validated-section").empty();
      // $("#validated-section").empty();

      $("#raw-tab").click();
    } catch (err) {
      frappe.dom.unfreeze();
      console.error(err);
      frappe.msgprint("❌ Failed to load data");
    }
  });

  // ✅ Validate Button (from Raw Data)
  $(document).on("click", "#validate-btn", function () {
    validateFromTable("#attendance-table tbody tr");
  });

  // 📥 Download Raw Data
  $(document)
    .off("click", "#download-raw-btn")
    .on("click", "#download-raw-btn", async function () {
      try {
        frappe.dom.freeze("Generating Raw Attendance Excel...");
        const formData = new FormData();
        formData.append("logs", JSON.stringify(rawData));

        const res = await fetch(
          "/api/method/pinnaclehrms.utility.attendance_formatter.download_final_attendance_excel",
          {
            method: "POST",
            headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
            body: formData,
          }
        );

        const contentType = res.headers.get("Content-Type");
        if (
          contentType &&
          contentType.includes(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          )
        ) {
          const blob = await res.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = "Raw_Attendance_Sheet.xlsx";
          document.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);
          frappe.show_alert({
            message: "✅ Raw Data Downloaded successfully",
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
    });

  // 📥 Download Validated Data
  $(document)
    .off("click", "#download-validated-btn")
    .on("click", "#download-validated-btn", async function () {
      try {
        frappe.dom.freeze("Generating Validated Attendance Excel...");
        const formData = new FormData();
        formData.append("logs", JSON.stringify(validatedRecord));

        const res = await fetch(
          "/api/method/pinnaclehrms.utility.attendance_formatter.download_final_attendance_excel",
          {
            method: "POST",
            headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
            body: formData,
          }
        );

        const contentType = res.headers.get("Content-Type");
        if (
          contentType &&
          contentType.includes(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          )
        ) {
          const blob = await res.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = "Validated_Attendance_Sheet.xlsx";
          document.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);
          frappe.show_alert({
            message: "✅ Validated Data Downloaded successfully",
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
    });

  // 📥 Import Validated Data
  $(wrapper).on("click", "#import-validated-btn", function () {
    frappe.call({
      method:
        "pinnaclehrms.utility.attendance_formatter.create_data_import_for_attendance",
      args: { attendance_data: validatedRecord },
      callback: function (r) {
        if (!r.exc) {
          frappe.msgprint({
            title: "Success",
            message: `Data Import created: <a href="/app/data-import/${r.message}">${r.message}</a>`,
            indicator: "green",
          });
        }
      },
    });
  });

  function validatePresence(row) {
    if (!row.inTime || !row.outTime) {
      return {
        valid: false,
        message: `❌ Row ${row.index}: Missing In/Out time`,
      };
    }
    return { valid: true };
  }
  // 🔁 Validate Again Button (from Non-Validated tab)
  $(document).on("click", "#revalidate-btn", function () {
    validateFromTable("#non-validated-section tbody tr");
  });

  // 📌 Common validation logic
  function validateFromTable(selector) {
    let invalidRows = [];
    let validRows = [];

    $(selector).each(function () {
      const rowIndex = $(this).data("index");
      const row = {
        index: rowIndex,
        employee:
          $(this).find("td:eq(1)").text().trim() ||
          $(this).find("input").eq(0).val(),
        empName: $(this).find("td:eq(2)").text().trim(),
        date: $(this).find("td:eq(3)").text().trim(),
        shift: $(this).find("td:eq(4)").text().trim(),
        logInFrom:
          $(this).find(".log-in-from").val() ||
          $(this).find("td:eq(5)").text().trim(),
        inTime:
          $(this).find(".in-time").val() ||
          $(this).find("td:eq(6)").text().trim(),
        logOutFrom:
          $(this).find(".log-out-from").val() ||
          $(this).find("td:eq(7)").text().trim(),
        outTime:
          $(this).find(".out-time").val() ||
          $(this).find("td:eq(8)").text().trim(),
      };

      const result = validateRow(row);

      if (!result.valid) {
        invalidRows.push(row);
      } else {
        validRows.push(row);
        if (selector === "#non-validated-section tbody tr") {
          frappe.show_alert({
            message: `✅ Row ${row.index}:${row.empName} validated successfully`,
            indicator: "green",
          });
        }
      }
    });

    // 🔴 Non-Validated Section
    if (invalidRows.length) {
      let invalidHtml = `<table class="table table-bordered table-danger">
      <thead>
        <tr><th>Sr. No.</th><th>Employee</th><th>Employee Name</th><th>Date</th>
        <th>Shift</th><th>Log In From</th><th>In Time</th>
        <th>Log Out From</th><th>Out Time</th></tr>
      </thead><tbody>`;

      invalidRows.forEach((r) => {
        invalidHtml += `<tr data-index="${r.index}">
          <td>${r.index}</td><td>${r.employee}</td><td>${r.empName}</td>
          <td>${r.date}</td><td>${r.shift}</td>
          <td><input type="text" class="form-control log-in-from" value="${
            r.logInFrom || ""
          }"></td>
          <td><input type="time" class="form-control in-time" value="${
            r.inTime || ""
          }"></td>
          <td><input type="text" class="form-control log-out-from" value="${
            r.logOutFrom || ""
          }"></td>
          <td><input type="time" class="form-control out-time" value="${
            r.outTime || ""
          }"></td>
        </tr>`;
      });

      invalidHtml += "</tbody></table>";
      invalidHtml += `<div class="mt-3 text-center">
            <button id="revalidate-btn" class="btn btn-warning">Validate Again</button>
          </div>`;
      $("#non-validated-section").html(invalidHtml);
    } else {
      $("#non-validated-section").html(
        `<div class="alert alert-success">✅ No invalid rows!</div>`
      );
    }

    // ✅ Validated Section
    if (validRows.length) {
      let validHtml = ``;

      validRows.forEach((r) => {
        if (!validatedRecord[r.employee]) {
          validatedRecord[r.employee] = [];
        }

        validatedRecord[r.employee].push({
          employee: r.employee,
          employee_name: r.empName,
          attendance_date: r.date,
          shift: r.shift,
          custom_log_in_from: r.logInFrom,
          in_time: r.inTime,
          custom_log_out_from: r.logOutFrom,
          out_time: r.outTime,
          index: r.index,
        });

        validHtml += `<tr>
          <td>${r.index}</td><td>${r.employee}</td><td>${r.empName}</td>
          <td>${r.date}</td><td>${r.shift}</td>
          <td>${r.logInFrom}</td><td>${r.inTime}</td>
          <td>${r.logOutFrom}</td><td>${r.outTime}</td>
        </tr>`;
      });

      if ($("#validated-section table").length) {
        $("#validated-section table tbody").append(validHtml);
      } else {
        validHtml =
          `<table class="table table-bordered table-success">
          <thead><tr><th>Sr. No.</th><th>Employee</th><th>Employee Name</th>
          <th>Date</th><th>Shift</th><th>Log In From</th><th>In Time</th>
          <th>Log Out From</th><th>Out Time</th></tr></thead><tbody>` +
          validHtml +
          "</tbody></table>";
        $("#validated-section").html(validHtml);
      }
    }

    $("#validated-tab").click();
  }

  function validateDifferentTimes(row) {
    if (row.inTime === row.outTime) {
      return {
        valid: false,
        message: `❌ Row ${row.index}: In-Time and Out-Time are same`,
      };
    }
    return { valid: true };
  }

  function validateRow(row) {
    const checks = [validatePresence, validateDifferentTimes];

    for (let check of checks) {
      const result = check(row);
      if (!result.valid) {
        return result;
      }
    }

    return { valid: true };
  }
};
