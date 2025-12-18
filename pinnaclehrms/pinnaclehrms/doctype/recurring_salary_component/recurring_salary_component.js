// Copyright (c) 2025, OTPL and contributors
// For license information, please see license.txt

frappe.ui.form.on("Recurring Salary Component", {
  refresh(frm) {
    if (!frm.doc.year) {
      frm.set_value("year", new Date().getFullYear());
    }
  },
});
