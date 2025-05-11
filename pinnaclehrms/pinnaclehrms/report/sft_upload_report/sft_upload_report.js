frappe.query_reports["SFT Upload Report"] = {
    onload: function(report) {
        report.page.set_title("My Custom Report Title");
    },
    get_file_name: function(filters) {
        let date = frappe.datetime.nowdate();
        return `My_Custom_Report_${date}`;
    }
};
