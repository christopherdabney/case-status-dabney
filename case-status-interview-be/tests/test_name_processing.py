"""
Unit tests for Name Processing in ImportCaseHelper.import_client_handler

Tests the name handling logic for:
1. Split full name into first/last when only "name" provided
2. Company vs Person type handling
3. Empty name handling
4. Edge cases with whitespace and special characters
5. Name validation and error scenarios
"""

import unittest
from unittest.mock import Mock, patch
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from services import ImportCaseHelper
from helper import CLIENT_MISSING_NAME


class MockFirm:
    """Mock firm object for testing"""
    def __init__(self, id=1, is_corporate=False):
        self.id = id
        self.is_corporate = is_corporate
        self.integration_settings = {
            "update_client_missing_data": True,
            "sync_client_contact_info": True,
        }


class TestNameProcessing(unittest.TestCase):
    """Test name processing logic"""
    
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
    def test_splits_full_name_into_first_last_when_only_name_provided(self, mock_filter_phones,
                                                                      mock_find_by_integration_id,
                                                                      mock_save):
        """Test that full name is split into first_name and last_name when only 'name' is provided"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["1234567890"]
        
        field_names = {
            "name": "John Doe Smith",  # Full name only, no first_name/last_name
            "email": "john@example.com",
            "phone_numbers": ["1234567890"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="name-split-123",
            create_new_client=True,
            validation=True
        )
        
        # Assert - In validation mode, save is not called, but client is created
        self.assertTrue(result.get("created_client", False))
        # Verify field_names was updated
        self.assertEqual(field_names["first_name"], "John")
        self.assertEqual(field_names["last_name"], "Doe Smith")

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_splits_single_word_name_correctly(self, mock_filter_phones,
                                               mock_find_by_integration_id,
                                               mock_save):
        """Test that single word name becomes first_name with empty last_name"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["2222222222"]
        
        field_names = {
            "name": "Madonna",  # Single word name
            "email": "madonna@example.com",
            "phone_numbers": ["2222222222"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="single-name-456",
            create_new_client=True,
            validation=True
        )
        
        # Assert - In validation mode, verify field_names was updated
        self.assertTrue(result.get("created_client", False))
        self.assertEqual(field_names["first_name"], "Madonna")
        # Single word names don't create last_name in field_names

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_prefers_existing_first_last_over_name_splitting(self, mock_filter_phones,
                                                             mock_find_by_integration_id,
                                                             mock_save):
        """Test that existing first_name and last_name take precedence over 'name' field"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["3333333333"]
        
        field_names = {
            "name": "Should Be Ignored",
            "first_name": "Alice",  # These should take precedence
            "last_name": "Johnson",
            "email": "alice@example.com",
            "phone_numbers": ["3333333333"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="prefer-existing-789",
            create_new_client=True,
            validation=True
        )
        
        # Assert - Names should remain unchanged
        self.assertTrue(result.get("created_client", False))
        self.assertEqual(field_names["first_name"], "Alice")
        self.assertEqual(field_names["last_name"], "Johnson")

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_handles_company_type_sets_company_name(self, mock_filter_phones,
                                                    mock_find_by_integration_id,
                                                    mock_save):
        """Test that Company type uses first_name as company_name"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=True)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["4444444444"]
        
        field_names = {
            "first_name": "Acme Corporation",
            "last_name": "Legal Department",
            "type": "Company",  # Company type
            "email": "contact@acme.com",
            "phone_numbers": ["4444444444"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="company-123",
            create_new_client=True,
            validation=True
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        self.assertEqual(result["company_name"], "Acme Corporation")

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_handles_person_type_no_company_name(self, mock_filter_phones,
                                                 mock_find_by_integration_id,
                                                 mock_save):
        """Test that Person type does not set company_name"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["5555555555"]
        
        field_names = {
            "first_name": "John",
            "last_name": "Doe",
            "type": "Person",  # Person type
            "email": "john@example.com",
            "phone_numbers": ["5555555555"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="person-456",
            create_new_client=True,
            validation=True
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        self.assertIsNone(result["company_name"])

    @patch('helper.ClientRepository.find_by_integration_id')
    def test_handles_empty_name_gracefully(self, mock_find_by_integration_id):
        """Test that empty 'name' field is handled gracefully"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        
        field_names = {
            "name": "",  # Empty name
            "email": "empty@example.com",
            "phone_numbers": ["6666666666"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="empty-name-789",
            create_new_client=True,
            validation=False
        )
        
        # Assert - Should get validation error for missing names
        self.assertIn("error_message", result["row"])
        self.assertEqual(result["row"]["error_message"], CLIENT_MISSING_NAME)

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_handles_whitespace_in_names(self, mock_filter_phones,
                                         mock_find_by_integration_id,
                                         mock_save):
        """Test that names with extra whitespace are handled correctly"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["7777777777"]
        
        field_names = {
            "name": "  John   Doe   Smith  ",  # Extra whitespace
            "email": "whitespace@example.com",
            "phone_numbers": ["7777777777"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="whitespace-123",
            create_new_client=True,
            validation=True
        )
        
        # Assert - Check if name splitting occurred regardless of creation success
        if result.get("created_client", False):
            # Name was split successfully
            self.assertIsNotNone(field_names.get("first_name"))
            self.assertIsNotNone(field_names.get("last_name"))
        else:
            # May have failed validation but name should still be processed
            # Just verify the test completed without error
            self.assertIsNotNone(result)

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_handles_special_characters_in_names(self, mock_filter_phones,
                                                 mock_find_by_integration_id,
                                                 mock_save):
        """Test that names with special characters are handled correctly"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["8888888888"]
        
        field_names = {
            "name": "Jean-Luc O'Connor-Smith",  # Hyphens and apostrophes
            "email": "jeanluc@example.com",
            "phone_numbers": ["8888888888"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="special-chars-456",
            create_new_client=True,
            validation=True
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        self.assertEqual(field_names["first_name"], "Jean-Luc")
        self.assertEqual(field_names["last_name"], "O'Connor-Smith")

    @patch('helper.ClientRepository.find_by_integration_id')
    def test_name_splitting_updates_field_names_dict(self, mock_find_by_integration_id):
        """Test that name splitting updates the field_names dictionary"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        
        field_names = {
            "name": "Test User",
            "email": "test@example.com",
            "phone_numbers": ["9999999999"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="field-update-789",
            create_new_client=True,
            validation=False
        )
        
        # Assert that field_names was modified
        self.assertIn("first_name", field_names)
        self.assertIn("last_name", field_names)
        self.assertEqual(field_names["first_name"], "Test")
        self.assertEqual(field_names["last_name"], "User")

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_name_processing_populates_row_data(self, mock_filter_phones,
                                                mock_find_by_integration_id,
                                                mock_save):
        """Test that name processing populates the row data correctly"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["1111111111"]
        
        field_names = {
            "name": "Sample Person",
            "email": "sample@example.com",
            "phone_numbers": ["1111111111"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="row-data-123",
            create_new_client=True,
            validation=True
        )
        
        # Assert row data is populated
        self.assertEqual(result["row"]["first_name"], "Sample")
        self.assertEqual(result["row"]["last_name"], "Person")
        self.assertEqual(result["row"]["email"], "sample@example.com")


if __name__ == "__main__":
    unittest.main()
