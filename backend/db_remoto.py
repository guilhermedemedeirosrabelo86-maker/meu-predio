"""Banco na nuvem (Turso): fala com o servidor pela API HTTP do libSQL e imita o módulo sqlite3.

Só a parte do sqlite3 que o app usa: execute, executemany, executescript, commit, rollback, close,
cursores com fetchone/fetchall/lastrowid/rowcount e linhas acessíveis por nome ou posição.
Não usa bibliotecas externas: os pedidos saem com urllib.
"""
import base64
import json
import sqlite3
import urllib.error
import urllib.request

ESCRITA = ("INSERT", "UPDATE", "DELETE", "REPLACE")


def eh_remoto(caminho):
    return str(caminho).startswith(("libsql://", "https://", "http://"))


class Linha:
    """Equivale a sqlite3.Row: linha["coluna"], linha[0], linha.keys() e dict(linha)."""

    __slots__ = ("_colunas", "_valores")

    def __init__(self, colunas, valores):
        self._colunas = colunas
        self._valores = valores

    def keys(self):
        return list(self._colunas)

    def __getitem__(self, chave):
        if isinstance(chave, (int, slice)):
            return self._valores[chave]
        try:
            return self._valores[self._colunas.index(chave)]
        except ValueError:
            for i, coluna in enumerate(self._colunas):
                if coluna.lower() == chave.lower():
                    return self._valores[i]
            raise IndexError("No item with that key") from None

    def __iter__(self):
        return iter(self._valores)

    def __len__(self):
        return len(self._valores)

    def __repr__(self):
        return f"Linha({dict(zip(self._colunas, self._valores))!r})"


class Cursor:
    def __init__(self, resultado):
        self._colunas = [coluna["name"] for coluna in resultado["cols"]]
        self._linhas = [Linha(self._colunas, [_valor(v) for v in linha]) for linha in resultado["rows"]]
        self.rowcount = resultado.get("affected_row_count", -1)
        rowid = resultado.get("last_insert_rowid")
        self.lastrowid = int(rowid) if rowid is not None else None
        self.description = [(nome, None, None, None, None, None, None) for nome in self._colunas] or None

    def fetchone(self):
        return self._linhas.pop(0) if self._linhas else None

    def fetchall(self):
        linhas, self._linhas = self._linhas, []
        return linhas

    def __iter__(self):
        while self._linhas:
            yield self._linhas.pop(0)


class Conexao:
    """Uma conexão com o banco no Turso. Como no sqlite3, a transação começa sozinha antes da
    primeira escrita e termina no commit ou rollback. Cada commit/rollback fecha a conexão no
    servidor (economiza um pedido); a próxima instrução abre outra."""

    def __init__(self, url, token=None, timeout=15):
        self.url = "https://" + url[len("libsql://"):] if url.startswith("libsql://") else url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.row_factory = None  # ignorado: as linhas já vêm como Linha
        self._baton = None
        self._em_transacao = False

    # --- interface do sqlite3 -------------------------------------------------

    def execute(self, sql, parametros=()):
        pedidos = []
        if not self._em_transacao and sql.lstrip().upper().startswith(ESCRITA):
            pedidos.append(_instrucao("BEGIN"))
        pedidos.append(_instrucao(sql, parametros))
        resultados = self._enviar(pedidos)
        return Cursor(resultados[-1])

    def executemany(self, sql, lista_parametros):
        lista_parametros = list(lista_parametros)
        if not lista_parametros:
            return None
        pedidos = [] if self._em_transacao else [_instrucao("BEGIN")]
        pedidos += [_instrucao(sql, parametros) for parametros in lista_parametros]
        resultados = self._enviar(pedidos)
        cursor = Cursor(resultados[-1])
        cursor.rowcount = sum(r.get("affected_row_count", 0) for r in resultados[-len(lista_parametros):])
        return cursor

    def executescript(self, script):
        self.commit()
        instrucoes, atual = [], ""
        for linha in script.splitlines(keepends=True):
            atual += linha
            if sqlite3.complete_statement(atual):
                instrucoes.append(atual.strip())
                atual = ""
        if atual.strip():
            instrucoes.append(atual.strip())
        if instrucoes:
            self._enviar([_instrucao(sql) for sql in instrucoes])
        return None

    def commit(self):
        self._finalizar("COMMIT")

    def rollback(self):
        self._finalizar("ROLLBACK")

    def close(self):
        self._finalizar("ROLLBACK")

    def __enter__(self):
        return self

    def __exit__(self, tipo, *_):
        self.commit() if tipo is None else self.rollback()
        return False

    # --- comunicação ----------------------------------------------------------

    def _finalizar(self, comando):
        if self._baton is None:
            self._em_transacao = False
            return
        pedidos = [_instrucao(comando)] if self._em_transacao else []
        try:
            self._enviar(pedidos, fechar=True)
        finally:
            self._baton = None
            self._em_transacao = False

    def _enviar(self, instrucoes, fechar=False):
        """Manda as instruções num só pedido e devolve o resultado de cada uma.
        Numa conexão nova, liga antes as chaves estrangeiras (vale por conexão, como no SQLite)."""
        pedidos = list(instrucoes)
        prefixo = 0
        if self._baton is None:
            pedidos.insert(0, _instrucao("PRAGMA foreign_keys = ON"))
            prefixo = 1
        if fechar:
            pedidos.append({"type": "close"})
        resposta = self._post({"baton": self._baton, "requests": pedidos})
        self._baton = None if fechar else resposta.get("baton")
        if resposta.get("base_url"):
            self.url = resposta["base_url"].rstrip("/")
        resultados = []
        for pedido, item in zip(pedidos[prefixo:], resposta["results"][prefixo:]):
            if pedido["type"] == "close":
                continue
            sql = pedido["stmt"]["sql"].strip().upper()
            if item["type"] != "ok":
                raise _erro(item.get("error") or {})
            if sql.startswith("BEGIN"):
                self._em_transacao = True
            elif sql in ("COMMIT", "ROLLBACK", "END"):
                self._em_transacao = False
            resultados.append(item["response"]["result"])
        return resultados

    def _post(self, corpo):
        pedido = urllib.request.Request(
            self.url + "/v2/pipeline", data=json.dumps(corpo).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json"},
        )
        if self.token:
            pedido.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(pedido, timeout=self.timeout) as resposta:
                return json.loads(resposta.read())
        except urllib.error.HTTPError as erro:
            detalhe = erro.read().decode("utf-8", "replace")[:300]
            self._baton = None
            self._em_transacao = False
            raise sqlite3.OperationalError(f"Banco respondeu {erro.code}: {detalhe}") from None
        except (urllib.error.URLError, TimeoutError) as erro:
            self._baton = None
            self._em_transacao = False
            raise sqlite3.OperationalError(f"Sem conexão com o banco: {erro}") from None


def conectar(url, token=None):
    return Conexao(url, token)


def _instrucao(sql, parametros=()):
    return {"type": "execute", "stmt": {"sql": sql, "args": [_argumento(p) for p in parametros]}}


def _argumento(valor):
    if valor is None:
        return {"type": "null"}
    if isinstance(valor, bool):
        return {"type": "integer", "value": str(int(valor))}
    if isinstance(valor, int):
        return {"type": "integer", "value": str(valor)}
    if isinstance(valor, float):
        return {"type": "float", "value": valor}
    if isinstance(valor, (bytes, bytearray, memoryview)):
        return {"type": "blob", "base64": base64.b64encode(bytes(valor)).decode("ascii")}
    return {"type": "text", "value": str(valor)}


def _valor(item):
    tipo = item["type"]
    if tipo == "null":
        return None
    if tipo == "integer":
        return int(item["value"])
    if tipo == "float":
        return float(item["value"])
    if tipo == "blob":
        texto = item.get("base64") or ""
        return base64.b64decode(texto + "=" * (-len(texto) % 4))  # o servidor pode omitir o "=" final
    return item["value"]


def _erro(erro):
    mensagem = erro.get("message") or "Erro no banco."
    codigo = erro.get("code") or ""
    if codigo.startswith("SQLITE_CONSTRAINT") or "constraint failed" in mensagem:
        return sqlite3.IntegrityError(mensagem)
    return sqlite3.OperationalError(mensagem)
