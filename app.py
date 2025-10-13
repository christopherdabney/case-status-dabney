from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, nullable=False)
    first_name = db.Column(db.String(128), nullable=False)
    last_name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), unique=True)
    cell_phone = db.Column(db.String(32))
    integration_id = db.Column(db.String(128), nullable=False)


@app.route("/")
def hello():
    return "Hello, Flask with SQLite and SQLAlchemy!"


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
