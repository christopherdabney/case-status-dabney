from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from helper import ImportCaseHelper, IntegrationHelper

# Initialize Flask app and database
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Import models and initialize with database instance
from models import init_models, Firm, User, Client
init_models(db)


@app.route("/")
def hello():
    return "Hello, Interviewee!"


@app.route("/clients", methods=["GET"])
def get_clients():
    """Get all clients in the system."""
    clients = Client.query.all()
    client_list = [
        {
            "id": c.id,
            "firm_id": c.firm_id,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "birth_date": c.birth_date,
            "email": c.email,
            "cell_phone": c.cell_phone,
            "integration_id": c.integration_id,
            "ssn": c.ssn,
        }
        for c in clients
    ]
    return {"clients": client_list}


@app.route("/clients", methods=["PATCH"])
def patch_client():
    """Create or update a client using the import handler."""
    data = request.get_json()

    firm = Firm(data.get("firm_id", 1))
    result = ImportCaseHelper.import_client_handler(
        session=db.session,
        firm=firm,
        row={},
        field_names=data,
        integration_type=IntegrationHelper.CSV_IMPORT,
        integration_id=data.get("integration_id", None),
        matter_id="123456",
        integration_response_object=None,
        create_new_client=True,
        validation=False,
    )
    
    if error_message := result["row"].get("error_message", None):
        return {"status": "error", "errors": error_message}
    
    return {"status": "success", "result": result["row"].get("success_msg")}


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)