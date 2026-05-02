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
echo Actualizando pip y pyinstaller si hay nuevas versiones...
echo =========================================
python -m pip install --upgrade pip
pip install --upgrade pyinstaller

echo =========================================
echo Instalando dependencias necesarias...
echo =========================================
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

echo =========================================
echo Compilando nuevo ejecutable con PyInstaller...
echo =========================================
pyinstaller --onefile ^
 --add-data "templates;templates" ^
 --add-data "static;static" ^
 --add-data "instance/taller.db;instance" ^
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
echo Actualizando version.json y version.txt...
echo =========================================
setlocal enabledelayedexpansion

REM Leer versión actual de version.json si existe
set current=0.0.0
for /f "tokens=2 delims=:," %%A in ('findstr "version" version.json 2^>nul') do set current=%%~A
set current=!current:"=!

echo Versión actual: !current!
echo.
echo Selecciona qué incrementar:
echo 1 - MAJOR
echo 2 - MINOR
echo 3 - PATCH
set /p choice=Opción:

for /f "tokens=1-3 delims=." %%a in ("!current!") do (
    set major=%%a
    set minor=%%b
    set patch=%%c
)

if "!choice!"=="1" (
    set /a major+=1
    set minor=0
    set patch=0
)
if "!choice!"=="2" (
    set /a minor+=1
    set patch=0
)
if "!choice!"=="3" (
    set /a patch+=1
)

set version=!major!.!minor!.!patch!

REM Actualizar ambos archivos
echo { "version": "!version!", "url": "https://github.com/danielop9305/taller/releases/download/!version!/app.exe" } > version.json
echo !version! > version.txt

echo =========================================
echo Subiendo version.json y version.txt al repositorio Git...
echo =========================================
git add version.json version.txt
git commit -m "Actualizacion automatica de version !version!"
git push origin main

echo =========================================
echo Verificando si el release ya existe...
echo =========================================
gh release view !version! >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo ⚠️ El release !version! ya existe. Se actualizara con el nuevo ejecutable...
    gh release upload !version! dist\app.exe --clobber
) ELSE (
    echo =========================================
    echo Publicando nuevo ejecutable en GitHub Releases...
    echo =========================================
    gh release create !version! dist\app.exe --title "Version !version!" --notes "Compilacion automatica"
)

echo =========================================
echo Proceso terminado correctamente.
echo El nuevo .exe esta en la carpeta "dist" y publicado en GitHub.
echo =========================================
pause
