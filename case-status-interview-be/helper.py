"""
Utilities and Helper Functions

Contains utility functions, constants, and integration helpers.
Repository layer is in repositories.py, service layer is in services.py.
"""
from sqlalchemy import exc
from repositories import ClientRepository, UserRepository


# Integration Helper Classes

class IntegrationHelper:
    """Constants and helpers for integration types."""
    CSV_IMPORT = "CSV_IMPORT"
    THIRD_PARTY = "THIRD_PARTY"
    MYCASE = "MYCASE"


# Utility Functions

def log_integration_response(
    firm_id, integration_response_object, request=None, matter_id=None
):
    """Log integration response for debugging and audit purposes."""
    # Implementation placeholder
    pass


def identify_orphaned_user_by_phone_number(
    session, phone_number, first_name=None, last_name=None, client_email_address=None
):
    """Identify orphaned users by phone number matching."""
    # Implementation placeholder
    pass


def encrypt_ssn(ssn):
    """Encrypt SSN for secure storage."""
    # Implementation placeholder - returns SSN as-is
    return ssn


def filter_cell_phone_numbers(phone_numbers, firm):
    """Filter and validate phone numbers based on firm settings."""
    # Import here to avoid circular import
    valid_numbers = []
    for number in phone_numbers:
        is_valid = ImportCaseHelper.parse_cell_phone_number(number, firm)
        if is_valid:
            valid_numbers.append(number)  # Append the actual number, not True
    return valid_numbers


def _update_client(session, client_instance, client_data_to_update):
    """Update client instance with provided data."""
    updated = False
    for field, value in client_data_to_update.items():
        if hasattr(client_instance, field) and value is not None:
            setattr(client_instance, field, value)
            updated = True
    if updated:
        session.commit()
    return updated


# Error Message Constants

CLIENT_MISSING_NAME = "Client missing name."
CELL_PHONE_INVALID = "Cell phone invalid: {}"
CLIENT_NOT_FOUND_STOP_ZAP = "Client not found, stopping import."
USER_ALREADY_EXISTS = "User already exists: {}, {}"
CLIENT_UPDATED = "Client updated."
CLIENT_CONTACT_INFO_FIELD_NAMES = ["first_name", "last_name", "email", "cell_phone"]


# Backwards Compatibility - Re-export service layer
from services import ImportCaseHelper