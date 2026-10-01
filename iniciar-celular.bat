@echo off
cd /d "%~dp0"
echo Abrindo o Meu Predio para o celular (mesma rede Wi-Fi)...
echo Se o Windows perguntar se o Python pode acessar a rede, clique em Permitir.
python rodar.py --host 0.0.0.0 --abrir celular %*
pause
