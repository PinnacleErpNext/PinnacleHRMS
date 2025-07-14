frappe.pages["attendance-sheet-formatter"].on_page_load = function (wrapper) {
  frappe.ui.make_app_page({
    parent: wrapper,
    title: "Attendance Sheet Formatter",
    single_column: true,
  });
};

frappe.pages["attendance-sheet-formatter"].on_page_show = function (wrapper) {
  const html = `
    <div class="mt-2">
      <label>Select Action:</label>
      <select id="action-type" class="form-control">
        <option value="format">Format Attendance Sheet</option>
        <option value="final">Create Final Attendance</option>
      </select>
    </div>

    <div>
      <label>Upload Attendance Files:</label>
      <input type="file" id="excel-upload" accept=".xlsx" />
    </div>

    <div class="mt-2" id="excel-type-container">
      <label>Select Excel Type:</label>
      <select id="excel-type" class="form-control">
        <option value="">Select</option>
        <option value="Pinnacle">Pinnacle</option>
        <option value="Opticode">Opticode</option>
      </select>
    </div>

    <div class="mt-3">
      <button id="preview-btn" class="btn btn-primary">Preview</button>
      <button id="download-btn" class="btn btn-success">Download</button>
    </div>

    <div id="attendance-preview" class="mt-4"></div>
  `;

  $(wrapper).find(".page-body").html(html);

  // 🔁 Switch behavior based on action
  $("#action-type")
    .on("change", function () {
      const selectedAction = $(this).val();

      if (selectedAction === "format") {
        $("#excel-upload").attr("multiple", false);
        $("#excel-type-container").show();
      } else if (selectedAction === "final") {
        $("#excel-upload").attr("multiple", true);
        $("#excel-type-container").hide();
      }
    })
    .trigger("change"); // 👈 trigger once on load

  // 🔍 Preview Button
  $("#preview-btn").on("click", async function () {
    const actionType = $("#action-type").val();
    const files = document.getElementById("excel-upload").files;
    const excelType = $("#excel-type").val();

    if (!files.length) {
      frappe.msgprint("Please upload file(s).");
      return;
    }

    if (actionType === "format") {
      if (!excelType) {
        frappe.msgprint("Please select Excel type.");
        return;
      }

      const formData = new FormData();
      formData.append("file", files[0]);
      formData.append("excel_type", excelType);

      frappe.dom.freeze("Previewing formatted file...");
      const res = await fetch(
        "/api/method/pinnaclehrms.utility.attendance_formatter.upload_excel",
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
    } else if (actionType === "final") {
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append("files[]", files[i]);
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
    }
  });

  // 📥 Download Button
  $("#download-btn").on("click", async function () {
    const actionType = $("#action-type").val();
    const files = document.getElementById("excel-upload").files;
    const excelType = $("#excel-type").val();

    if (!files.length) {
      frappe.msgprint("Please upload file(s).");
      return;
    }

    let endpoint = "";
    let formData = new FormData();

    if (actionType === "format") {
      if (!excelType) {
        frappe.msgprint("Please select Excel type.");
        return;
      }
      formData.append("file", files[0]);
      formData.append("excel_type", excelType);
      endpoint =
        "/api/method/pinnaclehrms.utility.attendance_formatter.download_excel";
    } else {
      for (let i = 0; i < files.length; i++) {
        formData.append("files[]", files[i]);
      }
      endpoint =
        "/api/method/pinnaclehrms.utility.attendance_formatter.download_final_attendance_excel";
    }

    frappe.dom.freeze("Downloading...");
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
      body: formData,
    });

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
      a.download =
        actionType === "final"
          ? "Final_Attendance_Sheet.xlsx"
          : "Formatted_Attendance.xlsx";
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
