from collections import defaultdict

from ..utils.date_time import (
    is_empty_or_zero,
    parse_time_safe,
)
from ..utils.normalization import coerce_json_arg


def validate_attendance_data(
    attendance_data=None,
):
    """
    Validate final attendance records.

    Returns:

        validated
        non_validated
        total_valid
        total_invalid
    """

    data = coerce_json_arg(attendance_data)

    if not data:
        return {
            "validated": {},
            "non_validated": [],
            "total_valid": 0,
            "total_invalid": 0,
        }

    # ---------------------------------------------------------
    # Normalize input
    # ---------------------------------------------------------

    if isinstance(data, dict):

        rows = []

        for employee in data:
            rows.extend(data[employee])

    elif isinstance(data, list):

        rows = data

    else:

        return {
            "validated": {},
            "non_validated": [],
            "total_valid": 0,
            "total_invalid": 0,
        }

    validated = defaultdict(list)
    non_validated = []

    seen_dates = set()

    # ---------------------------------------------------------
    # Validation rules
    # ---------------------------------------------------------

    def rule_missing_punch(row):

        if is_empty_or_zero(row.get("time")):
            return False, "Missing time"

        return True, None

    def rule_missing_employee(row):

        if not row.get("employee") or not row.get("employee_name"):
            return (
                False,
                "Missing employee information",
            )

        return True, None

    def rule_invalid_time(row):

        time_value = row.get("time")

        if is_empty_or_zero(time_value):
            return True, None

        time_obj = parse_time_safe(str(time_value))

        if time_obj is None:
            return (
                False,
                "Invalid time format",
            )

        return True, None

    def rule_duplicate(row):

        key = (
            row.get("employee"),
            row.get("attendance_date"),
            row.get("time"),
        )

        if key in seen_dates:
            return False, "Duplicate entry"

        seen_dates.add(key)

        return True, None

    validations = [
        rule_missing_punch,
        rule_invalid_time,
        rule_duplicate,
        rule_missing_employee,
    ]

    # ---------------------------------------------------------
    # Run validation
    # ---------------------------------------------------------

    for row in rows:

        errors = []

        for check in validations:

            ok, message = check(row)

            if not ok:
                errors.append(message)

        if errors:

            row["errors"] = errors

            non_validated.append(row)

        else:

            validated[row.get("employee")].append(row)

    validated = dict(validated)

    return {
        "message": "Validation completed",
        "validated": validated,
        "non_validated": non_validated,
        "total_valid": sum(len(value) for value in validated.values()),
        "total_invalid": len(non_validated),
    }
