"""Testes do controle de pagamento da taxa condominial."""
import sqlite3
from datetime import date
from unittest import mock

from backend import rotas_contas, rotas_painel, rotas_taxas
from tests.base import BaseApi

HOJE = date(2026, 10, 15)  # depois do vencimento (dia 10)


class TesteTaxas(BaseApi):
    def setUp(self):
        self.hoje = HOJE
        for modulo in (rotas_taxas, rotas_painel, rotas_contas):
            trava = mock.patch.object(modulo, "hoje", side_effect=lambda: self.hoje)
            trava.start()
            self.addCleanup(trava.stop)

    def preparar(self, configurar=True):
        """Condomínio no app desde agosto, com taxa de R$ 350 vencendo no dia 10."""
        sindico, morador, cid, _ = self.condominio_com_morador()
        conn = sqlite3.connect(self.servidor.caminho_db)
        with conn:
            conn.execute("UPDATE condominios SET criado_em = '2026-08-03 12:00:00' WHERE id = ?", (cid,))
        conn.close()
        if configurar:
            self.assertEqual(sindico.patch(f"/api/condominios/{cid}/taxas/config",
                                           {"valor_centavos": 35_000, "vencimento": 10})[0], 200)
        unidades = {u["unidade"]: u["id"] for u in sindico.get(f"/api/condominios/{cid}/taxas")[1]["unidades"]}
        return sindico, morador, cid, unidades

    def pagar(self, cliente, cid, unidade_id, mes, **ajustes):
        return cliente.post(f"/api/condominios/{cid}/taxas/pagamentos", {
            "unidade_id": unidade_id, "mes": mes, "valor_centavos": 35_000, "pago_em": "2026-10-12", **ajustes,
        })

    def test_permissoes_e_configuracao(self):
        sindico, morador, cid, unidades = self.preparar(configurar=False)
        url = f"/api/condominios/{cid}/taxas"
        self.assertEqual(morador.get(url)[0], 403)
        self.assertEqual(morador.patch(f"{url}/config", {"valor_centavos": 1, "vencimento": 5})[0], 403)
        self.assertEqual(self.pagar(morador, cid, unidades["102"], "2026-10")[0], 403)
        for corpo in ({"valor_centavos": 0, "vencimento": 10}, {"valor_centavos": 35_000, "vencimento": 29},
                      {"valor_centavos": 35_000, "vencimento": 0}, {"valor_centavos": "350", "vencimento": 10}):
            with self.subTest(corpo=corpo):
                self.assertEqual(sindico.patch(f"{url}/config", corpo)[0], 400)
        self.assertEqual(sindico.patch(f"{url}/config", {"valor_centavos": 40_000, "vencimento": 5})[0], 200)
        self.assertEqual(sindico.get(url)[1]["config"]["valor_centavos"], 40_000)
        self.assertEqual(morador.get(f"{url}/minha")[1]["config"]["vencimento"], 5)

    def test_portaria_nao_ve(self):
        _, _, porteiro, cid = self.com_porteiro()
        self.assertEqual(porteiro.get(f"/api/condominios/{cid}/taxas")[0], 403)
        self.assertEqual(porteiro.get(f"/api/condominios/{cid}/taxas/minha")[0], 403)

    def test_pagar_lanca_na_prestacao_de_contas(self):
        sindico, morador, cid, unidades = self.preparar()
        url = f"/api/condominios/{cid}/taxas"
        mes = sindico.get(url)[1]
        self.assertEqual(mes["mes"], "2026-10")
        self.assertEqual([u["situacao"] for u in mes["unidades"]], ["atrasada"] * 3)
        self.assertEqual(mes["unidades"][1]["moradores"], "Bruno")

        status, pago = self.pagar(sindico, cid, unidades["102"], "2026-10")
        self.assertEqual(status, 201)
        self.assertEqual(self.pagar(sindico, cid, unidades["102"], "2026-10")[0], 409)

        mes = sindico.get(url)[1]
        self.assertEqual(mes["totais"], {"unidades": 3, "pagas": 1, "atrasadas": 2, "recebido": 35_000})
        self.assertEqual(mes["unidades"][1]["pagamento"], {"id": pago["id"], "valor_centavos": 35_000, "pago_em": "2026-10-12"})

        contas = morador.get(f"/api/condominios/{cid}/contas")[1]
        self.assertEqual(contas["resumo"]["entradas"], 35_000)
        self.assertEqual(contas["lancamentos"][0]["descricao"], "Taxa out/2026 · unidade 102")
        self.assertEqual(contas["lancamentos"][0]["categoria"], "taxa")

    def test_situacao_do_morador_e_painel(self):
        sindico, morador, cid, unidades = self.preparar()
        self.pagar(sindico, cid, unidades["102"], "2026-10")
        minha = morador.get(f"/api/condominios/{cid}/taxas/minha")[1]
        self.assertEqual(minha["unidade"], "102")
        # Só desde que o condomínio entrou no app (agosto).
        self.assertEqual([(m["mes"], m["situacao"]) for m in minha["meses"]],
                         [("2026-10", "paga"), ("2026-09", "atrasada"), ("2026-08", "atrasada")])

        painel = morador.get(f"/api/condominios/{cid}/painel")[1]
        self.assertEqual(painel["taxa"], {"mes": "2026-10", "situacao": "paga", "meses_atrasados": 2, "vencimento": 10})
        self.assertEqual(sindico.get(f"/api/condominios/{cid}/painel")[1]["pendencias"]["taxas_atrasadas"], 3)

        self.pagar(sindico, cid, unidades["102"], "2026-09")
        self.pagar(sindico, cid, unidades["102"], "2026-08")
        self.assertEqual(sindico.get(f"/api/condominios/{cid}/painel")[1]["pendencias"]["taxas_atrasadas"], 2)
        self.assertEqual(morador.get(f"/api/condominios/{cid}/painel")[1]["taxa"]["meses_atrasados"], 0)

    def test_antes_do_vencimento_fica_pendente(self):
        sindico, morador, cid, _ = self.preparar()
        self.hoje = date(2026, 10, 10)
        mes = sindico.get(f"/api/condominios/{cid}/taxas")[1]
        self.assertEqual({u["situacao"] for u in mes["unidades"]}, {"pendente"})
        self.assertEqual(morador.get(f"/api/condominios/{cid}/painel")[1]["taxa"]["situacao"], "pendente")

    def test_sem_valor_definido_nao_cobra(self):
        sindico, morador, cid, _ = self.preparar(configurar=False)
        self.assertEqual(sindico.get(f"/api/condominios/{cid}/painel")[1]["pendencias"]["taxas_atrasadas"], 0)
        self.assertIsNone(morador.get(f"/api/condominios/{cid}/painel")[1]["taxa"])

    def test_desfazer_dos_dois_lados(self):
        sindico, morador, cid, unidades = self.preparar()
        pago = self.pagar(sindico, cid, unidades["102"], "2026-10")[1]
        self.assertEqual(sindico.delete(f"/api/condominios/{cid}/taxas/pagamentos/{pago['id']}")[0], 200)
        self.assertEqual(morador.get(f"/api/condominios/{cid}/contas")[1]["lancamentos"], [])
        self.assertEqual(sindico.delete(f"/api/condominios/{cid}/taxas/pagamentos/{pago['id']}")[0], 404)

        # Excluir a entrada na prestação de contas desfaz o pagamento.
        pago = self.pagar(sindico, cid, unidades["102"], "2026-10")[1]
        self.assertEqual(sindico.delete(f"/api/condominios/{cid}/contas/{pago['lancamento_id']}")[0], 200)
        minha = morador.get(f"/api/condominios/{cid}/taxas/minha")[1]
        self.assertEqual(minha["meses"][0]["situacao"], "atrasada")

    def test_validacao_do_pagamento(self):
        sindico, _, cid, unidades = self.preparar()
        outro_sindico, _, outro_cid, _ = self.condominio_com_morador()
        self.assertEqual(self.pagar(sindico, cid, unidades["102"], "2026-12")[0], 400)  # longe demais
        self.assertEqual(self.pagar(sindico, cid, unidades["102"], "2026-11")[0], 201)  # adiantado pode
        self.assertEqual(self.pagar(sindico, cid, unidades["101"], "2026-10", pago_em="2026-10-16")[0], 400)
        self.assertEqual(self.pagar(sindico, cid, unidades["101"], "2026-10", valor_centavos=0)[0], 400)
        self.assertEqual(self.pagar(sindico, cid, unidades["101"], "10/2026")[0], 400)
        self.assertEqual(self.pagar(outro_sindico, outro_cid, unidades["101"], "2026-10")[0], 400)
        pago = self.pagar(sindico, cid, unidades["101"], "2026-10")[1]
        self.assertEqual(outro_sindico.delete(f"/api/condominios/{outro_cid}/taxas/pagamentos/{pago['id']}")[0], 404)
