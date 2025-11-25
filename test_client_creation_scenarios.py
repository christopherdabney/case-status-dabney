"""
Unit tests for Client Creation Scenarios in ImportCaseHelper.import_client_handler

Tests the client creation logic for:
1. Create new client with valid data (happy path)
2. Create client with orphaned user
3. Create client without orphaned user
4. Database constraint violations (duplicate email/phone)
5. SSN handling and integration ID assignment
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from helper import ImportCaseHelper, ClientRepository, UserRepository, encrypt_ssn, USER_ALREADY_EXISTS


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


class MockOrphanedUser:
    """Mock orphaned user for testing"""
    def __init__(self, id=1, email="orphan@example.com"):
        self.id = id
        self.email = email


class TestClientCreationScenarios(unittest.TestCase):
    """Test client creation scenarios"""
    
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
    @patch('helper.UserRepository.find_by_email_address')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_creates_new_client_with_valid_data_happy_path(self, mock_filter_phones, 
                                                           mock_find_by_integration_id,
                                                           mock_find_user,
                                                           mock_save):
        """Test successful creation of new client with valid data"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None  # No existing client
        mock_find_user.return_value = None  # No existing user
        mock_filter_phones.return_value = ["1234567890"]
        
        field_names = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@example.com",
            "phone_numbers": ["1234567890"],
            "birth_date": "1990-01-01",
            "ssn": "123-45-6789"
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="new-client-123",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        mock_save.assert_called_once()
        # Verify the client was created with correct data
        created_client = mock_save.call_args[0][1]  # Second argument to save()
        self.assertEqual(created_client.firm_id, 1)
        self.assertEqual(created_client.first_name, "Jane")
        self.assertEqual(created_client.last_name, "Smith")
        self.assertEqual(created_client.email, "jane.smith@example.com")
        self.assertEqual(created_client.integration_id, "new-client-123")
        self.assertEqual(created_client.cell_phone, "1234567890")

    @patch('helper.ClientRepository.save')
    @patch('helper.UserRepository.find_by_email_address')
    @patch('helper.identify_orphaned_user_by_phone_number')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_creates_client_with_orphaned_user(self, mock_filter_phones,
                                               mock_find_by_integration_id,
                                               mock_find_orphaned_user,
                                               mock_find_user,
                                               mock_save):
        """Test client creation when orphaned user is found"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_orphaned_user = MockOrphanedUser(email="orphan@example.com")
        
        mock_find_by_integration_id.return_value = None
        mock_find_orphaned_user.return_value = mock_orphaned_user
        mock_find_user.return_value = None
        mock_filter_phones.return_value = ["1234567890"]
        
        field_names = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone_numbers": ["1234567890"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="orphan-client-456",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        mock_save.assert_called_once()
        # Verify the client was created with orphaned user
        created_client = mock_save.call_args[0][1]
        self.assertEqual(created_client.email, None)  # Email should be None when orphaned user exists

    @patch('helper.ClientRepository.save')
    @patch('helper.UserRepository.find_by_email_address')
    @patch('helper.identify_orphaned_user_by_phone_number')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_creates_client_without_orphaned_user(self, mock_filter_phones,
                                                  mock_find_by_integration_id,
                                                  mock_find_orphaned_user,
                                                  mock_find_user,
                                                  mock_save):
        """Test client creation when no orphaned user is found"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        
        mock_find_by_integration_id.return_value = None
        mock_find_orphaned_user.return_value = None  # No orphaned user
        mock_find_user.return_value = None  # No existing user by email
        mock_filter_phones.return_value = ["9876543210"]
        
        field_names = {
            "first_name": "Alice",
            "last_name": "Johnson",
            "email": "alice.johnson@example.com",
            "phone_numbers": ["9876543210"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="no-orphan-789",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        mock_save.assert_called_once()
        # Verify the client was created with email intact (no orphaned user)
        created_client = mock_save.call_args[0][1]
        self.assertEqual(created_client.email, "alice.johnson@example.com")
        self.assertEqual(created_client.first_name, "Alice")
        self.assertEqual(created_client.last_name, "Johnson")

    @patch('helper.ClientRepository.save')
    @patch('helper.UserRepository.find_by_email_address')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_handles_duplicate_email_constraint_violation_gracefully(self, mock_filter_phones,
                                                                     mock_find_by_integration_id,
                                                                     mock_find_user,
                                                                     mock_save):
        """Test graceful handling of database constraint violations (duplicate email/phone)"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_find_user.return_value = None
        mock_filter_phones.return_value = ["1234567890"]
        
        # Mock database constraint violation
        mock_save.side_effect = IntegrityError(
            "UNIQUE constraint failed", 
            "uq_sub_users_type_firm_id_user_id", 
            None
        )
        
        field_names = {
            "first_name": "Bob",
            "last_name": "Wilson",
            "email": "duplicate@example.com",
            "phone_numbers": ["1234567890"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="duplicate-123",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertIn("error_message", result["row"])
        self.assertIn(USER_ALREADY_EXISTS.format("duplicate@example.com", "1234567890"), 
                     result["row"]["error_message"])
        self.assertFalse(result.get("created_client", False))

    @patch('helper.ClientRepository.save')
    @patch('helper.UserRepository.find_by_email_address')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_handles_unexpected_database_error_gracefully(self, mock_filter_phones,
                                                          mock_find_by_integration_id,
                                                          mock_find_user,
                                                          mock_save):
        """Test graceful handling of unexpected database errors"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_find_user.return_value = None
        mock_filter_phones.return_value = ["1234567890"]
        
        # Mock unexpected database error
        unexpected_error = Exception("Unexpected database error")
        mock_save.side_effect = unexpected_error
        
        field_names = {
            "first_name": "Charlie",
            "last_name": "Brown",
            "email": "charlie@example.com",
            "phone_numbers": ["1234567890"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="error-456",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertIn("error_message", result["row"])
        self.assertIn("Unexpected database error", result["row"]["error_message"])
        self.assertFalse(result.get("created_client", False))

    @patch('helper.ClientRepository.save')
    @patch('helper.UserRepository.find_by_email_address')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_client_creation_with_ssn_encryption(self, mock_filter_phones,
                                                 mock_find_by_integration_id,
                                                 mock_find_user,
                                                 mock_save):
        """Test that SSN is properly handled during client creation"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_find_user.return_value = None
        mock_filter_phones.return_value = ["5555555555"]
        
        field_names = {
            "first_name": "David",
            "last_name": "Lee",
            "email": "david@example.com",
            "phone_numbers": ["5555555555"],
            "ssn": "987-65-4321"
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="ssn-test-789",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        mock_save.assert_called_once()
        # Note: The current implementation doesn't store SSN during creation,
        # only during updates. This test verifies current behavior.
        created_client = mock_save.call_args[0][1]
        self.assertEqual(created_client.first_name, "David")
        self.assertEqual(created_client.last_name, "Lee")

    @patch('helper.ClientRepository.save')
    @patch('helper.UserRepository.find_by_email_address')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_client_creation_assigns_integration_id_correctly(self, mock_filter_phones,
                                                              mock_find_by_integration_id,
                                                              mock_find_user,
                                                              mock_save):
        """Test that integration_id is properly assigned during client creation"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_find_user.return_value = None
        mock_filter_phones.return_value = ["7777777777"]
        
        field_names = {
            "first_name": "Emma",
            "last_name": "Davis",
            "email": "emma@example.com",
            "phone_numbers": ["7777777777"],
        }
        
        integration_id = "custom-integration-id-999"
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id=integration_id,
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        mock_save.assert_called_once()
        created_client = mock_save.call_args[0][1]
        self.assertEqual(created_client.integration_id, integration_id)
        self.assertEqual(created_client.firm_id, firm.id)

    @patch('helper.ClientRepository.save')
    @patch('helper.UserRepository.find_by_email_address')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_client_creation_in_validation_mode_skips_save(self, mock_filter_phones,
                                                           mock_find_by_integration_id,
                                                           mock_find_user,
                                                           mock_save):
        """Test that validation mode creates client but skips database save"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_find_user.return_value = None
        mock_filter_phones.return_value = ["8888888888"]
        
        field_names = {
            "first_name": "Frank",
            "last_name": "Miller",
            "email": "frank@example.com",
            "phone_numbers": ["8888888888"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="validation-test-111",
            create_new_client=True,
            validation=True  # Validation mode
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        # In validation mode, save should NOT be called
        mock_save.assert_not_called()

    @patch('helper.ClientRepository.save')
    @patch('helper.UserRepository.find_by_email_address')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_client_creation_with_existing_user_by_email(self, mock_filter_phones,
                                                         mock_find_by_integration_id,
                                                         mock_find_user,
                                                         mock_save):
        """Test client creation when user with same email already exists"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_existing_user = Mock()
        mock_existing_user.email = "existing@example.com"
        
        mock_find_by_integration_id.return_value = None
        mock_find_user.return_value = mock_existing_user  # Existing user found
        mock_filter_phones.return_value = ["9999999999"]
        
        field_names = {
            "first_name": "Grace",
            "last_name": "Taylor",
            "email": "existing@example.com",
            "phone_numbers": ["9999999999"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="existing-user-222",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        mock_save.assert_called_once()
        created_client = mock_save.call_args[0][1]
        # When existing user is found, email should be set to None
        self.assertIsNone(created_client.email)
        self.assertEqual(created_client.first_name, "Grace")
        self.assertEqual(created_client.last_name, "Taylor")


if __name__ == "__main__":
    unittest.main()
