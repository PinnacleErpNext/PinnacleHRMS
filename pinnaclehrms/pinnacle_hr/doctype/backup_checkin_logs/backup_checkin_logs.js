// Copyright (c) 2026, OTPL and contributors
// For license information, please see license.txt

frappe.ui.form.on("Backup Checkin Logs", {
  refresh(frm) {
    // Make all fields read-only
    frm.fields.forEach((field) => {
      frm.set_df_property(field.df.fieldname, "read_only", 1);
    });

    // Refresh fields
    frm.refresh_fields();

    // Disable Save button
    frm.disable_save();

    // Add Restore button
    frm.add_custom_button(__("Restore"), () => {
      frappe.confirm(
        __("Are you sure you want to restore this check-in log?"),
        () => {
          frappe.call({
            method: "pinnacle_hr.doctype.backup_checkin_logs.backup_checkin_logs.restore_checkin",
            args: {
              backup_checkin: frm.doc.name,
            },
            freeze: true,
            freeze_message: __("Restoring Check-in..."),
            callback: function (r) {
              if (r.message) {
                frappe.show_alert({
                  message: __("Check-in restored successfully"),
                  indicator: "green",
                });

                frm.reload_doc();
              }
            },
          });
        },
      );
    });
  },
});
