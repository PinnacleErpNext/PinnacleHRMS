// Copyright (c) 2025, OTPL and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Correction", {
  refresh(frm) {
    if (frm.is_new() & frappe.session.user !== "Administrator") {
      frappe.db
        .get_value("Employee", { user_id: frappe.session.user }, "name")
        .then((r) => {
          if (r.message) {
            frm.set_value("employee", r.message.name);
            frm.set_df_property("employee","read_only",1)
          }
        });
        
    }
    if (frm.doc.status) {
      frm.page.set_indicator(
        frm.doc.status,
        {
          Pending: "gray",
          Approved: "green",
          Rejected: "red",
        }[frm.doc.status]
      );
    }
    if (frappe.user.has_role("Team Lead")) {
      // Unlock the 'status' field
      frm.set_df_property("status", "read_only", 0);
      if (frappe.session.user === "Administrator") {
        return;
      }
      frm.disable_save();
      // Lock all other fields
      Object.values(frm.fields_dict).forEach((field) => {
        if (field.df.fieldname !== "status") {
          frm.set_df_property(field.df.fieldname, "read_only", 1);
        }
      });
    }
  },
  attendance_date(frm) {
    frappe.db
      .get_list("Attendance", {
        filters: {
          employee: frm.doc.employee,
          attendance_date: frm.doc.attendance_date,
          docstatus: 1,
        },
        limit: 1,
      })
      .then((records) => {
        if (!records.length) {
          frappe.msgprint(
            "No submitted attendance record found for the selected date."
          );
          frm.set_value("actual_in_time", null);
          frm.set_value("actual_out_time", null);
          return;
        }

        // Fetch the full document by name
        frappe.db.get_doc("Attendance", records[0].name).then((doc) => {
          frm.set_value("actual_in_time", doc.in_time);
          frm.set_value("actual_out_time", doc.out_time);
        });
      });
  },
  status(frm) {
    if (frm.doc.status === "Approved") {
      frm.save("Submit");
    } else if (frm.doc.status === "Rejected") {
      frm.save("Submit");
      frm.save("Cancel");
    }
  },
  before_save: function (frm) {
    let reason_field;
    let label;

    if (frm.doc.status === "Pending") {
      reason_field = "reason_for_correction";
      label = "Reason For Correction";
    } else if (frm.doc.status === "Rejected") {
      reason_field = "reason_for_approval";
      label = "Reason For Rejection";
    } else if (frm.doc.status === "Approved") {
      reason_field = "reason_for_approval";
      label = "Reason For Approval";
    }

    if (reason_field && !frm.doc[reason_field]) {
      frappe.prompt(
        {
          label: label,
          fieldname: reason_field,
          fieldtype: "Data",
          reqd: 1,
        },
        function (values) {
          frm.set_value(reason_field, values[reason_field]);
          if (frm.doc.status === "Pending") {
            frm.save();
          } else if (frm.doc.status === "Approved") {
            frm.save("Submit");
          } else if (frm.doc.status === "Rejected") {
            frm.save("Submit");
            frm.save("Cancel");
          }
        },
        "Provide Reason"
      );

      // Prevent the default save for now
      frappe.validated = false;
    }
  },
});
