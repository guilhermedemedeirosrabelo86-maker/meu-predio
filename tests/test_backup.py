"""Backup do Turso para um arquivo e restauração para um banco vazio (com o Turso falso dos testes)."""
import os
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import backup
from backend import db
from tests.turso_falso import TursoFalso


def turso(arquivo):
    servidor = TursoFalso(str(arquivo))
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor


class TesteBackup(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.servidores = []
        # Banco "em produção" com um pouco de tudo, inclusive uma foto (blob) e chaves estrangeiras.
        self.producao = self.pasta / "producao.db"
        db.inicializar(str(self.producao))
        conn = sqlite3.connect(self.producao)
        with conn:
            conn.execute("INSERT INTO usuarios (id, nome, email, senha_hash) VALUES (1, 'Ana', 'ana@x.com', 'h')")
            conn.execute("INSERT INTO condominios (id, nome, codigo_convite, foto) VALUES (1, 'Flores', 'ABC234', 'f.jpg')")
            conn.execute("INSERT INTO unidades (id, condominio_id, identificador) VALUES (1, 1, '101')")
            conn.execute("INSERT INTO membros (usuario_id, condominio_id, unidade_id, papel, status) VALUES (1, 1, 1, 'sindico', 'ativo')")
            conn.execute("INSERT INTO arquivos (nome, conteudo) VALUES ('predios/f.jpg', ?)", (b"\xff\xd8\xff" + bytes(range(256)) * 40,))
        conn.close()

    def tearDown(self):
        for s in self.servidores:
            s.shutdown()
            s.server_close()

    def subir(self, arquivo):
        s = turso(arquivo)
        self.servidores.append(s)
        return s.url

    def contagens(self, arquivo):
        conn = sqlite3.connect(arquivo)
        try:
            return {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in backup.tabelas_em_ordem(conn)}
        finally:
            conn.close()

    def test_backup_copia_tudo_e_abre_no_app(self):
        copia = self.pasta / "backups" / "b.db"
        backup.fazer_backup(self.subir(self.producao), None, copia)
        self.assertEqual(self.contagens(copia), self.contagens(self.producao))
        conn = db.conectar(str(copia))
        self.assertEqual(db.ler_arquivo(conn, "predios/f.jpg")[:3], b"\xff\xd8\xff")
        conn.close()
        db.inicializar(str(copia))  # o app consegue abrir e atualizar o backup

    def test_restaurar_vai_para_banco_vazio(self):
        copia = self.pasta / "b.db"
        backup.fazer_backup(self.subir(self.producao), None, copia)
        novo = self.pasta / "novo.db"
        sqlite3.connect(novo).close()
        with mock.patch.dict(os.environ, {"TURSO_AUTH_TOKEN": ""}):
            backup.restaurar(str(copia), self.subir(novo), None)
        self.assertEqual(self.contagens(novo), self.contagens(self.producao))

    def test_restaurar_recusa_banco_com_dados(self):
        copia = self.pasta / "b.db"
        backup.fazer_backup(self.subir(self.producao), None, copia)
        with self.assertRaises(SystemExit):
            backup.restaurar(str(copia), self.subir(self.producao), None)  # o próprio banco em uso
        self.assertEqual(self.contagens(self.producao)["usuarios"], 1)  # nada foi duplicado

    def test_nao_sobrescreve_backup_existente(self):
        copia = self.pasta / "b.db"
        copia.write_bytes(b"x")
        with self.assertRaises(SystemExit):
            backup.fazer_backup(self.subir(self.producao), None, copia)
        self.assertEqual(copia.read_bytes(), b"x")


class TesteToken(unittest.TestCase):
    TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicncifQ.c2lnbmF0dXJh"

    def test_colado_duas_vezes_fica_um_so(self):
        self.assertEqual(backup.limpar_token(self.TOKEN + self.TOKEN), self.TOKEN)

    def test_espacos_e_bearer(self):
        self.assertEqual(backup.limpar_token(f"  Bearer {self.TOKEN}\n"), self.TOKEN)

    def test_formato_errado_avisa(self):
        with self.assertRaises(SystemExit):
            backup.limpar_token("abc")
