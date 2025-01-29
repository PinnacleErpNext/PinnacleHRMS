frappe.pages["pay-slip-requests"].on_page_load = function (wrapper) {
  var page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Pay Slip Requests",
    single_column: true,
  });

  // Create a container for the table
  let table_container = $(`
        <div class="table-responsive">
            <table class="table table-bordered">
                <thead>
                    <tr>
						<th>Request Date</th>
                        <th>Employee Id</th>
                        <th>Year</th>
                        <th>Month</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody id="pay-slip-requests-table">
                    <!-- Data will be populated here -->
                </tbody>
            </table>
        </div>
    `).appendTo(page.body);

  // Fetch data and populate the table
  frappe.call("pinnaclehrms.api.getPaySlipRequests").then((r) => {
    if (r.message && r.message.length > 0) {
      const requests = r.message;

      requests.forEach((request) => {
        let row = $(`
                    <tr>
						<td>${request.requested_date}</td>
                        <td>${request.employee}</td>
                        <td>${request.year}</td>
                        <td>${request.month}</td>
                        <td class="status-cell">${request.status}</td>
                        <td>
                            <div class="btn-group">
                                <button type="button" class="btn btn-primary dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                    Action
                                </button>
                                <div class="dropdown-menu">
                                    <a class="dropdown-item btn-accept" data-id="${
                                      request.name
                                    }" data-request='${JSON.stringify(
          request
        )}' href="#">Accept</a>
                                    <a class="dropdown-item btn-reject" data-id="${
                                      request.name
                                    }" href="#">Reject</a>
                                </div>
                            </div>
                        </td>
                    </tr>
                `);
        row.appendTo("#pay-slip-requests-table");
      });

      // Accept button click event
      $(".btn-accept").on("click", function () {
        let request_id = $(this).data("id");
        let request = $(this).data("request");

        // Open dialog with pre-filled values
        let details = new frappe.ui.Dialog({
          title: "Enter details",
          fields: [
            {
              label: "Year",
              fieldname: "year",
              fieldtype: "Data",
              default: request.year,
              reqd: true,
            },
            {
              label: "Month",
              fieldname: "month",
              fieldtype: "Select",
              default: request.month,
              options:
                "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
              reqd: true,
            },
            {
              label: "Employee",
              fieldname: "select_employee",
              fieldtype: "Link",
              options: "Employee",
              default: request.employee,
              reqd: true,
            },
            {
              label: "Allowed Lates",
              fieldname: "allowed_lates",
              fieldtype: "Int",
              default: 3,
              reqd: true,
            },
            {
              label: "Auto Calculate Leave Encashment",
              fieldname: "auto_calculate_leave_encashment",
              default: 0,
              fieldtype: "Check",
            },
          ],
          primary_action_label: "Submit",
          primary_action(values) {
            const monthName = values.month;
            const months = {
              January: 1,
              February: 2,
              March: 3,
              April: 4,
              May: 5,
              June: 6,
              July: 7,
              August: 8,
              September: 9,
              October: 10,
              November: 11,
              December: 12,
            };

            values.month = months[monthName];

            if (!values.month) {
              frappe.msgprint("Invalid month name.");
              return;
            }

            frappe.call({
              method: "pinnaclehrms.api.approvePaySlipRequest",
              args: { data: values },
              callback: function (response) {
                console.log(response.message.message);
                if (response.message.message === "success") {
                  frappe.msgprint("Pay Slip Request Accepted");
                  // Update the status cell to "Accepted"
                  $(`a[data-id="${request_id}"]`)
                    .closest("tr")
                    .find(".status-cell")
                    .text("Accepted");
                  frappe.db.set_value(
                    "Request Pay Slip",
                    request.name,
                    "status",
                    "Approved"
                  );
                }
              },
            });
            details.hide();
          },
        });

        // Show the dialog
        details.show();
      });

      // Reject button click event
      $(".btn-reject").on("click", function () {
        let request_id = $(this).data("id");
        frappe.db
          .set_value("Request Pay Slip", request_id, "status", "Rejected")
          .then((r) => {
            let doc = r.message;
            console.log(doc);
          });
      });
    } else {
      frappe.msgprint("No Pay Slip Requests found.");
    }
  });
};
