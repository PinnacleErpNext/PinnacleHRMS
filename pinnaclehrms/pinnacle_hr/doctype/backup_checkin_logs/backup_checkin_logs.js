// Copyright (c) 2026, OTPL and contributors
// For license information, please see license.txt

frappe.ui.form.on("Backup Checkin Logs", {
  refresh(frm) {
    frm.fields.forEach((field) => {
      frm.set_df_property(field.df.fieldname, "read_only", 1);
    });

    // Refresh fields
    frm.refresh_fields();
    frm.disable_save();
  },
});
