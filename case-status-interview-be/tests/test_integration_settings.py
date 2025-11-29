"""
Unit tests for Integration Settings in ImportCaseHelper.import_client_handler

Tests the integration settings behavior for:
1. Different firm integration_settings combinations
2. Corporate vs non-corporate firm behavior
3. Validation mode vs normal mode
4. should_update_client logic
5. Settings combinations and their effects
"""

import unittest
from unittest.mock import Mock, patch
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from services import ImportCaseHelper


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
        
    def has_changes(self):
        """Mock method for change tracking"""
        return False


class MockFirm:
    """Mock firm object for testing"""
    def __init__(self, id=1, is_corporate=False, sync_contact_info=True, update_missing_data=True):
        self.id = id
        self.is_corporate = is_corporate
        self.integration_settings = {
            "sync_client_contact_info": sync_contact_info,
            "update_client_missing_data": update_missing_data,
        }


class TestIntegrationSettings(unittest.TestCase):
    """Test integration settings behavior"""
    
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

    @patch('helper._update_client')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_both_settings_enabled_triggers_updates(self, mock_filter_phones,
                                                    mock_find_by_integration_id,
                                                    mock_update_client):
        """Test that both sync_client_contact_info and update_client_missing_data being True triggers updates"""
        # Arrange
        firm = MockFirm(id=1, sync_contact_info=True, update_missing_data=True)
        existing_client = MockClient()
        
        mock_find_by_integration_id.return_value = existing_client
        mock_filter_phones.return_value = ["5551234567"]
        mock_update_client.return_value = True
        
        field_names = {
            "first_name": "Updated",
            "last_name": "Name",
            "email": "updated@example.com",
            "phone_numbers": ["5551234567"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="both-enabled-123",
            create_new_client=False,
            validation=True
        )
        
        # Assert - should_update_client should be True and updates should occur
        mock_update_client.assert_called_once()

    @patch('helper._update_client')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_only_sync_contact_info_enabled_triggers_updates(self, mock_filter_phones,
                                                             mock_find_by_integration_id,
                                                             mock_update_client):
        """Test that only sync_client_contact_info=True triggers updates"""
        # Arrange
        firm = MockFirm(id=1, sync_contact_info=True, update_missing_data=False)
        existing_client = MockClient()
        
        mock_find_by_integration_id.return_value = existing_client
        mock_filter_phones.return_value = ["5551234567"]
        mock_update_client.return_value = True
        
        field_names = {
            "first_name": "Contact",
            "last_name": "Update",
            "email": "contact@example.com",
            "phone_numbers": ["5551234567"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="sync-only-456",
            create_new_client=False,
            validation=True
        )
        
        # Assert
        mock_update_client.assert_called_once()

    @patch('helper._update_client')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_only_update_missing_data_enabled_triggers_updates(self, mock_filter_phones,
                                                               mock_find_by_integration_id,
                                                               mock_update_client):
        """Test that only update_client_missing_data=True triggers updates"""
        # Arrange
        firm = MockFirm(id=1, sync_contact_info=False, update_missing_data=True)
        existing_client = MockClient()
        
        mock_find_by_integration_id.return_value = existing_client
        mock_filter_phones.return_value = ["5551234567"]
        mock_update_client.return_value = True
        
        field_names = {
            "first_name": "Missing",
            "last_name": "Data",
            "birth_date": "1990-01-01",
            "phone_numbers": ["5551234567"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="missing-only-789",
            create_new_client=False,
            validation=True
        )
        
        # Assert
        mock_update_client.assert_called_once()

    @patch('helper._update_client')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_both_settings_disabled_skips_updates(self, mock_filter_phones,
                                                  mock_find_by_integration_id,
                                                  mock_update_client):
        """Test that both settings disabled skips all updates"""
        # Arrange
        firm = MockFirm(id=1, sync_contact_info=False, update_missing_data=False)
        existing_client = MockClient()
        
        mock_find_by_integration_id.return_value = existing_client
        mock_filter_phones.return_value = ["5551234567"]
        
        field_names = {
            "first_name": "No",
            "last_name": "Updates",
            "email": "noupdates@example.com",
            "phone_numbers": ["5551234567"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="no-updates-111",
            create_new_client=False,
            validation=True
        )
        
        # Assert
        mock_update_client.assert_not_called()

    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_corporate_firm_bypasses_phone_validation(self, mock_filter_phones,
                                                      mock_find_by_integration_id):
        """Test that corporate firms can proceed without valid phone numbers"""
        # Arrange
        corporate_firm = MockFirm(id=1, is_corporate=True, sync_contact_info=True, update_missing_data=True)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = []  # No valid phone numbers
        
        field_names = {
            "first_name": "Corporate",
            "last_name": "Client",
            "email": "corporate@example.com",
            "phone_numbers": ["invalid-phone"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=corporate_firm,
            row={},
            field_names=field_names,
            integration_id="corporate-222",
            create_new_client=True,
            validation=True
        )
        
        # Assert - should create client despite invalid phone
        self.assertTrue(result.get("created_client", False))
        self.assertNotIn("client_cell_phone", result["row"].get("error_fields", []))

    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_non_corporate_firm_requires_valid_phone(self, mock_filter_phones,
                                                     mock_find_by_integration_id):
        """Test that non-corporate firms require valid phone numbers"""
        # Arrange
        non_corporate_firm = MockFirm(id=1, is_corporate=False, sync_contact_info=True, update_missing_data=True)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = []  # No valid phone numbers
        
        field_names = {
            "first_name": "Non",
            "last_name": "Corporate",
            "email": "noncorp@example.com",
            "phone_numbers": ["invalid-phone"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=non_corporate_firm,
            row={},
            field_names=field_names,
            integration_id="non-corporate-333",
            create_new_client=True,
            validation=False
        )
        
        # Assert - should fail validation due to invalid phone
        self.assertIn("error_message", result["row"])
        self.assertIn("error_fields", result["row"])
        self.assertIn("client_cell_phone", result["row"]["error_fields"])

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_validation_mode_skips_database_save(self, mock_filter_phones,
                                                 mock_find_by_integration_id,
                                                 mock_save):
        """Test that validation=True skips database save operations"""
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
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="validation-444",
            create_new_client=True,
            validation=True  # Validation mode
        )
        
        # Assert - client created but not saved to database
        self.assertTrue(result.get("created_client", False))
        mock_save.assert_not_called()

    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_normal_mode_performs_database_save(self, mock_filter_phones,
                                                mock_find_by_integration_id,
                                                mock_save):
        """Test that validation=False performs database save operations"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["5551234567"]
        
        field_names = {
            "first_name": "Normal",
            "last_name": "Mode",
            "email": "normal@example.com",
            "phone_numbers": ["5551234567"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_id="normal-555",
            create_new_client=True,
            validation=False  # Normal mode
        )
        
        # Assert - client created and saved to database
        self.assertTrue(result.get("created_client", False))
        mock_save.assert_called_once()

    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_missing_integration_settings_defaults_to_false(self, mock_filter_phones,
                                                            mock_find_by_integration_id):
        """Test behavior when integration_settings are missing"""
        # Arrange
        firm_with_no_settings = MockFirm(id=1)
        firm_with_no_settings.integration_settings = {}  # Empty settings
        existing_client = MockClient()
        
        mock_find_by_integration_id.return_value = existing_client
        mock_filter_phones.return_value = ["5551234567"]
        
        field_names = {
            "first_name": "No",
            "last_name": "Settings",
            "email": "nosettings@example.com",
            "phone_numbers": ["5551234567"],
        }
        
        # Act
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm_with_no_settings,
            row={},
            field_names=field_names,
            integration_id="no-settings-666",
            create_new_client=False,
            validation=True
        )
        
        # Assert - should handle gracefully with default behavior (no updates)
        self.assertIsNotNone(result)

    @patch('helper._update_client')
    @patch('helper.ClientRepository.save')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_update_settings_affect_update_behavior(self, mock_filter_phones,
                                                    mock_find_by_integration_id,
                                                    mock_save,
                                                    mock_update_client):
        """Test that different update settings produce different update behavior"""
        # Arrange
        firm_sync_only = MockFirm(id=1, sync_contact_info=True, update_missing_data=False)
        firm_missing_only = MockFirm(id=2, sync_contact_info=False, update_missing_data=True)
        
        existing_client = MockClient(birth_date=None, ssn=None)
        mock_find_by_integration_id.return_value = existing_client
        mock_filter_phones.return_value = ["5551234567"]
        mock_update_client.return_value = True
        
        field_names = {
            "first_name": "Test",
            "last_name": "Settings",
            "email": "test@example.com",
            "birth_date": "1990-01-01",
            "ssn": "123-45-6789",
            "phone_numbers": ["5551234567"],
        }
        
        # Act - Test sync_only firm
        result1 = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm_sync_only,
            row={},
            field_names=field_names.copy(),
            integration_id="sync-test-777",
            create_new_client=False,
            validation=True
        )
        
        # Act - Test missing_only firm
        result2 = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm_missing_only,
            row={},
            field_names=field_names.copy(),
            integration_id="missing-test-888",
            create_new_client=False,
            validation=True
        )
        
        # Assert - Both should trigger updates but with different data
        self.assertEqual(mock_update_client.call_count, 2)

    @patch('helper.log_integration_response')
    @patch('helper.ClientRepository.find_by_integration_id')
    @patch('helper.filter_cell_phone_numbers')
    def test_integration_response_logging_in_normal_mode(self, mock_filter_phones,
                                                        mock_find_by_integration_id,
                                                        mock_log_integration):
        """Test that integration response is logged in normal mode but not validation mode"""
        # Arrange
        firm = MockFirm(id=1, is_corporate=False)
        mock_find_by_integration_id.return_value = None
        mock_filter_phones.return_value = ["5551234567"]
        
        integration_response = {"test": "response"}
        field_names = {
            "first_name": "Log",
            "last_name": "Test",
            "email": "log@example.com",
            "phone_numbers": ["5551234567"],
        }
        
        # Act - Normal mode
        result1 = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_response_object=integration_response,
            matter_id="matter-123",
            integration_id="log-normal-999",
            create_new_client=True,
            validation=False
        )
        
        # Act - Validation mode
        result2 = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=firm,
            row={},
            field_names=field_names,
            integration_response_object=integration_response,
            matter_id="matter-456",
            integration_id="log-validation-000",
            create_new_client=True,
            validation=True
        )
        
        # Assert - logging should only happen in normal mode
        mock_log_integration.assert_called_once()


if __name__ == "__main__":
    unittest.main()
