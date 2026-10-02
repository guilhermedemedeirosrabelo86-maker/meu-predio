"""Inicia o Meu Prédio: python rodar.py [--host 0.0.0.0] [--porta 8000] [--abrir [pagina]]"""
import argparse
import threading
import webbrowser
from pathlib import Path

from backend.rotas_sistema import ips_locais
from backend.servidor import criar_servidor

PASTA = Path(__file__).resolve().parent
TENTATIVAS_DE_PORTA = 10


def iniciar(host, porta, banco):
    """Usa a porta pedida ou, se estiver ocupada (outra janela do servidor aberta), a próxima livre."""
    for tentativa in range(TENTATIVAS_DE_PORTA):
        try:
            return criar_servidor(host, porta + tentativa, banco)
        except OSError:
            print(f"  A porta {porta + tentativa} está ocupada (talvez outra janela do servidor esteja aberta).")
    raise SystemExit(f"Nenhuma porta livre entre {porta} e {porta + TENTATIVAS_DE_PORTA - 1}. Feche as outras janelas do servidor.")


def main():
    parser = argparse.ArgumentParser(description="Servidor do app Meu Prédio")
    parser.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 para acessar pelo celular na mesma rede")
    parser.add_argument("--porta", type=int, default=8000)
    parser.add_argument("--banco", default=str(PASTA / "dados" / "condominio.db"))
    parser.add_argument("--abrir", nargs="?", const="", metavar="PAGINA", help="abre o navegador (ex.: --abrir celular)")
    args = parser.parse_args()

    Path(args.banco).parent.mkdir(parents=True, exist_ok=True)
    servidor = iniciar(args.host, args.porta, args.banco)
    porta = servidor.server_address[1]
    # Registro dos pedidos desta execução (recomeça a cada vez), para investigar lentidão.
    arquivo_log = Path(args.banco).parent / "acessos.log"
    arquivo_log.write_text("", encoding="utf-8")
    servidor.registro_acessos = {"arquivo": arquivo_log, "trava": threading.Lock()}
    print(f"\nMeu Prédio rodando em http://localhost:{porta}  (Ctrl+C ou feche esta janela para parar)")
    if args.host == "0.0.0.0":
        enderecos = [f"http://{ip}:{porta}" for ip in ips_locais()]
        for endereco in enderecos:
            print(f"  No celular (mesmo Wi-Fi): {endereco}")
        if not enderecos:
            print("  Nenhuma rede Wi-Fi encontrada neste computador.")
    if args.abrir is not None:
        webbrowser.open(f"http://localhost:{porta}/#/{args.abrir}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor parado.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
