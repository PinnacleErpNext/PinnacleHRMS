import frappe


def is_user_allowed_for_report(source_name, source_type, user=None):
    """
    Check whether a user is allowed to access a Report or Page.

    Args:
        source_name (str): Name of the Report or Page.
        source_type (str): "Report" or "Page".
        user (str, optional): User to check. Defaults to current session user.

    Rules:
        1. Administrator is always allowed.
        2. Check permissions configured for the specified Report or Page.
        3. Allow access if the user has at least one permitted role.

    Returns:
        bool: True if allowed, False otherwise.
    """

    user = user or frappe.session.user

    # Administrator has unrestricted access
    if user == "Administrator":
        return True

    # Validate source type
    if source_type not in ("Report", "Page"):
        return False

    # Check whether source exists
    if not frappe.db.exists(source_type, source_name):
        return False

    # Fetch source document
    doc = frappe.get_cached_doc(source_type, source_name)

    # Check configured role permissions
    return bool(doc.is_permitted())
