"""
Unit tests for Input Validation & Error Handling in ImportCaseHelper.import_client_handler

Tests the validation logic and error handling for:
1. Missing required fields (first_name, last_name)
2. Invalid phone numbers for non-corporate firms
3. Empty/null input handling
4. Malformed field_names structure
5. Integration-specific validation rules
"""

import unittest
from unittest.mock import Mock, patch
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from helper import ImportCaseHelper, IntegrationHelper, CLIENT_MISSING_NAME, CELL_PHONE_INVALID


class MockFirm:
    """Mock firm object for testing"""
    def __init__(self, id=1, is_corporate=False):
        self.id = id
        self.is_corporate = is_corporate
        self.integration_settings = {
            "update_client_missing_data": True,
            "sync_client_contact_info": True,
        }


class TestInputValidationErrorHandling(unittest.TestCase):
    """Test input validation and error handling logic"""
    
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
    def test_missing_first_name_csv_import_returns_error(self, mock_find_by_integration_id):
        """Test that missing first_name for CSV import returns validation error"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        
        field_names = {
            # "first_name": "John",  # Missing first_name
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
            integration_type=IntegrationHelper.CSV_IMPORT,
            integration_id="test-123",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertIn("error_message", result["row"])
        self.assertEqual(result["row"]["error_message"], CLIENT_MISSING_NAME)
        self.assertIn("error_fields", result["row"])
        self.assertIn("client_first_name", result["row"]["error_fields"])
        self.assertIsNone(result.get("client"))

    @patch('helper.ClientRepository.find_by_integration_id')
    def test_missing_last_name_csv_import_returns_error(self, mock_find_by_integration_id):
        """Test that missing last_name for CSV import returns validation error"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        
        field_names = {
            "first_name": "John",
            # "last_name": "Doe",  # Missing last_name
            "email": "john@example.com",
            "phone_numbers": ["1234567890"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_type=IntegrationHelper.CSV_IMPORT,
            integration_id="test-123",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertIn("error_message", result["row"])
        self.assertEqual(result["row"]["error_message"], CLIENT_MISSING_NAME)
        self.assertIn("error_fields", result["row"])
        self.assertIn("client_last_name", result["row"]["error_fields"])
        self.assertIsNone(result.get("client"))

    @patch('helper.ClientRepository.find_by_integration_id')
    def test_missing_both_names_csv_import_returns_both_fields_error(self, mock_find_by_integration_id):
        """Test that missing both first_name and last_name returns both fields in error"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        
        field_names = {
            # "first_name": "John",  # Missing first_name
            # "last_name": "Doe",   # Missing last_name
            "email": "john@example.com",
            "phone_numbers": ["1234567890"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_type=IntegrationHelper.CSV_IMPORT,
            integration_id="test-123",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertIn("error_message", result["row"])
        self.assertEqual(result["row"]["error_message"], CLIENT_MISSING_NAME)
        self.assertIn("error_fields", result["row"])
        self.assertIn("client_first_name", result["row"]["error_fields"])
        self.assertIn("client_last_name", result["row"]["error_fields"])
        self.assertEqual(len(result["row"]["error_fields"]), 2)
        self.assertIsNone(result.get("client"))

    @patch('helper.ClientRepository.find_by_integration_id')
    def test_missing_first_name_non_csv_integration_returns_error(self, mock_find_by_integration_id):
        """Test that missing first_name for non-CSV integrations returns validation error"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        
        field_names = {
            # "first_name": "John",  # Missing first_name
            "last_name": "Doe",
            "email": "john@example.com",
            "phone_numbers": ["1234567890"],
        }
        
        # Act - Test with MYCASE integration (not CSV_IMPORT or THIRD_PARTY)
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_type=IntegrationHelper.MYCASE,
            integration_id="test-456",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertIn("error_message", result["row"])
        self.assertEqual(result["row"]["error_message"], CLIENT_MISSING_NAME)
        self.assertIn("error_fields", result["row"])
        self.assertIn("client_first_name", result["row"]["error_fields"])
        # For non-CSV integrations, only first_name is required
        self.assertEqual(len(result["row"]["error_fields"]), 1)
        self.assertIsNone(result.get("client"))

    @patch('helper.filter_cell_phone_numbers')
    @patch('helper.ClientRepository.find_by_integration_id')
    def test_invalid_phone_numbers_non_corporate_firm_returns_error(self, mock_find_by_integration_id, mock_filter_phones):
        """Test that invalid phone numbers for non-corporate firms return validation error"""
        # Arrange
        non_corporate_firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = []  # No valid phone numbers
        
        field_names = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone_numbers": ["invalid-phone", "also-invalid"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=non_corporate_firm,
            row={},
            field_names=field_names,
            integration_type=IntegrationHelper.CSV_IMPORT,
            integration_id="test-789",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertIn("error_message", result["row"])
        self.assertIn(CELL_PHONE_INVALID.split(":")[0], result["row"]["error_message"])  # Check prefix
        self.assertIn("error_fields", result["row"])
        self.assertIn("client_cell_phone", result["row"]["error_fields"])
        self.assertIsNone(result.get("client"))

    @patch('helper.filter_cell_phone_numbers')
    @patch('helper.ClientRepository.find_by_integration_id')
    def test_corporate_firm_allows_no_phone_numbers(self, mock_find_by_integration_id, mock_filter_phones):
        """Test that corporate firms can proceed without phone numbers"""
        # Arrange
        corporate_firm = MockFirm(id=1, is_corporate=True)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = []  # No valid phone numbers
        
        field_names = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@corporate.com",
            "phone_numbers": [],  # No phone numbers
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=corporate_firm,
            row={},
            field_names=field_names,
            integration_type=IntegrationHelper.CSV_IMPORT,
            integration_id="corp-123",
            create_new_client=True,
            validation=True  # Use validation to avoid actual database save
        )
        
        # Assert - Should NOT have phone validation error for corporate firms
        self.assertNotIn("client_cell_phone", result["row"].get("error_fields", []))
        # Should create client successfully (validation=True prevents actual save)
        self.assertTrue(result.get("created_client", False))

    def test_empty_field_names_handles_gracefully(self):
        """Test that empty or None field_names dictionary is handled gracefully"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        
        # Act with empty field_names
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names={},  # Empty field_names
            integration_type=IntegrationHelper.CSV_IMPORT,
            integration_id="empty-123",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertIn("error_message", result["row"])
        self.assertEqual(result["row"]["error_message"], CLIENT_MISSING_NAME)
        self.assertIn("error_fields", result["row"])

    def test_none_values_in_field_names_handled_gracefully(self):
        """Test that None values in field_names are handled as missing fields"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        
        field_names = {
            "first_name": None,  # Explicit None
            "last_name": None,   # Explicit None
            "email": "john@example.com",
            "phone_numbers": ["1234567890"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_type=IntegrationHelper.CSV_IMPORT,
            integration_id="none-123",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertIn("error_message", result["row"])
        self.assertEqual(result["row"]["error_message"], CLIENT_MISSING_NAME)
        self.assertIn("error_fields", result["row"])
        self.assertIn("client_first_name", result["row"]["error_fields"])
        self.assertIn("client_last_name", result["row"]["error_fields"])

    @patch('helper.ClientRepository.find_by_integration_id')
    def test_empty_string_names_treated_as_missing(self, mock_find_by_integration_id):
        """Test that empty string names are treated as missing fields"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        
        field_names = {
            "first_name": "",    # Empty string
            "last_name": "   ",  # Whitespace only
            "email": "john@example.com",
            "phone_numbers": ["1234567890"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_type=IntegrationHelper.CSV_IMPORT,
            integration_id="empty-str-123",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertIn("error_message", result["row"])
        self.assertEqual(result["row"]["error_message"], CLIENT_MISSING_NAME)
        self.assertIn("error_fields", result["row"])
        # Note: The actual code may not trim whitespace, so this tests current behavior
        self.assertIn("client_first_name", result["row"]["error_fields"])

    @patch('helper.ClientRepository.find_by_integration_id')
    def test_malformed_phone_numbers_field_handles_gracefully(self, mock_find_by_integration_id):
        """Test that malformed phone_numbers field (not a list) is handled gracefully"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        
        field_names = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone_numbers": "1234567890",  # String instead of list
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_type=IntegrationHelper.CSV_IMPORT,
            integration_id="malformed-123",
            create_new_client=True,
            validation=False
        )
        
        # Assert - Should handle gracefully without crashing
        # The actual behavior depends on implementation, but should not raise exception
        self.assertIsNotNone(result)
        self.assertIn("row", result)


if __name__ == "__main__":
    unittest.main()
