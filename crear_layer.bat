@echo off
:: Ruta del script (sin barra final)
SET CURRENT_DIR=%~dp0
SET CURRENT_DIR=%CURRENT_DIR:~0,-1%

:: Definir carpeta de aje-libs (hermana de la actual)
pushd "%CURRENT_DIR%\..\aje-libs"
SET AJELIB_DIR=%CD%
popd

SET PYTHON_VERSION=3.10

echo ===================================
echo AWS Lambda Layers Generator
echo ===================================
echo.

:: Confirmación del usuario
echo Este script generará los siguientes layers para AWS Lambda:
echo  - layer_aje_libs
echo  - layer_odbc
echo  - layer_docs
echo  - layer_pinecone
echo.
echo Los layers se crearán en: %CURRENT_DIR%
echo.
set /p CONFIRM=¿Desea continuar? (S/N): 
if /i not "%CONFIRM%"=="S" goto :EOF

:: Crear entorno virtual
echo.
echo Creando entorno virtual...
python -m venv venv
call venv\Scripts\activate.bat

:: Actualizar pip
echo.
echo Actualizando pip...
python -m pip install --upgrade pip

:: Crear layers
call :create_layer "layer_aje_libs" "%AJELIB_DIR%"
call :create_layer "layer_odbc" "pyodbc>=4.0.39"
call :create_layer "layer_docs" "python-docx>=0.8.11 python-pptx>=0.6.21 openpyxl>=3.1.0 PyPDF2>=3.0.0 lxml==4.9.2"
call :create_layer "layer_pinecone" "pinecone>=2.2.0"
call :create_layer "layer_pinecone" "requests>=2.31.0"

:: Desactivar entorno virtual
call venv\Scripts\deactivate.bat

:: Mensaje final
echo.
echo ===================================
echo Proceso completado
echo ===================================
echo.
echo Layers creados en: %CURRENT_DIR%
echo.
pause > nul
goto :eof

:: ===================================
:: Función: create_layer
:: ===================================
:create_layer
SETLOCAL
set LAYER_NAME=%~1
set DEPENDENCIES=%~2
set TARGET_DIR=%CURRENT_DIR%\%LAYER_NAME%
echo.
echo ===================================
echo Creando %LAYER_NAME%
echo ===================================
if exist "%TARGET_DIR%" rmdir /s /q "%TARGET_DIR%"
mkdir "%TARGET_DIR%\python"
echo Instalando: %DEPENDENCIES%
pip install --no-cache-dir -t "%TARGET_DIR%\python" %DEPENDENCIES%

:: Comprimir y crear el .zip
echo Comprimiendo %LAYER_NAME%...
pushd "%TARGET_DIR%"
powershell Compress-Archive -Path "python" -DestinationPath "%TARGET_DIR%\%LAYER_NAME%.zip" -Force
popd

:: Eliminar la carpeta 'python' después de comprimir, si quieres
rmdir /s /q "%TARGET_DIR%\python"

echo %LAYER_NAME% creado: %TARGET_DIR%\%LAYER_NAME%.zip
ENDLOCAL
goto :eof
