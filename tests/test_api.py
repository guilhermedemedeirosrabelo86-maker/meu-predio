"""Testes da API rodando o servidor de verdade numa porta livre: python -m unittest -v"""
import unittest
import urllib.error
import urllib.request

from tests.base import BaseApi, Cliente


class TesteApi(BaseApi):
    # --- Conta ----------------------------------------------------------------

    def test_cadastro_login_logout(self):
        cliente = Cliente(self.base)
        self.assertEqual(cliente.get("/api/eu")[0], 401)
        corpo = {"nome": "Carla", "email": "Carla@Exemplo.com", "senha": "12345678"}
        self.assertEqual(cliente.post("/api/auth/cadastro", corpo)[0], 201)
        self.assertEqual(cliente.post("/api/auth/cadastro", corpo)[0], 409)
        self.assertEqual(cliente.get("/api/eu")[1]["usuario"]["email"], "carla@exemplo.com")

        self.assertEqual(cliente.post("/api/auth/logout")[0], 200)
        self.assertEqual(cliente.get("/api/eu")[0], 401)

        status, erro = cliente.post("/api/auth/login", {"email": "carla@exemplo.com", "senha": "errada!!"})
        self.assertEqual(status, 401)
        self.assertIn("incorretos", erro["erro"])
        self.assertEqual(cliente.post("/api/auth/login", {"email": "CARLA@exemplo.com", "senha": "12345678"})[0], 200)
        self.assertEqual(cliente.get("/api/eu")[0], 200)

    def test_validacao_cadastro(self):
        cliente = Cliente(self.base)
        self.assertEqual(cliente.post("/api/auth/cadastro", {"nome": "X", "email": "x@x.com", "senha": "curta"})[0], 400)
        self.assertEqual(cliente.post("/api/auth/cadastro", {"nome": "X", "email": "sem-arroba", "senha": "12345678"})[0], 400)
        self.assertEqual(cliente.post("/api/auth/cadastro", {"nome": "", "email": "y@y.com", "senha": "12345678"})[0], 400)

    def test_contatos_emergencia(self):
        cliente = self.novo_usuario()
        status, criado = cliente.post("/api/eu/contatos", {"nome": "Mãe", "telefone": "11 99999-0000", "parentesco": "mãe"})
        self.assertEqual(status, 201)
        self.assertEqual(len(cliente.get("/api/eu/contatos")[1]["contatos"]), 1)
        outro = self.novo_usuario()
        self.assertEqual(outro.delete(f"/api/eu/contatos/{criado['id']}")[0], 404)
        self.assertEqual(cliente.delete(f"/api/eu/contatos/{criado['id']}")[0], 200)

    # --- Condomínio e moradores -----------------------------------------------

    def test_pedido_pendente_nao_acessa_condominio(self):
        sindico = self.novo_usuario()
        cid = sindico.post("/api/condominios", {"nome": "Ed. Sol", "unidades": ["1", "2"]})[1]["id"]
        codigo = sindico.get(f"/api/condominios/{cid}")[1]["codigo_convite"]
        morador = self.novo_usuario()
        unidade = morador.get(f"/api/convites/{codigo}")[1]["unidades"][0]
        morador.post(f"/api/convites/{codigo}/entrar", {"unidade_id": unidade["id"]})
        self.assertEqual(morador.post(f"/api/convites/{codigo}/entrar", {"unidade_id": unidade["id"]})[0], 409)
        self.assertEqual(morador.get(f"/api/condominios/{cid}/avisos")[0], 403)
        pendentes = sindico.get(f"/api/condominios/{cid}/cadastro")[1]["pendentes"]
        self.assertEqual([p["unidade"] for p in pendentes], ["1"])

    def test_codigo_invalido_e_unidade_de_outro_condominio(self):
        a = self.novo_usuario()
        cid_a = a.post("/api/condominios", {"nome": "A", "unidades": ["1"]})[1]["id"]
        unidade_a = a.get(f"/api/condominios/{cid_a}/unidades")[1]["unidades"][0]["id"]
        b = self.novo_usuario()
        cid_b = b.post("/api/condominios", {"nome": "B", "unidades": ["1"]})[1]["id"]
        codigo_b = b.get(f"/api/condominios/{cid_b}")[1]["codigo_convite"]
        morador = self.novo_usuario()
        self.assertEqual(morador.get("/api/convites/NAOEXISTE")[0], 404)
        self.assertEqual(morador.post(f"/api/convites/{codigo_b}/entrar", {"unidade_id": unidade_a})[0], 400)

    def test_morador_nao_ve_codigo_nem_cadastro(self):
        _, morador, cid, _ = self.condominio_com_morador()
        self.assertNotIn("codigo_convite", morador.get(f"/api/condominios/{cid}")[1])
        self.assertEqual(morador.get(f"/api/condominios/{cid}/cadastro")[0], 403)
        self.assertEqual(morador.post(f"/api/condominios/{cid}/convite")[0], 403)

    def test_estranho_nao_acessa(self):
        _, _, cid, _ = self.condominio_com_morador()
        estranho = self.novo_usuario()
        for caminho in (f"/api/condominios/{cid}", f"/api/condominios/{cid}/avisos", f"/api/condominios/{cid}/unidades"):
            self.assertEqual(estranho.get(caminho)[0], 403, caminho)

    def test_cadastro_do_sindico_mostra_moradores_contatos_e_veiculos(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        morador.post("/api/eu/contatos", {"nome": "Irmã", "telefone": "11 98888-0000"})
        self.assertEqual(morador.post(f"/api/condominios/{cid}/veiculos", {"placa": "abc-1d23", "modelo": "Onix"})[0], 201)
        unidades = sindico.get(f"/api/condominios/{cid}/cadastro")[1]["unidades"]
        u102 = next(u for u in unidades if u["identificador"] == "102")
        self.assertEqual(u102["moradores"][0]["nome"], "Bruno")
        self.assertEqual(u102["moradores"][0]["contatos"][0]["nome"], "Irmã")
        self.assertEqual(u102["veiculos"][0]["placa"], "ABC1D23")
        self.assertEqual([u["identificador"] for u in unidades], ["101", "102", "201"])

    def test_veiculos(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        self.assertEqual(morador.post(f"/api/condominios/{cid}/veiculos", {"placa": "12345"})[0], 400)
        vid = morador.post(f"/api/condominios/{cid}/veiculos", {"placa": "XYZ9876"})[1]["id"]
        self.assertEqual(morador.post(f"/api/condominios/{cid}/veiculos", {"placa": "XYZ-9876"})[0], 409)
        self.assertEqual(len(morador.get(f"/api/condominios/{cid}/veiculos")[1]["veiculos"]), 1)
        self.assertEqual(sindico.get(f"/api/condominios/{cid}/veiculos")[1]["veiculos"], [])  # unidade 101
        vid_sindico = sindico.post(f"/api/condominios/{cid}/veiculos", {"placa": "AAA1111"})[1]["id"]
        self.assertEqual(morador.delete(f"/api/condominios/{cid}/veiculos/{vid_sindico}")[0], 403)
        self.assertEqual(sindico.delete(f"/api/condominios/{cid}/veiculos/{vid}")[0], 200)

    def test_sempre_ha_um_sindico(self):
        sindico, morador, cid, membro_morador = self.condominio_com_morador()
        eu_sindico = sindico.get("/api/eu")[1]["condominios"][0]["membro_id"]
        self.assertEqual(sindico.delete(f"/api/condominios/{cid}/membros/{eu_sindico}")[0], 409)
        self.assertEqual(sindico.patch(f"/api/condominios/{cid}/membros/{eu_sindico}", {"papel": "morador"})[0], 409)
        # Passa o cargo para o morador e então pode sair.
        self.assertEqual(sindico.patch(f"/api/condominios/{cid}/membros/{membro_morador}", {"papel": "sindico"})[0], 200)
        self.assertEqual(sindico.delete(f"/api/condominios/{cid}/membros/{eu_sindico}")[0], 200)
        self.assertEqual(morador.get(f"/api/condominios/{cid}/cadastro")[0], 200)

    def test_morador_sai_e_nao_remove_outros(self):
        sindico, morador, cid, membro_morador = self.condominio_com_morador()
        eu_sindico = sindico.get("/api/eu")[1]["condominios"][0]["membro_id"]
        self.assertEqual(morador.delete(f"/api/condominios/{cid}/membros/{eu_sindico}")[0], 403)
        self.assertEqual(morador.delete(f"/api/condominios/{cid}/membros/{membro_morador}")[0], 200)
        self.assertEqual(morador.get(f"/api/condominios/{cid}/avisos")[0], 403)

    def test_unidades(self):
        sindico, _, cid, _ = self.condominio_com_morador()
        self.assertEqual(sindico.post(f"/api/condominios/{cid}/unidades", {"identificador": "102"})[0], 409)
        nova = sindico.post(f"/api/condominios/{cid}/unidades", {"identificador": "301"})[1]["id"]
        unidades = sindico.get(f"/api/condominios/{cid}/unidades")[1]["unidades"]
        ocupada = next(u for u in unidades if u["identificador"] == "102")["id"]
        self.assertEqual(sindico.delete(f"/api/condominios/{cid}/unidades/{ocupada}")[0], 409)
        self.assertEqual(sindico.delete(f"/api/condominios/{cid}/unidades/{nova}")[0], 200)

    # --- Avisos ----------------------------------------------------------------

    def test_avisos_fluxo_completo(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        self.assertEqual(morador.post(f"/api/condominios/{cid}/avisos", {"titulo": "x", "corpo": "y"})[0], 403)

        status, a1 = sindico.post(f"/api/condominios/{cid}/avisos", {"titulo": "Limpeza da caixa d'água", "corpo": "Sábado, 8h."})
        self.assertEqual(status, 201)
        _, a2 = sindico.post(f"/api/condominios/{cid}/avisos", {"titulo": "Regras da piscina", "corpo": "...", "fixado": True})

        resumo = morador.get(f"/api/condominios/{cid}/avisos/resumo")[1]
        self.assertEqual(resumo["nao_lidos"], 2)
        self.assertEqual(resumo["ultimo"]["id"], a2["id"])

        avisos = morador.get(f"/api/condominios/{cid}/avisos")[1]["avisos"]
        self.assertEqual([a["id"] for a in avisos], [a2["id"], a1["id"]])  # fixado primeiro
        self.assertNotIn("leituras", avisos[0])
        self.assertFalse(avisos[0]["lido"])

        morador.post(f"/api/condominios/{cid}/avisos/lidos")
        self.assertEqual(morador.get(f"/api/condominios/{cid}/avisos/resumo")[1]["nao_lidos"], 0)

        lista_sindico = sindico.get(f"/api/condominios/{cid}/avisos")[1]
        self.assertEqual(lista_sindico["total_moradores"], 2)
        self.assertEqual(lista_sindico["avisos"][0]["leituras"], 2)

        self.assertEqual(sindico.patch(f"/api/condominios/{cid}/avisos/{a1['id']}", {"titulo": "Limpeza adiada", "corpo": "Domingo."})[0], 200)
        editado = morador.get(f"/api/condominios/{cid}/avisos/{a1['id']}")[1]["aviso"]
        self.assertEqual(editado["titulo"], "Limpeza adiada")
        self.assertIsNotNone(editado["editado_em"])

        self.assertEqual(sindico.delete(f"/api/condominios/{cid}/avisos/{a1['id']}")[0], 200)
        self.assertEqual(morador.get(f"/api/condominios/{cid}/avisos/{a1['id']}")[0], 404)

    def test_aviso_de_outro_condominio(self):
        sindico_a, _, cid_a, _ = self.condominio_com_morador()
        sindico_b, _, cid_b, _ = self.condominio_com_morador()
        aid = sindico_a.post(f"/api/condominios/{cid_a}/avisos", {"titulo": "A", "corpo": "A"})[1]["id"]
        self.assertEqual(sindico_b.delete(f"/api/condominios/{cid_b}/avisos/{aid}")[0], 404)
        self.assertEqual(sindico_b.get(f"/api/condominios/{cid_a}/avisos/{aid}")[0], 403)

    # --- Servidor --------------------------------------------------------------

    def test_arquivos_estaticos_e_rotas_invalidas(self):
        with urllib.request.urlopen(self.base + "/") as resposta:
            self.assertIn(b"<!doctype html>", resposta.read().lower())
        with urllib.request.urlopen(self.base + "/js/app.js") as resposta:
            self.assertTrue(resposta.headers["Content-Type"].startswith("text/javascript"))
        for caminho in ("/../rodar.py", "/%2e%2e/rodar.py", "/nao-existe.txt"):
            with self.assertRaises(urllib.error.HTTPError) as erro:
                urllib.request.urlopen(self.base + caminho)
            self.assertEqual(erro.exception.code, 404)
        cliente = Cliente(self.base)
        self.assertEqual(cliente.get("/api/nada")[0], 404)
        self.assertEqual(cliente.delete("/api/eu")[0], 405)

    def test_rede_para_abrir_no_celular(self):
        from backend import rotas_sistema
        cliente = Cliente(self.base)
        status, rede = cliente.get("/api/rede")
        self.assertEqual(status, 200)
        self.assertFalse(rede["aberto_na_rede"])  # o servidor de teste escuta só em 127.0.0.1
        original = dict(rotas_sistema.INFO)
        rotas_sistema.INFO.update(host="0.0.0.0")
        try:
            rede = cliente.get("/api/rede")[1]
        finally:
            rotas_sistema.INFO.update(original)
        self.assertTrue(rede["aberto_na_rede"])
        for endereco in rede["enderecos"]:
            self.assertRegex(endereco, r"^http://\d+\.\d+\.\d+\.\d+:\d+$")
            self.assertNotIn("127.0.0.1", endereco)

    def test_corpo_precisa_ser_json(self):
        req = urllib.request.Request(self.base + "/api/auth/login", data=b"email=a", method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with self.assertRaises(urllib.error.HTTPError) as erro:
            urllib.request.urlopen(req)
        self.assertEqual(erro.exception.code, 415)


if __name__ == "__main__":
    unittest.main()
