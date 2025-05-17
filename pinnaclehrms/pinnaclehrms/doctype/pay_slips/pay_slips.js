// Copyright (c) 2025, OTPL and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pay Slips", {
  refresh(frm) {},
});

frappe.ui.form.on("Salary Calculation", {
  days: function (frm, cdt, cdn) {
    const row = locals[cdt][cdn];

    const days = row.days || 0;
    const rate = row.rate || 0;
    const percentage = row.effective_percentage || 0;

    const amount = (days * rate * percentage) / 100;

    frappe.model.set_value(cdt, cdn, "amount", amount);
  },
  amount: function (frm) {
    updateTotal(frm);
  },
});

frappe.ui.form.on("Other Earnings", {
  amount: function (frm) {
    updateOtherEarningsTotal(frm);
  },
});

function updateTotal(frm) {
  itemTotal = 0;
  frm.doc.salary_calculation.forEach((item) => {
    itemTotal = itemTotal + item.amount;
  });
  frm.set_value("total", itemTotal);
  updateNetPayable(frm);
}

function updateNetPayable(frm) {
  netPayable = 0;
  frm.doc.other_earnings.forEach((item) => {
    netPayable = netPayable + item.amount;
  });
  netPayable = netPayable + frm.doc.total;

  frm.set_value("net_payble_amount", netPayable);
}

function updateOtherEarningsTotal(frm) {
  total = 0;
  frm.doc.other_earnings.forEach((item) => {
    total = total + item.amount;
  });
  frm.set_value("other_earnings_total", total);
  updateNetPayable(frm);
}
