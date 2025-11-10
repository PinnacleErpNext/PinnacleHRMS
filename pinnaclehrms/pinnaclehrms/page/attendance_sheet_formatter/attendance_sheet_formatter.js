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
  previewData = {};
  const fileMapping = {
    "zicom-attendance": "pinnacle",
    "essl-attendance": "opticode",
    "mantra-attendance": "mantra",
    "app-attendance": "app",
    "other-attendance": "other",
  };

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

  const html = frappe.render_template("attendance_sheet_formatter", {});

  $(wrapper).find(".page-body").html(html);

  // Create Company Link Field
  // const companyControl = frappe.ui.form.make_control({
  //   df: {
  //     label: "Company",
  //     fieldtype: "Link",
  //     options: "Company",
  //     reqd: 1,
  //     onchange: () => (selectedCompany = companyControl.get_value()),
  //   },
  //   parent: $("#company-link-field"),
  //   render_input: true,
  // });

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
          // Get last day of the month
          let lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);

          // Format as yyyy-mm-dd in local time
          const yyyy = lastDay.getFullYear();
          const mm = String(lastDay.getMonth() + 1).padStart(2, "0");
          const dd = String(lastDay.getDate()).padStart(2, "0");
          const formatted = `${yyyy}-${mm}-${dd}`;
          payrollToField.set_value(formatted);
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

  // Nested Raw Data Tabs
  $("#raw-sub-tabs .nav-link").on("click", function () {
    const target = $(this).data("target");

    // Activate clicked sub-tab
    $("#raw-sub-tabs .nav-link").removeClass("active");
    $(this).addClass("active");

    // Show corresponding table
    $("#raw-tab-pane .tab-pane").removeClass("show active");
    $(target).addClass("show active");
  });

  // Handle Main Tabs
  $("#attendance-tabs .nav-link").on("click", function () {
    const target = $(this).data("target");

    // Activate main tab
    $("#attendance-tabs .nav-link").removeClass("active");
    $(this).addClass("active");

    // Show target tab content
    $(".tab-pane").removeClass("show active");
    $(target).addClass("show active");

    // Reset Raw sub-tabs only if leaving Raw
    if (target !== "#raw-tab-pane") {
      $("#raw-sub-tabs .nav-link").removeClass("active");
      // Do NOT force show a specific raw sub-tab
      $("#raw-tab-pane .tab-pane").removeClass("show active");
    } else {
      // Show the previously active sub-tab or default to first
      const activeSub = $("#raw-sub-tabs .nav-link.active").data("target");
      if (activeSub) {
        $("#raw-tab-pane .tab-pane").removeClass("show active");
        $(activeSub).addClass("show active");
      } else {
        $("#raw-sub-tabs .nav-link").first().addClass("active");
        $("#raw-tab-pane .tab-pane").removeClass("show active");
        $("#raw-tab-pane .tab-pane").first().addClass("show active");
      }
    }
  });

  // function ensureCompanySelected() {
  //   if (!selectedCompany) {
  //     frappe.msgprint("❌ Please select a company.");
  //     return false;
  //   }
  //   return true;
  // }

  // render Raw Data in Tables
  function renderRawDataByFile(rawData) {
    for (const tabId in fileMapping) {
      const key = fileMapping[tabId];
      const data = rawData[key] || [];
      const html = generateTableHtml(data);
      $("#" + tabId).html(html);
    }
  }

  function generateTableHtml(data) {
    if (!data || !data.length) {
      return `
      <div class="scrollable-table-container">
        <table class="table table-bordered table-sm mb-0">
          <thead class="table-light">
            <tr>
              <th>Sr. No.</th>
              <th>Employee</th>
              <th>Name</th>
              <th>Date</th>
              <th>Shift</th>
              <th>Log In From</th>
              <th>In Time</th>
              <th>Log Out From</th>
              <th>Out Time</th>
            </tr>
          </thead>
          <tbody>
            <tr><td colspan="9" class="text-center text-muted">No records yet.</td></tr>
          </tbody>
        </table>
      </div>
    `;
    }

    let html = `
    <div class="scrollable-table-container">
      <table class="table table-bordered table-sm mb-0">
        <thead class="table-light">
          <tr>
            <th>Sr. No.</th>
            <th>Employee/Device Id</th>
            <th>Name</th>
            <th>Date</th>
            <th>Shift</th>
            <th>Log In From</th>
            <th>In Time</th>
            <th>Log Out From</th>
            <th>Out Time</th>
          </tr>
        </thead>
        <tbody>
  `;

    data.forEach((row, index) => {
      html += `
      <tr data-index="${index + 1}">
        <td>${index + 1}</td>
        <td>${row.employee_id || row.device_id || ""}</td>
        <td>${row.employee_name || ""}</td>
        <td>${row.attendance_date || ""}</td>
        <td>${row.shift || ""}</td>
        <td>${row.device || ""}</td>
        <td>${row.in_time || ""}</td>
        <td>${row.device || ""}</td>
        <td>${row.out_time || ""}</td>
      </tr>
    `;
    });

    html += `
        </tbody>
      </table>
    </div>
  `;

    return html;
  }

  // Load Raw Data
  $("#load-raw-data-btn").on("click", async function () {
    // if (!ensureCompanySelected()) return;

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
    // formData.append("company", selectedCompany);
    formData.append("from_date", payrollFrom);
    formData.append("to_date", payrollTo);
    if (pinnacleFile) formData.append("pinnacle_file", pinnacleFile);
    if (opticodeFile) formData.append("opticode_file", opticodeFile);
    if (mantraFile) formData.append("mantra_file", mantraFile);
    if (otherFile) formData.append("other_file", otherFile);

    frappe.dom.freeze("Loading...");
    try {
      const res = await fetch(
        "/api/method/pinnaclehrms.utility.attendance_formatter.load_raw_attendance_data",
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
      console.log(data.message);
      rawData = {
        pinnacle: data.message.pinnacle_attendance || [],
        opticode: data.message.opticode_attendance || [],
        mantra: data.message.mantra_attendance || [],
        other: data.message.other_attendance || [],
        app: data.message.app_attendance || [],
      };
      console.log(rawData);
      renderRawDataByFile(rawData);
    } catch (err) {
      frappe.dom.unfreeze();
      frappe.msgprint("❌ Failed to load data");
    }
  });

  // Generate Preview Button
  $("#generate-preview-btn").on("click", async function () {
    if (!rawData || !Object.keys(rawData).length) {
      return frappe.msgprint("Load raw data first.");
    }

    frappe.dom.freeze("Loading...");
    frappe.call({
      method:
        "pinnaclehrms.utility.attendance_formatter.preview_final_attendance_sheet",
      args: { raw_data: rawData },
      callback: function (data) {
        frappe.dom.unfreeze();

        if (!data.message) {
          return frappe.msgprint("❌ Error loading data");
        }

        previewData = data.message.data;
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
        for (const empId of Object.keys(previewData).sort()) {
          for (const row of previewData[empId]) {
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

        // Switch to Preview tab
        $("#preview-tab").click();
      },
      error: function (err) {
        frappe.dom.unfreeze();
        frappe.msgprint(
          "❌ Failed to load data: " + (err?.message || "Unknown error")
        );
      },
    });
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
  $("#download-preview-btn").on("click", async () =>
    downloadExcel(previewData, "Preview_Attendance_Sheet.xlsx")
  );

  // Download Validated Data
  $("#download-validated-btn").on("click", async () =>
    downloadExcel(validatedRecord, "Validated_Attendance_Sheet.xlsx")
  );

  $("#download-raw-excell-btn").on("click", function () {
    // Find active sub-tab inside Raw tab
    const activeSubTab = $("#raw-sub-tabs .nav-link.active").data("target");

    if (!activeSubTab) {
      frappe.msgprint("No active sub-tab found.");
      return;
    }

    dataSet = fileMapping[activeSubTab.replace("#", "")];
    data = rawData[dataSet] || [];
    console.log(data);
    if (!data || !data.length) {
      frappe.msgprint("No data available to download.");
      return;
    }

    // Call your existing function to download table
    // Pass the table element or id as argument
    downloadExcel(data, `${dataSet}_Raw_Attendance_Sheet.xlsx`);
  });

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
