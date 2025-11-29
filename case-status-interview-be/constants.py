"""
Constants and Configuration

Contains constants, enums, and configuration helpers used across the application.
"""

class IntegrationHelper:
    """Constants and helpers for integration types."""
    CSV_IMPORT = "CSV_IMPORT"
    THIRD_PARTY = "THIRD_PARTY"
    MYCASE = "MYCASE"

# Error Message Constants

CLIENT_MISSING_NAME = "Client missing name."
CELL_PHONE_INVALID = "Cell phone invalid: {}"
CLIENT_NOT_FOUND_STOP_ZAP = "Client not found, stopping import."
USER_ALREADY_EXISTS = "User already exists: {}, {}"
CLIENT_UPDATED = "Client updated."
CLIENT_CONTACT_INFO_FIELD_NAMES = ["first_name", "last_name", "email", "cell_phone"]