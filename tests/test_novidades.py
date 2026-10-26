"""Testes de encomendas, telefones úteis, enquetes e dos números novos do painel."""
from datetime import date
from unittest import mock

from backend import rotas_enquetes, rotas_painel
from tests.base import BaseApi

HOJE = date(2026, 10, 21)


class TesteEncomendas(BaseApi):
    def test_portaria_registra_e_morador_ve_so_a_sua(self):
        sindico, morador, porteiro, cid = self.com_porteiro()
        url = f"/api/condominios/{cid}/encomendas"
        unidades = {u["identificador"]: u["id"] for u in porteiro.get(url)[1]["unidades"]}
        self.assertEqual(morador.post(url, {"unidade_id": unidades["102"], "descricao": "Caixa"})[0], 403)
        self.assertEqual(porteiro.post(url, {"unidade_id": unidades["102"], "descricao": ""})[0], 400)
        self.assertEqual(porteiro.post(url, {"unidade_id": 9999, "descricao": "Caixa"})[0], 400)
        status, criada = porteiro.post(url, {"unidade_id": unidades["102"], "descricao": "Caixa Mercado Livre"})
        self.assertEqual(status, 201)
        sindico.post(url, {"unidade_id": unidades["201"], "descricao": "Envelope"})

        _, do_morador = morador.get(url)
        self.assertEqual([e["descricao"] for e in do_morador["aguardando"]], ["Caixa Mercado Livre"])
        self.assertEqual(do_morador["unidades"], [])
        self.assertEqual(len(porteiro.get(url)[1]["aguardando"]), 2)
        self.assertEqual(morador.get(f"/api/condominios/{cid}/painel")[1]["encomendas"], 1)
        # O síndico registrou uma das duas: só a que a portaria registrou conta para ele.
        self.assertEqual(sindico.get(f"/api/condominios/{cid}/painel")[1]["portaria"]["encomendas"], 1)

        retirada = f"{url}/{criada['id']}/retirada"
        self.assertEqual(morador.post(retirada, {})[0], 403)
        self.assertEqual(porteiro.post(retirada, {"retirada_por": "Bruno"})[0], 200)
        self.assertEqual(porteiro.post(retirada, {})[0], 409)
        _, depois = morador.get(url)
        self.assertEqual(depois["aguardando"], [])
        self.assertEqual(depois["retiradas"][0]["retirada_por"], "Bruno")
        self.assertEqual(depois["retiradas"][0]["entregue_por"], "Seu Zé")
        self.assertEqual(morador.get(f"/api/condominios/{cid}/painel")[1]["encomendas"], 0)

    def test_outro_condominio_nao_mexe(self):
        _, _, porteiro, cid = self.com_porteiro()
        url = f"/api/condominios/{cid}/encomendas"
        uid = porteiro.get(url)[1]["unidades"][0]["id"]
        eid = porteiro.post(url, {"unidade_id": uid, "descricao": "Caixa"})[1]["id"]
        intruso = self.novo_usuario("Intruso")
        cid_b = intruso.post("/api/condominios", {"nome": "B", "unidades": ["1"]})[1]["id"]
        self.assertEqual(intruso.get(url)[0], 403)
        self.assertEqual(intruso.delete(f"/api/condominios/{cid_b}/encomendas/{eid}")[0], 404)
        self.assertEqual(porteiro.delete(f"{url}/{eid}")[0], 200)


class TesteTelefones(BaseApi):
    def test_sindico_mantem_e_todos_veem(self):
        sindico, morador, porteiro, cid = self.com_porteiro()
        url = f"/api/condominios/{cid}/telefones"
        contato = {"nome": "Seu Antônio", "descricao": "Encanador", "telefone": "(11) 98888-1111"}
        self.assertEqual(morador.post(url, contato)[0], 403)
        self.assertEqual(sindico.post(url, {**contato, "telefone": "123"})[0], 400)
        tid = sindico.post(url, contato)[1]["id"]
        sindico.post(url, {"nome": "Administradora", "telefone": "(11) 3333-4444"})
        self.assertEqual([t["nome"] for t in porteiro.get(url)[1]["telefones"]], ["Administradora", "Seu Antônio"])
        self.assertEqual(sindico.patch(f"{url}/{tid}", {**contato, "descricao": "Encanador e eletricista"})[0], 200)
        self.assertEqual(morador.get(url)[1]["telefones"][1]["descricao"], "Encanador e eletricista")
        self.assertEqual(morador.delete(f"{url}/{tid}")[0], 403)
        self.assertEqual(sindico.delete(f"{url}/{tid}")[0], 200)
        self.assertEqual(len(morador.get(url)[1]["telefones"]), 1)


class TesteEnquetes(BaseApi):
    def setUp(self):
        for modulo in (rotas_enquetes, rotas_painel):
            trava = mock.patch.object(modulo, "hoje", return_value=HOJE)
            trava.start()
            self.addCleanup(trava.stop)

    def test_um_voto_por_unidade(self):
        sindico, morador, porteiro, cid = self.com_porteiro()
        url = f"/api/condominios/{cid}/enquetes"
        enquete = {"pergunta": "Cor da fachada?", "opcoes": ["Cinza", "Bege", " "], "encerra_em": "2026-10-30"}
        self.assertEqual(morador.post(url, enquete)[0], 403)
        self.assertEqual(sindico.post(url, {**enquete, "opcoes": ["Só uma"]})[0], 400)
        self.assertEqual(sindico.post(url, {**enquete, "opcoes": ["A", "a"]})[0], 400)
        self.assertEqual(sindico.post(url, {**enquete, "encerra_em": "2026-10-01"})[0], 400)
        eid = sindico.post(url, enquete)[1]["id"]
        self.assertEqual(porteiro.get(url)[0], 403)

        _, lista = morador.get(url)
        criada = lista["enquetes"][0]
        self.assertEqual([o["texto"] for o in criada["opcoes"]], ["Cinza", "Bege"])
        self.assertTrue(criada["aberta"])
        self.assertEqual(lista["total_unidades"], 3)
        self.assertEqual(morador.get(f"/api/condominios/{cid}/painel")[1]["enquetes_sem_voto"], 1)

        cinza, bege = (o["id"] for o in criada["opcoes"])
        self.assertEqual(morador.post(f"{url}/{eid}/voto", {"opcao_id": 99999})[0], 400)
        self.assertEqual(morador.post(f"{url}/{eid}/voto", {"opcao_id": cinza})[0], 200)
        self.assertEqual(morador.post(f"{url}/{eid}/voto", {"opcao_id": bege})[0], 200)  # muda o voto
        sindico.post(f"{url}/{eid}/voto", {"opcao_id": bege})
        _, depois = morador.get(url)
        self.assertEqual(depois["enquetes"][0]["meu_voto"], bege)
        self.assertEqual(depois["enquetes"][0]["total_votos"], 2)
        self.assertEqual([o["votos"] for o in depois["enquetes"][0]["opcoes"]], [0, 2])
        self.assertEqual(morador.get(f"/api/condominios/{cid}/painel")[1]["enquetes_sem_voto"], 0)

        self.assertEqual(morador.post(f"{url}/{eid}/encerrar")[0], 403)
        self.assertEqual(sindico.post(f"{url}/{eid}/encerrar")[0], 200)
        self.assertEqual(morador.post(f"{url}/{eid}/voto", {"opcao_id": cinza})[0], 409)
        self.assertFalse(morador.get(url)[1]["enquetes"][0]["aberta"])
        self.assertEqual(sindico.delete(f"{url}/{eid}")[0], 200)
        self.assertEqual(morador.get(url)[1]["enquetes"], [])

    def test_prazo_vencido_encerra(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        url = f"/api/condominios/{cid}/enquetes"
        corpo = {"pergunta": "Festa junina?", "opcoes": ["Sim", "Não"], "encerra_em": "2026-10-21"}
        eid = sindico.post(url, corpo)[1]["id"]
        opcao = morador.get(url)[1]["enquetes"][0]["opcoes"][0]["id"]
        with mock.patch.object(rotas_enquetes, "hoje", return_value=date(2026, 10, 22)):
            self.assertEqual(morador.post(f"{url}/{eid}/voto", {"opcao_id": opcao})[0], 409)
            self.assertFalse(morador.get(url)[1]["enquetes"][0]["aberta"])


class TestePainelCaixa(BaseApi):
    def test_caixa_no_inicio(self):
        sindico, morador, porteiro, cid = self.com_porteiro()
        url = f"/api/condominios/{cid}/contas"
        with mock.patch.object(rotas_painel, "hoje", return_value=HOJE):
            sindico.post(url, {"tipo": "receita", "categoria": "multa", "descricao": "Multa",
                               "valor_centavos": 10_000, "data": "2026-09-10"})
            sindico.post(url, {"tipo": "despesa", "categoria": "energia", "descricao": "Luz",
                               "valor_centavos": 3_000, "data": "2026-10-05"})
            caixa = morador.get(f"/api/condominios/{cid}/painel")[1]["caixa"]
            self.assertEqual(caixa, {"saldo": 7_000, "entradas": 0, "saidas": 3_000})
            self.assertNotIn("caixa", porteiro.get(f"/api/condominios/{cid}/painel")[1])
