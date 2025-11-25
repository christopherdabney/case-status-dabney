from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from helper import ImportCaseHelper
from helper import IntegrationHelper

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Firm:
    def __init__(self, id, is_corporate=False):
        self.id = id
        self.is_corporate = is_corporate
        self.integration_settings = {
            "update_client_missing_data": True,
            "sync_client_contact_info": True,
        }


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, nullable=False)
    first_name = db.Column(db.String(128), nullable=False)
    last_name = db.Column(db.String(128), nullable=False)
    birth_date = db.Column(db.String(128), nullable=True)
    email = db.Column(db.String(128), unique=True)
    cell_phone = db.Column(db.String(32))
    integration_id = db.Column(db.String(128), nullable=False)
    ssn = db.Column(db.String(128), nullable=True)


@app.route("/")
def hello():
    return "Hello, Interviewee!"


@app.route("/clients", methods=["GET"])
def get_clients():
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
