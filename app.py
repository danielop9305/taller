from flask import Flask
from flask_migrate import Migrate
from models import db   # importa la instancia única
import routes
import requests
import os
import sys

# -------------------------------
# Configuración de actualización
# -------------------------------
LOCAL_VERSION = "1.0.0"   # versión actual de tu app
VERSION_URL = "https://raw.githubusercontent.com/danielop9305/taller/main/version.json"

app = Flask(__name__, template_folder="templates")

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
        exe_name = "app_update.exe"   # o "app.exe" si quieres reemplazar directamente

        with open(exe_name, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        print(f"Descarga completa: {exe_name}")
        
        # Lanzar el nuevo ejecutable automáticamente
        os.startfile(exe_name)
        
        # Cerrar la aplicación actual
        sys.exit(0)

    except Exception as e:
        print(f"Error al descargar actualización: {e}")

# -------------------------------
# Configuración de Flask
# -------------------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taller.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "clave_secreta_segura"

db.init_app(app)        # aquí se vincula la instancia al app
migrate = Migrate(app, db)

with app.app_context():
    db.create_all()

routes.init_app(app)

if __name__ == "__main__":
    # Primero verificar actualización
    check_for_update()
    # Luego arrancar la aplicación Flask
    app.run(debug=True)
