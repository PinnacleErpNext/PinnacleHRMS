// Copyright (c) 2026, OTPL and contributors
// For license information, please see license.txt

frappe.ui.form.on("Shift Variation", {
  refresh(frm) {
    // Show / Hide Failure Tab + Banner
    toggle_failure_tab(frm);

    // Add custom button only if company selected
    if (frm.doc.company) {
      frm.add_custom_button("Get Employees", () => {
        frm.trigger("fetch_employees");
      });
    }

    // Add a visual indicator if shift requests are in background
    if (frm.doc.background_processing) {
      frm.dashboard.set_headline_alert(
        __("Shift Requests are being created in the background..."),
        "blue",
      );
    }
  },

  onload(frm) {
    toggle_failure_tab(frm);
  },

  company(frm) {
    // Set department filter by company
    frm.set_query("department", () => {
      return {
        filters: {
          company: frm.doc.company,
        },
      };
    });

    // Set employee filter based on company only
    frm.fields_dict.employee_list.grid.get_field("employee").get_query = () => {
      return {
        filters: {
          company: frm.doc.company,
        },
      };
    };
  },

  department(frm) {
    // Set employee filter based on company + department
    frm.fields_dict.employee_list.grid.get_field("employee").get_query = () => {
      return {
        filters: {
          company: frm.doc.company,
          department: frm.doc.department,
        },
      };
    };
  },

  fetch_employees(frm) {
    if (!frm.doc.company) {
      frappe.msgprint("Please select Company");
      return;
    }

    // Clear existing
    frm.clear_table("employee_list");
    frm.refresh_field("employee_list");

    let filters = { company: frm.doc.company };
    if (frm.doc.department) {
      filters.department = frm.doc.department;
    }

    frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "Employee",
        filters: filters,
        fields: ["name", "employee_name", "department"],
      },
      callback(res) {
        if (res.message && res.message.length > 0) {
          res.message.forEach((emp) => {
            let row = frm.add_child("employee_list");
            row.employee = emp.name;
            row.employee_name = emp.employee_name;
            row.department = emp.department;
          });

          frm.refresh_field("employee_list");
          frappe.msgprint(`${res.message.length} employee(s) added.`);
        } else {
          frappe.msgprint("No employees found");
        }
      },
    });
  },
});

/* ---------------------------------------------
   FAILURE TAB VISIBILITY CONTROL
--------------------------------------------- */

function toggle_failure_tab(frm) {
  // Hide if no failure
  if (!frm.doc.has_failure) {
    frm.toggle_display("failure_details_tab", false);
    return;
  }

  // Show tab + failure log
  frm.toggle_display("failure_details_tab", true);

  frm.dashboard.set_headline_alert(
    __("Shift Variation failed. Check Failure Details tab."),
    "red",
  );
}
