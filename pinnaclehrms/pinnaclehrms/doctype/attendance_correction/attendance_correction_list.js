frappe.listview_settings["Attendance Correction"] = {
  get_indicator: function (doc) {
    // console.log("Evaluating indicator for Sales Order:", doc);
    if (doc.docstatus === 0) {
      return [__("Pending"), "gray", "docstatus,=,0"];
    } else if (doc.docstatus === 1) {
      return [__("Approved"), "green", "docstatus,=,1"];
    } else if (doc.docstatus === 2) {
      return [__("Rejected"), "red", "docstatus,=,2"];
    }
  },
};
