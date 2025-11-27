"""
Service Layer - Business Logic

Contains all business logic for client import operations.
Services orchestrate repositories and implement complex workflows.
"""
from sqlalchemy import exc
from repositories import ClientRepository, UserRepository
import helper


class ImportCaseHelper:
    """
    Service for handling client import operations.
    
    Contains the main business logic for client import workflows.
    This class contains the god method that will be refactored next.
    """

    @staticmethod
    def parse_cell_phone_number(number, firm):
        """Parse and validate cell phone number based on firm settings."""
        # Implementation placeholder - currently stubbed
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
            helper.log_integration_response(
                firm.id,
                integration_response_object,
                request="Client object",
                matter_id=matter_id,
            )

        # Get Client Data:
        first_name = field_names.get("first_name")
        last_name = field_names.get("last_name")
        client_name = field_names.get("name")
        company_name = first_name if field_names.get("type") == "Company" else None

        phone_numbers = field_names.get("phone_numbers", [])
        if phone_numbers is None:
            phone_numbers = []

        filtered_cell_phone_numbers = helper.filter_cell_phone_numbers(phone_numbers, firm)

        primary_number = (
            filtered_cell_phone_numbers[0] if filtered_cell_phone_numbers else None
        )

        # Handle cases where an integration provides a name, but no first/last name
        if client_name and (not first_name or not last_name):
            split_name = client_name.split(" ")
            first_name = split_name[0]
            if len(split_name) > 1:
                last_name = " ".join(split_name[1:])

            field_names["first_name"] = first_name
            field_names["last_name"] = last_name

        client_email_address = field_names.get("email")
        birth_date = field_names.get("birth_date")
        ssn = field_names.get("ssn")

        row["email"] = client_email_address
        row["first_name"] = first_name
        row["last_name"] = last_name
        row["cell_phone"] = ", ".join(
            number for number in phone_numbers if number is not None
        )
        results["company_name"] = company_name

        # Check to see if client can be found in system already
        # Integration ID is easiest
        if integration_id:
            client_instance = ClientRepository.find_by_integration_id(
                session, firm.id, integration_id
            )
        # If the client is corporate, they may be found by an email address
        if not client_instance and firm.is_corporate and client_email_address:
            client_instance = ClientRepository.find_by_email_address(
                session, client_email_address, firm.id
            )
        # If still no client, try to use a cell phone number
        if not client_instance and filtered_cell_phone_numbers:
            for phone_number in filtered_cell_phone_numbers:
                client_instance = ClientRepository.find_by_phone_number_firm(
                    session, phone_number, firm.id
                )
                # When found by cell number, record that number in the row and move on
                if client_instance:
                    row["cell_phone"] = phone_number
                    break

                orphaned_user = helper.identify_orphaned_user_by_phone_number(
                    session,
                    phone_number,
                    first_name=first_name,
                    last_name=last_name,
                    client_email_address=client_email_address,
                )
                if orphaned_user:
                    row["cell_phone"] = phone_number
                    break
        if not client_instance and not orphaned_user:
            if integration_type in (
                helper.IntegrationHelper.CSV_IMPORT,
                helper.IntegrationHelper.THIRD_PARTY,
            ):
                # Must have valid first and last name to proceed
                missing_fields = [
                    field[0]
                    for field in [
                        ("client_first_name", first_name),
                        ("client_last_name", last_name),
                    ]
                    if not field[1]
                ]
                if missing_fields:
                    row["error_fields"] = missing_fields
                    row["error_message"] = helper.CLIENT_MISSING_NAME
                    results["row"].update(row)
                    return results
            else:
                if not first_name:
                    row["error_fields"] = ["client_first_name"]
                    row["error_message"] = helper.CLIENT_MISSING_NAME
                    results["row"].update(row)
                    return results
            if not firm.is_corporate and not filtered_cell_phone_numbers:
                row["error_fields"] = ["client_cell_phone"]
                row["error_message"] = helper.CELL_PHONE_INVALID.format(
                    row["cell_phone"] or "<None>"
                )
                results["row"].update(row)
                return results

            if not create_new_client:
                row["error_message"] = helper.CLIENT_NOT_FOUND_STOP_ZAP
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
                from models import Client

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
                    row["error_message"] = helper.USER_ALREADY_EXISTS.format(
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
                    if k in helper.CLIENT_CONTACT_INFO_FIELD_NAMES
                }
                # There is a chance that an integration would pass us a null value for cell phone number.
                # We do not ever want to null out a client cell phone number.
                if primary_number:
                    client_data_to_update["cell_phone"] = primary_number

            if firm.integration_settings.get("update_client_missing_data"):
                if integration_type in (
                    helper.IntegrationHelper.CSV_IMPORT,
                    helper.IntegrationHelper.THIRD_PARTY,
                    helper.IntegrationHelper.MYCASE,
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
                client_updated = helper._update_client(
                    session, client_instance, client_data_to_update
                )

            if (
                client_updated
                or hasattr(client_instance, "_committed_changes")
                and client_instance.has_changes()
            ):
                row["success_msg"] = helper.CLIENT_UPDATED
                if not validation:
                    ClientRepository.save(session, client_instance)

        results["row"].update(row)
        results["client"] = client_instance
        return results