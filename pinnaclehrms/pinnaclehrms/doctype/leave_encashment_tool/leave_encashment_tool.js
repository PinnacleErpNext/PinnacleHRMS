// Copyright (c) 2025, OTPL and contributors
// For license information, please see license.txt

frappe.ui.form.on("Leave Encashment Tool", {
  year: function (frm) {
    frm.trigger("render_employee_list");
  },

  month: function (frm) {
    frm.trigger("render_employee_list");
  },

  refresh(frm) {
    frm.disable_save();
    frm.trigger("set_primary_action");

    if (!frm.doc.year) {
      frm.set_value("year", new Date().getFullYear());
    }
  },

  set_primary_action(frm) {
    frm.page.set_primary_action(__("Generate Leave Encashment"), () => {
      if (!frm.doc.year || !frm.doc.month) {
        frappe.msgprint(__("Please select both Year and Month."));
        return;
      }

      let selectedEmp = getSelectedEmployees();
      let monthCode = getMonthCode(frm.doc.month);
      let data = {
        year: frm.doc.year,
        month: monthCode,
        selected_emp: selectedEmp,
      };

      if (selectedEmp.length === 0) {
        frappe.msgprint(__("Please select at least one employee!"));
        return;
      }

      frappe.call({
        method:
          "pinnaclehrms.pinnaclehrms.doctype.leave_encashment_tool.leave_encashment_tool.generate_leave_encashment",
        args: { data: data },
        callback: function (res) {
          if (res.message) {
            frm.employee_data = res.message;
            frm.current_page = 1;
            frm.page_size = 10;
            renderEncashmentTable(frm);
          }
        },
        error: function (err) {
          console.error("Error generating leave encashment:", err);
        },
      });
    });
  },

  render_employee_list(frm) {
    if (!frm.doc.year || !frm.doc.month) {
      frappe.msgprint(__("Please select both Year and Month."));
      return;
    }

    let monthCode = getMonthCode(frm.doc.month);
    let data = {
      year: frm.doc.year,
      month: monthCode,
    };

    frappe.call({
      method:
        "pinnaclehrms.pinnaclehrms.doctype.leave_encashment_tool.leave_encashment_tool.eligible_employee_for_leave_encashment",
      args: { data: data },
      callback: function (res) {
        
        if (res.message) {
          frm.employee_data = res.message;
          frm.current_page = 1;
          frm.page_size = 10;
          renderEmployeeTable(frm);
        }
      },
      error: function (err) {
        console.error("Error fetching eligible employees:", err);
      },
    });
  },
});

function getMonthCode(month) {
  const monthMap = {
    January: 1,
    February: 2,
    March: 3,
    April: 4,
    May: 5,
    June: 6,
    July: 7,
    August: 8,
    September: 9,
    October: 10,
    November: 11,
    December: 12,
  };
  return monthMap[month] || 0;
}

function renderEncashmentTable(frm) {
  let employees = frm.employee_data || [];
  let currentPage = frm.current_page || 1;
  let pageSize = frm.page_size || 10;
  let totalPages = Math.ceil(employees.length / pageSize);
  let start = (currentPage - 1) * pageSize;
  let paginatedEmployees = employees.slice(start, start + pageSize);

  let html = `<table class="table table-bordered">
                <thead>
                  <tr>
                    <th>Employee ID</th>
                    <th>Employee Name</th>
                    <th>From</th>
                    <th>Upto</th>
                    <th>Encashment Date</th>
                    <th>Next Encashment Date</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>`;

  paginatedEmployees.forEach((emp) => {
    html += `<tr>
                <td>${emp.employee}</td>
                <td>${emp.employee_name}</td>
                <td>${formatDate(emp.from)}</td>
                <td>${formatDate(emp.upto)}</td>
                <td>${formatDate(emp.encashment_date)}</td>
                <td>${formatDate(emp.next_encashment_date)}</td>
                <td>${emp.amount.toLocaleString()}</td>
              </tr>`;
  });

  html += `</tbody></table>`;
  html += generatePaginationControls(frm, totalPages);

  frm.set_df_property("encashment_html", "options", html);
  frm.refresh_field("encashment_html");
}

function renderEmployeeTable(frm) {
  let employees = frm.employee_data || [];
  let currentPage = frm.current_page || 1;
  let pageSize = frm.page_size || 10;
  let totalPages = Math.ceil(employees.length / pageSize);
  let start = (currentPage - 1) * pageSize;
  let paginatedEmployees = employees.slice(start, start + pageSize);

  let html = `<table class="table table-bordered">
                <thead>
                  <tr>
                    <th><input type="checkbox" id="select-all"> Select All</th>
                    <th>Employee Name</th>
                    <th>Date of Joining</th>
                    <th>Last Encashment Date</th>
                    <th>Next Encashment Date</th>
                    <th>Eligible</th>
                    <th>Generate Encashment</th>
                  </tr>
                </thead>
                <tbody>`;

  paginatedEmployees.forEach((emp) => {
    html += `<tr>
                <td><input type="checkbox" class="select-employee" data-employee="${
                  emp.employee
                }" data-name="${emp.employee_name}" data-joining="${
      emp.date_of_joining
    }" data-eligible="${emp.eligible}"></td>
                <td>${emp.employee_name}</td>
                <td>${
                  emp.date_of_joining ? formatDate(emp.date_of_joining) : "N/A"
                }</td>
                <td>${
                  emp.last_encashment_date
                    ? formatDate(emp.last_encashment_date)
                    : "N/A"
                }</td>
                <td>${
                  emp.next_encashment_date
                    ? formatDate(emp.next_encashment_date)
                    : "N/A"
                }</td>
                <td>${emp.eligible}</td>
                <td>
                  <button class="btn btn-sm btn-primary generate-encashment" 
                          data-employee='${JSON.stringify({
                            employee: emp.employee,
                            employee_name: emp.employee_name,
                            doj: emp.date_of_joining,
                            last_encashment_date: emp.last_encashment_date,
                          })}'>
                    Generate
                  </button>
                </td>
              </tr>`;
  });

  html += `</tbody></table>`;
  html += generatePaginationControls(frm, totalPages);

  frm.set_df_property("employee_html", "options", html);
  frm.refresh_field("employee_html");
}

function generatePaginationControls(frm, totalPages) {
  return `<div style="display: flex; justify-content: space-between; margin-top: 10px;">
            <button class="btn btn-sm btn-secondary" id="prev-page" ${
              frm.current_page === 1 ? "disabled" : ""
            }>Previous</button>
            <span> Page ${frm.current_page} of ${totalPages} </span>
            <button class="btn btn-sm btn-secondary" id="next-page" ${
              frm.current_page === totalPages ? "disabled" : ""
            }>Next</button>
          </div>`;
}

document.addEventListener("click", function (event) {
  if (event.target.id === "prev-page" || event.target.id === "next-page") {
    let frm = cur_frm;
    frm.current_page += event.target.id === "prev-page" ? -1 : 1;
    renderEmployeeTable(frm);
  }
});

document.addEventListener("click", function (event) {
  if (event.target.classList.contains("generate-encashment")) {
    let emp;
    try {
      emp = JSON.parse(event.target.dataset.employee);
    } catch (e) {
      frappe.msgprint("Invalid employee data.");
      return;
    }

    let d = new frappe.ui.Dialog({
      title: "Enter details",
      fields: [
        {
          label: "Employee",
          fieldname: "employee",
          fieldtype: "Link",
          options: "Employee",
          default: emp.employee,
          read_only: 1,
        },
        {
          label: "Employee Name",
          fieldname: "employee_name",
          fieldtype: "Data",
          default: emp.employee_name,
          read_only: 1,
        },
        {
          label: "From Date",
          fieldname: "from_date",
          fieldtype: "Date",
          default: emp.last_encashment_date || emp.doj || "",
        },
        {
          label: "To Date",
          fieldname: "to_date",
          fieldtype: "Date",
        },
        {
          label: "Next Encashment Date",
          fieldname: "next_encashment_date",
          fieldtype: "Date",
        },
      ],
      size: "small",
      primary_action_label: "Submit",
      primary_action(values) {
        const data = {
          year: cur_frm.doc.year,
          month: getMonthCode(cur_frm.doc.month),
          selected_emp: [
            {
              employee: emp.employee,
              employee_name: emp.employee_name,
              eligible: "Yes",
            },
          ],
          from_date: values.from_date,
          to_date: values.to_date,
          next_encashment_date: values.next_encashment_date,
        };

        frappe.call({
          method:
            "pinnaclehrms.pinnaclehrms.doctype.leave_encashment_tool.leave_encashment_tool.generate_leave_encashment",
          args: { data: data },
          callback: function (res) {
            console.log("Leave Encashment Response:", res.message);

            if (res.message) {
              cur_frm.employee_data = res.message;
              cur_frm.page_size = 10;
              cur_frm.current_page = 1;
              renderEncashmentTable(frm);
            }
          },
          error: function (err) {
            console.error("Error generating leave encashment:", err);
          },
        });
        d.hide();
      },
    });

    d.show();
  }
});

document.addEventListener("change", function (event) {
  if (event.target.id === "select-all") {
    document.querySelectorAll(".select-employee").forEach((checkbox) => {
      checkbox.checked = event.target.checked;
    });
  }
});

function getSelectedEmployees() {
  let selectedEmployees = [];
  document.querySelectorAll(".select-employee:checked").forEach((checkbox) => {
    selectedEmployees.push({
      employee: checkbox.dataset.employee,
      employee_name: checkbox.dataset.name,
      date_of_joining: checkbox.dataset.joining,
      eligible: checkbox.dataset.eligible,
    });
  });
  return selectedEmployees;
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}
