// Copyright (c) 2025, OTPL and contributors
// For license information, please see license.txt

frappe.ui.form.on("Self Attendance", {
  refresh(frm) {
    if (frm.is_new() && frappe.user.has_role("Employee")) {
      frm.set_value("status", "Pending");
      frm.set_df_property("status", "read_only", 1);
    }
  },
  onload: function (frm) {
    // frm.page.add_action_item("Delete", () => delete_items());
    if (
      (!frm.is_new() && frappe.user.has_role("Team Leader")) ||
      frappe.user.has_role("HR Manager")
    ) {
      // Adding buttons for Team Leader and HR Manager
      frm.page.add_action_item("Approve", () => {
        frm.set_value("status", "Approved");
        frm.save();
      });
      frm.page.add_action_item("Reject", () => {
        frm.set_value("status", "Rejected");
        frm.save();
      });
    }

    if (!frm.is_new() && frappe.user.has_role("HR Manager")) {
      // Adding "Attendance" button only for HR Manager
      frm.page.add_action_item("Mark Attendance", () => {
        if (frm.doc.status === "Approved") {
          frappe.call({
            method:
              "pinnaclehrms.pinnaclehrms.doctype.self_attendance.self_attendance.mark_self_attendance",
            args: {
              doc_id: frm.doc.name,
            },

            callback: (res) => {
              frm.set_value("status", res.message.status);
              frm.set_value("ref_attendance", res.message.attendance);
              frm.save();
            },
            error: (res) => {
              console.log(res.message);
            },
          });
        } else {
          frames.msgprint("Attendance is not approved.");
        }
      });
    }
  },
  validate: function (frm) {
    if (!frm.doc.employee) {
      frappe.throw("Please select employee!");
    }
    if (frm.doc.check_in) {
      let selected_datetime = new Date(frm.doc.check_in);
      let current_datetime = new Date();

      // Compare if the selected datetime is in the future
      if (selected_datetime > current_datetime) {
        frappe.throw("Attendance can not marked for future dates!");
      }
    }
    if (frm.doc.check_out) {
      let selected_datetime = new Date(frm.doc.check_out);
      let current_datetime = new Date();

      // Compare if the selected datetime is in the future
      if (selected_datetime > current_datetime) {
        frappe.throw("Attendance can not marked for future dates!");
      }
    }
  },
});
