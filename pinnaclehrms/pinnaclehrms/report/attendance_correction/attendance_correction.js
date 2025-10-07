frappe.query_reports["Attendance Correction"] = {
  filters: [
    {
      fieldname: "fiscal_year",
      label: __("Fiscal Year"),
      fieldtype: "Link",
      options: "Fiscal Year",
      default: frappe.defaults.get_user_default("fiscal_year"),
      reqd: 1,
    },
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: frappe.defaults.get_user_default("company"),
      reqd: 1,                      
    },
    {
      fieldname: "employee",
      label: __("Employee"),
      fieldtype: "Link",
      options: "Employee",
      reqd: 0,
    },
  ],

  onload: function (report) {
    // Auto-refresh when filters change
    report.page.set_primary_action(__("Refresh"), function () {
      report.refresh();
    });
  },
};
