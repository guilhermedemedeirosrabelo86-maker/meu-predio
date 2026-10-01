"""Servidor de teste numa porta livre e clientes HTTP com cookie de sessão."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

from backend.servidor import Manipulador, criar_servidor


class Cliente:
    """Um navegador simplificado: guarda o cookie de sessão entre as chamadas."""

    def __init__(self, base):
        self.base = base
        self.abridor = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))

    def chamar(self, metodo, caminho, corpo=None):
        dados = json.dumps(corpo).encode() if corpo is not None else None
        req = urllib.request.Request(self.base + caminho, data=dados, method=metodo)
        if dados is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with self.abridor.open(req) as resposta:
                return resposta.status, json.loads(resposta.read() or b"{}")
        except urllib.error.HTTPError as erro:
            return erro.code, json.loads(erro.read() or b"{}")

    def get(self, caminho):
        return self.chamar("GET", caminho)

    def post(self, caminho, corpo=None):
        return self.chamar("POST", caminho, corpo if corpo is not None else {})

    def patch(self, caminho, corpo):
        return self.chamar("PATCH", caminho, corpo)

    def delete(self, caminho):
        return self.chamar("DELETE", caminho)


class BaseApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pasta = tempfile.TemporaryDirectory()
        cls.servidor = criar_servidor("127.0.0.1", 0, str(Path(cls.pasta.name) / "teste.db"))
        cls.base = f"http://127.0.0.1:{cls.servidor.server_address[1]}"
        Manipulador.log_request = lambda *args, **kwargs: None  # só erros aparecem na saída
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        cls.pasta.cleanup()

    _contador = 0

    def novo_usuario(self, nome="Fulano"):
        BaseApi._contador += 1
        cliente = Cliente(self.base)
        status, _ = cliente.post("/api/auth/cadastro", {
            "nome": nome, "email": f"pessoa{BaseApi._contador}@exemplo.com", "senha": "senha-segura",
        })
        self.assertEqual(status, 201)
        return cliente

    def condominio_com_morador(self):
        """Síndico cria o condomínio; morador entra pelo convite e é aprovado."""
        sindico = self.novo_usuario("Síndica Ana")
        status, criado = sindico.post("/api/condominios", {
            "nome": "Residencial Flores", "unidades": ["101", "102", "201"], "minha_unidade": "101",
        })
        self.assertEqual(status, 201)
        cid = criado["id"]
        codigo = sindico.get(f"/api/condominios/{cid}")[1]["codigo_convite"]

        morador = self.novo_usuario("Bruno")
        _, convite = morador.get(f"/api/convites/{codigo.lower()}")
        unidade_102 = next(u for u in convite["unidades"] if u["identificador"] == "102")
        status, _ = morador.post(f"/api/convites/{codigo}/entrar", {"unidade_id": unidade_102["id"]})
        self.assertEqual(status, 201)
        membro_id = morador.get("/api/eu")[1]["condominios"][0]["membro_id"]
        self.assertEqual(sindico.patch(f"/api/condominios/{cid}/membros/{membro_id}", {"status": "ativo"})[0], 200)
        return sindico, morador, cid, membro_id

    def com_porteiro(self):
        """Condomínio com síndico, morador e um funcionário da portaria aprovados."""
        sindico, morador, cid, _ = self.condominio_com_morador()
        codigo = sindico.get(f"/api/condominios/{cid}")[1]["codigo_convite"]
        porteiro = self.novo_usuario("Seu Zé")
        self.assertEqual(porteiro.post(f"/api/convites/{codigo}/entrar", {"funcionario": True})[0], 201)
        pendente = sindico.get(f"/api/condominios/{cid}/cadastro")[1]["pendentes"][0]
        self.assertEqual(pendente["papel"], "portaria")
        sindico.patch(f"/api/condominios/{cid}/membros/{pendente['id']}", {"status": "ativo"})
        return sindico, morador, porteiro, cid
