frappe.query_reports["Attendance Approval"] = {
  filters: [
    {
      fieldname: "year",
      label: "Year",
      fieldtype: "Int",
      default: new Date().getFullYear(),
    },
    {
      fieldname: "month",
      label: "Month",
      fieldtype: "Select",
      options:
        "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
      default: new Intl.DateTimeFormat("en", { month: "long" }).format(
        new Date()
      ),
    },
    {
      fieldname: "shift",
      label: "Shift",
      fieldtype: "Link",
      options: "Shift Type",
    },
    {
      fieldname: "employee",
      label: "Employee",
      fieldtype: "Link",
      options: "Employee",
    },
    {
      fieldname: "date",
      label: "Date",
      fieldtype: "Date",
    },
  ],

  onload: function (report) {
    // ✅ Add to ACTION dropdown
    if (report.page._download_excel_hooked) return;
    report.page._download_excel_hooked = true;

    // Put it under the existing "..." menu to avoid duplicating the Actions button
    report.page.add_menu_item(__("Download Excel"), function () {
      const filters = report.get_values();
      if (!filters) return;

      // POST -> backend writes frappe.response (binary) -> browser downloads
      open_url_post(
        "/api/method/pinnaclehrms.pinnaclehrms.report.attendance_approval.attendance_approval.download_final_attendance_excel",
        { filters: JSON.stringify(filters) }
      );
    });

    // Approve button logic stays the same
    let approveBtn = report.page
      .add_inner_button("Approve Selected", function () {
        let selected_rows = [];
        $(".approve-checkbox:checked").each(function () {
          let emp = $(this).data("employee");
          let date = $(this).data("date");
          selected_rows.push({ employee: emp, date: date });
        });

        if (selected_rows.length === 0) {
          frappe.msgprint("Please select at least one row to approve.");
          return;
        }

        frappe.call({
          method:
            "pinnaclehrms.pinnaclehrms.report.attendance_approval.attendance_approval.bulk_approve_attendance",
          args: { records: selected_rows },
          callback: function (r) {
            if (!r.exc) {
              frappe.msgprint("Selected attendance records approved.");
              frappe.query_report.refresh();
            }
          },
        });
      })
      .addClass("btn-primary");

    approveBtn.hide();

    $(document).on("change", ".approve-checkbox", function () {
      let anyChecked = $(".approve-checkbox:checked").length > 0;
      if (anyChecked) {
        approveBtn.show();
      } else {
        approveBtn.hide();
      }
    });

    $(document).on("change", "#select-all-checkbox", function () {
      $(".approve-checkbox")
        .prop("checked", $(this).is(":checked"))
        .trigger("change");
    });
  },
};
