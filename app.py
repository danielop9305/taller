from flask import Flask
from flask_migrate import Migrate, upgrade
from models import db
import routes
import requests
import os
import sys
import webbrowser

# Leer la versión local desde version.txt en lugar de hardcodear
try:
    with open("version.txt") as f:
        LOCAL_VERSION = f.read().strip()
except FileNotFoundError:
    LOCAL_VERSION = "0.0.0"

VERSION_URL = "https://raw.githubusercontent.com/danielop9305/taller/main/version.json"

app = Flask(__name__, template_folder="templates")

if getattr(sys, 'frozen', False):
    # Ejecutable compilado (.exe)
    DB_PATH = r"C:\MotoPinguino\instance\taller.db"
else:
    # Entorno de desarrollo
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASE_DIR, "instance", "taller.db")

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "clave_secreta_segura"

db.init_app(app)
migrate = Migrate(app, db)

def check_for_update():
    try:
        response = requests.get(VERSION_URL)
        if response.status_code == 200:
            data = response.json()
            remote_version = data["version"].strip()
            local_version = LOCAL_VERSION.strip()
            download_url = data["url"]

            print(f"Local: {local_version}, Remoto: {remote_version}")  # log de depuración

            if remote_version == local_version:
                print("La aplicación está actualizada.")
            else:
                print(f"Nueva versión disponible: {remote_version}")
                download_update(download_url)
        else:
            print("No se pudo obtener la información de versión.")
    except Exception as e:
        print(f"Error al verificar actualización: {e}")


def download_update(url):
    try:
        print("Descargando nueva versión...")
        response = requests.get(url, stream=True)
        exe_name = "app_update.exe"  # usar el mismo nombre que subes al release

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
    webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=False, use_reloader=False)
