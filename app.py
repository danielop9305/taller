from flask import Flask
from flask_migrate import Migrate
from models import db   # importa la instancia única
import routes

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taller.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "clave_secreta_segura"

db.init_app(app)        # aquí se vincula la instancia al app
migrate = Migrate(app, db)

routes.init_app(app)

if __name__ == "__main__":
    app.run(debug=True)
