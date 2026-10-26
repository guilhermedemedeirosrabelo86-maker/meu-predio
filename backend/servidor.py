"""Servidor HTTP: entrega o app (pasta web/) e a API JSON (/api/...)."""
import gzip
import json
import os
import socket
import sys
import traceback
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from . import auth, db
from . import (  # noqa: F401  (registram as rotas)
    historico, rotas_avisos, rotas_condominio, rotas_conta, rotas_contas, rotas_encomendas, rotas_enquetes, rotas_ocorrencias,
    rotas_painel, rotas_privacidade, rotas_reservas, rotas_sistema, rotas_taxas, rotas_telefones, rotas_visitas,
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
COMPACTAVEIS = {".html", ".js", ".css", ".json", ".webmanifest", ".svg", ".txt"}
_compactados = {}  # (caminho, etag) -> conteúdo em gzip, para não compactar o mesmo arquivo toda vez
CSP = "default-src 'self'; img-src 'self' data: blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"


class Manipulador(BaseHTTPRequestHandler):
    server_version = "MeuPredio/0.1"
    # HTTP/1.1 mantém a conexão aberta entre os pedidos (keep-alive): no celular, pelo Wi-Fi,
    # cada conexão nova custa uma ida e volta a mais. Conexões paradas fecham depois de 30 s.
    protocol_version = "HTTP/1.1"
    timeout = 30

    @property
    def caminho_db(self):
        """Arquivo do SQLite ou endereço do Turso. Na Vercel, a subclasse em api/index.py o define direto."""
        return self.server.caminho_db

    def ip_cliente(self):
        """Endereço de quem fez o pedido. Na Vercel, api/index.py lê o cabeçalho que ela preenche."""
        return self.client_address[0]

    def endereco_app(self):
        """Endereço público do app, para links em e-mails. Hospedado, defina APP_URL: o cabeçalho
        Host vem de quem pede e poderia apontar o link para outro site."""
        if os.environ.get("APP_URL"):
            return os.environ["APP_URL"].rstrip("/")
        protocolo = self.headers.get("X-Forwarded-Proto") or "http"
        return f"{protocolo}://{self.headers.get('Host') or 'localhost'}"

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
            self._corpo_lido = False
            self._descartar_corpo()
            self._responder_json(405, {"erro": "Método não permitido."})

    # --- API ------------------------------------------------------------------

    def _api(self, metodo, caminho, query):
        conn = db.conectar(self.caminho_db)
        cookies = []
        self._corpo_lido = metodo not in ("POST", "PATCH")
        try:
            funcao, params = encontrar(metodo, caminho)
            corpo, bruto, tipo = self._ler_corpo() if metodo in ("POST", "PATCH") else ({}, None, "")
            usuario, token_hash = self._sessao(conn)
            req = Requisicao(conn, corpo, usuario, token_hash, query, bruto, tipo, self.ip_cliente(), self.endereco_app())
            req.autorizacao = self.headers.get("Authorization") or ""
            resultado = funcao(req, **params)
            status, dados = resultado if isinstance(resultado, tuple) else (200, resultado)
            conn.commit()
            cookies = req.cookies_saida
        except ErroHTTP as erro:
            conn.rollback()
            status, dados = erro.status, {"erro": erro.mensagem}
            self._descartar_corpo()
        except Exception:
            conn.rollback()
            self._descartar_corpo()
            self.log_error("Erro inesperado em %s %s\n%s", metodo, caminho, traceback.format_exc())
            status, dados = 500, {"erro": "Erro interno. Tente novamente."}
        finally:
            conn.close()
        if isinstance(dados, Arquivo):
            self._responder_arquivo(dados)
        else:
            self._responder_json(status, dados, cookies)

    def log_message(self, formato, *args):
        super().log_message(formato, *args)
        registro = getattr(self.server, "registro_acessos", None)
        if registro is not None:
            # Para diagnóstico: quem pede a página inicial também diz qual navegador é.
            navegador = f' "{self.headers.get("User-Agent", "")}"' if getattr(self, "path", "").split("?")[0] == "/" else ""
            linha = f"{self.log_date_time_string()} {self.address_string()} {formato % args}{navegador}\n"
            with registro["trava"]:
                with open(registro["arquivo"], "a", encoding="utf-8") as arquivo:
                    arquivo.write(linha)

    def _descartar_corpo(self):
        """Erro antes de ler o corpo do pedido: lê e joga fora, para a conexão servir ao próximo pedido.
        Se o corpo for grande demais (ou inválido), fecha a conexão avisando o navegador."""
        if self._corpo_lido:
            return
        self._corpo_lido = True
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            tamanho = -1
        if 0 <= tamanho <= LIMITE_IMAGEM:
            self.rfile.read(tamanho)
        else:
            self.close_connection = True

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
            self._corpo_lido = True
            return {}, self.rfile.read(tamanho), tipo
        if tamanho > LIMITE_CORPO:
            raise ErroHTTP(413, "Conteúdo grande demais.")
        if not tipo.startswith("application/json"):
            raise ErroHTTP(415, "Envie os dados em JSON.")
        bruto = self.rfile.read(tamanho)
        self._corpo_lido = True
        try:
            corpo = json.loads(bruto)
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
        if self.close_connection:
            self.send_header("Connection", "close")
        # Hospedado com HTTPS (a Vercel avisa por este cabeçalho), o cookie só viaja criptografado.
        seguro = "; Secure" if self.headers.get("X-Forwarded-Proto") == "https" else ""
        for cookie in cookies:
            self.send_header("Set-Cookie", cookie + seguro)
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
        # O navegador guarda o arquivo e pergunta se mudou (ETag); se não mudou, a resposta é vazia (304).
        info = arquivo.stat()
        etag = f'"{info.st_mtime_ns:x}-{info.st_size:x}"'
        if self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            return
        conteudo = arquivo.read_bytes()
        compactar = arquivo.suffix in COMPACTAVEIS and "gzip" in (self.headers.get("Accept-Encoding") or "")
        if compactar:
            chave = (arquivo, etag)
            if chave not in _compactados:
                _compactados[chave] = gzip.compress(conteudo, compresslevel=6)
            conteudo = _compactados[chave]
        self.send_response(200)
        self.send_header("Content-Type", TIPOS.get(arquivo.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(conteudo)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("ETag", etag)
        self.send_header("Vary", "Accept-Encoding")
        if compactar:
            self.send_header("Content-Encoding", "gzip")
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

    def handle_error(self, request, client_address):
        # Com keep-alive, o navegador fecha conexões que não vai mais usar: isso não é erro.
        if issubclass(sys.exc_info()[0] or type(None), (ConnectionError, TimeoutError)):
            return
        super().handle_error(request, client_address)

    def server_bind(self):
        if os.name == "nt":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def criar_servidor(host, porta, caminho_db):
    db.inicializar(caminho_db)
    conn = db.conectar(caminho_db)
    try:
        rotas_privacidade.limpar_dados_antigos(conn)
    finally:
        conn.close()
    servidor = Servidor((host, porta), Manipulador)
    servidor.caminho_db = caminho_db
    rotas_sistema.INFO.update(host=host, porta=servidor.server_address[1])
    return servidor
