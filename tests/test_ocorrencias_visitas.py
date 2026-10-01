"""Testes de ocorrências (com fotos), visitas por QR Code, portaria e painel inicial."""
import json
import urllib.error
import urllib.request
from datetime import date
from unittest import mock

from backend import rotas_painel, rotas_visitas
from tests.base import BaseApi

HOJE = date(2026, 10, 1)
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64  # o servidor só confere a assinatura


def enviar_foto(cliente, caminho, conteudo, tipo="image/jpeg"):
    req = urllib.request.Request(cliente.base + caminho, data=conteudo, method="POST", headers={"Content-Type": tipo})
    try:
        with cliente.abridor.open(req) as resposta:
            return resposta.status, json.loads(resposta.read())
    except urllib.error.HTTPError as erro:
        return erro.code, json.loads(erro.read() or b"{}")


def baixar(cliente, caminho):
    try:
        with cliente.abridor.open(cliente.base + caminho) as resposta:
            return resposta.status, resposta.headers["Content-Type"], resposta.read()
    except urllib.error.HTTPError as erro:
        return erro.code, None, None


class TesteOcorrencias(BaseApi):
    def test_fluxo_completo_com_foto_e_resposta(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        url = f"/api/condominios/{cid}/ocorrencias"
        self.assertEqual(morador.post(url, {"categoria": "inexistente", "titulo": "x"})[0], 400)
        status, criada = morador.post(url, {"categoria": "vazamento", "titulo": "Vazamento na garagem", "local": "Vaga 12"})
        self.assertEqual(status, 201)
        oid = criada["id"]

        self.assertEqual(enviar_foto(morador, f"{url}/{oid}/fotos", b"isto nao e imagem", "image/jpeg")[0], 415)
        status, foto = enviar_foto(morador, f"{url}/{oid}/fotos", JPEG)
        self.assertEqual(status, 201)
        status, tipo, conteudo = baixar(morador, f"{url}/fotos/{foto['id']}")
        self.assertEqual((status, tipo, conteudo), (200, "image/jpeg", JPEG))

        lista = sindico.get(url)[1]["ocorrencias"]
        self.assertEqual(lista[0]["foto_capa"], foto["id"])
        self.assertEqual(lista[0]["unidade"], "102")

        # Morador não muda status; síndico muda e comenta
        self.assertEqual(morador.post(f"{url}/{oid}/mensagens", {"texto": "ok", "status": "resolvida"})[0], 403)
        self.assertEqual(morador.post(f"{url}/{oid}/mensagens", {"texto": ""})[0], 400)
        self.assertEqual(sindico.post(f"{url}/{oid}/mensagens", {"texto": "Encanador chamado.", "status": "andamento"})[0], 201)
        detalhe = morador.get(f"{url}/{oid}")[1]["ocorrencia"]
        self.assertEqual(detalhe["status"], "andamento")
        self.assertEqual(detalhe["fotos"], [foto["id"]])
        self.assertEqual(detalhe["mensagens"][0]["status_novo"], "andamento")
        self.assertTrue(detalhe["mensagens"][0]["do_sindico"])

    def test_privacidade(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        url = f"/api/condominios/{cid}/ocorrencias"
        oid = sindico.post(url, {"categoria": "barulho", "titulo": "Som alto no 201"})[1]["id"]
        foto = enviar_foto(sindico, f"{url}/{oid}/fotos", JPEG)[1]["id"]
        self.assertEqual(morador.get(url)[1]["ocorrencias"], [])
        self.assertEqual(morador.get(f"{url}/{oid}")[0], 404)
        self.assertEqual(baixar(morador, f"{url}/fotos/{foto}")[0], 404)
        estranho = self.novo_usuario()
        self.assertEqual(baixar(estranho, f"{url}/fotos/{foto}")[0], 403)

    def test_limite_de_fotos(self):
        _, morador, cid, _ = self.condominio_com_morador()
        url = f"/api/condominios/{cid}/ocorrencias"
        oid = morador.post(url, {"categoria": "outro", "titulo": "Teste"})[1]["id"]
        for _ in range(5):
            self.assertEqual(enviar_foto(morador, f"{url}/{oid}/fotos", JPEG)[0], 201)
        self.assertEqual(enviar_foto(morador, f"{url}/{oid}/fotos", JPEG)[0], 400)


class TesteVisitas(BaseApi):
    def setUp(self):
        for modulo in (rotas_visitas, rotas_painel):
            trava = mock.patch.object(modulo, "hoje", return_value=HOJE)
            trava.start()
            self.addCleanup(trava.stop)

    def test_fluxo_qr_code(self):
        sindico, morador, porteiro, cid = self.com_porteiro()
        url = f"/api/condominios/{cid}/visitas"
        status, criada = morador.post(url, {"nome": "Carlos (encanador)", "tipo": "prestador",
                                            "data_inicio": "2026-10-01", "data_fim": "2026-10-03"})
        self.assertEqual(status, 201)
        visita = criada["visita"]
        self.assertEqual(visita["situacao"], "valida")
        self.assertNotIn("telefone_morador", visita)
        token = visita["token"]

        # Link público do visitante: sem login, sem dados da unidade
        anonimo = self.novo_usuario()
        anonimo.post("/api/auth/logout")
        status, passe = anonimo.get(f"/api/passes/{token}")
        self.assertEqual(status, 200)
        self.assertEqual(passe["passe"]["condominio"], "Residencial Flores")
        self.assertNotIn("unidade", passe["passe"])
        self.assertEqual(anonimo.get("/api/passes/nao-existe")[0], 404)

        # Só a equipe valida e registra entrada
        self.assertEqual(morador.get(f"/api/passes/{token}/portaria")[0], 403)
        self.assertEqual(anonimo.post(f"/api/passes/{token}/entradas")[0], 401)
        validacao = porteiro.get(f"/api/passes/{token}/portaria")[1]
        self.assertEqual(validacao["visita"]["unidade"], "102")
        self.assertEqual(porteiro.post(f"/api/passes/{token}/entradas")[0], 201)
        self.assertEqual(sindico.post(f"/api/passes/{token}/entradas")[0], 201)

        painel = porteiro.get(f"/api/condominios/{cid}/portaria")[1]
        self.assertEqual([v["nome"] for v in painel["esperados"]], ["Carlos (encanador)"])
        self.assertEqual(len(painel["entradas"]), 2)
        self.assertEqual(porteiro.get(f"/api/condominios/{cid}/portaria/codigo/{visita['codigo'].lower()}")[1]["token"], token)
        self.assertEqual(morador.get(f"/api/condominios/{cid}/portaria")[0], 403)
        self.assertEqual(morador.get(url)[1]["visitas"][0]["entradas"], 2)

        # Cancelada não entra mais
        self.assertEqual(morador.delete(f"{url}/{visita['id']}")[0], 200)
        status, erro = porteiro.post(f"/api/passes/{token}/entradas")
        self.assertEqual(status, 409)
        self.assertIn("cancelada", erro["erro"])

    def test_validade(self):
        _, morador, porteiro, cid = self.com_porteiro()
        url = f"/api/condominios/{cid}/visitas"
        self.assertEqual(morador.post(url, {"nome": "A", "data_inicio": "2026-09-30"})[0], 400)
        self.assertEqual(morador.post(url, {"nome": "A", "data_inicio": "2026-10-05", "data_fim": "2026-10-04"})[0], 400)
        self.assertEqual(morador.post(url, {"nome": "A", "data_inicio": "2026-10-01", "data_fim": "2026-11-15"})[0], 400)
        self.assertEqual(morador.post(url, {"nome": "A", "tipo": "festa", "data_inicio": "2026-10-01"})[0], 400)
        futura = morador.post(url, {"nome": "Ana", "data_inicio": "2026-10-10"})[1]["visita"]
        self.assertEqual(futura["situacao"], "futura")
        self.assertEqual(porteiro.post(f"/api/passes/{futura['token']}/entradas")[0], 409)
        with mock.patch.object(rotas_visitas, "hoje", return_value=date(2026, 10, 11)):
            self.assertEqual(porteiro.get(f"/api/passes/{futura['token']}/portaria")[1]["visita"]["situacao"], "expirada")

    def test_portaria_nao_libera_visita_nem_ve_cadastro(self):
        _, _, porteiro, cid = self.com_porteiro()
        self.assertEqual(porteiro.post(f"/api/condominios/{cid}/visitas", {"nome": "X", "data_inicio": "2026-10-01"})[0], 403)
        self.assertEqual(porteiro.get(f"/api/condominios/{cid}/cadastro")[0], 403)

    def test_cancelar_visita_de_outra_unidade(self):
        sindico, morador, _, cid = self.com_porteiro()
        url = f"/api/condominios/{cid}/visitas"
        da_sindica = sindico.post(url, {"nome": "Visita da 101", "data_inicio": "2026-10-01"})[1]["visita"]
        self.assertEqual(morador.delete(f"{url}/{da_sindica['id']}")[0], 403)
        self.assertEqual(morador.delete(f"{url}/999999")[0], 404)

    def test_painel(self):
        sindico, morador, porteiro, cid = self.com_porteiro()
        sindico.post(f"/api/condominios/{cid}/avisos", {"titulo": "Aviso", "corpo": "..."})
        morador.post(f"/api/condominios/{cid}/visitas", {"nome": "Ana", "data_inicio": "2026-10-01"})
        morador.post(f"/api/condominios/{cid}/ocorrencias", {"categoria": "barulho", "titulo": "Som alto"})

        do_morador = morador.get(f"/api/condominios/{cid}/painel")[1]
        self.assertEqual(do_morador["avisos_nao_lidos"], 1)
        self.assertTrue(do_morador["ultimo_aviso"]["novo"])
        self.assertEqual(do_morador["visitas_hoje"], 1)
        self.assertEqual(do_morador["ocorrencias_abertas"], 1)
        self.assertNotIn("pendencias", do_morador)
        self.assertNotIn("portaria", do_morador)

        do_sindico = sindico.get(f"/api/condominios/{cid}/painel")[1]
        self.assertEqual(do_sindico["ocorrencias_abertas"], 1)
        self.assertEqual(do_sindico["pendencias"], {"pedidos_entrada": 0, "reservas": 0})
        self.assertEqual(do_sindico["portaria"]["esperados"], 1)
        self.assertEqual(porteiro.get(f"/api/condominios/{cid}/painel")[1]["portaria"]["esperados"], 1)
