"""Testes da prestação de contas."""
from datetime import date
from unittest import mock

from backend import rotas_contas
from tests.base import BaseApi
from tests.test_ocorrencias_visitas import JPEG, baixar, enviar_foto

HOJE = date(2026, 10, 15)


def lancamento(**ajustes):
    return {"tipo": "despesa", "categoria": "energia", "descricao": "Conta de luz",
            "valor_centavos": 45_090, "data": "2026-10-05", **ajustes}


class TesteContas(BaseApi):
    def setUp(self):
        trava = mock.patch.object(rotas_contas, "hoje", return_value=HOJE)
        trava.start()
        self.addCleanup(trava.stop)

    def test_so_sindico_lanca_e_portaria_nao_ve(self):
        sindico, morador, porteiro, cid = self.com_porteiro()
        url = f"/api/condominios/{cid}/contas"
        self.assertEqual(morador.post(url, lancamento())[0], 403)
        status, criado = sindico.post(url, lancamento())
        self.assertEqual(status, 201)
        self.assertEqual(morador.get(url)[0], 200)
        self.assertEqual(porteiro.get(url)[0], 403)
        self.assertEqual(porteiro.get(f"{url}/{criado['id']}")[0], 403)
        self.assertEqual(morador.patch(f"{url}/{criado['id']}", lancamento(valor_centavos=1))[0], 403)
        self.assertEqual(morador.delete(f"{url}/{criado['id']}")[0], 403)

    def test_validacao(self):
        sindico, _, cid, _ = self.condominio_com_morador()
        url = f"/api/condominios/{cid}/contas"
        invalidos = [
            lancamento(tipo="investimento"),
            lancamento(categoria="taxa"),  # categoria de entrada numa saída
            lancamento(valor_centavos=0),
            lancamento(valor_centavos=12.5),
            lancamento(valor_centavos="100"),
            lancamento(descricao=" "),
            lancamento(data="2026-13-01"),
            lancamento(data="1999-12-31"),
        ]
        for corpo in invalidos:
            with self.subTest(corpo=corpo):
                self.assertEqual(sindico.post(url, corpo)[0], 400)
        self.assertEqual(sindico.get(f"{url}?mes=2026-1")[0], 400)

    def test_resumo_categorias_e_historico(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        url = f"/api/condominios/{cid}/contas"
        sindico.post(url, lancamento(tipo="receita", categoria="taxa", descricao="Taxas de setembro",
                                     valor_centavos=300_000, data="2026-09-10"))
        sindico.post(url, lancamento(descricao="Luz de setembro", valor_centavos=50_000, data="2026-09-20"))
        sindico.post(url, lancamento(tipo="receita", categoria="taxa", descricao="Taxas", valor_centavos=320_000))
        sindico.post(url, lancamento())
        sindico.post(url, lancamento(categoria="limpeza", descricao="Faxina", valor_centavos=80_000, data="2026-10-07"))
        sindico.post(url, lancamento(categoria="energia", descricao="Lâmpadas", valor_centavos=10_000))
        sindico.post(url, lancamento(descricao="Mês que vem", data="2026-11-02"))

        dados = morador.get(url)[1]  # sem ?mes, usa o mês de hoje
        self.assertEqual(dados["mes"], "2026-10")
        self.assertEqual(dados["resumo"], {"entradas": 320_000, "saidas": 135_090,
                                           "saldo_caixa": 300_000 - 50_000 + 320_000 - 135_090})
        self.assertEqual(dados["categorias"], [{"categoria": "limpeza", "total": 80_000},
                                               {"categoria": "energia", "total": 55_090}])
        self.assertEqual(len(dados["lancamentos"]), 4)
        self.assertEqual(dados["lancamentos"][0]["data"], "2026-10-07")  # mais recente primeiro
        self.assertEqual(dados["lancamentos"][0]["autor"], "Síndica Ana")
        self.assertEqual([m["mes"] for m in dados["historico"]],
                         ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"])
        self.assertEqual(dados["historico"][4], {"mes": "2026-09", "entradas": 300_000, "saidas": 50_000})

        # A virada de ano não quebra o histórico.
        janeiro = morador.get(f"{url}?mes=2027-01")[1]
        self.assertEqual(janeiro["historico"][0]["mes"], "2026-08")
        self.assertEqual(janeiro["resumo"]["saldo_caixa"], dados["resumo"]["saldo_caixa"] - 45_090)

    def test_editar_e_excluir(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        url = f"/api/condominios/{cid}/contas"
        lid = sindico.post(url, lancamento())[1]["id"]
        self.assertEqual(sindico.patch(f"{url}/{lid}", lancamento(tipo="receita", categoria="multa",
                                                                  descricao="Multa 202"))[0], 200)
        visto = morador.get(f"{url}/{lid}")[1]["lancamento"]
        self.assertEqual((visto["tipo"], visto["categoria"], visto["descricao"]), ("receita", "multa", "Multa 202"))
        self.assertEqual(sindico.delete(f"{url}/{lid}")[0], 200)
        self.assertEqual(morador.get(f"{url}/{lid}")[0], 404)

    def test_comprovante(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        url = f"/api/condominios/{cid}/contas"
        lid = sindico.post(url, lancamento())[1]["id"]
        self.assertEqual(baixar(morador, f"{url}/{lid}/comprovante")[0], 404)
        self.assertEqual(enviar_foto(morador, f"{url}/{lid}/comprovante", JPEG)[0], 403)
        self.assertEqual(enviar_foto(sindico, f"{url}/{lid}/comprovante", b"nao e imagem")[0], 415)
        self.assertEqual(enviar_foto(sindico, f"{url}/{lid}/comprovante", JPEG)[0], 201)
        self.assertTrue(morador.get(f"{url}/{lid}")[1]["lancamento"]["comprovante"])
        self.assertEqual(baixar(morador, f"{url}/{lid}/comprovante"), (200, "image/jpeg", JPEG))

        pasta = self.servidor.pasta_arquivos / "contas"
        outro_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        self.assertEqual(enviar_foto(sindico, f"{url}/{lid}/comprovante", outro_png, "image/png")[0], 201)
        self.assertEqual(len(list(pasta.iterdir())), 1)  # o anterior foi apagado
        self.assertEqual(sindico.delete(f"{url}/{lid}/comprovante")[0], 200)
        self.assertEqual(list(pasta.iterdir()), [])
        self.assertFalse(morador.get(f"{url}/{lid}")[1]["lancamento"]["comprovante"])

    def test_outro_condominio_nao_acessa(self):
        sindico_a, _, cid_a, _ = self.condominio_com_morador()
        sindico_b, _, cid_b, _ = self.condominio_com_morador()
        lid = sindico_a.post(f"/api/condominios/{cid_a}/contas", lancamento())[1]["id"]
        self.assertEqual(sindico_b.get(f"/api/condominios/{cid_a}/contas")[0], 403)
        self.assertEqual(sindico_b.get(f"/api/condominios/{cid_b}/contas/{lid}")[0], 404)
        self.assertEqual(sindico_b.delete(f"/api/condominios/{cid_b}/contas/{lid}")[0], 404)
