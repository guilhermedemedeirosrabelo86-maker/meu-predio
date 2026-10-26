"""Foto do prédio: o síndico envia (dia e, opcional, noite) e todos do condomínio veem no topo do Início."""
import sqlite3

from tests.base import BaseApi
from tests.test_ocorrencias_visitas import JPEG, baixar, enviar_foto

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


class TesteFotoPredio(BaseApi):
    def guardadas(self):
        conn = sqlite3.connect(self.arquivo_db)
        try:
            return conn.execute("SELECT COUNT(*) FROM arquivos WHERE nome LIKE 'predios/%'").fetchone()[0]
        finally:
            conn.close()

    def test_sindico_envia_e_morador_ve(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        url = f"/api/condominios/{cid}/foto"
        self.assertEqual(enviar_foto(morador, f"{url}/dia", JPEG)[0], 403)
        status, dados = enviar_foto(sindico, f"{url}/dia", JPEG)
        self.assertEqual(status, 201)
        nome = dados["foto"]

        meu = morador.get("/api/eu")[1]["condominios"][0]
        self.assertEqual(meu["foto"], nome)
        self.assertIsNone(meu["foto_noite"])
        self.assertEqual(baixar(morador, f"/api/condominios/{cid}/fotos/{nome}"), (200, "image/jpeg", JPEG))
        self.assertEqual(baixar(self.novo_usuario(), f"/api/condominios/{cid}/fotos/{nome}")[0], 403)

    def test_trocar_apaga_a_anterior_e_muda_o_nome(self):
        sindico, _, cid, _ = self.condominio_com_morador()
        url = f"/api/condominios/{cid}/foto"
        antes = self.guardadas()  # o banco é o mesmo para todos os testes da classe
        primeira = enviar_foto(sindico, f"{url}/dia", JPEG)[1]["foto"]
        segunda = enviar_foto(sindico, f"{url}/dia", PNG, "image/png")[1]["foto"]
        self.assertNotEqual(primeira, segunda)
        self.assertEqual(self.guardadas(), antes + 1)
        self.assertEqual(baixar(sindico, f"/api/condominios/{cid}/fotos/{primeira}")[0], 404)  # a antiga não vale mais

    def test_noite_e_remover(self):
        sindico, _, cid, _ = self.condominio_com_morador()
        url = f"/api/condominios/{cid}/foto"
        antes = self.guardadas()
        enviar_foto(sindico, f"{url}/dia", JPEG)
        noite = enviar_foto(sindico, f"{url}/noite", JPEG)[1]["foto"]
        self.assertEqual(sindico.get(f"/api/condominios/{cid}")[1]["foto_noite"], noite)
        self.assertEqual(self.guardadas(), antes + 2)
        self.assertEqual(sindico.delete(f"{url}/noite")[0], 200)
        self.assertIsNone(sindico.get(f"/api/condominios/{cid}")[1]["foto_noite"])
        self.assertEqual(self.guardadas(), antes + 1)
        textos = [i["texto"] for i in sindico.get(f"/api/condominios/{cid}/historico")[1]["itens"]]
        self.assertIn("Removeu a foto do prédio à noite", textos)

    def test_validacoes(self):
        sindico, _, cid, _ = self.condominio_com_morador()
        url = f"/api/condominios/{cid}/foto"
        self.assertEqual(enviar_foto(sindico, f"{url}/tarde", JPEG)[0], 404)
        self.assertEqual(enviar_foto(sindico, f"{url}/dia", b"nao e imagem", "image/jpeg")[0], 415)
