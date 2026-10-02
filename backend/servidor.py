"""Servidor HTTP: entrega o app (pasta web/) e a API JSON (/api/...)."""
import json
import os
import socket
import traceback
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from . import auth, db
from . import (  # noqa: F401  (registram as rotas)
    rotas_avisos, rotas_condominio, rotas_conta, rotas_contas, rotas_ocorrencias, rotas_painel, rotas_reservas,
    rotas_sistema, rotas_taxas, rotas_visitas,
)
from .web import Arquivo, ErroHTTP, Requisicao, encontrar

PASTA_WEB = Path(__file__).resolve().parent.parent / "web"
LIMITE_CORPO = 64 * 1024
LIMITE_IMAGEM = 3 * 1024 * 1024
TIPOS = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".webmanifest": "application/manifest+json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
}
CSP = "default-src 'self'; img-src 'self' data: blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"


class Manipulador(BaseHTTPRequestHandler):
    server_version = "MeuPredio/0.1"

    def do_GET(self):
        self._despachar("GET")

    def do_POST(self):
        self._despachar("POST")

    def do_PATCH(self):
        self._despachar("PATCH")

    def do_DELETE(self):
        self._despachar("DELETE")

    def _despachar(self, metodo):
        partes = urlsplit(self.path)
        caminho = partes.path
        if caminho.startswith("/api/"):
            self._api(metodo, caminho, dict(parse_qsl(partes.query)))
        elif metodo == "GET":
            self._estatico(caminho)
        else:
            self._responder_json(405, {"erro": "Método não permitido."})

    # --- API ------------------------------------------------------------------

    def _api(self, metodo, caminho, query):
        conn = db.conectar(self.server.caminho_db)
        cookies = []
        try:
            funcao, params = encontrar(metodo, caminho)
            corpo, bruto, tipo = self._ler_corpo() if metodo in ("POST", "PATCH") else ({}, None, "")
            usuario, token_hash = self._sessao(conn)
            req = Requisicao(conn, corpo, usuario, token_hash, query, bruto, tipo, self.server.pasta_arquivos)
            resultado = funcao(req, **params)
            status, dados = resultado if isinstance(resultado, tuple) else (200, resultado)
            conn.commit()
            cookies = req.cookies_saida
        except ErroHTTP as erro:
            conn.rollback()
            status, dados = erro.status, {"erro": erro.mensagem}
        except Exception:
            conn.rollback()
            self.log_error("Erro inesperado em %s %s\n%s", metodo, caminho, traceback.format_exc())
            status, dados = 500, {"erro": "Erro interno. Tente novamente."}
        finally:
            conn.close()
        if isinstance(dados, Arquivo):
            self._responder_arquivo(dados)
        else:
            self._responder_json(status, dados, cookies)

    def _responder_arquivo(self, arquivo):
        self.send_response(200)
        self.send_header("Content-Type", arquivo.tipo)
        self.send_header("Content-Length", str(len(arquivo.conteudo)))
        self.send_header("Cache-Control", "private, max-age=86400")
        self._cabecalhos_seguranca()
        self.end_headers()
        self.wfile.write(arquivo.conteudo)

    def _ler_corpo(self):
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ErroHTTP(400, "Requisição inválida.")
        tipo = self.headers.get("Content-Type") or ""
        if tamanho == 0:
            return {}, None, ""
        if tipo.startswith("image/"):
            if tamanho > LIMITE_IMAGEM:
                raise ErroHTTP(413, "Foto grande demais (máximo 3 MB).")
            return {}, self.rfile.read(tamanho), tipo
        if tamanho > LIMITE_CORPO:
            raise ErroHTTP(413, "Conteúdo grande demais.")
        if not tipo.startswith("application/json"):
            raise ErroHTTP(415, "Envie os dados em JSON.")
        try:
            corpo = json.loads(self.rfile.read(tamanho))
        except (ValueError, UnicodeDecodeError):
            raise ErroHTTP(400, "JSON inválido.")
        if not isinstance(corpo, dict):
            raise ErroHTTP(400, "JSON inválido.")
        return corpo, None, ""

    def _sessao(self, conn):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie") or "")
        except CookieError:
            return None, None
        if "sessao" not in cookie:
            return None, None
        token_hash = auth.hash_token(cookie["sessao"].value)
        usuario = conn.execute(
            """SELECT u.* FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id
               WHERE s.token_hash = ? AND s.expira_em > datetime('now')""",
            (token_hash,),
        ).fetchone()
        return (usuario, token_hash) if usuario else (None, None)

    def _responder_json(self, status, dados, cookies=()):
        conteudo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(conteudo)))
        self.send_header("Cache-Control", "no-store")
        for cookie in cookies:
            self.send_header("Set-Cookie", cookie)
        self._cabecalhos_seguranca()
        self.end_headers()
        self.wfile.write(conteudo)

    # --- Arquivos do app ------------------------------------------------------

    def _estatico(self, caminho):
        arquivo = (PASTA_WEB / (caminho.lstrip("/") or "index.html")).resolve()
        if not arquivo.is_relative_to(PASTA_WEB) or not arquivo.is_file():
            conteudo = b"Nao encontrado"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(conteudo)))
            self.end_headers()
            self.wfile.write(conteudo)
            return
        conteudo = arquivo.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", TIPOS.get(arquivo.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(conteudo)))
        self.send_header("Cache-Control", "no-cache")
        self._cabecalhos_seguranca()
        self.end_headers()
        self.wfile.write(conteudo)

    def _cabecalhos_seguranca(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", CSP)


class Servidor(ThreadingHTTPServer):
    daemon_threads = True
    # No Windows, SO_REUSEADDR deixa dois servidores na mesma porta (cada pedido cai num deles).
    # Lá pedimos a porta com exclusividade; se estiver ocupada, a abertura falha e rodar.py tenta outra.
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def criar_servidor(host, porta, caminho_db):
    db.inicializar(caminho_db)
    servidor = Servidor((host, porta), Manipulador)
    servidor.caminho_db = caminho_db
    rotas_sistema.INFO.update(host=host, porta=servidor.server_address[1])
    servidor.pasta_arquivos = Path(caminho_db).resolve().parent / "arquivos"
    servidor.pasta_arquivos.mkdir(parents=True, exist_ok=True)
    return servidor
