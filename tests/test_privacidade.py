"""LGPD: baixar os próprios dados, excluir a conta e limpeza de dados antigos."""
import os
import sqlite3
from unittest import mock

from backend import db, rotas_privacidade
from tests.base import BaseApi


class TestePrivacidade(BaseApi):
    def consultar(self, sql, params=()):
        conn = sqlite3.connect(self.arquivo_db)
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def test_exportar_dados(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        morador.post("/api/eu/contatos", {"nome": "Mãe", "telefone": "11 99999-0000"})
        status, dados = morador.get("/api/eu/dados")
        self.assertEqual(status, 200)
        self.assertEqual(dados["conta"]["nome"], "Bruno")
        self.assertTrue(dados["conta"]["termos_aceitos_em"])
        self.assertNotIn("senha_hash", dados["conta"])
        self.assertEqual(dados["contatos_emergencia"][0]["nome"], "Mãe")
        self.assertEqual(dados["condominios"][0]["unidade"], "102")

    def test_excluir_conta_de_morador(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        email = morador.get("/api/eu")[1]["usuario"]["email"]
        self.assertEqual(morador.post("/api/eu/excluir", {"senha": "errada"})[0], 400)
        self.assertEqual(morador.post("/api/eu/excluir", {"senha": "senha-segura"})[0], 200)
        self.assertEqual(morador.get("/api/eu")[0], 401)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM usuarios WHERE email = ?", (email,))[0][0], 0)
        textos = [i["texto"] for i in sindico.get(f"/api/condominios/{cid}/historico")[1]["itens"]]
        self.assertIn("Excluiu a própria conta e saiu do condomínio", textos)

    def test_unico_sindico_precisa_passar_o_cargo(self):
        sindico, morador, cid, membro_id = self.condominio_com_morador()
        status, dados = sindico.post("/api/eu/excluir", {"senha": "senha-segura"})
        self.assertEqual(status, 409)
        self.assertIn("único síndico", dados["erro"])
        sindico.patch(f"/api/condominios/{cid}/membros/{membro_id}", {"papel": "sindico"})
        self.assertEqual(sindico.post("/api/eu/excluir", {"senha": "senha-segura"})[0], 200)
        self.assertEqual(morador.get(f"/api/condominios/{cid}")[0], 200)  # o prédio continua

    def test_sozinho_no_condominio_apaga_o_condominio(self):
        sindico = self.novo_usuario()
        cid = sindico.post("/api/condominios", {"nome": "Solar", "unidades": ["1"], "minha_unidade": "1"})[1]["id"]
        self.assertEqual(sindico.post("/api/eu/excluir", {"senha": "senha-segura"})[0], 200)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM condominios WHERE id = ?", (cid,))[0][0], 0)

    def test_limpeza_de_dados_antigos(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        unidade = self.consultar("SELECT id FROM unidades WHERE condominio_id = ? LIMIT 1", (cid,))[0][0]
        conn = sqlite3.connect(self.arquivo_db)
        with conn:
            for token, fim in (("velha", "2020-01-01"), ("nova", "2999-01-01")):
                conn.execute(
                    "INSERT INTO visitas (condominio_id, unidade_id, nome, tipo, data_inicio, data_fim, token, codigo) "
                    "VALUES (?, ?, 'Visitante', 'visita', ?, ?, ?, ?)", (cid, unidade, fim, fim, token, token))
        conn.close()
        conn = db.conectar(self.arquivo_db)
        try:
            apagados = rotas_privacidade.limpar_dados_antigos(conn)
        finally:
            conn.close()
        self.assertEqual(apagados["visitas"], 1)
        self.assertEqual([l[0] for l in self.consultar("SELECT token FROM visitas")], ["nova"])

    def test_limpeza_agendada_exige_segredo(self):
        cliente = self.novo_usuario()
        self.assertEqual(cliente.get("/api/sistema/limpeza")[0], 404)  # sem CRON_SECRET configurado
        with mock.patch.dict(os.environ, {"CRON_SECRET": "segredo-do-cron"}):
            self.assertEqual(cliente.get("/api/sistema/limpeza")[0], 404)
            cliente.abridor.addheaders = [("Authorization", "Bearer segredo-do-cron")]
            status, dados = cliente.get("/api/sistema/limpeza")
        self.assertEqual(status, 200)
        self.assertIn("visitas", dados["apagados"])
