frappe.pages["recurring-salary-com"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Recurring Salary Components Tool",
    single_column: true,
  });

  // Hide default page title to prevent duplicate heading
  $(page.page).find(".title-area").hide();

  // -------------------- Enhanced UI --------------------
  $(`
  <!-- Employee Selection Section -->
  <div class="card shadow-sm p-4 mb-4 rounded-lg bg-light border">
    <h5 class="mb-3">
      <i class="fa fa-user"></i> Select Employee
    </h5>

    <div class="row align-items-center">
      <!-- Employee Field -->
      <div class="col-md-4 mb-3">
        <div id="employee-field" class="fw-bold"></div>
      </div>

      <!-- Employee Details -->
      <div id="employee-details" class="col-md-8" style="display: none;">
        <div class="row g-3">
          <div class="col-md-4">
            <label class="form-label text-muted small">Name</label>
            <div id="emp_name" class="fw-semibold text-dark"></div>
          </div>
          <div class="col-md-4">
            <label class="form-label text-muted small">Company</label>
            <div id="emp_company" class="fw-semibold text-dark"></div>
          </div>
          <div class="col-md-4">
            <label class="form-label text-muted small">Department</label>
            <div id="emp_department" class="fw-semibold text-dark"></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Salary Component Table -->
  <div id="salary-component-table" class="card shadow-sm p-4 mb-4 rounded-lg border" style="display:none; height: auto;">
    <h5 class="mb-3"><i class="fa fa-money-bill"></i> Salary Component Details</h5>
    
    <div class="table-responsive position-relative">
      <table class="table table-bordered align-middle">
        <thead class="custom-table-header sticky-top">
          <tr>
            <th>Salary Component</th>
            <th>Component Type</th>
            <th>Amount</th>
            <th>Number of Months</th>
            <th>Start Date</th>
          </tr>
        </thead>
        <tbody id="salary-component-rows">
          <tr>
            <td class="salary-component position-relative"></td>
            <td class="component-type"></td>
            <td class="total-amount"></td>
            <td class="months"></td>
            <td class="start-date"></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="mt-3 text-end">
      <button class="btn btn-sm btn-info" id="preview-components">
        <i class="fa fa-eye"></i> Preview
      </button>
    </div>
  </div>

  <!-- Preview Table Section -->
  <div id="preview-table-section" class="card shadow-sm p-4 rounded-lg border" style="display:none; position: relative;">
    <h5 class="mb-3"><i class="fa fa-table"></i> Preview Distribution</h5>

    <!-- Scrollable Table with Fixed Header -->
    <div class="table-container" style="max-height: 500px; overflow-y: auto;">
      <table class="table table-hover table-bordered mb-0">
        <thead class="custom-table-header sticky-top" style="top: 0; z-index: 10;">
          <tr>
            <th>Month</th>
            <th>Amount</th>
            <th>Status</th>
            <th>Override</th>
          </tr>
        </thead>
        <tbody id="preview-rows"></tbody>
      </table>
    </div>

    <!-- Save Button at Bottom Right -->
    <div class="mt-3 text-end">
      <button class="btn btn-sm btn-success" id="save-components">
        <i class="fa fa-save"></i> Save Components
      </button>
    </div>
  </div>

  <style>
    /* Table Header Styling */
    .custom-table-header th {
      background-color: #dee2e6 !important; /* Darker grey header */
      color: #000;
      font-weight: 600;
    }

    /* Table rows clean white, no alternate striping */
    .table-hover tbody tr {
      background: #fff;
    }

    /* Ensure dropdowns are visible */
    .card,
    .table-responsive,
    td,
    .salary-component {
      overflow: visible !important;
    }

    .dropdown-menu {
      position: absolute !important;
      z-index: 1055 !important;
      max-height: 250px;
      overflow-y: auto;
    }

    /* Fixed header inside scroll */
    .table-container {
      max-height: 300px;
      overflow-y: auto;
    }

    .table-container thead th {
      position: sticky;
      top: 0;
      background: #dee2e6;
      z-index: 10;
    }

    /* Save button position */
    #save-components {
      position: relative;
      bottom: 0;
      right: 0;
    }
  </style>
`).appendTo(page.body);

  // -------------------- Employee Field --------------------
  const employeeField = frappe.ui.form.make_control({
    df: {
      label: "Employee",
      fieldname: "employee",
      fieldtype: "Link",
      options: "Employee",
      reqd: 1,
      change: function () {
        const empId = employeeField.get_value();

        if (empId) {
          frappe.db.get_doc("Employee", empId).then((emp) => {
            $("#emp_name").text(emp.employee_name || "N/A");
            $("#emp_company").text(emp.company || "N/A");
            $("#emp_department").text(emp.department || "N/A");

            if (emp.employee_name || emp.company || emp.department) {
              $("#employee-details").fadeIn();
              $("#salary-component-table").fadeIn();
            }
          });
        } else {
          $("#emp_name, #emp_company, #emp_department").text("");
          $("#employee-details, #salary-component-table").hide();
        }
      },
    },
    parent: $("#employee-field")[0],
    render_input: true,
  });

  // -------------------- Helper Functions --------------------
  function clearPreview() {
    $("#preview-rows").empty();
    $("#preview-table-section").hide();
  }

  function formatStatusBadge(status) {
    const colorClass = status === "Existing" ? "badge-danger" : "badge-success";
    return `<span class="badge ${colorClass}">${status}</span>`;
  }

  // -------------------- Row Controls --------------------
  function createRowControls(row) {
    const compType = frappe.ui.form.make_control({
      df: { fieldtype: "Data", read_only: 1, placeholder: "Component Type" },
      parent: row.find(".component-type")[0],
      render_input: true,
    });

    const salaryComp = frappe.ui.form.make_control({
      df: {
        fieldtype: "Link",
        options: "Salary Component",
        placeholder: "Select Salary Component",
        change: function () {
          const compName = salaryComp.get_value();
          if (compName) {
            frappe.db
              .get_value("Salary Component", compName, "type")
              .then((r) => {
                compType.set_value(r.message?.type || "");
                clearPreview();
              });
          } else {
            compType.set_value("");
            clearPreview();
          }
        },
      },
      parent: row.find(".salary-component")[0],
      render_input: true,
    });

    frappe.ui.form.make_control({
      df: {
        fieldtype: "Currency",
        placeholder: "Enter Total Amount",
        change: clearPreview,
      },
      parent: row.find(".total-amount")[0],
      render_input: true,
    });

    frappe.ui.form.make_control({
      df: {
        fieldtype: "Int",
        placeholder: "Enter Number of Months",
        change: clearPreview,
      },
      parent: row.find(".months")[0],
      render_input: true,
    });

    frappe.ui.form.make_control({
      df: {
        fieldtype: "Date",
        placeholder: "Select Start Date",
        change: clearPreview,
      },
      parent: row.find(".start-date")[0],
      render_input: true,
    });
  }

  createRowControls($("#salary-component-rows tr").first());

  // -------------------- Generate Preview --------------------
  function generatePreview() {
    $("#preview-rows").empty();

    const empId = employeeField.get_value();
    const salaryComp = $(
      "#salary-component-rows .salary-component input"
    ).val();
    const totalAmount =
      parseFloat(
        $("#salary-component-rows .total-amount input").val()?.replace(/,/g, "")
      ) || 0;
    const numMonths =
      parseInt($("#salary-component-rows .months input").val()) || 0;
    let startDate = $("#salary-component-rows .start-date input").val();

    if (!empId || !salaryComp || !totalAmount || !numMonths || !startDate) {
      frappe.msgprint(
        "Please fill Employee, Salary Component, Total Amount, Number of Months, and Start Date before preview."
      );
      return;
    }

    if (startDate.includes("-")) {
      const parts = startDate.split("-");
      if (parts[0].length === 2)
        startDate = `${parts[2]}-${parts[1]}-${parts[0]}`;
    }

    frappe.call({
      method:
        "pinnaclehrms.pinnaclehrms.doctype.recurring_salary_component.recurring_salary_component.get_existing_records",
      args: {
        employee: empId,
        salary_component: salaryComp,
        start_date: startDate,
        num_months: numMonths,
      },
      callback: function (res) {
        const existingMonths = res.message || [];

        for (let i = 0; i < numMonths; i++) {
          const nextDateStr = frappe.datetime.add_months(startDate, i);
          const nextDate = new Date(nextDateStr);

          const monthName = nextDate.toLocaleString("default", {
            month: "long",
          });
          const year = nextDate.getFullYear();

          const periodLabel = `${monthName}-${year}`;

          const status = existingMonths.includes(periodLabel)
            ? "Existing"
            : "New";
          const isDisabled = status === "New" ? "disabled" : "";

          const rowHtml = `
                <tr>
                  <td>${periodLabel}</td>
                  <td><input type="number" value="${totalAmount}" class="amount-input form-control form-control-sm" /></td>
                  <td>${formatStatusBadge(status)}</td>
                  <td class="text-center">
                    <input type="checkbox" class="form-check-input override-checkbox" ${isDisabled} />
                  </td>
                </tr>
              `;

          $("#preview-rows").append(rowHtml);
        }

        $("#preview-table-section").fadeIn();
      },
    });
  }

  $("#preview-components").on("click", generatePreview);

  // -------------------- Save Components --------------------
  $("#save-components").on("click", function () {
    const empId = employeeField.get_value();
    if (!empId) {
      frappe.msgprint("Please select an Employee first.");
      return;
    }

    const salaryComp = $(
      "#salary-component-rows .salary-component input"
    ).val();
    const compType = $("#salary-component-rows .component-type input").val();
    const totalAmount = $("#salary-component-rows .total-amount input").val();
    const numMonths = $("#salary-component-rows .months input").val();
    const startDate = $("#salary-component-rows .start-date input").val();

    if (!salaryComp || !totalAmount || !numMonths || !startDate) {
      frappe.msgprint(
        "Please fill all Salary Component details before saving."
      );
      return;
    }

    const previewData = [];
    $("#preview-rows tr").each(function () {
      const monthLabel = $(this).find("td:first").text();
      const amount = parseFloat($(this).find("input.amount-input").val()) || 0;
      const status = $(this).find("td:eq(2)").text().trim();
      const overrideChecked = $(this).find(".override-checkbox").is(":checked");

      if (status === "New" || (status === "Existing" && overrideChecked)) {
        previewData.push({
          month: monthLabel,
          amount: amount,
          override: status === "Existing" && overrideChecked,
        });
      }
    });

    if (previewData.length === 0) {
      frappe.msgprint("No new or overridden records to create.");
      return;
    }

    const payload = {
      employee: empId,
      salary_component: salaryComp,
      component_type: compType,
      total_amount: totalAmount,
      number_of_months: numMonths,
      start_date: startDate,
      schedule: previewData,
    };

    frappe.call({
      method:
        "pinnaclehrms.pinnaclehrms.doctype.recurring_salary_component.recurring_salary_component.create_rsc",
      args: { data: JSON.stringify(payload) },
      callback: function (res) {
        if (!res.exc) {
          const created =
            (res.message.message && res.message.message.created) || [];

          if (created.length) {
            created.forEach((name) => {
              const link = `<a href="/app/recurring-salary-component/${name}" target="_blank">${name}</a>`;
              frappe.show_alert(
                {
                  message: `Recurring Salary Component Created: ${link}`,
                  indicator: "green",
                },
                10
              );
            });
          }

          frappe.msgprint(
            `Recurring Salary Components saved successfully! Total created: ${created.length}`
          );
        }
      },
    });
  });
};
