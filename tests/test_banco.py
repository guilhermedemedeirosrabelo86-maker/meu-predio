import sqlite3
import tempfile
import unittest
import urllib.request
from pathlib import Path

from backend import db
from tests.base import BaseApi


class TestImportarArquivos(unittest.TestCase):
    def test_fotos_da_pasta_antiga_vao_para_o_banco(self):
        with tempfile.TemporaryDirectory() as pasta:
            antiga = Path(pasta) / "arquivos" / "contas"
            antiga.mkdir(parents=True)
            (antiga / "abc.jpg").write_bytes(b"foto")
            caminho = str(Path(pasta) / "teste.db")
            db.inicializar(caminho)
            db.inicializar(caminho)  # a segunda vez não acha mais a pasta e não faz nada

            conn = db.conectar(caminho)
            self.assertEqual(db.ler_arquivo(conn, "contas/abc.jpg"), b"foto")
            conn.close()
            self.assertFalse((Path(pasta) / "arquivos").exists())
            self.assertTrue((Path(pasta) / "arquivos-importados" / "contas" / "abc.jpg").is_file())


class TestCookieSeguro(BaseApi):
    def cookie_do_cadastro(self, cabecalhos):
        BaseApi._contador += 1
        req = urllib.request.Request(
            self.base + "/api/auth/cadastro", method="POST",
            data=f'{{"nome": "Ana", "email": "cookie{BaseApi._contador}@exemplo.com", "senha": "senha-segura", "aceito_termos": true}}'.encode(),
            headers={"Content-Type": "application/json", **cabecalhos},
        )
        with urllib.request.urlopen(req) as resposta:
            return resposta.headers["Set-Cookie"]

    def test_secure_so_com_https(self):
        self.assertNotIn("Secure", self.cookie_do_cadastro({}))
        self.assertTrue(self.cookie_do_cadastro({"X-Forwarded-Proto": "https"}).endswith("; Secure"))


class TestBancoRemoto(BaseApi):
    """O adaptador do Turso se comporta como o sqlite3 nos pontos que o app usa."""

    def conexao(self):
        if not self.turso:
            self.skipTest("rode com MEU_PREDIO_TESTE_TURSO=1")
        return db.conectar(self.turso.url)

    def test_transacao_e_tipos(self):
        conn = self.conexao()
        conn.executescript("CREATE TABLE t (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, valor REAL, dado BLOB);")
        cursor = conn.execute("INSERT INTO t (nome, valor, dado) VALUES (?, ?, ?)", ("a", 1.5, b"\x00\xff"))
        self.assertEqual(cursor.lastrowid, 1)
        conn.rollback()
        self.assertIsNone(conn.execute("SELECT * FROM t").fetchone())

        conn.executemany("INSERT INTO t (nome, valor, dado) VALUES (?, ?, ?)", [("a", 1.5, b"\x00\xff"), ("b", None, None)])
        conn.commit()
        linha = conn.execute("SELECT * FROM t WHERE nome = ?", ("a",)).fetchone()
        self.assertEqual(dict(linha), {"id": 1, "nome": "a", "valor": 1.5, "dado": b"\x00\xff"})
        self.assertEqual((linha[0], linha["NOME"]), (1, "a"))
        self.assertEqual([tuple(l) for l in conn.execute("SELECT id, valor FROM t ORDER BY id")], [(1, 1.5), (2, None)])

        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO t (nome) VALUES ('a')")
        conn.rollback()
        self.assertEqual(conn.execute("UPDATE t SET valor = 2").rowcount, 2)
        conn.commit()
        conn.close()
        self.assertEqual(self.turso.conexoes, {})  # nenhuma conexão esquecida aberta no servidor
