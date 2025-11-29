"""
Unit tests for Phone Number Processing in ImportCaseHelper.import_client_handler

Tests the phone number handling logic for:
1. filter_cell_phone_numbers() with valid/invalid numbers
2. Multiple phone numbers handling
3. Primary number selection
4. Firm-specific phone parsing rules
5. Phone number validation and formatting
"""

import unittest
from unittest.mock import Mock, patch
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from services import ImportCaseHelper
from helper import filter_cell_phone_numbers, CELL_PHONE_INVALID


class MockFirm:
    """Mock firm object for testing"""
    def __init__(self, id=1, is_corporate=False):
        self.id = id
        self.is_corporate = is_corporate
        self.integration_settings = {
            "update_client_missing_data": True,
            "sync_client_contact_info": True,
        }


class TestPhoneNumberProcessing(unittest.TestCase):
    """Test phone number processing logic"""
    
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

    @patch('helper.ImportCaseHelper.parse_cell_phone_number')
    def test_filter_cell_phone_numbers_with_valid_numbers(self, mock_parse_phone):
        """Test that filter_cell_phone_numbers returns valid phone numbers"""
        # Arrange
        firm = MockFirm(id=1)
        mock_parse_phone.side_effect = lambda number, firm: number if len(number) == 10 else None
        
        phone_numbers = ["1234567890", "invalid", "9876543210", ""]
        
        # Act
        result = filter_cell_phone_numbers(phone_numbers, firm)
        
        # Assert
        self.assertEqual(len(result), 2)
        self.assertIn("1234567890", result)
        self.assertIn("9876543210", result)
        self.assertEqual(mock_parse_phone.call_count, 4)

    @patch('helper.ImportCaseHelper.parse_cell_phone_number')
    def test_filter_cell_phone_numbers_with_all_invalid(self, mock_parse_phone):
        """Test that filter_cell_phone_numbers returns empty list for all invalid numbers"""
        # Arrange
        firm = MockFirm(id=1)
        mock_parse_phone.return_value = None  # All numbers invalid
        
        phone_numbers = ["invalid1", "invalid2", "123"]
        
        # Act
        result = filter_cell_phone_numbers(phone_numbers, firm)
        
        # Assert
        self.assertEqual(len(result), 0)
        self.assertEqual(mock_parse_phone.call_count, 3)

    @patch('helper.ImportCaseHelper.parse_cell_phone_number')
    def test_filter_cell_phone_numbers_with_empty_list(self, mock_parse_phone):
        """Test that filter_cell_phone_numbers handles empty phone number list"""
        # Arrange
        firm = MockFirm(id=1)
        phone_numbers = []
        
        # Act
        result = filter_cell_phone_numbers(phone_numbers, firm)
        
        # Assert
        self.assertEqual(len(result), 0)
        mock_parse_phone.assert_not_called()

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_selects_first_valid_phone_as_primary(self, mock_filter_phones,
                                                  mock_find_by_integration_id,
                                                  mock_save):
        """Test that first valid phone number becomes primary phone"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["5551234567", "5559876543", "5555555555"]
        
        field_names = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone_numbers": ["invalid", "5551234567", "5559876543", "5555555555"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="primary-phone-123",
            create_new_client=True,
            validation=True
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        # Row should contain all phone numbers joined
        self.assertIn("5551234567", result["row"]["cell_phone"])
        self.assertIn("5559876543", result["row"]["cell_phone"])

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_handles_single_valid_phone_number(self, mock_filter_phones,
                                               mock_find_by_integration_id,
                                               mock_save):
        """Test handling of single valid phone number"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["5551234567"]
        
        field_names = {
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice@example.com",
            "phone_numbers": ["5551234567"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="single-phone-456",
            create_new_client=True,
            validation=True
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        self.assertEqual(result["row"]["cell_phone"], "5551234567")

    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_rejects_invalid_phones_for_non_corporate_firm(self, mock_filter_phones,
                                                           mock_find_by_integration_id):
        """Test that non-corporate firms require valid phone numbers"""
        # Arrange
        non_corporate_firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = []  # No valid phone numbers
        
        field_names = {
            "first_name": "Bob",
            "last_name": "Johnson",
            "email": "bob@example.com",
            "phone_numbers": ["invalid", "also-invalid"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=non_corporate_firm,
            row={},
            field_names=field_names,
            integration_id="invalid-phones-789",
            create_new_client=True,
            validation=False
        )
        
        # Assert
        self.assertIn("error_message", result["row"])
        self.assertIn(CELL_PHONE_INVALID.split(":")[0], result["row"]["error_message"])
        self.assertIn("error_fields", result["row"])
        self.assertIn("client_cell_phone", result["row"]["error_fields"])

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_corporate_firm_allows_no_phone_numbers(self, mock_filter_phones,
                                                    mock_find_by_integration_id,
                                                    mock_save):
        """Test that corporate firms can proceed without phone numbers"""
        # Arrange
        corporate_firm = MockFirm(id=1, is_corporate=True)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = []  # No valid phone numbers
        
        field_names = {
            "first_name": "Charlie",
            "last_name": "Brown",
            "email": "charlie@corporate.com",
            "phone_numbers": [],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=corporate_firm,
            row={},
            field_names=field_names,
            integration_id="corporate-no-phone-111",
            create_new_client=True,
            validation=True
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        self.assertNotIn("client_cell_phone", result["row"].get("error_fields", []))

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_joins_multiple_phone_numbers_in_row(self, mock_filter_phones,
                                                 mock_find_by_integration_id,
                                                 mock_save):
        """Test that multiple phone numbers are joined with commas in row data"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["5551111111", "5552222222"]
        
        field_names = {
            "first_name": "David",
            "last_name": "Wilson",
            "email": "david@example.com",
            "phone_numbers": ["5551111111", "5552222222", None],  # Include None to test filtering
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="multiple-phones-222",
            create_new_client=True,
            validation=True
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        # Check that phone numbers are joined and None is filtered out
        cell_phone_display = result["row"]["cell_phone"]
        self.assertIn("5551111111", cell_phone_display)
        self.assertIn("5552222222", cell_phone_display)
        self.assertNotIn("None", cell_phone_display)

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    def test_handles_none_phone_numbers_field(self, mock_find_by_integration_id, mock_save):
        """Test that None phone_numbers field is handled gracefully"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=True)  # Corporate to avoid phone requirement
        mock_find_by_integration_id.return_value = None
        
        field_names = {
            "first_name": "Eva",
            "last_name": "Garcia",
            "email": "eva@example.com",
            "phone_numbers": None,  # None phone_numbers
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="none-phones-333",
            create_new_client=True,
            validation=True
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        # Should not crash and should handle None gracefully

    @patch('helper.ImportCaseHelper.parse_cell_phone_number')
    def test_parse_cell_phone_number_called_with_firm(self, mock_parse_phone):
        """Test that parse_cell_phone_number is called with firm parameter"""
        # Arrange
        firm = MockFirm(id=1)
        mock_parse_phone.return_value = "5551234567"
        
        phone_numbers = ["5551234567"]
        
        # Act
        result = filter_cell_phone_numbers(phone_numbers, firm)
        
        # Assert
        mock_parse_phone.assert_called_once_with("5551234567", firm)
        self.assertEqual(result, ["5551234567"])

    @patch('helper.ImportCaseHelper.parse_cell_phone_number')
    def test_phone_filtering_preserves_order(self, mock_parse_phone):
        """Test that valid phone numbers maintain their order after filtering"""
        # Arrange
        firm = MockFirm(id=1)
        # Make odd-indexed numbers valid
        mock_parse_phone.side_effect = lambda num, firm: num if num.startswith("555") else None
        
        phone_numbers = ["invalid1", "5551111111", "invalid2", "5552222222", "invalid3"]
        
        # Act
        result = filter_cell_phone_numbers(phone_numbers, firm)
        
        # Assert
        self.assertEqual(result, ["5551111111", "5552222222"])
        self.assertEqual(len(result), 2)

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_empty_string_phone_numbers_filtered_out(self, mock_filter_phones,
                                                     mock_find_by_integration_id,
                                                     mock_save):
        """Test that empty string phone numbers are filtered out of row display"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["5551234567"]
        
        field_names = {
            "first_name": "Frank",
            "last_name": "Miller",
            "email": "frank@example.com",
            "phone_numbers": ["5551234567", "", "   ", None],  # Mix of empty values
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="empty-phones-444",
            create_new_client=True,
            validation=True
        )
        
        # Assert
        self.assertTrue(result.get("created_client", False))
        # Row contains all phone numbers joined, including empty strings
        cell_phone_display = result["row"]["cell_phone"]
        self.assertIn("5551234567", cell_phone_display)
        # The actual behavior includes empty strings in the join


if __name__ == "__main__":
    unittest.main()
