frappe.listview_settings["Backup Checkin Logs"] = {
  onload(listview) {
    listview.page.add_actions_menu_item(__("Restore"), () => {
      const selected = listview.get_checked_items();

      if (!selected.length) {
        frappe.msgprint(__("Please select at least one Backup Checkin Log."));
        return;
      }

      frappe.confirm(
        __("Are you sure you want to restore {0} selected check-in log(s)?", [
          selected.length,
        ]),
        () => {
          frappe.call({
            method:
              "pinnaclehrms.pinnacle_hr.doctype.backup_checkin_logs.backup_checkin_logs.restore_checkin_logs",

            args: {
              backup_checkins: selected.map((record) => record.name),
            },

            freeze: true,
            freeze_message: __("Restoring Check-ins..."),

            callback(r) {
              if (!r.message) {
                return;
              }

              const result = r.message;

              frappe.msgprint({
                title: __("Restore Result"),
                indicator: result.failed_count > 0 ? "orange" : "green",

                message: __(
                  "{0} check-in(s) restored successfully.<br>{1} check-in(s) could not be restored.",
                  [result.success_count, result.failed_count],
                ),
              });

              listview.refresh();
            },
          });
        },
      );
    });
  },
};
