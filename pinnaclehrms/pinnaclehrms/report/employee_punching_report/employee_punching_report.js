frappe.query_reports["Employee Punching Report"] = {
    filters: [
        {
            fieldname: "employee",
            label: "Employee",
            fieldtype: "Link",
            options: "Employee",
            width: "200px"
        },
        {
            fieldname: "month",
            label: "Month",
            fieldtype: "Select",
            options: [
                "", "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ],
            width: "120px"
        },
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            width: "100px"
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            width: "100px"
        }
    ],
    onload: function(report) {
        // Auto set current month on report load
        const monthNames = ["January", "February", "March", "April", "May", "June",
                            "July", "August", "September", "October", "November", "December"];
        const today = new Date();
        const currentMonthName = monthNames[today.getMonth()];

        // Set default filter value for month
        frappe.query_report.set_filter_value('month', currentMonthName);

        // Optional: Clear button for convenience
        report.page.add_inner_button(__('Clear Filters'), function() {
            frappe.query_report.set_filter_value('employee', '');
            frappe.query_report.set_filter_value('month', '');
            frappe.query_report.set_filter_value('from_date', '');
            frappe.query_report.set_filter_value('to_date', '');
        });
    }
};
