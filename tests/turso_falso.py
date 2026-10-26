"""Imitação local da API HTTP do Turso (/v2/pipeline) sobre um arquivo SQLite.

Serve para rodar os testes com o banco "remoto": MEU_PREDIO_TESTE_TURSO=1 python -m unittest
Responde no mesmo formato do Turso (inteiros como texto, blobs em base64, erros com código).
"""
import base64
import json
import secrets
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class TursoFalso(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, arquivo_db):
        super().__init__(("127.0.0.1", 0), _Manipulador)
        self.arquivo_db = arquivo_db
        self.conexoes = {}  # baton -> conexão sqlite3
        self.trava = threading.Lock()
        self.pedidos = 0

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_address[1]}"


class _Manipulador(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path != "/v2/pipeline":
            self.send_error(404)
            return
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        servidor = self.server
        with servidor.trava:
            servidor.pedidos += 1
            baton = corpo.get("baton")
            conn = servidor.conexoes.pop(baton, None) if baton else None
        if baton and conn is None:
            self._json(400, {"message": "baton inválido"})
            return
        if conn is None:
            conn = sqlite3.connect(servidor.arquivo_db, timeout=10, isolation_level=None, check_same_thread=False)
        resultados, fechada = [], False
        for pedido in corpo["requests"]:
            if pedido["type"] == "close":
                conn.close()
                fechada = True
                resultados.append({"type": "ok", "response": {"type": "close"}})
                continue
            resultados.append(_executar(conn, pedido["stmt"]))
        novo_baton = None
        if not fechada:
            novo_baton = secrets.token_hex(8)
            with servidor.trava:
                servidor.conexoes[novo_baton] = conn
        self._json(200, {"baton": novo_baton, "base_url": None, "results": resultados})

    def _json(self, status, dados):
        conteudo = json.dumps(dados).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(conteudo)))
        self.end_headers()
        self.wfile.write(conteudo)


def _executar(conn, stmt):
    try:
        cursor = conn.execute(stmt["sql"], [_valor(a) for a in stmt.get("args", [])])
        linhas = cursor.fetchall()
    except sqlite3.Error as erro:
        codigo = "SQLITE_CONSTRAINT" if isinstance(erro, sqlite3.IntegrityError) else "SQLITE_ERROR"
        return {"type": "error", "error": {"message": str(erro), "code": codigo}}
    colunas = [{"name": d[0], "decltype": None} for d in cursor.description or []]
    return {"type": "ok", "response": {"type": "execute", "result": {
        "cols": colunas,
        "rows": [[_argumento(v) for v in linha] for linha in linhas],
        "affected_row_count": max(cursor.rowcount, 0),
        "last_insert_rowid": str(cursor.lastrowid) if cursor.lastrowid else None,
        "replication_index": None,
    }}}


def _valor(arg):
    tipo = arg["type"]
    if tipo == "null":
        return None
    if tipo == "integer":
        return int(arg["value"])
    if tipo == "float":
        return float(arg["value"])
    if tipo == "blob":
        return base64.b64decode(arg["base64"])
    return arg["value"]


def _argumento(valor):
    if valor is None:
        return {"type": "null"}
    if isinstance(valor, int):
        return {"type": "integer", "value": str(valor)}
    if isinstance(valor, float):
        return {"type": "float", "value": valor}
    if isinstance(valor, bytes):
        # O Turso manda base64 sem o "=" do final.
        return {"type": "blob", "base64": base64.b64encode(valor).decode().rstrip("=")}
    return {"type": "text", "value": valor}
