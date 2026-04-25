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
setlocal enabledelayedexpansion
for /f %%A in ('powershell -NoLogo -NoProfile -Command "(Get-Date).ToString(\"yyyyMMdd\")"') do set fecha=%%A
set version=1.0.%fecha%

echo { "version": "%version%", "url": "https://github.com/danielop9305/taller/releases/download/%version%/app.exe" } > version.json

echo =========================================
echo Subiendo version.json al repositorio Git...
echo =========================================
git add version.json
git commit -m "Actualizacion automatica de version %version%"
git push origin main

echo =========================================
echo Verificando si el release ya existe...
echo =========================================
gh release view %version% >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo ⚠️ El release %version% ya existe. Se actualizara con el nuevo ejecutable...
    gh release upload %version% dist\app.exe --clobber
) ELSE (
    echo =========================================
    echo Publicando nuevo ejecutable en GitHub Releases...
    echo =========================================
    gh release create %version% dist\app.exe --title "Version %version%" --notes "Compilacion automatica del %fecha%"
)

echo =========================================
echo Proceso terminado correctamente.
echo El nuevo .exe esta en la carpeta "dist" y publicado en GitHub.
echo =========================================
pause
