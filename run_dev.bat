@echo off
REM Script para cargar base de datos de prueba y arrancar Flask en modo desarrollo
REM Guarda este archivo como run_dev_with_seed.bat en la carpeta de tu proyecto

echo ⚙️ Cargando base de datos de prueba...
py seed_test_data.py

echo 🚀 Iniciando servidor Flask en modo desarrollo...
set FLASK_ENV=development
set FLASK_DEBUG=1
flask run