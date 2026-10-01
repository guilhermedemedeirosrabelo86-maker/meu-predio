"""Testes das áreas comuns e reservas."""
from datetime import date
from unittest import mock

from backend import rotas_reservas
from tests.base import BaseApi

HOJE = date(2026, 10, 1)
AREA = {"nome": "Salão de festas", "regras": "Até 22h.", "exige_aprovacao": False,
        "antecedencia_dias": 30, "limite_por_unidade": 1}


class TesteReservas(BaseApi):
    def setUp(self):
        trava = mock.patch.object(rotas_reservas, "hoje", return_value=HOJE)
        trava.start()
        self.addCleanup(trava.stop)

    def com_area(self, **ajustes):
        sindico, morador, cid, membro_id = self.condominio_com_morador()
        status, criada = sindico.post(f"/api/condominios/{cid}/areas", {**AREA, **ajustes})
        self.assertEqual(status, 201)
        return sindico, morador, cid, criada["id"]

    def test_areas_so_sindico_gerencia(self):
        sindico, morador, cid, aid = self.com_area()
        self.assertEqual(morador.post(f"/api/condominios/{cid}/areas", {**AREA, "nome": "Churrasqueira"})[0], 403)
        self.assertEqual(sindico.post(f"/api/condominios/{cid}/areas", AREA)[0], 409)
        self.assertEqual(sindico.post(f"/api/condominios/{cid}/areas", {**AREA, "nome": "X", "antecedencia_dias": 0})[0], 400)
        areas = morador.get(f"/api/condominios/{cid}/areas")[1]
        self.assertEqual(areas["areas"][0]["nome"], "Salão de festas")
        self.assertEqual(areas["hoje"], "2026-10-01")
        self.assertEqual(sindico.patch(f"/api/condominios/{cid}/areas/{aid}", {**AREA, "regras": "Até 23h."})[0], 200)
        self.assertEqual(sindico.delete(f"/api/condominios/{cid}/areas/{aid}")[0], 200)
        self.assertEqual(morador.get(f"/api/condominios/{cid}/areas")[1]["areas"], [])

    def test_reserva_confirmada_e_data_ocupada(self):
        sindico, morador, cid, aid = self.com_area()
        status, r = morador.post(f"/api/condominios/{cid}/reservas", {"area_id": aid, "data": "2026-10-10", "observacao": "Aniversário"})
        self.assertEqual((status, r["status"]), (201, "confirmada"))
        self.assertEqual(sindico.post(f"/api/condominios/{cid}/reservas", {"area_id": aid, "data": "2026-10-10"})[0], 409)

        do_morador = morador.get(f"/api/condominios/{cid}/reservas?area_id={aid}&mes=2026-10")[1]["reservas"]
        self.assertTrue(do_morador[0]["minha"])
        self.assertEqual(do_morador[0]["unidade"], "102")
        self.assertEqual(do_morador[0]["observacao"], "Aniversário")
        self.assertEqual(morador.get(f"/api/condominios/{cid}/reservas?area_id={aid}&mes=2026-11")[1]["reservas"], [])

    def test_vizinho_nao_ve_detalhes(self):
        sindico, morador, cid, aid = self.com_area()
        sindico.post(f"/api/condominios/{cid}/reservas", {"area_id": aid, "data": "2026-10-05", "observacao": "Reunião"})
        reserva = morador.get(f"/api/condominios/{cid}/reservas?area_id={aid}&mes=2026-10")[1]["reservas"][0]
        self.assertFalse(reserva["minha"])
        self.assertEqual(reserva["unidade"], "101")
        self.assertNotIn("observacao", reserva)
        self.assertNotIn("reservado_por", reserva)

    def test_regras_de_data_e_limite(self):
        sindico, morador, cid, aid = self.com_area()
        url = f"/api/condominios/{cid}/reservas"
        self.assertEqual(morador.post(url, {"area_id": aid, "data": "2026-09-30"})[0], 400)  # passado
        self.assertEqual(morador.post(url, {"area_id": aid, "data": "2026-11-15"})[0], 400)  # além de 30 dias
        self.assertEqual(morador.post(url, {"area_id": aid, "data": "31/10/2026"})[0], 400)
        self.assertEqual(morador.post(url, {"area_id": aid, "data": "2026-10-01"})[0], 201)  # hoje vale
        _, erro = morador.post(url, {"area_id": aid, "data": "2026-10-20"})
        self.assertIn("limite", erro["erro"])
        # O síndico pode reservar além da antecedência e para outra unidade
        unidades = sindico.get(f"/api/condominios/{cid}/unidades")[1]["unidades"]
        u201 = next(u["id"] for u in unidades if u["identificador"] == "201")
        status, _ = sindico.post(url, {"area_id": aid, "data": "2026-12-20", "unidade_id": u201})
        self.assertEqual(status, 201)

    def test_aprovacao(self):
        sindico, morador, cid, aid = self.com_area(exige_aprovacao=True)
        _, r = morador.post(f"/api/condominios/{cid}/reservas", {"area_id": aid, "data": "2026-10-12"})
        self.assertEqual(r["status"], "pendente")
        self.assertEqual(morador.patch(f"/api/condominios/{cid}/reservas/{r['id']}", {"status": "confirmada"})[0], 403)
        pendentes = sindico.get(f"/api/condominios/{cid}/reservas/proximas")[1]["pendentes"]
        self.assertEqual([p["id"] for p in pendentes], [r["id"]])
        self.assertNotIn("pendentes", morador.get(f"/api/condominios/{cid}/reservas/proximas")[1])
        self.assertEqual(sindico.patch(f"/api/condominios/{cid}/reservas/{r['id']}", {"status": "confirmada"})[0], 200)
        minhas = morador.get(f"/api/condominios/{cid}/reservas/proximas")[1]["minhas"]
        self.assertEqual(minhas[0]["status"], "confirmada")
        self.assertEqual(minhas[0]["area"], "Salão de festas")

    def test_cancelamento(self):
        sindico, morador, cid, aid = self.com_area(limite_por_unidade=5)
        url = f"/api/condominios/{cid}/reservas"
        da_sindica = sindico.post(url, {"area_id": aid, "data": "2026-10-03"})[1]["id"]
        do_morador = morador.post(url, {"area_id": aid, "data": "2026-10-04"})[1]["id"]
        self.assertEqual(morador.delete(f"{url}/{da_sindica}")[0], 403)
        self.assertEqual(morador.delete(f"{url}/{do_morador}")[0], 200)
        passada = morador.post(url, {"area_id": aid, "data": "2026-10-02"})[1]["id"]
        with mock.patch.object(rotas_reservas, "hoje", return_value=date(2026, 10, 5)):
            self.assertEqual(morador.delete(f"{url}/{passada}")[0], 400)
            self.assertEqual(sindico.delete(f"{url}/{passada}")[0], 200)

    def test_isolamento_entre_condominios(self):
        sindico_a, _, cid_a, aid_a = self.com_area()
        sindico_b, _, cid_b, _ = self.com_area()
        rid = sindico_a.post(f"/api/condominios/{cid_a}/reservas", {"area_id": aid_a, "data": "2026-10-09"})[1]["id"]
        self.assertEqual(sindico_b.post(f"/api/condominios/{cid_b}/reservas", {"area_id": aid_a, "data": "2026-10-10"})[0], 404)
        self.assertEqual(sindico_b.delete(f"/api/condominios/{cid_b}/reservas/{rid}")[0], 404)
        self.assertEqual(sindico_b.get(f"/api/condominios/{cid_b}/reservas?area_id={aid_a}&mes=2026-10")[0], 404)

    def test_parametros_invalidos(self):
        _, morador, cid, aid = self.com_area()
        for consulta in ("", f"?area_id={aid}", f"?area_id={aid}&mes=2026-13", "?area_id=x&mes=2026-10"):
            self.assertEqual(morador.get(f"/api/condominios/{cid}/reservas{consulta}")[0], 400, consulta)
