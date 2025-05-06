frappe.listview_settings["Employee Checkin"] = {
  onload: function (listview) {
    listview.page.add_field({
      label: "Status",
      fieldtype: "Select",
      fieldname: "workflow_state",
      options: ["", "Pending", "Approved", "Rejected"],
      change() {
        var workflow_state =
          listview.page.fields_dict.workflow_state.get_value();
        listview.filter_area.add([
          "Employee Checkin",
          "workflow_state",
          "=",
          workflow_state,
        ]);
      },
    });
  },
};
