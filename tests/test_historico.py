"""Histórico de ações do síndico."""
from backend import historico
from tests.base import BaseApi


class TesteHistorico(BaseApi):
    def textos(self, cliente, cid):
        status, dados = cliente.get(f"/api/condominios/{cid}/historico")
        self.assertEqual(status, 200)
        return [i["texto"] for i in dados["itens"]]

    def test_dinheiro_e_moradores_ficam_registrados(self):
        sindico, morador, cid, membro_id = self.condominio_com_morador()
        url = f"/api/condominios/{cid}/contas"
        lid = sindico.post(url, {"tipo": "despesa", "categoria": "energia", "descricao": "Conta de luz",
                                 "valor_centavos": 31240, "data": "2026-10-05"})[1]["id"]
        sindico.patch(f"{url}/{lid}", {"tipo": "despesa", "categoria": "energia", "descricao": "Conta de luz",
                                       "valor_centavos": 21240, "data": "2026-10-05"})
        sindico.delete(f"{url}/{lid}")
        sindico.patch(f"/api/condominios/{cid}/membros/{membro_id}", {"papel": "sindico"})

        textos = self.textos(sindico, cid)
        self.assertEqual(textos[0], "Mudou Bruno (unidade 102) de morador para síndico")
        self.assertEqual(textos[1], 'Excluiu o lançamento "Conta de luz" (despesa de R$ 212,40 em 05/10/2026)')
        self.assertIn("era \"Conta de luz\" (despesa de R$ 312,40", textos[2])
        self.assertEqual(textos[3], 'Lançou a despesa "Conta de luz" de R$ 312,40 em 05/10/2026')
        self.assertEqual(textos[4], "Aprovou a entrada de Bruno (unidade 102) como morador")
        item = sindico.get(f"/api/condominios/{cid}/historico")[1]["itens"][0]
        self.assertEqual(item["autor"], "Síndica Ana")

    def test_so_sindico_ve(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        self.assertEqual(morador.get(f"/api/condominios/{cid}/historico")[0], 403)

    def test_paginas(self):
        sindico, _, cid, _ = self.condominio_com_morador()
        for valor in range(historico.POR_PAGINA + 2):
            sindico.patch(f"/api/condominios/{cid}/taxas/config", {"valor_centavos": 100 + valor, "vencimento": 10})
        primeira = sindico.get(f"/api/condominios/{cid}/historico")[1]
        self.assertEqual(len(primeira["itens"]), historico.POR_PAGINA)
        self.assertTrue(primeira["tem_mais"])
        segunda = sindico.get(f"/api/condominios/{cid}/historico?antes={primeira['itens'][-1]['id']}")[1]
        self.assertEqual(len(segunda["itens"]), 3)  # 2 taxas + a aprovação do morador
        self.assertFalse(segunda["tem_mais"])

    def test_formatos(self):
        self.assertEqual(historico.reais(123456789), "R$ 1.234.567,89")
        self.assertEqual(historico.reais(5), "R$ 0,05")
