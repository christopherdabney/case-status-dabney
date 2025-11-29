"""
Unit tests for Database Transaction Management in ImportCaseHelper.import_client_handler

Tests the database transaction handling for:
1. Successful commits
2. Rollback on exceptions
3. Session handling in error cases
4. Database constraint violations
5. Transaction state management
"""

import unittest
from unittest.mock import Mock, patch
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from services import ImportCaseHelper
from repositories import ClientRepository
from helper import USER_ALREADY_EXISTS


class MockClient:
    """Mock client object for testing"""
    def __init__(self, id=1, firm_id=1, first_name="John", last_name="Doe", 
                 email="john@example.com", integration_id="int-123", 
                 cell_phone="1234567890", birth_date=None, ssn=None):
        self.id = id
        self.firm_id = firm_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.integration_id = integration_id
        self.cell_phone = cell_phone
        self.birth_date = birth_date
        self.ssn = ssn


class MockFirm:
    """Mock firm object for testing"""
    def __init__(self, id=1, is_corporate=False):
        self.id = id
        self.is_corporate = is_corporate
        self.integration_settings = {
            "update_client_missing_data": True,
            "sync_client_contact_info": True,
        }


class TestDatabaseTransactionManagement(unittest.TestCase):
    """Test database transaction management"""
    
    def setUp(self):
        """Set up test fixtures"""
        import app
        app.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        self.app = app.app
        self.app_context = self.app.app_context()
        self.app_context.push()
        app.db.create_all()
        self.session = app.db.session
        
    def tearDown(self):
        """Clean up test fixtures"""
        import app
        app.db.session.remove()
        app.db.drop_all()
        self.app_context.pop()

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_successful_client_creation_commits_transaction(self, mock_filter_phones,
                                                           mock_find_by_integration_id,
                                                           mock_save):
        """Test that successful client creation commits the transaction"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["5551234567"]
        
        field_names = {
            "first_name": "Success",
            "last_name": "Test",
            "email": "success@example.com",
            "phone_numbers": ["5551234567"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="success-123",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        mock_save.assert_called_once()

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_database_integrity_error_triggers_rollback(self, mock_filter_phones,
                                                        mock_find_by_integration_id,
                                                        mock_save):
        """Test that database integrity errors trigger session rollback"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["5551234567"]
        
        # Mock IntegrityError with expected constraint violation
        integrity_error = IntegrityError(
            "UNIQUE constraint failed",
            "uq_sub_users_type_firm_id_user_id",
            None
        )
        mock_save.side_effect = integrity_error
        
        field_names = {
            "first_name": "Duplicate",
            "last_name": "User",
            "email": "duplicate@example.com",
            "phone_numbers": ["5551234567"],
        }
        
        # Act
        with patch.object(self.session, 'rollback') as mock_rollback:
            result = ImportCaseHelper.import_client_handler(
                session=self.session,
                firm=firm,
                row={},
                field_names=field_names,
                integration_id="duplicate-456",
                create_new_client=True,
                validation=False
            )
        
        # Assert
        mock_rollback.assert_called_once()
        self.assertIn("error_message", result["row"])
        self.assertIn(USER_ALREADY_EXISTS.format("duplicate@example.com", "5551234567"), 
                     result["row"]["error_message"])

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_unexpected_database_error_triggers_rollback(self, mock_filter_phones,
                                                         mock_find_by_integration_id,
                                                         mock_save):
        """Test that unexpected database errors trigger session rollback"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["5551234567"]
        
        # Mock unexpected database error
        unexpected_error = DatabaseError("Unexpected database connection error", None, None)
        mock_save.side_effect = unexpected_error
        
        field_names = {
            "first_name": "Error",
            "last_name": "Test",
            "email": "error@example.com",
            "phone_numbers": ["5551234567"],
        }
        
        # Act
        with patch.object(self.session, 'rollback') as mock_rollback:
            result = ImportCaseHelper.import_client_handler(
                session=self.session,
                firm=firm,
                row={},
                field_names=field_names,
                integration_id="error-789",
                create_new_client=True,
                validation=False
            )
        
        # Assert
        mock_rollback.assert_called_once()
        self.assertIn("error_message", result["row"])
        self.assertIn("Unexpected database connection error", result["row"]["error_message"])

    @patch('helper._update_client')
    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_successful_client_update_commits_transaction(self, mock_filter_phones,
                                                          mock_find_by_integration_id,
                                                          mock_save,
                                                          mock_update_client):
        """Test that successful client updates commit the transaction"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        firm.integration_settings["sync_client_contact_info"] = True
        firm.integration_settings["update_client_missing_data"] = True
        
        existing_client = MockClient()
        
        mock_find_by_integration_id.return_value = existing_client
        mock_filter_phones.return_value = ["5551234567"]
        mock_update_client.return_value = True
        
        field_names = {
            "first_name": "Updated",
            "last_name": "Client",
            "email": "updated@example.com",
            "phone_numbers": ["5551234567"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="update-success-111",
            create_new_client=False,
            validation=False
        )
        
        # Assert
        mock_update_client.assert_called_once()
        mock_save.assert_called_once_with(self.session, existing_client)

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_validation_mode_skips_transaction_operations(self, mock_filter_phones,
                                                          mock_find_by_integration_id,
                                                          mock_save):
        """Test that validation mode skips actual database transaction operations"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["5551234567"]
        
        field_names = {
            "first_name": "Validation",
            "last_name": "Mode",
            "email": "validation@example.com",
            "phone_numbers": ["5551234567"],
        }
        
        # Act
        with patch.object(self.session, 'commit') as mock_commit:
            with patch.object(self.session, 'rollback') as mock_rollback:
                result = ImportCaseHelper.import_client_handler(
                    session=self.session,
                    firm=firm,
                    row={},
                    field_names=field_names,
                    integration_id="validation-222",
                    create_new_client=True,
                    validation=True
                )
        
        # Assert - no database operations in validation mode
        mock_save.assert_not_called()
        mock_commit.assert_not_called()
        mock_rollback.assert_not_called()

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_session_rollback_on_client_creation_exception(self, mock_filter_phones,
                                                           mock_find_by_integration_id,
                                                           mock_save):
        """Test that session rollback occurs when client creation raises any exception"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["5551234567"]
        
        # Mock generic exception during save
        generic_error = Exception("Generic save error")
        mock_save.side_effect = generic_error
        
        field_names = {
            "first_name": "Exception",
            "last_name": "Test",
            "email": "exception@example.com",
            "phone_numbers": ["5551234567"],
        }
        
        # Act
        with patch.object(self.session, 'rollback') as mock_rollback:
            result = ImportCaseHelper.import_client_handler(
                session=self.session,
                firm=firm,
                row={},
                field_names=field_names,
                integration_id="exception-333",
                create_new_client=True,
                validation=False
            )
        
        # Assert
        mock_rollback.assert_called_once()
        self.assertIn("error_message", result["row"])

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_known_integrity_error_patterns_handled_gracefully(self, mock_filter_phones,
                                                               mock_find_by_integration_id,
                                                               mock_save):
        """Test that known integrity error patterns are handled with user-friendly messages"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["5551234567"]
        
        # Test different known error patterns
        known_errors = [
            IntegrityError("UNIQUE constraint failed", "uq_sub_users_type_firm_id_user_id", None),
            Exception("The email or phone number you entered is already in use")
        ]
        
        field_names = {
            "first_name": "Known",
            "last_name": "Error",
            "email": "known@example.com",
            "phone_numbers": ["5551234567"],
        }
        
        for i, error in enumerate(known_errors):
            mock_save.side_effect = error
            
            # Act
            result = ImportCaseHelper.import_client_handler(
                session=self.session,
                firm=firm,
                row={},
                field_names=field_names,
                integration_id=f"known-error-{i}",
                create_new_client=True,
                validation=False
            )
            
            # Assert
            self.assertIn("error_message", result["row"])
            self.assertIn(USER_ALREADY_EXISTS.format("known@example.com", "5551234567"), 
                         result["row"]["error_message"])

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_error_logging_during_exception_handling(self, mock_filter_phones,
                                                     mock_find_by_integration_id,
                                                     mock_save):
        """Test that errors are logged during exception handling"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["5551234567"]
        
        test_error = Exception("Test logging error")
        mock_save.side_effect = test_error
        
        field_names = {
            "first_name": "Logging",
            "last_name": "Test",
            "email": "logging@example.com",
            "phone_numbers": ["5551234567"],
        }
        
        # Act
        with patch('builtins.print') as mock_print:
            result = ImportCaseHelper.import_client_handler(
                session=self.session,
                firm=firm,
                row={},
                field_names=field_names,
                integration_id="logging-555",
                create_new_client=True,
                validation=False
            )
        
        # Assert
        mock_print.assert_called_once()
        # Verify the error was logged
        logged_message = mock_print.call_args[0][0]
        self.assertIn("import_client_handler():", logged_message)
        self.assertIn("Test logging error", logged_message)


if __name__ == "__main__":
    unittest.main()
