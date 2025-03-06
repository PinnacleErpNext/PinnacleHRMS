frappe.listview_settings["Self Attendance"] = {
  onload: function (listview) {
    listview.page.add_action_item("Approve", () => {
      let selected_items = listview.get_checked_items();
      if (!selected_items.length) {
        frappe.msgprint("Please select one or more items to reject.");
        return;
      }
      selected_items.forEach((attendance) => {
        frappe.call({
          method:
            "pinnaclehrms.pinnaclehrms.doctype.self_attendance.self_attendance.approve_self_attendance",
          args: {
            doc_id: attendance.name,
          },

          callback: (res) => {
            console.log(res.message.status);
            update_status(attendance, res.message.status);
          },
          error: (res) => {
            console.log(res.message);
          },
        });
      });
    });
    listview.page.add_action_item("Reject", () => {
      // Get the selected items from the list view
      let selected_items = listview.get_checked_items();

      if (!selected_items.length) {
        frappe.msgprint("Please select one or more items to reject.");
        return;
      }

      // For each selected item, update its status field to "Rejected"
      selected_items.forEach((attendance) => {
        update_status(attendance, "Rejected");
      });
      listview.refresh();
      frappe.msgprint("Selected items updated to Rejected");
    });
  },
};

function update_status(attendance, value) {
  frappe.call({
    method: "frappe.client.set_value",
    args: {
      doctype: "Self Attendance",
      name: attendance.name,
      fieldname: "status",
      value: value,
    },
    callback: function (r) {
      if (!r.exc) {
        frappe.msgprint(`Item ${attendance.name} updated to ${value}`);
      }
      listview.refresh();
    },
  });
}
