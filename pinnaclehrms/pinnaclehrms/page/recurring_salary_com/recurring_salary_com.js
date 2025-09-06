frappe.pages["recurring-salary-com"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Recurring Salary Components Tool",
    single_column: true,
  });

  // -------------------- UI HTML --------------------
  $(`
    <div class="employee-section" style="display: flex; align-items: center; gap: 24px; flex-wrap: wrap; margin-bottom: 20px;">
        <div id="employee-field" style="min-width: 260px;"></div>

        <!-- Hidden initially -->
        <div id="employee-details" class="d-flex align-items-center" style="gap: 16px; display: none;">
            <div><strong>Name:</strong> <span id="emp_name"></span></div>
            <div><strong>Company:</strong> <span id="emp_company"></span></div>
            <div><strong>Department:</strong> <span id="emp_department"></span></div>
        </div>
    </div>

    <!-- Salary Component Table -->
    <div id="salary-component-table" style="margin-top: 20px; display:none;">
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>Salary Component</th>
                    <th>Component Type</th>
                    <th>Total Amount</th>
                    <th>Number of Months</th>
                    <th>Start Date</th>
                </tr>
            </thead>
            <tbody id="salary-component-rows">
                <tr>
                    <td class="salary-component"></td>
                    <td class="component-type"></td>
                    <td class="total-amount"></td>
                    <td class="months"></td>
                    <td class="start-date"></td>
                </tr>
            </tbody>
        </table>
        <div style="margin-top:10px;">
          <button class="btn btn-sm btn-info" id="preview-components">Preview</button>
        </div>
    </div>

    <!-- Preview Table -->
    <div id="preview-table-section" style="margin-top: 30px; display:none;">
        <h5>Preview Distribution</h5>
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>Month</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody id="preview-rows"></tbody>
        </table>
        <button class="btn btn-sm btn-success" id="save-components" style="margin-left:10px;">Save Components</button>
    </div>
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
            $("#emp_name").text(emp.employee_name || "");
            $("#emp_company").text(emp.company || "");
            $("#emp_department").text(emp.department || "");

            if (emp.employee_name || emp.company || emp.department) {
              $("#employee-details").show();
              $("#salary-component-table").show();
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

  // Clear Preview on any value change
  function clearPreview() {
    $("#preview-rows").empty();
    $("#preview-table-section").hide();
  }

  // -------------------- Row Controls --------------------
  function createRowControls(row) {
    // Component Type (auto-filled, read-only)
    const compType = frappe.ui.form.make_control({
      df: {
        fieldtype: "Data",
        read_only: 1,
        placeholder: "Component Type",
      },
      parent: row.find(".component-type")[0],
      render_input: true,
    });

    // Salary Component (Link)
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

    // Total Amount
    frappe.ui.form.make_control({
      df: {
        fieldtype: "Currency",
        placeholder: "Enter Total Amount",
        change: clearPreview,
      },
      parent: row.find(".total-amount")[0],
      render_input: true,
    });

    // Number of Months
    frappe.ui.form.make_control({
      df: {
        fieldtype: "Int",
        placeholder: "Enter Number of Months",
        change: clearPreview,
      },
      parent: row.find(".months")[0],
      render_input: true,
    });

    // Start Date
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

  // Initialize first row
  createRowControls($("#salary-component-rows tr").first());

  // -------------------- Generate Preview --------------------
  function generatePreview() {
    $("#preview-rows").empty();

    const totalAmount =
      parseFloat(
        $("#salary-component-rows .total-amount input").val()?.replace(/,/g, "")
      ) || 0;
    const numMonths =
      parseInt($("#salary-component-rows .months input").val()) || 0;
    let startDate = $("#salary-component-rows .start-date input").val();

    if (!totalAmount || !numMonths || !startDate) {
      frappe.msgprint(
        "Please fill Total Amount, Number of Months, and Start Date before preview."
      );
      return;
    }

    // Convert DD-MM-YYYY → YYYY-MM-DD if needed
    if (startDate.includes("-")) {
      const parts = startDate.split("-");
      if (parts[0].length === 2) {
        startDate = `${parts[2]}-${parts[1]}-${parts[0]}`;
      }
    }

    const start = new Date(startDate);
    if (isNaN(start.getTime())) {
      frappe.msgprint("Invalid Start Date");
      return;
    }

    // Divide equally for preview
    for (let i = 0; i < numMonths; i++) {
      const nextDate = new Date(start.getFullYear(), start.getMonth() + i, 1);
      const monthName = nextDate.toLocaleString("default", { month: "long" });
      const year = nextDate.getFullYear();

      const rowHtml = `
        <tr>
          <td>${monthName}-${year}</td>
          <td>
            <input type="number" value="${totalAmount}" class="amount-input" 
              style="width:100%; border:none; outline:none; text-align:left;" />
          </td>
        </tr>
      `;
      $("#preview-rows").append(rowHtml);
    }

    $("#preview-table-section").show();
  }

  // Preview Button
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

    // Extract data from Preview Table
    const previewData = [];
    $("#preview-rows tr").each(function () {
      const monthLabel = $(this).find("td:first").text();
      const amount = parseFloat($(this).find("input.amount-input").val()) || 0;

      previewData.push({
        month: monthLabel,
        amount: amount,
      });
    });

    // Final payload
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
         

          // Extract created array safely
          const created = (res.message && res.message.message.created) || [];

          if (created.length) {
            created.forEach((name) => {
              const link = `<a href="/app/recurring-salary-component/${name}" target="_blank">${name}</a>`;
              frappe.show_alert(
                {
                  message: __("Recurring Salary Component Created: {0}", [
                    link,
                  ]),
                  indicator: "green",
                },
                10
              );
            });
          }

          frappe.msgprint(
            __(
              "Recurring Salary Components saved successfully! Total created: {0}",
              [created.length]
            )
          );
        }
      },
    });
  });
};
