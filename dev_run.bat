@echo off
echo =========================================
echo Activando entorno virtual...
echo =========================================
call venv\Scripts\activate
pause

echo =========================================
echo Aplicando migraciones...
echo =========================================
flask db stamp head
flask db migrate -m "Reset esquema dev"
flask db upgrade
pause

echo =========================================
echo Cargando datos de prueba (3 semanas)...
echo =========================================
python seed_test_data.py
pause

IF %ERRORLEVEL% NEQ 0 (
    echo =========================================
    echo ERROR: Fallo la carga de datos de prueba.
    echo =========================================
    pause
    exit /b %ERRORLEVEL%
)

echo =========================================
echo Iniciando servidor Flask en modo DEBUG...
echo =========================================
set FLASK_ENV=development
set FLASK_DEBUG=1
flask run

pause

