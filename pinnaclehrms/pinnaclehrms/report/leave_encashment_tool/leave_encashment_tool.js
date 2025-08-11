// Copyright (c) 2025, OTPL and contributors
// For license information, please see license.txt

frappe.query_reports["Leave Encashment Tool"] = {
  filters: [
    {
      fieldname: "company",
      label: "Company",
      fieldtype: "Link",
      options: "Company",
      reqd: 1,
    },
    {
      fieldname: "month",
      label: "Month",
      fieldtype: "Select",
      options: [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
      ],
      default: frappe.datetime
        .str_to_obj(frappe.datetime.get_today())
        .toLocaleString("en-us", { month: "long" }),
      reqd: 1,
    },
    {
      fieldname: "year",
      label: "Year",
      fieldtype: "Int",
      default: new Date().getFullYear(),
      reqd: 1,
    },
  ],

  onload: function (report) {
    report.page.add_inner_button("Generate for All Eligible", () => {
      const filters = report.get_values();

      // Collect all eligible employees from the report data
      const emp_list = (frappe.query_report.data || [])
        .filter((row) => row.eligible === "Yes")
        .map((row) => ({
          employee: row.employee,
          employee_name: row.employee_name,
          eligible: row.eligible,
          from_date: row.last_encashment_date || row.date_of_joining,
        }));

      if (!emp_list.length) {
        frappe.msgprint("No eligible employees found.");
        return;
      }

      const payload = {
        month: filters.month,
        year: filters.year,
        selected_emp: emp_list,
      };

      frappe.call({
        method:
          "pinnaclehrms.pinnaclehrms.doctype.pinnacle_leave_encashment.pinnacle_leave_encashment.generate_leave_encashment",
        args: {
          data: payload,
        },
        callback: function (r) {
          frappe.msgprint(
            "Leave Encashment generated for all eligible employees."
          );
          report.refresh();
        },
      });
    });

    // Delegate button click for dynamic rows
    $(document).on("click", ".generate-encashment", function (event) {
      const data = this.dataset;

      fromDate = "";
      if (data.last != "None") {
        const d = new Date(data.last);
        d.setDate(d.getDate() + 1);
        fromDate = frappe.datetime.obj_to_str(d);
      }

      const dialog = new frappe.ui.Dialog({
        title: "Generate Leave Encashment",
        fields: [
          {
            label: "Employee",
            fieldname: "employee",
            fieldtype: "Link",
            options: "Employee",
            default: data.emp,
            read_only: 1,
          },
          {
            label: "Employee Name",
            fieldname: "employee_name",
            fieldtype: "Data",
            default: data.empname,
            read_only: 1,
          },
          {
            label: "From Date",
            fieldname: "from_date",
            fieldtype: "Date",
            default: fromDate || data.doj || "",
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
            default: getCurrentFinancialYearEnd(),
          },
        ],
        primary_action_label: "Submit",
        primary_action(values) {
          const payload = {
            selected_emp: [
              {
                employee: data.emp,
                employee_name: data.empname,
                eligible: "Yes",
              },
            ],
            from_date: values.from_date,
            to_date: values.to_date,
            next_encashment_date: values.next_encashment_date,
          };

          frappe.call({
            method: "frappe.client.insert",
            args: {
              doc: {
                doctype: "Pinnacle Leave Encashment",
                employee: data.emp,
                from_date: values.from_date,
                to_date: values.to_date,
              },
            },
            callback: function (res) {
              if (!res.exc && res.message) {
                dialog.hide();
                let docname = res.message.name;
                report.refresh();
                frappe.msgprint({
                  title: "Success",
                  indicator: "green",
                  message: `Leave Encashment created: <a href="/app/pinnacle-leave-encashment/${docname}" target="_blank">${docname}</a>`,
                });
              }
            },
          });
        },
      });

      dialog.show();
    });
  },
};

function monthStrToNumber(month) {
  const months = {
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

  return months[month] || 0;
}

function getCurrentFinancialYearEnd() {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth(); // 0 = Jan, 11 = Dec

  // Financial year ends on March 31
  const fyEndYear = month < 3 ? year : year + 1;

  const endDate = new Date(fyEndYear, 2, 31); // March = 2

  const day = String(endDate.getDate()).padStart(2, "0");
  const mon = String(endDate.getMonth() + 1).padStart(2, "0"); // +1 to convert from 0-indexed
  const yyyy = endDate.getFullYear();

  return `${yyyy}-${mon}-${day}`;
}
