# Copyright (c) 2024, OTPL and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime
from frappe.model.document import Document


class Requestpayslip(Document):
	def before_save(self):
    		self.requested_date = datetime.today().strftime('%Y-%m-%d')
