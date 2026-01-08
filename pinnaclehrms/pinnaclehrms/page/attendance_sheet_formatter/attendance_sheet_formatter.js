frappe.pages["attendance-sheet-formatter"].on_page_load = function (wrapper) {
  frappe.ui.make_app_page({
    parent: wrapper,
    title: "Attendance Sheet Formatter",
    single_column: true,
  });
};

frappe.pages["attendance-sheet-formatter"].on_page_show = function (wrapper) {
  // ========= GLOBAL DATA STORES ========= //
  let attendanceData = []; // preview rows
  let rawData = {};
  let previewData = {};
  let validatedRecord = {};
  let nonValidatedRecord = [];

  const fileMapping = {
    "zicom-attendance": "pinnacle",
    "essl-attendance": "opticode",
    "mantra-attendance": "mantra",
    "app-attendance": "app",
    "other-attendance": "other",
  };

  // Load XLSX if not present
  if (typeof XLSX === "undefined") {
    const script = document.createElement("script");
    script.src =
      "https://cdn.sheetjs.com/xlsx-latest/package/dist/xlsx.full.min.js";
    script.onload = setupDownloadButton;
    document.head.appendChild(script);
  } else {
    setupDownloadButton();
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

  // Render HTML
  const html = frappe.render_template("attendance_sheet_formatter", {});
  $(wrapper).find(".page-body").html(html);

  // ========== PAYROLL DATE CONTROLS ========== //
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

          let yyyy = lastDay.getFullYear();
          let mm = String(lastDay.getMonth() + 1).padStart(2, "0");
          let dd = String(lastDay.getDate()).padStart(2, "0");
          let formatted = `${yyyy}-${mm}-${dd}`;
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

  // ============== TAB EVENTS ============== //
  $("#raw-sub-tabs .nav-link").on("click", function () {
    const target = $(this).data("target");
    $("#raw-sub-tabs .nav-link").removeClass("active");
    $(this).addClass("active");
    $("#raw-tab-pane .tab-pane").removeClass("show active");
    $(target).addClass("show active");
  });

  $("#attendance-tabs .nav-link").on("click", function () {
    const target = $(this).data("target");
    $("#attendance-tabs .nav-link").removeClass("active");
    $(this).addClass("active");
    $(".tab-pane").removeClass("show active");
    $(target).addClass("show active");
  });

  // ============= LOAD RAW DATA ============= //
  $("#load-raw-data-btn").on("click", async function () {
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

      rawData = {
        pinnacle: data.message.pinnacle_attendance || [],
        opticode: data.message.opticode_attendance || [],
        mantra: data.message.mantra_attendance || [],
        other: data.message.other_attendance || [],
        app: data.message.app_attendance || [],
      };

      renderRawDataByFile(rawData);
      frappe.show_alert("✅ Raw data loaded");
    } catch (err) {
      frappe.dom.unfreeze();
      frappe.msgprint("❌ Failed to load data");
    }
  });

  function renderRawDataByFile(data) {
    for (const tabId in fileMapping) {
      const key = fileMapping[tabId];
      $("#" + tabId).html(generateTableHtml(data[key] || []));
    }
  }

  function generateTableHtml(data) {
    if (!data || !data.length) {
      return `<div class="scrollable-table-container">
                <table class="table table-bordered table-sm mb-0">
                <thead class="table-light">
                <tr><th>Sr. No.</th><th>Employee</th><th>Name</th><th>Date</th><th>Shift</th>
                <th>Log In From</th><th>In</th><th>Log Out From</th><th>Out</th></tr>
                </thead><tbody><tr><td colspan="9" class="text-center text-muted">No records</td></tr></tbody></table></div>`;
    }

    let html = `<div class="scrollable-table-container">
        <table class="table table-bordered table-sm mb-0">
        <thead class="table-light">
        <tr><th>Sr. No.</th><th>Employee/Device</th><th>Name</th><th>Date</th><th>Shift</th>
        <th>Log In</th><th>In</th><th>Log Out</th><th>Out</th></tr></thead><tbody>`;

    data.forEach((row, idx) => {
      html += `<tr>
            <td>${idx + 1}</td>
            <td>${row.employee_id || row.device_id || ""}</td>
            <td>${row.employee_name || ""}</td>
            <td>${row.attendance_date || ""}</td>
            <td>${row.shift || ""}</td>
            <td>${row.device || ""}</td>
            <td>${row.in_time || ""}</td>
            <td>${row.device || ""}</td>
            <td>${row.out_time || ""}</td></tr>`;
    });

    return html + "</tbody></table></div>";
  }

  // ============= PREVIEW ============= //
  $("#generate-preview-btn").on("click", function () {
    if (!rawData || !Object.keys(rawData).length) {
      return frappe.msgprint("Load raw data first.");
    }

    frappe.dom.freeze("Generating Preview...");
    frappe.call({
      method:
        "pinnaclehrms.utility.attendance_formatter.preview_final_attendance_sheet",
      args: { raw_data: rawData },
      callback: function (r) {
        frappe.dom.unfreeze();
        if (!r.message) return frappe.msgprint("❌ Error generating preview");

        previewData = r.message.data;
        attendanceData = [];

        let html = `<table id="attendance-table" class="table table-bordered table-sm">
                <thead><tr>
                <th>Sr.</th><th>Employee</th><th>Name</th><th>Date</th>
                <th>Shift</th><th>Log In</th><th>In</th>
                <th>Log Out</th><th>Out</th></tr></thead><tbody>`;

        let i = 1;
        for (const empId of Object.keys(previewData).sort()) {
          previewData[empId].forEach((row) => {
            attendanceData.push({ ...row, index: i });
            html += `<tr data-index="${i}">
                        <td>${i}</td><td>${row.employee}</td><td>${
              row.employee_name
            }</td>
                        <td>${row.attendance_date}</td><td>${row.shift}</td>
                        <td>${row.custom_log_in_from || ""}</td><td>${
              row.in_time
            }</td>
                        <td>${row.custom_log_out_from || ""}</td><td>${
              row.out_time
            }</td></tr>`;
            i++;
          });
        }
        html += "</tbody></table>";

        $("#attendance-preview").html(html);
        $("#preview-tab").click();
        frappe.show_alert("✅ Preview generated");
      },
    });
  });

  // ============= NEW VALIDATION (BACKEND) ============= //
  $("#validate-btn").on("click", function () {
    if (!attendanceData.length)
      return frappe.msgprint("Generate preview first");

    frappe.dom.freeze("Validating...");
    frappe.call({
      method:
        "pinnaclehrms.utility.attendance_formatter.validate_attendance_data",
      args: { attendance_data: attendanceData },
      callback: function (r) {
        frappe.dom.unfreeze();
        if (!r.message) return frappe.msgprint("Validation failed");

        validatedRecord = r.message.validated || {};
        nonValidatedRecord = r.message.non_validated || [];

        renderValidatedTable();
        renderNonValidatedTable();

        $("#validated-tab").click();

        $("#import-validated-btn").prop(
          "disabled",
          Object.keys(validatedRecord).length === 0
        );

        frappe.show_alert(
          `✅ Validation complete — Valid: ${r.message.total_valid}, Invalid: ${r.message.total_invalid}`
        );
      },
    });
  });

  function renderValidatedTable() {
    let html = `<table class="table table-bordered table-success table-sm">
        <thead><tr><th>#</th><th>Employee</th><th>Name</th><th>Date</th>
        <th>Shift</th><th>Log In</th><th>In</th><th>Log Out</th><th>Out</th></tr></thead><tbody>`;

    let i = 1;
    Object.keys(validatedRecord)
      .sort()
      .forEach((emp) => {
        validatedRecord[emp].forEach((row) => {
          html += `<tr><td>${i++}</td><td>${row.employee}</td><td>${
            row.employee_name
          }</td>
                <td>${row.attendance_date}</td><td>${row.shift}</td>
                <td>${row.custom_log_in_from}</td><td>${row.in_time}</td>
                <td>${row.custom_log_out_from}</td><td>${
            row.out_time
          }</td></tr>`;
        });
      });

    html += "</tbody></table>";
    $("#validated-section").html(html);
  }

  function renderNonValidatedTable() {
    if (!nonValidatedRecord.length) {
      return $("#non-validated-section").html(
        `<div class="alert alert-success mt-3">✅ No invalid rows!</div>`
      );
    }

    let html = `
    <table class="table table-bordered table-danger table-sm">
        <thead>
            <tr>
                <th>#</th>
                <th>Emp</th>
                <th>Name</th>
                <th>Date</th>
                <th>Shift</th>
                <th>In</th>
                <th>Out</th>
                <th>Errors</th>
                <th class="text-center">Skip Validation</th>
            </tr>
        </thead>
        <tbody>
    `;

    nonValidatedRecord.forEach((r, i) => {
      html += `
        <tr data-index="${i}">
            <td>${i + 1}</td>
            <td>${r.employee || ""}</td>
            <td>${r.employee_name || ""}</td>
            <td>${r.attendance_date || ""}</td>
            <td>${r.shift || ""}</td>

            <td>
                <input type="time"
                    value="${r.in_time || ""}"
                    class="form-control form-control-sm in-time" />
            </td>

            <td>
                <input type="time"
                    value="${r.out_time || ""}"
                    class="form-control form-control-sm out-time" />
            </td>

            <td class="text-danger small">
                ${(r.errors || []).join(", ")}
            </td>

            <td class="text-center">
                <input type="checkbox"
                    class="form-check-input skip-validation"
                    ${r.skip_validation ? "checked" : ""} />
            </td>
        </tr>`;
    });

    html += `
        </tbody>
    </table>

    <div class="text-center mt-2">
        <button id="revalidate-btn" class="btn btn-warning">
            Re-Validate
        </button>
    </div>
    `;

    $("#non-validated-section").html(html);
  }

  // ✅ Re-Validate Corrected Invalid Rows
  $(document).on("click", "#revalidate-btn", function () {
    let attendance_data = []; // needs validation
    let corrected_attendance = []; // skip validation → auto-validated

    $("#non-validated-section tbody tr").each(function () {
      const $row = $(this);

      const rowData = {
        employee: $row.find("td:eq(1)").text().trim(),
        employee_name: $row.find("td:eq(2)").text().trim(),
        attendance_date: $row.find("td:eq(3)").text().trim(),
        shift: $row.find("td:eq(4)").text().trim(),

        custom_log_in_from: $row.data("log-in-from") || "Manual",
        custom_log_out_from: $row.data("log-out-from") || "Manual",

        in_time: $row.find("td:eq(5) input").val(),
        out_time: $row.find("td:eq(6) input").val(),
      };

      const skipValidation = $row.find(".skip-validation").is(":checked");

      if (skipValidation) {
        // ✅ Directly move to validated
        corrected_attendance.push(rowData);
      } else {
        // ❌ Needs validation
        attendance_data.push(rowData);
      }
    });

    // ---------------------------------------
    // 1️⃣ Add skipped records directly
    // ---------------------------------------
    corrected_attendance.forEach((r) => {
      if (!validatedRecord[r.employee]) {
        validatedRecord[r.employee] = [];
      }
      validatedRecord[r.employee].push(r);
    });

    // ---------------------------------------
    // 2️⃣ Validate remaining records (if any)
    // ---------------------------------------
    if (!attendance_data.length) {
      nonValidatedRecord = [];
      renderValidatedTable();
      renderNonValidatedTable();
      $("#validated-tab").click();
      $("#import-validated-btn").prop("disabled", false);
      return;
    }

    frappe.call({
      method:
        "pinnaclehrms.utility.attendance_formatter.validate_attendance_data",
      args: {
        attendance_data: attendance_data,
      },
      callback: function (r) {
        // merge validated
        Object.keys(r.message.validated || {}).forEach((emp) => {
          if (!validatedRecord[emp]) validatedRecord[emp] = [];
          validatedRecord[emp] = validatedRecord[emp].concat(
            r.message.validated[emp]
          );
        });

        // update remaining non-validated
        nonValidatedRecord = r.message.non_validated || [];

        renderValidatedTable();
        renderNonValidatedTable();

        $("#validated-tab").click();

        if (nonValidatedRecord.length === 0) {
          $("#import-validated-btn").prop("disabled", false);
        }
      },
    });
  });

  // ============= DOWNLOAD BUTTONS ============= //
  $("#download-preview-btn").on("click", () =>
    downloadExcel(previewData, "Preview_Attendance.xlsx")
  );
  $("#download-validated-btn").on("click", () =>
    downloadExcel(validatedRecord, "Validated_Attendance.xlsx")
  );

  $("#download-raw-excell-btn").on("click", function () {
    const activeSubTab = $("#raw-sub-tabs .nav-link.active").data("target");
    if (!activeSubTab) return frappe.msgprint("No active sub-tab");

    let key = fileMapping[activeSubTab.replace("#", "")];
    let data = rawData[key] || [];
    if (!data.length) return frappe.msgprint("No data to download");

    downloadExcel(data, `${key}_Raw.xlsx`);
  });

  // ============= IMPORT BUTTON ============= //
  $("#import-validated-btn").on("click", function () {
    frappe.call({
      method:
        "pinnaclehrms.utility.attendance_formatter.create_data_import_for_attendance",
      args: { attendance_data: validatedRecord },
      callback: function (r) {
        frappe.msgprint(
          `✅ Data Import created: <a href="/app/data-import/${r.message}">${r.message}</a>`
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
