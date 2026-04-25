@echo off
setlocal enabledelayedexpansion

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
pip install pandas openpyxl requests

echo =========================================
echo Reiniciando historial de migraciones...
echo =========================================
rmdir /s /q migrations\versions
mkdir migrations\versions

python -c "import sqlite3; conn=sqlite3.connect('instance/taller.db'); cur=conn.cursor(); cur.execute('DROP TABLE IF EXISTS alembic_version'); conn.commit(); conn.close()"

flask db stamp head
flask db migrate -m "Reset total de esquema"
flask db upgrade

IF %ERRORLEVEL% NEQ 0 (
    echo =========================================
    echo ERROR: La migracion fallo.
    echo =========================================
    pause
    exit /b %ERRORLEVEL%
)

:: ============================
:: BLOQUE DE VERSION INTERACTIVO
:: ============================
set /p VERSION=<version.txt
echo Versión actual: %VERSION%

for /f "tokens=1-3 delims=." %%a in ("%VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
    set PATCH=%%c
)

echo =========================================
echo Selecciona el tipo de incremento:
echo [1] MAJOR (ej: 2.0.0)
echo [2] MINOR (ej: 1.1.0)
echo [3] PATCH (ej: 1.0.5)
echo =========================================
set /p choice=Opción:

if "%choice%"=="1" (
    set /a MAJOR+=1
    set MINOR=0
    set PATCH=0
)
if "%choice%"=="2" (
    set /a MINOR+=1
    set PATCH=0
)
if "%choice%"=="3" (
    set /a PATCH+=1
)

set NEW_VERSION=%MAJOR%.%MINOR%.%PATCH%
echo Nueva versión: %NEW_VERSION%
echo %NEW_VERSION%>version.txt

echo =========================================
echo Compilando nuevo ejecutable con PyInstaller...
echo =========================================
pyinstaller --onefile ^
 --add-data "templates;templates" ^
 --add-data "static;static" ^
 app.py

IF %ERRORLEVEL% NEQ 0 (
    echo =========================================
    echo ERROR: Fallo la compilacion del ejecutable.
    echo =========================================
    pause
    exit /b %ERRORLEVEL%
)

echo =========================================
echo Aplicando .gitignore optimizado...
echo =========================================
git rm -r --cached . >nul 2>&1
git add .
git commit -m "Aplicar .gitignore optimizado automaticamente" >nul 2>&1

echo =========================================
echo Actualizando version.json...
echo =========================================
echo { "version": "%NEW_VERSION%", "url": "https://github.com/danielop9305/taller/releases/download/%NEW_VERSION%/app.exe" } > version.json

git add version.json
git commit -m "Actualizacion automatica de version %NEW_VERSION%"
git push origin main

echo =========================================
echo Verificando si el release ya existe...
echo =========================================
gh release view %NEW_VERSION% >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo ⚠️ El release %NEW_VERSION% ya existe. Se actualizara con el nuevo ejecutable...
    gh release upload %NEW_VERSION% dist\app.exe --clobber
) ELSE (
    echo Publicando nuevo ejecutable en GitHub Releases...
    gh release create %NEW_VERSION% dist\app.exe --title "Version %NEW_VERSION%" --notes "Compilacion automatica"
)

echo =========================================
echo Proceso terminado correctamente.
echo El nuevo .exe esta en la carpeta "dist" y publicado en GitHub.
echo =========================================
pause

