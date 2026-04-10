@echo off
echo =========================================
echo Limpiando compilaciones anteriores...
echo =========================================
rmdir /s /q build
rmdir /s /q dist
del app.spec

echo =========================================
echo Activando entorno virtual...
echo =========================================
call venv\Scripts\activate

echo =========================================
echo Instalando dependencias necesarias...
echo =========================================
pip install --upgrade pip
pip install pandas openpyxl

echo =========================================
echo Aplicando migraciones pendientes...
echo =========================================
flask db upgrade

IF %ERRORLEVEL% NEQ 0 (
    echo =========================================
    echo ERROR: La migracion fallo.
    echo =========================================
    pause
    exit /b %ERRORLEVEL%
)

echo =========================================
echo Compilando nuevo ejecutable con PyInstaller...
echo =========================================
pyinstaller --onefile ^
 --add-data "templates;templates" ^
 --add-data "static;static" ^
 --add-data "instance/taller.db;instance" ^
 app.py

echo =========================================
echo Subiendo cambios al repositorio Git...
echo =========================================
git add .
set /p mensaje=Escribe el mensaje del commit: 
git commit -m "%mensaje%"
git push origin main

echo =========================================
echo Proceso terminado.
echo El nuevo .exe está en la carpeta "dist".
echo =========================================
pause
