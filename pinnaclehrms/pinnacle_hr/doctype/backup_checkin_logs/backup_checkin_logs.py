# Copyright (c) 2026, OTPL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BackupCheckinLogs(Document):

    def before_insert(self):

        if self.employee and self.time and self.log_type:

            self.unique_key = (
                f"{self.employee}_"
                f"{self.time.strftime('%Y%m%d%H%M%S')}_"
                f"{self.log_type}"
            )