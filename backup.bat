@echo off
cd /d "%~dp0"
echo Backup do banco do Meu Predio (Turso) para a pasta dados\backups
echo.
python backup.py
echo.
pause
