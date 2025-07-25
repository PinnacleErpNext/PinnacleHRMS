frappe.pages["attendance-sheet-formatter"].on_page_load = function (wrapper) {
  frappe.ui.make_app_page({
    parent: wrapper,
    title: "Attendance Sheet Formatter",
    single_column: true,
  });
};

frappe.pages["attendance-sheet-formatter"].on_page_show = function (wrapper) {
  const html = `
    <div>
      <label>Upload Pinnacle Attendance File:</label>
      <input type="file" id="pinnacle-excel-upload" accept=".xlsx" />
      <br/>
      <label>Upload Opticode Attendance File:</label>
      <input type="file" id="opticode-excel-upload" accept=".xlsx" />
    </div>

    <div class="mt-3">
      <button id="preview-btn" class="btn btn-primary">Preview</button>
      <button id="download-btn" class="btn btn-success">Download</button>
    </div>

    <div id="attendance-preview" class="mt-4"></div>
  `;

  $(wrapper).find(".page-body").html(html);

  // 🔍 Preview Button
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
    if (pinnacleFile) {
      formData.append("pinnacle_file", pinnacleFile);
    }
    if (opticodeFile) {
      formData.append("opticode_file", opticodeFile);
    }

    frappe.dom.freeze("Generating preview...");
    const res = await fetch(
      "/api/method/pinnaclehrms.utility.attendance_formatter.preview_final_attendance_sheet",
      {
        method: "POST",
        headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
        body: formData,
      }
    );
    frappe.dom.unfreeze();

    const result = await res.text();
    if (res.ok) {
      $("#attendance-preview").html(result);
    } else {
      frappe.msgprint("❌ " + result);
    }
  });

  // 📥 Download Button
  $("#download-btn").on("click", async function () {
    const pinnacleFile = document.getElementById("pinnacle-excel-upload")
      .files[0];
    const opticodeFile = document.getElementById("opticode-excel-upload")
      .files[0];

    if (!pinnacleFile && !opticodeFile) {
      frappe.msgprint("Please upload at least one file.");
      return;
    }

    const formData = new FormData();
    if (pinnacleFile) {
      formData.append("pinnacle_file", pinnacleFile);
    }
    if (opticodeFile) {
      formData.append("opticode_file", opticodeFile);
    }

    frappe.dom.freeze("Downloading...");
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
      a.download = "Final_Attendance_Sheet.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      frappe.dom.unfreeze();
      frappe.show_alert({
        message: "✅ Downloaded successfully",
        indicator: "green",
      });
    } else {
      const errorText = await res.text();
      frappe.dom.unfreeze();
      frappe.msgprint("❌ " + errorText);
    }
  });
};
