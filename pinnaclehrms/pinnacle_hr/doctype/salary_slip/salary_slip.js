/* =====================================================
   SALARY SLIP ACKNOWLEDGEMENT CONTROL
   ===================================================== */

/*
 * Final Flow
 *
 * Employee
 *    |
 *    +-- enable_late_acknowledgment = 0
 *    |       -> Normal Salary Slip
 *    |
 *    +-- enable_late_acknowledgment = 1
 *            |
 *            +-- Attendance in_time > 10:30
 *            |   AND in_time < 11:00
 *            |
 *            +-- < 14
 *            |      -> Normal Salary Slip
 *            |
 *            +-- 14 to 20
 *            |      -> Blue Urgent Notice
 *            |      -> late_acknowledgment = 1
 *            |
 *            +-- > 20
 *                   -> Red High Alert
 *                   -> late_acknowledgment = 1
 *
 * Administrator:
 *    -> Always bypass
 */

/* =====================================================
   GLOBAL STATE
   ===================================================== */

let salary_slip_ack_check_running = false;
let salary_slip_ack_check_timer = null;

let late_early_dialog_open = false;

/*
 * Every route change increments this token.
 *
 * Any old asynchronous request belonging to a previous
 * route becomes invalid.
 */
let salary_slip_route_token = 0;

/* =====================================================
   SALARY SLIP FORM EVENTS
   ===================================================== */

frappe.ui.form.on("Salary Slip", {
  refresh(frm) {
    schedule_salary_slip_acknowledgement_check(frm);
  },
});

/* =====================================================
   SPA ROUTE CHANGE
   ===================================================== */

frappe.router.on("change", function () {
  /*
   * Invalidate all previous async operations.
   */
  salary_slip_route_token++;

  /*
   * Cancel pending check timer.
   */
  if (salary_slip_ack_check_timer) {
    clearTimeout(salary_slip_ack_check_timer);

    salary_slip_ack_check_timer = null;
  }

  /*
   * Reset frontend state.
   */
  salary_slip_ack_check_running = false;
  late_early_dialog_open = false;

  /*
   * Remove old Salary Slip acknowledgement UI.
   */
  cleanup_salary_slip_acknowledgement_ui();

  const route = frappe.get_route();

  /*
   * Only continue for Salary Slip form.
   */
  if (!route || route[0] !== "Form" || route[1] !== "Salary Slip") {
    return;
  }

  /*
   * Administrator bypass.
   */
  if (frappe.session.user === "Administrator") {
    return;
  }

  /*
   * Wait for Frappe SPA form restoration.
   */
  setTimeout(function () {
    const current_route = frappe.get_route();

    if (
      !current_route ||
      current_route[0] !== "Form" ||
      current_route[1] !== "Salary Slip"
    ) {
      return;
    }

    if (!cur_frm || cur_frm.doctype !== "Salary Slip") {
      return;
    }

    schedule_salary_slip_acknowledgement_check(cur_frm);
  }, 300);
});

/* =====================================================
   SCHEDULE ACKNOWLEDGEMENT CHECK
   ===================================================== */

function schedule_salary_slip_acknowledgement_check(frm) {
  /*
   * Invalid form.
   */
  if (!frm || frm.doctype !== "Salary Slip") {
    return;
  }

  /*
   * Administrator bypass.
   */
  if (frappe.session.user === "Administrator") {
    return;
  }

  /*
   * Do not check unsaved Salary Slips.
   */
  if (frm.is_new()) {
    return;
  }

  /*
   * Make sure Salary Slip is the active route.
   */
  if (!is_salary_slip_route()) {
    return;
  }

  /*
   * Do not create duplicate dialog.
   */
  if (late_early_dialog_open) {
    return;
  }

  if ($(".late-early-acknowledgement-dialog").length) {
    return;
  }

  /*
   * Cancel previous timer.
   */
  if (salary_slip_ack_check_timer) {
    clearTimeout(salary_slip_ack_check_timer);

    salary_slip_ack_check_timer = null;
  }

  /*
   * Capture route token.
   */
  const request_token = salary_slip_route_token;

  const salary_slip_name = frm.doc.name;

  /*
   * Small delay allows Frappe SPA to finish restoring
   * the form before the backend request starts.
   */
  salary_slip_ack_check_timer = setTimeout(function () {
    salary_slip_ack_check_timer = null;

    /*
     * Route changed while waiting.
     */
    if (request_token !== salary_slip_route_token) {
      return;
    }

    /*
     * Salary Slip route changed.
     */
    if (!is_salary_slip_route()) {
      return;
    }

    /*
     * Verify active form.
     */
    if (!cur_frm || cur_frm.doctype !== "Salary Slip") {
      return;
    }

    /*
     * Make sure it is the same Salary Slip.
     */
    if (cur_frm.doc.name !== salary_slip_name) {
      return;
    }

    /*
     * Prevent duplicate backend calls.
     */
    if (salary_slip_ack_check_running) {
      return;
    }

    salary_slip_ack_check_running = true;

    check_salary_slip_acknowledgement(cur_frm, request_token).finally(
      function () {
        salary_slip_ack_check_running = false;
      },
    );
  }, 250);
}

/* =====================================================
   CHECK SALARY SLIP ROUTE
   ===================================================== */

function is_salary_slip_route() {
  const route = frappe.get_route();

  return !!(route && route[0] === "Form" && route[1] === "Salary Slip");
}

/* =====================================================
   CHECK ACTIVE SALARY SLIP
   ===================================================== */

function is_active_salary_slip(salary_slip_name) {
  if (!is_salary_slip_route()) {
    return false;
  }

  if (!cur_frm || cur_frm.doctype !== "Salary Slip") {
    return false;
  }

  if (cur_frm.doc.name !== salary_slip_name) {
    return false;
  }

  return true;
}

/* =====================================================
   CHECK SALARY SLIP ACCESS
   ===================================================== */

async function check_salary_slip_acknowledgement(frm, request_token) {
  const salary_slip_name = frm.doc.name;

  /*
   * Route already changed.
   */
  if (request_token !== salary_slip_route_token) {
    return;
  }

  try {
    /*
     * Administrator bypass.
     */
    if (frappe.session.user === "Administrator") {
      return;
    }

    /*
     * Make sure Salary Slip is still active.
     */
    if (!is_active_salary_slip(salary_slip_name)) {
      return;
    }

    /*
     * Backend check.
     *
     * IMPORTANT:
     * Do NOT use freeze:true here.
     *
     * This prevents the SPA from getting stuck behind
     * a Frappe freeze overlay while navigating.
     */
    const response = await frappe.call({
      method:
        "pinnaclehrms.pinnacle_hr.doctype.salary_slip.salary_slip.get_salary_slip_access",

      args: {
        salary_slip: salary_slip_name,
      },

      freeze: false,
    });

    /*
     * User may have navigated away while request
     * was running.
     */
    if (request_token !== salary_slip_route_token) {
      return;
    }

    if (!is_active_salary_slip(salary_slip_name)) {
      return;
    }

    const data = response.message;

    if (!data) {
      return;
    }

    /* =================================================
           SALARY ALLOWED
           ================================================= */

    if (data.allowed) {
      show_salary_details(frm);

      /*
       * If already acknowledged,
       * show permanent ribbon.
       */
      if (data.acknowledged) {
        if (data.acknowledgment_type === "high_alert") {
          show_high_alert_ribbon(frm);
        } else if (data.acknowledgment_type === "late") {
          show_late_acknowledgment_ribbon(frm);
        }
      }

      return;
    }

    /* =================================================
           ACKNOWLEDGEMENT REQUIRED
           ================================================= */

    if (data.required && !data.acknowledged) {
      /*
       * Hide salary fields before showing popup.
       */
      hide_salary_details(frm);

      /*
       * Verify route one more time.
       */
      if (!is_active_salary_slip(salary_slip_name)) {
        return;
      }

      /*
       * > 20
       * RED HIGH ALERT
       */
      if (data.acknowledgment_type === "high_alert") {
        show_high_alert_warning(frm, data);

        return;
      }

      /*
       * 14 to 20
       * BLUE URGENT NOTICE
       */
      if (data.acknowledgment_type === "late") {
        show_urgent_notice_warning(frm, data);
      }
    }
  } catch (error) {
    /*
     * Ignore errors caused by SPA navigation.
     */
    if (!is_active_salary_slip(salary_slip_name)) {
      return;
    }

    console.error("Salary Slip acknowledgement error:", error);

    hide_salary_details(frm);

    frappe.msgprint({
      title: __("Access Check Failed"),

      message: __(
        "Unable to verify attendance acknowledgement. " +
          "Salary details have been hidden.",
      ),

      indicator: "red",
    });
  }
}

/* =====================================================
   HIDE SALARY DETAILS
   ===================================================== */

function hide_salary_details(frm) {
  const salary_fields = [
    "earnings",
    "deductions",

    "gross_pay",
    "gross_year_to_date",
    "gross_pay_to_date",

    "total_deduction",
    "total_deduction_year_to_date",

    "net_pay",
    "net_pay_after_tax",

    "rounded_total",
    "rounded_total_in_words",

    "year_to_date",
    "month_to_date",

    "bank_name",
    "bank_account_no",

    "income_tax_deducted_till_date",
    "income_tax_deducted_this_period",

    "total_in_words",

    "base_gross_pay",
    "base_net_pay",
    "base_total_deduction",
  ];

  salary_fields.forEach(function (fieldname) {
    if (frm.fields_dict[fieldname]) {
      frm.toggle_display(fieldname, false);
    }
  });

  add_salary_block_message(frm);
}

/* =====================================================
   SHOW SALARY DETAILS
   ===================================================== */

function show_salary_details(frm) {
  const salary_fields = [
    "earnings",
    "deductions",

    "gross_pay",
    "gross_year_to_date",
    "gross_pay_to_date",

    "total_deduction",
    "total_deduction_year_to_date",

    "net_pay",
    "net_pay_after_tax",

    "rounded_total",
    "rounded_total_in_words",

    "year_to_date",
    "month_to_date",

    "bank_name",
    "bank_account_no",

    "income_tax_deducted_till_date",
    "income_tax_deducted_this_period",

    "total_in_words",

    "base_gross_pay",
    "base_net_pay",
    "base_total_deduction",
  ];

  salary_fields.forEach(function (fieldname) {
    if (frm.fields_dict[fieldname]) {
      frm.toggle_display(fieldname, true);
    }
  });

  remove_salary_block_message(frm);
}

/* =====================================================
   SALARY BLOCK MESSAGE
   ===================================================== */

function add_salary_block_message(frm) {
  if (frm.$wrapper.find(".late-early-salary-block").length) {
    return;
  }

  const message = $(`
        <div
            class="late-early-salary-block"
            style="
                margin: 15px 0;
                padding: 18px;
                border: 1px solid #ff4d4f;
                background: #fff1f0;
                border-radius: 8px;
                color: #a8071a;
                font-size: 14px;
                line-height: 1.6;
            "
        >

            <div
                style="
                    font-size: 17px;
                    font-weight: 600;
                    margin-bottom: 8px;
                "
            >
                ⚠ Salary Details Locked
            </div>

            <div>
                Your salary details are currently hidden
                because an attendance acknowledgement
                is required.
            </div>

            <div
                style="margin-top: 8px;"
            >
                Please review and acknowledge your
                attendance information to continue.
            </div>

        </div>
    `);

  frm.$wrapper.find(".form-layout").first().prepend(message);
}

/* =====================================================
   REMOVE SALARY BLOCK MESSAGE
   ===================================================== */

function remove_salary_block_message(frm) {
  if (!frm || !frm.$wrapper) {
    return;
  }

  frm.$wrapper.find(".late-early-salary-block").remove();
}

/* =====================================================
   COMMON WARNING DIALOG
   ===================================================== */

function show_attendance_acknowledgement_warning(frm, data) {
  /*
   * Prevent duplicate dialog.
   */
  if (late_early_dialog_open) {
    return;
  }

  if ($(".late-early-acknowledgement-dialog").length) {
    return;
  }

  /*
   * Make sure Salary Slip is still active.
   */
  if (!is_active_salary_slip(frm.doc.name)) {
    return;
  }

  /*
   * Lock BEFORE creating dialog.
   */
  late_early_dialog_open = true;

  const is_high_alert = data.acknowledgment_type === "high_alert";

  const title = is_high_alert ? __("High Alert") : __("Urgent Notice");

  const color = is_high_alert ? "#cf1322" : "#1677ff";

  const background = is_high_alert ? "#fff1f0" : "#e6f4ff";

  const border = is_high_alert ? "#ff4d4f" : "#1677ff";

  const icon = is_high_alert ? "🔴" : "🔵";

  /*
   * Exact requested messages.
   */
  const message = is_high_alert
    ? `
                You are required to improve your habit
                of continuous late reporting; otherwise,
                there will be an adjustment of
                <strong>25% instead of 10%</strong>.
              `
    : `
                It has been observed that you have been
                reporting to the office late on a regular
                basis.

                <br><br>

                You are required to ensure that you report
                to the office on time and maintain
                punctuality going forward.

                <br><br>

                Please note that continued late attendance
                may result in a salary adjustment of
                <strong>
                    25% instead of the previously applicable 10%
                </strong>.
              `;

  const dialog = new frappe.ui.Dialog({
    title: title,

    /*
     * Prevent normal close.
     */
    no_close: true,

    fields: [
      {
        fieldtype: "HTML",
        fieldname: "warning",
      },
    ],

    primary_action_label: __("I Acknowledge"),

    primary_action() {
      acknowledge_salary_slip(frm, dialog, data.acknowledgment_type);
    },
  });

  dialog.$wrapper.addClass("late-early-acknowledgement-dialog");

  /*
   * Readable dates.
   */
  const from_date = format_readable_date(data.from_date);

  const to_date = format_readable_date(data.to_date);

  /*
   * Warning content.
   */
  dialog.fields_dict.warning.$wrapper.html(`

            <div
                style="
                    background: ${background};
                    border: 2px solid ${border};
                    border-radius: 8px;
                    padding: 22px;
                    color: ${color};
                    line-height: 1.7;
                    font-size: 14px;
                "
            >

                <div
                    style="
                        font-size: 22px;
                        font-weight: 700;
                        margin-bottom: 15px;
                    "
                >

                    ${icon}
                    ${title}

                </div>


                <div>

                    ${message}

                </div>



                <div
                    style="
                        margin-top: 18px;
                        padding: 12px;
                        background: #fff;
                        border-left: 4px solid ${border};
                        font-weight: 600;
                    "
                >

                    Please click
                    <strong>"I Acknowledge"</strong>
                    to continue viewing your salary details.

                </div>

            </div>

        `);

  /*
   * Show dialog.
   */
  dialog.show();

  /*
   * Remove ALL close buttons.
   */
  dialog.$wrapper
    .find(
      ".modal-header .btn-close, " +
        ".modal-header .close, " +
        ".modal-header button.close, " +
        ".modal-header button[data-dismiss='modal'], " +
        ".modal-header button[data-bs-dismiss='modal'], " +
        ".modal-header [data-dismiss='modal'], " +
        ".modal-header [data-bs-dismiss='modal']",
    )
    .remove();

  /*
   * Additional fallback.
   */
  dialog.$wrapper.find(".modal-header button").each(function () {
    const button = $(this);

    const text = button.text().trim();

    const aria_label = button.attr("aria-label");

    if (
      button.hasClass("btn-close") ||
      button.hasClass("close") ||
      text === "×" ||
      text === "✕" ||
      aria_label === "Close" ||
      aria_label === "close"
    ) {
      button.remove();
    }
  });

  /*
   * Prevent ESC.
   */
  dialog.$wrapper.on("keydown", function (e) {
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();

      return false;
    }
  });

  /*
   * Prevent outside click dismissal.
   */
  dialog.$wrapper.off("click.dismiss.bs.modal");

  /*
   * Remove secondary/cancel button.
   */
  dialog.$wrapper.find(".modal-footer .btn-secondary").remove();

  /*
   * If navigation occurs while dialog is open,
   * release frontend lock.
   */
  dialog.$wrapper.on("hidden.bs.modal", function () {
    if (!is_active_salary_slip(frm.doc.name)) {
      late_early_dialog_open = false;
    }
  });
}

/* =====================================================
   BLUE URGENT NOTICE
   ===================================================== */

function show_urgent_notice_warning(frm, data) {
  show_attendance_acknowledgement_warning(frm, data);
}

/* =====================================================
   RED HIGH ALERT
   ===================================================== */

function show_high_alert_warning(frm, data) {
  show_attendance_acknowledgement_warning(frm, data);
}

/* =====================================================
   ACKNOWLEDGE SALARY SLIP
   ===================================================== */

async function acknowledge_salary_slip(frm, dialog, acknowledgment_type) {
  /*
   * Prevent double-click.
   */
  if (dialog.__acknowledgement_in_progress) {
    return;
  }

  /*
   * Validate acknowledgement type.
   */
  if (acknowledgment_type !== "late" && acknowledgment_type !== "high_alert") {
    frappe.msgprint({
      title: __("Acknowledgement Failed"),

      message: __("Invalid attendance acknowledgement type."),

      indicator: "red",
    });

    return;
  }

  /*
   * Make sure Salary Slip is still active.
   */
  if (!is_active_salary_slip(frm.doc.name)) {
    return;
  }

  dialog.__acknowledgement_in_progress = true;

  const primary_button = dialog.get_primary_btn();

  if (primary_button) {
    primary_button.prop("disabled", true).text(__("Processing..."));
  }

  try {
    /*
     * Server validates everything again.
     *
     * No freeze here.
     */
    const response = await frappe.call({
      method:
        "pinnaclehrms.pinnacle_hr.doctype.salary_slip.salary_slip.acknowledge_salary_slip",

      args: {
        salary_slip: frm.doc.name,

        acknowledgment_type: acknowledgment_type,
      },

      freeze: false,
    });

    /*
     * User navigated away.
     */
    if (!is_active_salary_slip(frm.doc.name)) {
      return;
    }

    const data = response.message;

    if (!data || !data.success) {
      throw new Error("Backend did not confirm acknowledgement.");
    }

    /*
     * IMPORTANT:
     *
     * Do NOT use frm.reload_doc() here.
     *
     * Reloading the form can trigger another
     * refresh/check while the dialog is being
     * removed, causing SPA overlay/freeze issues.
     *
     * The backend has already updated the field.
     */
    frm.doc.late_acknowledgment = 1;

    /*
     * Hide dialog.
     */
    dialog.hide();

    late_early_dialog_open = false;

    /*
     * Salary can now be displayed.
     */
    show_salary_details(frm);

    /*
     * Show permanent ribbon.
     */
    if (acknowledgment_type === "high_alert") {
      show_high_alert_ribbon(frm);
    } else {
      show_late_acknowledgment_ribbon(frm);
    }

    /*
     * Success message.
     */
    frappe.show_alert({
      message: __("Attendance acknowledgement recorded successfully."),

      indicator: "green",
    });
  } catch (error) {
    console.error("Acknowledgement error:", error);

    /*
     * Release lock only after failure.
     */
    dialog.__acknowledgement_in_progress = false;

    if (primary_button) {
      primary_button.prop("disabled", false).text(__("I Acknowledge"));
    }

    /*
     * Keep the dialog open.
     *
     * User must successfully acknowledge
     * before salary becomes visible.
     */
    if (is_active_salary_slip(frm.doc.name)) {
      frappe.msgprint({
        title: __("Acknowledgement Failed"),

        message: __(
          "Something went wrong while recording your acknowledgement. Please try again.",
        ),

        indicator: "red",
      });
    }
  }
}

/* =====================================================
   FORMAT DATE
   ===================================================== */

function format_readable_date(date_string) {
  if (!date_string) {
    return "";
  }

  /*
   * Handle:
   *
   * 2026-06-01
   *
   * and
   *
   * 2026-06-01T00:00:00
   */
  const clean_date = String(date_string).split("T")[0];

  const parts = clean_date.split("-");

  if (parts.length !== 3) {
    return date_string;
  }

  const year = parseInt(parts[0], 10);

  const month = parseInt(parts[1], 10) - 1;

  const day = parseInt(parts[2], 10);

  const date = new Date(year, month, day);

  return date.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

/* =====================================================
   BLUE ACKNOWLEDGEMENT RIBBON
   ===================================================== */

function show_late_acknowledgment_ribbon(frm) {
  remove_all_acknowledgement_ribbons(frm);

  const ribbon = $(`
        <div
            class="late-acknowledgment-ribbon"
            style="
                margin: 0 0 15px 0;
                padding: 14px 18px;
                background: #e6f4ff;
                border: 1px solid #1677ff;
                border-left: 5px solid #1677ff;
                border-radius: 6px;
                color: #0958d9;
                font-size: 14px;
                line-height: 1.6;
            "
        >

            <strong>
                🔵 Urgent Notice
            </strong>

            <br>

            Your Late/Early attendance acknowledgement
            has been recorded.

        </div>
    `);

  frm.$wrapper.find(".form-layout").first().prepend(ribbon);
}

/* =====================================================
   RED HIGH ALERT RIBBON
   ===================================================== */

function show_high_alert_ribbon(frm) {
  remove_all_acknowledgement_ribbons(frm);

  const ribbon = $(`
        <div
            class="high-alert-ribbon"
            style="
                margin: 0 0 15px 0;
                padding: 14px 18px;
                background: #fff1f0;
                border: 1px solid #ff4d4f;
                border-left: 5px solid #cf1322;
                border-radius: 6px;
                color: #a8071a;
                font-size: 14px;
                line-height: 1.6;
                font-weight: 500;
            "
        >

            <strong>
                🔴 High Alert
            </strong>

            <br>

            Your Late/Early attendance acknowledgement
            has been recorded.

        </div>
    `);

  frm.$wrapper.find(".form-layout").first().prepend(ribbon);
}

/* =====================================================
   REMOVE ALL ACKNOWLEDGEMENT RIBBONS
   ===================================================== */

function remove_all_acknowledgement_ribbons(frm) {
  if (!frm || !frm.$wrapper) {
    return;
  }

  frm.$wrapper
    .find(
      ".late-acknowledgment-ribbon, " +
        ".high-alert-ribbon, " +
        ".late-deduction-ribbon",
    )
    .remove();
}

/* =====================================================
   CLEANUP SALARY SLIP ACKNOWLEDGEMENT UI
   ===================================================== */

function cleanup_salary_slip_acknowledgement_ui() {
  /*
   * --------------------------------------------------
   * Cancel pending timer
   * --------------------------------------------------
   */

  if (salary_slip_ack_check_timer) {
    clearTimeout(salary_slip_ack_check_timer);

    salary_slip_ack_check_timer = null;
  }

  /*
   * --------------------------------------------------
   * Remove acknowledgement dialogs
   * --------------------------------------------------
   */

  $(".late-early-acknowledgement-dialog").each(function () {
    const wrapper = $(this);

    try {
      /*
       * Only hide if Bootstrap modal
       * is actually active.
       */
      if (wrapper.hasClass("show")) {
        wrapper.modal("hide");
      }
    } catch (e) {
      /*
       * Ignore errors during SPA
       * navigation.
       */
    }

    wrapper.remove();
  });

  /*
   * --------------------------------------------------
   * Remove acknowledgement backdrops
   * --------------------------------------------------
   */

  $(".modal-backdrop.late-early-acknowledgement-backdrop").remove();

  /*
   * Remove orphan modal backdrops ONLY when
   * there is no visible modal.
   *
   * This prevents the screen from staying dark
   * after SPA navigation.
   */
  if (!$(".modal.show:visible").length) {
    $(".modal-backdrop").remove();

    $("body").removeClass("modal-open").css("padding-right", "");
  }

  /*
   * --------------------------------------------------
   * Remove Frappe freeze overlay if any
   * --------------------------------------------------
   */

  try {
    if (frappe.dom && frappe.dom.unfreeze) {
      frappe.dom.unfreeze();
    }
  } catch (e) {
    console.warn("Unable to unfreeze Frappe UI:", e);
  }

  /*
   * --------------------------------------------------
   * Remove Salary Slip temporary UI.
   * --------------------------------------------------
   */

  if (cur_frm && cur_frm.doctype === "Salary Slip") {
    remove_salary_block_message(cur_frm);

    remove_all_acknowledgement_ribbons(cur_frm);
  }
}
