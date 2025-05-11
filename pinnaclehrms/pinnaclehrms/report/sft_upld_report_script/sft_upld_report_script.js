frappe.query_reports["SFT upld report script"] = {
  onload: function (report) {
    // Helper function to get formatted date
    function get_formatted_date() {
      let today = frappe.datetime.now_date(); // yyyy-mm-dd
      let parts = today.split("-");
      let day = parts[2];
      let month = "05";
      let year = parts[0];
      return `${day}-${month}-${year}`;
    }

    // Prepare custom report name with date
    const base_report_name = "SFT upld report script";
    const formatted_date = get_formatted_date();
    const custom_report_name = `${base_report_name} - ${formatted_date}`;

    // 1️⃣ Set custom Page Title
    report.page.set_title(custom_report_name);

    // 2️⃣ Override get_export_options to inject custom title
    const original_get_export_options = frappe.query_report.get_export_options;
    frappe.query_report.get_export_options = function (file_format) {
      let options = original_get_export_options.call(
        frappe.query_report,
        file_format
      );
      options.title = custom_report_name;
      return options;
    };
  },
};
