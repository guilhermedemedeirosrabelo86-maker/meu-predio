"""Contadores das abas do menu (o que pede atenção), consultados pelo app a cada poucos segundos."""
from tests.base import BaseApi


class TesteContadores(BaseApi):
    def contadores(self, cliente, cid):
        status, dados = cliente.get(f"/api/condominios/{cid}/contadores")
        self.assertEqual(status, 200)
        return dados

    def test_aviso_novo_aparece_e_some_ao_ler(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        self.assertEqual(self.contadores(morador, cid)["abas"]["avisos"], 0)
        sindico.post(f"/api/condominios/{cid}/avisos", {"titulo": "Limpeza da caixa", "corpo": "Sábado."})
        dados = self.contadores(morador, cid)
        self.assertEqual(dados["abas"]["avisos"], 1)
        self.assertEqual(dados["ultimo_aviso"]["titulo"], "Limpeza da caixa")
        morador.post(f"/api/condominios/{cid}/avisos/lidos")
        self.assertEqual(self.contadores(morador, cid)["abas"]["avisos"], 0)

    def test_sindico_ve_pedidos_de_entrada(self):
        sindico, _, cid, _ = self.condominio_com_morador()
        codigo = sindico.get(f"/api/condominios/{cid}")[1]["codigo_convite"]
        self.assertEqual(self.contadores(sindico, cid)["abas"]["moradores"], 0)
        novo = self.novo_usuario("Carla")
        unidade = novo.get(f"/api/convites/{codigo}")[1]["unidades"][-1]["id"]
        novo.post(f"/api/convites/{codigo}/entrar", {"unidade_id": unidade})
        self.assertEqual(self.contadores(sindico, cid)["abas"]["moradores"], 1)

    def test_morador_nao_recebe_numeros_do_sindico(self):
        _, morador, cid, _ = self.condominio_com_morador()
        abas = self.contadores(morador, cid)["abas"]
        self.assertNotIn("moradores", abas)
        self.assertNotIn("reservas", abas)

    def test_so_quem_e_do_condominio(self):
        _, _, cid, _ = self.condominio_com_morador()
        self.assertEqual(self.novo_usuario().get(f"/api/condominios/{cid}/contadores")[0], 403)

    def test_encomendas_portaria_ve_todas_morador_so_as_suas(self):
        sindico, morador, porteiro, cid = self.com_porteiro()
        url = f"/api/condominios/{cid}/encomendas"
        unidades = {u["identificador"]: u["id"] for u in porteiro.get(url)[1]["unidades"]}
        porteiro.post(url, {"unidade_id": unidades["102"], "descricao": "Caixa"})
        sindico.post(url, {"unidade_id": unidades["201"], "descricao": "Envelope"})
        sindico.post(url, {"unidade_id": unidades["201"], "descricao": "Revista"})
        self.assertEqual(self.contadores(porteiro, cid)["abas"]["encomendas"], 2)  # as do síndico, de todo o prédio
        self.assertEqual(self.contadores(morador, cid)["abas"]["encomendas"], 1)   # só a da unidade 102

    def test_ninguem_e_avisado_do_que_fez(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        self.assertEqual(sindico.post(f"/api/condominios/{cid}/enquetes", {"pergunta": "Pintar a fachada?", "opcoes": ["Sim", "Não"]})[0], 201)
        self.assertEqual(morador.post(f"/api/condominios/{cid}/ocorrencias", {"categoria": "barulho", "titulo": "Som alto"})[0], 201)
        self.assertEqual(sindico.post(f"/api/condominios/{cid}/ocorrencias", {"categoria": "manutencao", "titulo": "Lâmpada queimada"})[0], 201)
        do_sindico = self.contadores(sindico, cid)["abas"]
        self.assertEqual(do_sindico["enquetes"], 0)     # ele mesmo criou
        self.assertEqual(do_sindico["ocorrencias"], 1)  # só a do morador
        self.assertEqual(self.contadores(morador, cid)["abas"]["enquetes"], 1)
        painel = sindico.get(f"/api/condominios/{cid}/painel")[1]
        self.assertEqual(painel["enquetes_sem_voto"], 0)
        self.assertEqual(painel["ocorrencias_abertas"], 1)
