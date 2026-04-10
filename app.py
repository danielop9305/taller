from flask import Flask
from flask_migrate import Migrate, upgrade
from models import db
import routes
import requests
import os
import sys
import webbrowser

LOCAL_VERSION = "1.0.0"
VERSION_URL = "https://raw.githubusercontent.com/danielop9305/taller/main/version.json"

app = Flask(__name__, template_folder="templates")
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "instance", "taller.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "clave_secreta_segura"

db.init_app(app)
migrate = Migrate(app, db)

def check_for_update():
    try:
        response = requests.get(VERSION_URL)
        if response.status_code == 200:
            data = response.json()
            remote_version = data["version"]
            download_url = data["url"]

            if remote_version != LOCAL_VERSION:
                print(f"Nueva versión disponible: {remote_version}")
                download_update(download_url)
            else:
                print("La aplicación está actualizada.")
        else:
            print("No se pudo obtener la información de versión.")
    except Exception as e:
        print(f"Error al verificar actualización: {e}")

def download_update(url):
    try:
        print("Descargando nueva versión...")
        response = requests.get(url, stream=True)
        exe_name = "app_update.exe"

        with open(exe_name, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        print(f"Descarga completa: {exe_name}")
        os.startfile(exe_name)
        sys.exit(0)

    except Exception as e:
        print(f"Error al descargar actualización: {e}")

routes.init_app(app)

if __name__ == "__main__":
    check_for_update()
    import webbrowser
    webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=False, use_reloader=False)


