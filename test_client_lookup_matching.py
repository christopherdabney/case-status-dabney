"""
Unit tests for Client Lookup & Matching Logic in ImportCaseHelper.import_client_handler

Tests the various ways the import_client_handler method finds existing clients:
1. By integration_id (highest priority)
2. By email address (corporate firms only)
3. By phone number (iterates through all provided numbers)
4. Orphaned user lookup by phone number
5. No client found scenarios
"""

import unittest
from unittest.mock import Mock, patch
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from helper import ImportCaseHelper, ClientRepository, identify_orphaned_user_by_phone_number


class MockClient:
    """Mock client object for testing"""
    def __init__(self, id=1, firm_id=1, first_name="John", last_name="Doe", 
                 email="john@example.com", integration_id="int-123", 
                 cell_phone="1234567890"):
        self.id = id
        self.firm_id = firm_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.integration_id = integration_id
        self.cell_phone = cell_phone
        self.birth_date = None
        self.ssn = None


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


class TestClientLookupMatching(unittest.TestCase):
    """Test client lookup and matching logic"""
    
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

    @patch('helper.ClientRepository.find_by_integration_id')
    def test_finds_client_by_integration_id_highest_priority(self, mock_find_by_integration_id):
        """Test that client is found by integration_id when available (highest priority lookup)"""
        # Arrange
        firm = MockFirm(id=1)
        mock_client = MockClient(integration_id="int-123")
        mock_find_by_integration_id.return_value = mock_client
        
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
            integration_id="int-123",
            create_new_client=False,
            validation=True
        )
        
        # Assert
        mock_find_by_integration_id.assert_called_once_with(self.session, 1, "int-123")
        self.assertIsNotNone(result.get("client"))
        self.assertEqual(result["client"].integration_id, "int-123")

    @patch('helper.ClientRepository.find_by_email_address')
    @patch('helper.ClientRepository.find_by_integration_id')
    def test_finds_client_by_email_corporate_firm_only(self, mock_find_by_integration_id, mock_find_by_email):
        """Test that client is found by email address only for corporate firms"""
        # Arrange
        corporate_firm = MockFirm(id=1, is_corporate=True)
        mock_client = MockClient(email="john@corporate.com")
        mock_find_by_integration_id.return_value = None  # No client found by integration_id
        mock_find_by_email.return_value = mock_client
        
        field_names = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@corporate.com",
            "phone_numbers": ["1234567890"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=corporate_firm,
            row={},
            field_names=field_names,
            integration_id="int-456",
            create_new_client=False,
            validation=True
        )
        
        # Assert
        mock_find_by_email.assert_called_once_with(self.session, "john@corporate.com", 1)
        self.assertIsNotNone(result.get("client"))
        self.assertEqual(result["client"].email, "john@corporate.com")

    @patch('helper.ClientRepository.find_by_email_address')
    @patch('helper.ClientRepository.find_by_integration_id')
    def test_skips_email_lookup_non_corporate_firm(self, mock_find_by_integration_id, mock_find_by_email):
        """Test that email lookup is skipped for non-corporate firms"""
        # Arrange
        non_corporate_firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        
        field_names = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone_numbers": ["1234567890"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=non_corporate_firm,
            row={},
            field_names=field_names,
            integration_id="int-789",
            create_new_client=True,  # Allow creation to complete the flow
            validation=True
        )
        
        # Assert - email lookup should NOT be called for non-corporate firms
        mock_find_by_email.assert_not_called()

    @patch('helper.identify_orphaned_user_by_phone_number')
    @patch('helper.ClientRepository.find_by_phone_number_firm')
    @patch('helper.ClientRepository.find_by_email_address')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_finds_client_by_phone_number_iterates_all_numbers(self, mock_filter_phones, 
                                                                mock_find_by_integration_id,
                                                                mock_find_by_email,
                                                                mock_find_by_phone,
                                                                mock_find_orphaned_user):
        """Test that client lookup iterates through all phone numbers until match found"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)  # Non-corporate to skip email lookup
        mock_client = MockClient(cell_phone="9876543210")
        
        mock_find_by_integration_id.return_value = None
        mock_find_by_email.return_value = None
        mock_filter_phones.return_value = ["1234567890", "9876543210", "5555555555"]
        
        # Mock phone lookup - first call returns None, second returns client
        mock_find_by_phone.side_effect = [None, mock_client, None]
        mock_find_orphaned_user.return_value = None
        
        field_names = {
            "first_name": "John",
            "last_name": "Doe",
            "phone_numbers": ["1234567890", "9876543210", "5555555555"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="test-456",
            create_new_client=False,
            validation=True
        )
        
        # Assert
        self.assertEqual(mock_find_by_phone.call_count, 2)  # Should stop after finding match
        mock_find_by_phone.assert_any_call(self.session, "1234567890", 1)
        mock_find_by_phone.assert_any_call(self.session, "9876543210", 1)
        self.assertIsNotNone(result.get("client"))
        # The client should be the mock_client we returned
        self.assertEqual(result["client"], mock_client)
        # The row should record the phone number that was matched
        self.assertEqual(result["row"]["cell_phone"], "9876543210")

    @patch('helper.identify_orphaned_user_by_phone_number')
    @patch('helper.ClientRepository.find_by_phone_number_firm')
    @patch('helper.ClientRepository.find_by_email_address')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_finds_orphaned_user_when_no_client_found_by_phone(self, mock_filter_phones,
                                                               mock_find_by_integration_id,
                                                               mock_find_by_email,
                                                               mock_find_by_phone,
                                                               mock_find_orphaned_user):
        """Test that orphaned user lookup is attempted when no client found by phone number"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)  # Non-corporate to skip email lookup
        mock_orphaned_user = MockOrphanedUser(email="orphan@example.com")
        
        mock_find_by_integration_id.return_value = None
        mock_find_by_email.return_value = None
        mock_filter_phones.return_value = ["1234567890", "9876543210"]
        mock_find_by_phone.return_value = None  # No client found by phone
        mock_find_orphaned_user.side_effect = [None, mock_orphaned_user]  # Found on second phone
        
        field_names = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone_numbers": ["1234567890", "9876543210"],
        }
        
        # Act - Create new client to avoid birth_date AttributeError
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="test-123",
            create_new_client=True,  # Allow creation to avoid the error path
            validation=True
        )
        
        # Assert
        self.assertEqual(mock_find_orphaned_user.call_count, 2)
        mock_find_orphaned_user.assert_any_call(
            self.session, "1234567890", 
            first_name="John", last_name="Doe", client_email_address="john@example.com"
        )
        mock_find_orphaned_user.assert_any_call(
            self.session, "9876543210", 
            first_name="John", last_name="Doe", client_email_address="john@example.com"
        )
        self.assertEqual(result["row"]["cell_phone"], "9876543210")

    @patch('helper.ClientRepository.find_by_integration_id')
    def test_no_client_found_returns_expected_error(self, mock_find_by_integration_id):
        """Test behavior when no client is found by any lookup method"""
        # Arrange
        firm = MockFirm(id=1)
        mock_find_by_integration_id.return_value = None
        
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
            integration_id="nonexistent-123",
            create_new_client=False,  # Don't create new client
            validation=True
        )
        
        # Assert
        self.assertIsNone(result.get("client"))
        self.assertIn("error_message", result["row"])
        self.assertEqual(result["row"]["error_message"], "Client not found, stopping import.")


if __name__ == "__main__":
    unittest.main()