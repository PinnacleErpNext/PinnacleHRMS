frappe.pages["recurring-salary-com"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Recurring Salary Components Tool",
    single_column: true,
  });

  // Render HTML structure
  $(`
    <div class="employee-section" style="display: flex; align-items: center; gap: 24px; flex-wrap: wrap; margin-bottom: 20px;">
        <div id="employee-field" style="min-width: 260px;"></div>

        <!-- Hidden initially -->
        <div id="employee-details" class="d-flex align-items-center" style="gap: 16px; display: none;">
            <div id="emp_name_block"><strong>Name:</strong> <span id="emp_name"></span></div>
            <div id="emp_company_block"><strong>Company:</strong> <span id="emp_company"></span></div>
            <div id="emp_department_block"><strong>Department:</strong> <span id="emp_department"></span></div>
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
          <button class="btn btn-sm btn-success" id="save-components" style="margin-left:10px;">Save Components</button>
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
    </div>
  `).appendTo(page.body);

  // Employee Link field
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
          $("#emp_name").text("");
          $("#emp_company").text("");
          $("#emp_department").text("");
          $("#employee-details").hide();
          $("#salary-component-table").hide();
        }
      },
    },
    parent: $("#employee-field")[0],
    render_input: true,
  });

  // --------- Clear Preview if any value changes ----------
  function clearPreview() {
    $("#preview-rows").empty();
    $("#preview-table-section").hide();
  }

  // Function to create row controls
  function createRowControls(row) {
    // Component Type (auto-filled, read-only Data)
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

    // Total Amount (Currency field)
    frappe.ui.form.make_control({
      df: {
        fieldtype: "Currency",
        placeholder: "Enter Total Amount",
        change: clearPreview,
      },
      parent: row.find(".total-amount")[0],
      render_input: true,
    });

    // Number of Months (Int field)
    frappe.ui.form.make_control({
      df: {
        fieldtype: "Int",
        placeholder: "Enter Number of Months",
        change: clearPreview,
      },
      parent: row.find(".months")[0],
      render_input: true,
    });

    // Start Date (Date field)
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

  // Initialize the single row
  createRowControls($("#salary-component-rows tr").first());

  // -------- Preview Function --------
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

    // Convert to YYYY-MM-DD safely
    if (startDate.includes("-")) {
      const parts = startDate.split("-");
      if (parts[0].length === 2) {
        // format DD-MM-YYYY → YYYY-MM-DD
        startDate = `${parts[2]}-${parts[1]}-${parts[0]}`;
      }
    }

    const start = new Date(startDate);
    if (isNaN(start.getTime())) {
      frappe.msgprint("Invalid Start Date");
      return;
    }

    const amountPerMonth = (totalAmount / numMonths).toFixed(2);

    for (let i = 0; i < numMonths; i++) {
      let year = start.getFullYear();
      let monthName = start.toLocaleString("default", { month: "long" });

      let rowHtml = `<tr><td>${year} - ${monthName}</td><td>${amountPerMonth}</td></tr>`;
      $("#preview-rows").append(rowHtml);

      // move to next month
      start.setMonth(start.getMonth() + 1);
    }

    $("#preview-table-section").show();
  }

  // Preview Button
  $("#preview-components").on("click", generatePreview);

  // Save Components
  $("#save-components").on("click", function () {
    const empId = employeeField.get_value();
    if (!empId) {
      frappe.msgprint("Please select an Employee first.");
      return;
    }

    let rows = [];
    $("#salary-component-rows tr").each(function () {
      const salaryComp = $(this).find(".salary-component input").val();
      const compType = $(this).find(".component-type input").val(); // Data field
      const totalAmount = $(this).find(".total-amount input").val();
      const numMonths = $(this).find(".months input").val();
      const startDate = $(this).find(".start-date input").val();

      if (salaryComp) {
        rows.push({
          salary_component: salaryComp,
          component_type: compType,
          total_amount: totalAmount || 0,
          number_of_months: numMonths || 0,
          start_date: startDate || null,
        });
      }
    });

    if (rows.length === 0) {
      frappe.msgprint("Please add a Salary Component.");
      return;
    }

    frappe.call({
      method:
        "pinnaclehrms.pinnaclehrms.doctype.recurring_salary_component.recurring_salary_component.create_rsc",
      args: {
        data: JSON.stringify({
          employee: empId,
          rows: rows,
        }),
      },
      callback: function (res) {
        if (!res.exc) {
          let rsc = res.message.created || [];
          if (rsc.length) {
            rsc.forEach((name) => {
              let link = `<a href="/app/recurring-salary-component/${name}" target="_blank">${name}</a>`;
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
            __("Recurring Salary Components saved successfully!")
          );
        }
      },
    });
  });
};
