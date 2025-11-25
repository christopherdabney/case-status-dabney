import unittest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from helper import ImportCaseHelper, ClientRepository


class Firm:
    def __init__(self, id, is_corporate=False):
        self.id = id
        self.is_corporate = is_corporate
        self.integration_settings = {
            "update_client_missing_data": True,
            "sync_client_contact_info": True,
        }


class ImportClientHandlerTestCase(unittest.TestCase):
    def setUp(self):
        import app

        app.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        self.app = app.app
        self.app_context = self.app.app_context()
        self.app_context.push()
        app.db.drop_all()
        app.db.create_all()
        self.session = app.db.session
        self.firm = Firm(id=1)

    def tearDown(self):
        import app

        app.db.session.remove()
        app.db.drop_all()
        self.app_context.pop()

    def test_update_preexisting_client(self):
        from app import Client

        # Create a client first
        row = {}
        field_names = {
            "first_name": "Alice",
            "last_name": "Brown",
            "email": "alice.brown@example.com",
            "phone_numbers": ["5559876543"],
            "type": "Person",
        }
        ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=self.firm,
            row=row,
            field_names=field_names,
            integration_type=None,
            integration_id="int-789",
            matter_id=None,
            integration_response_object=None,
            create_new_client=True,
            validation=False,
        )
        # Update the client using import_client_handler
        updated_row = {}
        updated_field_names = {
            "first_name": "Alicia",
            "last_name": "Brown",
            "email": "alice.brown@example.com",
            "phone_numbers": ["5559876543"],
            "type": "Person",
        }
        ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=self.firm,
            row=updated_row,
            field_names=updated_field_names,
            integration_type=None,
            integration_id="int-789",
            matter_id=None,
            integration_response_object=None,
            create_new_client=True,
            validation=False,
        )
        client = ClientRepository.find_by_integration_id(
            self.session, self.firm.id, "int-789"
        )
        self.assertIsNotNone(client)
        self.assertEqual(client.first_name, "Alicia")
        self.assertEqual(client.last_name, "Brown")
        self.assertEqual(client.email, "alice.brown@example.com")

    def setUp(self):
        from app import app, db

        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        self.app = app
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.session = db.session
        self.firm = Firm(id=1)

    def tearDown(self):
        from app import db

        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_import_client_handler_creates_client(self):
        row = {}
        field_names = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone_numbers": ["1234567890"],
            "type": "Person",
        }
        result = ImportCaseHelper.import_client_handler(
            session=self.session,
            firm=self.firm,
            row=row,
            field_names=field_names,
            integration_type=None,
            integration_id="int-123",
            matter_id=None,
            integration_response_object=None,
            create_new_client=True,
            validation=False,
        )
        client = ClientRepository.find_by_integration_id(
            self.session, self.firm.id, "int-123"
        )
        self.assertIsNotNone(client)
        self.assertEqual(client.first_name, "John")
        self.assertEqual(client.last_name, "Doe")
        self.assertEqual(client.email, "john.doe@example.com")
        self.assertEqual(client.integration_id, "int-123")


if __name__ == "__main__":
    unittest.main()
