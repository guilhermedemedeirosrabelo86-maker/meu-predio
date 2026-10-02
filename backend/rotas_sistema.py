"""Informações do servidor para abrir o app no celular pela rede Wi-Fi."""
import socket

from .web import rota

# Preenchido por criar_servidor com o host e a porta em que o servidor está escutando.
INFO = {"host": "127.0.0.1", "porta": 8000}


def ips_locais():
    ips = set()
    try:
        # "Conectar" UDP não envia nada; só descobre qual placa de rede seria usada.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    try:
        ips.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith(("127.", "169.254.")))


@rota("GET", "/api/rede")
def rede(req):
    porta = INFO["porta"]
    return {
        "aberto_na_rede": INFO["host"] in ("0.0.0.0", ""),
        "porta": porta,
        "enderecos": [f"http://{ip}:{porta}" for ip in ips_locais()],
    }

