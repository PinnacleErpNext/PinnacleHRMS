// Copyright (c) 2025, OTPL and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Correction", {
  refresh(frm) {
    if (frm.is_new() & (frappe.session.user !== "Administrator")) {
      frappe.db
        .get_value("Employee", { user_id: frappe.session.user }, "name")
        .then((r) => {
          if (r.message) {
            frm.set_value("employee", r.message.name);
            frm.set_df_property("employee", "read_only", 1);
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
    if (!frm.is_new()) {
      if (frappe.session.user === "Administrator") {
        // HR Manager can edit all fields
        Object.keys(frm.fields_dict).forEach((fieldname) => {
          frm.set_df_property(fieldname, "read_only", 0);
        });
        return;
      }
      if (frappe.user.has_role("Team Lead")) {
        // Team Lead can save
        frm.disable_save();

        // All fields read-only except 'status'
        Object.keys(frm.fields_dict).forEach((fieldname) => {
          if (fieldname !== "status") {
            frm.set_df_property(fieldname, "read_only", 1);
          }
        });

        // status editable
        frm.set_df_property("status", "read_only", 0);
        return;
      }

      // EMPLOYEE (but not Team Lead)
      if (frappe.user.has_role("Employee")) {
        // Disable save
        frm.disable_save();

        // All fields read-only
        Object.keys(frm.fields_dict).forEach((fieldname) => {
          frm.set_df_property(fieldname, "read_only", 1);
        });
      }
    }
  },
  attendance_date(frm) {
    frappe.call({
      method:
        "pinnaclehrms.pinnaclehrms.doctype.attendance_correction.attendance_correction.get_attendance",
      args: {
        emp: frm.doc.employee,
        att_date: frm.doc.attendance_date,
      },
      callback: function (r) {
        if (!r.message || !r.message.in_time) {
          frappe.msgprint(
            "No submitted attendance record found for the selected date."
          );
          frm.set_value("actual_in_time", null);
          frm.set_value("actual_out_time", null);
          return;
        }

        frm.set_value("actual_in_time", r.message.in_time);
        frm.set_value("actual_out_time", r.message.out_time);
      },
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
  view_corrected_attendance: function (frm) {
    if (frm.doc.corrected_attendance) {
      frappe.set_route(
        "Form",
        "Attendance",
        frm.doc.corrected_attendance
      );
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
