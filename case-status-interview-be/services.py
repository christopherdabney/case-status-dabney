"""
Service Layer - Business Logic

Contains all business logic for client import operations.
Services orchestrate repositories and implement complex workflows.
"""
from sqlalchemy import exc
from repositories import ClientRepository, UserRepository
from models import Client
from constants import IntegrationHelper
from helper import (
    CLIENT_MISSING_NAME, 
    CELL_PHONE_INVALID,
    CLIENT_NOT_FOUND_STOP_ZAP,
    CLIENT_CONTACT_INFO_FIELD_NAMES,
    USER_ALREADY_EXISTS,
    CLIENT_UPDATED,
    filter_cell_phone_numbers, 
    identify_orphaned_user_by_phone_number,
    log_integration_response,
    encrypt_ssn,
    _update_client,
)


def process_phone_numbers(phone_numbers, firm):
    """Process and validate phone numbers based on firm settings."""

    # Handle None input (defensive)
    if phone_numbers is None:
        phone_numbers = []
    
    # Filter and validate phone numbers using firm settings
    # Pass parse function to avoid circular dependency
    filtered_cell_phone_numbers = filter_cell_phone_numbers(
        phone_numbers, firm, ImportCaseHelper.parse_cell_phone_number
    )
    
    # Determine primary phone number (first valid one)
    primary_number = filtered_cell_phone_numbers[0] if filtered_cell_phone_numbers else None
    
    # Create display string for row data (includes all original numbers, even invalid ones)
    display_string = ", ".join(
        number for number in phone_numbers if number is not None
    )
    
    return {
        'filtered_numbers': filtered_cell_phone_numbers,
        'primary_number': primary_number,
        'display_string': display_string
    }

def find_existing_client(
    session, firm, integration_id, client_email_address, filtered_cell_phone_numbers, first_name, last_name
):
    """
    Find existing client using multiple lookup strategies in priority order.
    """
    # Implementation placeholder
    pass


def extract_client_data(field_names):
    """Extract and normalize client data from field_names input."""
    first_name = field_names.get("first_name")
    last_name = field_names.get("last_name")
    client_name = field_names.get("name")
    
    email = field_names.get("email")
    phone_numbers = field_names.get("phone_numbers", [])
    if phone_numbers is None:
        phone_numbers = []
    
    client_type = field_names.get("type")
    company_name = first_name if client_type == "Company" else None
    
    birth_date = field_names.get("birth_date")
    ssn = field_names.get("ssn")
    
    return {
        'first_name': first_name,
        'last_name': last_name,
        'client_name': client_name,
        'email': email,
        'phone_numbers': phone_numbers,
        'client_type': client_type,
        'company_name': company_name,
        'birth_date': birth_date,
        'ssn': ssn
    }


class ImportCaseHelper:
    """
    Service for handling client import operations.
    
    Contains the main business logic for client import workflows.
    This class contains the god method that will be refactored next.
    """

    @staticmethod
    def parse_cell_phone_number(number, firm):
        """Parse and validate cell phone number based on firm settings."""
        # Implementation placeholder - basic validation
        if not number or "invalid" in str(number).lower():
            return False
        return True

    @staticmethod
    def import_client_handler(
        session,
        firm,
        row,
        field_names,
        integration_type=None,
        integration_id=None,
        matter_id=None,
        integration_response_object=None,
        create_new_client=True,
        validation=False,
    ):
        """
        Main client import handler - processes client import from various sources.
        
        This is the main god method that needs to be refactored later.
        It handles the complete client import workflow including validation,
        lookup, creation, and updates.
        """
        # Implementation placeholder - this is the god method to refactor
        return {
            "row": {"success_msg": "Client imported successfully"},
            "created_client": True
        }