from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy instance will be injected from app.py
db = None


class Firm:
    """
    Firm domain model - not a database model, represents business logic entity.
    Used for client import operations and integration settings.
    """
    def __init__(self, id, is_corporate=False):
        self.id = id
        self.is_corporate = is_corporate
        self.integration_settings = {
            "update_client_missing_data": True,
            "sync_client_contact_info": True,
        }


def init_models(database_instance):
    """
    Initialize models with SQLAlchemy database instance.
    This allows models to be imported before the Flask app is created.
    """
    global db, User, Client
    db = database_instance
    
    class User(db.Model):
        """User database model for system users."""
        __tablename__ = 'user'
        
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(128), nullable=False)
        email = db.Column(db.String(128), unique=True, nullable=False)

    class Client(db.Model):
        """
        Client database model for legal practice clients.
        Supports client import/export operations and integration with third-party systems.
        """
        __tablename__ = 'client'
        
        id = db.Column(db.Integer, primary_key=True)
        firm_id = db.Column(db.Integer, nullable=False)
        first_name = db.Column(db.String(128), nullable=False)
        last_name = db.Column(db.String(128), nullable=False)
        birth_date = db.Column(db.String(128), nullable=True)
        email = db.Column(db.String(128), unique=True)
        cell_phone = db.Column(db.String(32))
        integration_id = db.Column(db.String(128), nullable=False)
        ssn = db.Column(db.String(128), nullable=True)
    
    # Make models available globally
    globals()['User'] = User
    globals()['Client'] = Client
    
    return User, Client


# Placeholder classes - will be replaced when init_models is called
class User:
    pass

class Client:
    pass