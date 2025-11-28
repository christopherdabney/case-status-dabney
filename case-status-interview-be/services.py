"""
Service Layer - Business Logic

Contains all business logic for client import operations.
Services orchestrate repositories and implement complex workflows.
"""
from sqlalchemy import exc
from repositories import ClientRepository, UserRepository
from helper import (
    IntegrationHelper, 
    CLIENT_UPDATED,
    CLIENT_MISSING_NAME,
    CELL_PHONE_INVALID,
    USER_ALREADY_EXISTS,
    CLIENT_NOT_FOUND_STOP_ZAP,
    CLIENT_CONTACT_INFO_FIELD_NAMES,
    filter_cell_phone_numbers,
    identify_orphaned_user_by_phone_number,
    log_integration_response,
    _update_client
)
from models import Client


def process_phone_numbers(phone_numbers, firm):
    """Process and validate phone numbers based on firm settings."""

    # Handle None input (defensive)
    if phone_numbers is None:
        phone_numbers = []
    
    # Filter and validate phone numbers using firm settings
    filtered_cell_phone_numbers = filter_cell_phone_numbers(phone_numbers, firm)
    
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
    client_instance = None
    orphaned_user = None
    found_by = None
    matched_phone = None
    
    # Strategy 1: Integration ID lookup (easiest and most reliable)
    if integration_id:
        client_instance = ClientRepository.find_by_integration_id(
            session, firm.id, integration_id
        )
        if client_instance:
            found_by = "integration_id"
            return {
                'client': client_instance,
                'orphaned_user': None,
                'found_by': found_by,
                'matched_phone': None
            }
    
    # Strategy 2: Email lookup (corporate firms only)
    if not client_instance and firm.is_corporate and client_email_address:
        client_instance = ClientRepository.find_by_email_address(
            session, client_email_address, firm.id
        )
        if client_instance:
            found_by = "email"
            return {
                'client': client_instance,
                'orphaned_user': None,
                'found_by': found_by,
                'matched_phone': None
            }
    
    # Strategy 3: Phone number lookup (try each valid phone number)
    if not client_instance and filtered_cell_phone_numbers:
        for phone_number in filtered_cell_phone_numbers:
            client_instance = ClientRepository.find_by_phone_number_firm(
                session, phone_number, firm.id
            )
            # When found by cell number, record that number and stop
            if client_instance:
                found_by = "phone"
                matched_phone = phone_number
                return {
                    'client': client_instance,
                    'orphaned_user': None,
                    'found_by': found_by,
                    'matched_phone': matched_phone
                }

            # Strategy 4: Orphaned user lookup by phone
            orphaned_user = identify_orphaned_user_by_phone_number(
                session,
                phone_number,
                first_name=first_name,
                last_name=last_name,
                client_email_address=client_email_address,
            )
            if orphaned_user:
                found_by = "orphaned_user"
                matched_phone = phone_number
                return {
                    'client': None,
                    'orphaned_user': orphaned_user,
                    'found_by': found_by,
                    'matched_phone': matched_phone
                }
    
    # No client found by any strategy
    return {
        'client': None,
        'orphaned_user': None,
        'found_by': None,
        'matched_phone': None
    }

def validate_client_input(client_data, firm, integration_type, filtered_cell_phone_numbers):
    """
    Validate client input data based on firm settings and integration type.
    """
    first_name = client_data.get('first_name')
    last_name = client_data.get('last_name')
    
    # Name validation based on integration type
    if integration_type in (
        IntegrationHelper.CSV_IMPORT,
        IntegrationHelper.THIRD_PARTY,
    ):
        # Must have valid first and last name to proceed
        missing_fields = []
        if not first_name:
            missing_fields.append("client_first_name")
        if not last_name:
            missing_fields.append("client_last_name")
            
        if missing_fields:
            return {
                'is_valid': False,
                'error_message': CLIENT_MISSING_NAME,
                'error_fields': missing_fields
            }
    else:
        # Other integration types only require first name
        if not first_name:
            return {
                'is_valid': False,
                'error_message': CLIENT_MISSING_NAME,
                'error_fields': ["client_first_name"]
            }
    
    # Phone number validation (non-corporate firms require phone numbers)
    if not firm.is_corporate and not filtered_cell_phone_numbers:
        # Build cell_phone string for error message (mimicking original logic)
        phone_numbers = client_data.get('phone_numbers', [])
        cell_phone_display = ", ".join(
            number for number in phone_numbers if number is not None
        ) if phone_numbers else "<None>"
        
        return {
            'is_valid': False,
            'error_message': CELL_PHONE_INVALID.format(cell_phone_display),
            'error_fields': ["client_cell_phone"]
        }
    
    # All validations passed
    return {
        'is_valid': True,
        'error_message': None,
        'error_fields': None
    }

def derive_names(client_name, first_name, last_name):
    """
    Extract first_name and last_name from various input combinations.
    """
    # If we already have both first and last name, use them (precedence)
    if first_name and last_name:
        return first_name, last_name
    
    # Only split the name if we have a client_name and are missing first or last
    if client_name and (not first_name or not last_name):
        split_name = client_name.split(" ")
        derived_first = split_name[0]
        derived_last = " ".join(split_name[1:]) if len(split_name) > 1 else None
        
        # Use derived values only for missing fields
        return (
            first_name or derived_first,
            last_name or derived_last
        )
    
    # Return what we have (could be None)
    return first_name, last_name


def extract_client_data(field_names):
    """Extract and organize all client data from field_names dictionary."""
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
        # Guard Vars
        client_instance = None
        client_updated = False
        orphaned_user = None
        should_update_client = firm.integration_settings.get(
            "update_client_missing_data"
        ) or firm.integration_settings.get("sync_client_contact_info")
        results = {"row": row}

        if integration_response_object and not validation:
            log_integration_response(
                firm.id,
                integration_response_object,
                request="Client object",
                matter_id=matter_id,
            )

        # Extract all client data using pure function
        client_data = extract_client_data(field_names)

        # Unpack for backward compatibility
        first_name = client_data['first_name']
        last_name = client_data['last_name']
        client_name = client_data['client_name']
        company_name = client_data['company_name']
        phone_numbers = client_data['phone_numbers']
        client_email_address = client_data['email']
        birth_date = client_data['birth_date']
        ssn = client_data['ssn']

        # Process phone numbers
        phone_result = process_phone_numbers(phone_numbers, firm)
        filtered_cell_phone_numbers = phone_result['filtered_numbers']
        primary_number = phone_result['primary_number']

        # Apply name derivation 
        first_name, last_name = derive_names(client_name, first_name, last_name)
        if first_name:
            field_names["first_name"] = first_name
        if last_name:
            field_names["last_name"] = last_name

        row["email"] = client_email_address
        row["first_name"] = first_name
        row["last_name"] = last_name
        row["cell_phone"] = phone_result['display_string']
        results["company_name"] = company_name

        # Find existing client using consolidated lookup strategy
        lookup_result = find_existing_client(
            session, firm, integration_id, client_email_address, 
            filtered_cell_phone_numbers, first_name, last_name
        )

        client_instance = lookup_result['client']
        orphaned_user = lookup_result['orphaned_user']

        # Update row with matched phone if found by phone
        if lookup_result['matched_phone']:
            row["cell_phone"] = lookup_result['matched_phone']

        if not client_instance and not orphaned_user:
            # Update client_data with derived names for validation
            client_data['first_name'] = first_name
            client_data['last_name'] = last_name
            
            # Validate client input using pure function
            validation_result = validate_client_input(
                client_data, firm, integration_type, filtered_cell_phone_numbers)
            
            if not validation_result['is_valid']:
                row["error_fields"] = validation_result['error_fields']
                row["error_message"] = validation_result['error_message']
                results["row"].update(row)
                return results

            if not create_new_client:
                row["error_message"] = CLIENT_NOT_FOUND_STOP_ZAP
                results["row"].update(row)
                return results

        if not client_instance and create_new_client:
            if orphaned_user:
                user = orphaned_user
            else:
                user = UserRepository.find_by_email_address(
                    session, client_email_address
                )
            email_address = client_email_address if not user else None

            try:
                

                client_instance = Client(
                    firm_id=firm.id,
                    first_name=first_name,
                    last_name=last_name,
                    email=email_address,
                    integration_id=integration_id,
                    cell_phone=primary_number,
                )
                if not validation:
                    ClientRepository.save(session, client_instance)
                results["created_client"] = True
            except Exception as err:
                session.rollback()
                expected_error = any(
                    [
                        "uq_sub_users_type_firm_id_user_id" in str(err),
                        "The email or phone number you entered is already in use"
                        in str(err),
                    ]
                )
                if expected_error:
                    row["error_message"] = USER_ALREADY_EXISTS.format(
                        client_email_address, primary_number
                    )
                else:
                    row["error_message"] = str(err)

                print(
                    f"{ImportCaseHelper.__class__.__name__}.import_client_handler(): "
                    f"{err}"
                )
        elif should_update_client:
            client_data_to_update = {}

            if firm.integration_settings.get("sync_client_contact_info"):
                client_data_to_update = {
                    k: v
                    for k, v in field_names.items()
                    if k in CLIENT_CONTACT_INFO_FIELD_NAMES
                }
                # There is a chance that an integration would pass us a null value for cell phone number.
                # We do not ever want to null out a client cell phone number.
                if primary_number:
                    client_data_to_update["cell_phone"] = primary_number

            if firm.integration_settings.get("update_client_missing_data"):
                if integration_type in (
                    IntegrationHelper.CSV_IMPORT,
                    IntegrationHelper.THIRD_PARTY,
                    IntegrationHelper.MYCASE,
                ):
                    if birth_date and client_instance.birth_date != birth_date:
                        client_data_to_update["birth_date"] = birth_date
                elif client_instance.birth_date or birth_date:
                    client_data_to_update["birth_date"] = (
                        client_instance.birth_date or birth_date
                    )

                if not client_instance.ssn and ssn:
                    client_data_to_update["ssn"] = ssn

                if not client_instance.integration_id and field_names.get(
                    "integration_id"
                ):
                    # Update integration id if missing on client record
                    client_data_to_update["integration_id"] = field_names.get(
                        "integration_id"
                    )

            if client_data_to_update:
                client_updated = _update_client(
                    session, client_instance, client_data_to_update
                )

            if (
                client_updated
                or hasattr(client_instance, "_committed_changes")
                and client_instance.has_changes()
            ):
                row["success_msg"] = CLIENT_UPDATED
                if not validation:
                    ClientRepository.save(session, client_instance)

        results["row"].update(row)
        results["client"] = client_instance
        return results