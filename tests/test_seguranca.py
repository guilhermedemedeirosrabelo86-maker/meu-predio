"""Limite de tentativas, senhas refeitas com a força atual e "esqueci minha senha"."""
import hashlib
import os
import re
import sqlite3
from unittest import mock

from backend import auth, limites
from tests.base import BaseApi, Cliente


class TesteLimites(BaseApi):
    def senha_guardada(self, email):
        conn = sqlite3.connect(self.arquivo_db)
        try:
            return conn.execute("SELECT senha_hash FROM usuarios WHERE email = ?", (email,)).fetchone()[0]
        finally:
            conn.close()

    def cadastrar(self):
        BaseApi._contador += 1
        email = f"limite{BaseApi._contador}@exemplo.com"
        Cliente(self.base).post("/api/auth/cadastro", {"nome": "Ana", "email": email, "senha": "senha-segura", "aceito_termos": True})
        return email

    def test_login_bloqueia_depois_de_errar_demais(self):
        email = self.cadastrar()
        visitante = Cliente(self.base)
        for _ in range(limites.LOGIN_POR_EMAIL):
            self.assertEqual(visitante.post("/api/auth/login", {"email": email, "senha": "errada"})[0], 401)
        status, dados = visitante.post("/api/auth/login", {"email": email, "senha": "senha-segura"})
        self.assertEqual(status, 429)  # nem a senha certa entra até a janela passar
        self.assertIn("Muitas tentativas", dados["erro"])

    def test_acertar_zera_a_contagem(self):
        email = self.cadastrar()
        visitante = Cliente(self.base)
        for _ in range(limites.LOGIN_POR_EMAIL - 1):
            visitante.post("/api/auth/login", {"email": email, "senha": "errada"})
        self.assertEqual(visitante.post("/api/auth/login", {"email": email, "senha": "senha-segura"})[0], 200)
        for _ in range(limites.LOGIN_POR_EMAIL - 1):
            self.assertEqual(visitante.post("/api/auth/login", {"email": email, "senha": "errada"})[0], 401)

    def test_convite_bloqueia_quem_chuta_codigos(self):
        sindico, morador, cid, _ = self.condominio_com_morador()
        codigo = sindico.get(f"/api/condominios/{cid}")[1]["codigo_convite"]
        chutador = self.novo_usuario()
        conn = sqlite3.connect(self.arquivo_db)
        with conn:  # quase no limite (o endereço é o mesmo para todos os testes desta classe)
            conn.execute("DELETE FROM tentativas")
            conn.executemany("INSERT INTO tentativas (chave) VALUES (?)",
                             [("convite-ip:127.0.0.1",)] * (limites.CONVITE_POR_IP - 1))
        conn.close()
        self.assertEqual(chutador.get("/api/convites/ZZZZZZ")[0], 404)
        self.assertEqual(chutador.get(f"/api/convites/{codigo}")[0], 429)

    def test_senha_antiga_e_refeita_no_login(self):
        email = self.cadastrar()
        sal = self.senha_guardada(email).split("$")[2]
        conn = sqlite3.connect(self.arquivo_db)
        with conn:  # simula uma senha guardada por uma versão antiga, com só 10 repetições
            chave = hashlib.pbkdf2_hmac("sha256", b"senha-segura", bytes.fromhex(sal), 10).hex()
            conn.execute("UPDATE usuarios SET senha_hash = ? WHERE email = ?", (f"pbkdf2_sha256$10${sal}${chave}", email))
        conn.close()
        self.assertEqual(Cliente(self.base).post("/api/auth/login", {"email": email, "senha": "senha-segura"})[0], 200)
        self.assertEqual(self.senha_guardada(email).split("$")[1], str(auth.ITERACOES))


class TesteNovaSenha(BaseApi):
    def setUp(self):
        conn = sqlite3.connect(self.arquivo_db)
        with conn:  # todos os testes vêm do mesmo endereço; cada um começa sem tentativas
            conn.execute("DELETE FROM tentativas")
        conn.close()

    def pedir_link(self, email):
        """Pede o link e devolve o token que iria no e-mail."""
        with mock.patch("backend.correio.enviar") as enviar:
            status, dados = Cliente(self.base).post("/api/auth/esqueci", {"email": email})
        self.assertEqual(status, 200)
        if not enviar.called:
            return None
        texto = enviar.call_args.args[2]
        return re.search(r"#/nova-senha/(\S+)", texto).group(1)

    def conta(self):
        BaseApi._contador += 1
        email = f"esqueci{BaseApi._contador}@exemplo.com"
        cliente = Cliente(self.base)
        cliente.post("/api/auth/cadastro", {"nome": "Ana Souza", "email": email, "senha": "senha-antiga", "aceito_termos": True})
        return email, cliente

    def test_troca_a_senha_e_derruba_as_sessoes(self):
        email, aparelho_antigo = self.conta()
        token = self.pedir_link(email)
        novo = Cliente(self.base)
        self.assertEqual(novo.post("/api/auth/nova-senha", {"token": token, "senha": "senha-nova-123"})[0], 200)
        self.assertEqual(novo.get("/api/eu")[0], 200)  # já entra logado
        self.assertEqual(aparelho_antigo.get("/api/eu")[0], 401)
        self.assertEqual(Cliente(self.base).post("/api/auth/login", {"email": email, "senha": "senha-antiga"})[0], 401)
        self.assertEqual(Cliente(self.base).post("/api/auth/login", {"email": email, "senha": "senha-nova-123"})[0], 200)
        # o link vale uma vez só
        status, dados = Cliente(self.base).post("/api/auth/nova-senha", {"token": token, "senha": "outra-senha-1"})
        self.assertEqual(status, 400)

    def test_email_desconhecido_tem_a_mesma_resposta(self):
        self.assertIsNone(self.pedir_link("ninguem@exemplo.com"))

    def test_link_vencido_nao_vale(self):
        email, _ = self.conta()
        token = self.pedir_link(email)
        conn = sqlite3.connect(self.arquivo_db)
        with conn:
            conn.execute("UPDATE recuperacoes SET expira_em = datetime('now', '-1 minute')")
        conn.close()
        self.assertEqual(Cliente(self.base).post("/api/auth/nova-senha", {"token": token, "senha": "senha-nova-123"})[0], 400)

    def test_link_novo_invalida_o_anterior(self):
        email, _ = self.conta()
        primeiro = self.pedir_link(email)
        segundo = self.pedir_link(email)
        self.assertEqual(Cliente(self.base).post("/api/auth/nova-senha", {"token": primeiro, "senha": "senha-nova-123"})[0], 400)
        self.assertEqual(Cliente(self.base).post("/api/auth/nova-senha", {"token": segundo, "senha": "senha-nova-123"})[0], 200)

    def test_limite_de_pedidos_por_email(self):
        email, _ = self.conta()
        for _ in range(limites.ESQUECI_POR_EMAIL):
            self.pedir_link(email)
        self.assertEqual(Cliente(self.base).post("/api/auth/esqueci", {"email": email})[0], 429)


class TesteRevisao(BaseApi):
    """Correções da revisão de segurança de 2026-10-26."""

    def setUp(self):
        conn = sqlite3.connect(self.arquivo_db)
        with conn:
            conn.execute("DELETE FROM tentativas")
        conn.close()

    def test_trocar_senha(self):
        BaseApi._contador += 1
        email = f"troca{BaseApi._contador}@exemplo.com"
        aparelho = Cliente(self.base)
        aparelho.post("/api/auth/cadastro", {"nome": "Ana", "email": email, "senha": "senha-antiga", "aceito_termos": True})
        outro = Cliente(self.base)
        outro.post("/api/auth/login", {"email": email, "senha": "senha-antiga"})

        self.assertEqual(aparelho.post("/api/eu/senha", {"senha_atual": "errada", "senha_nova": "senha-nova-1"})[0], 400)
        self.assertEqual(aparelho.post("/api/eu/senha", {"senha_atual": "senha-antiga", "senha_nova": "curta"})[0], 400)
        self.assertEqual(aparelho.post("/api/eu/senha", {"senha_atual": "senha-antiga", "senha_nova": "senha-nova-1"})[0], 200)
        self.assertEqual(aparelho.get("/api/eu")[0], 200)  # este aparelho continua conectado
        self.assertEqual(outro.get("/api/eu")[0], 401)     # os outros saem
        self.assertEqual(Cliente(self.base).post("/api/auth/login", {"email": email, "senha": "senha-nova-1"})[0], 200)

    def test_limite_de_cadastros_por_endereco(self):
        with mock.patch.object(limites, "CADASTRO_POR_IP", 2):
            for _ in range(2):
                self.novo_usuario()
            BaseApi._contador += 1
            status, dados = Cliente(self.base).post("/api/auth/cadastro", {
                "nome": "X", "email": f"spam{BaseApi._contador}@exemplo.com", "senha": "senha-segura", "aceito_termos": True})
        self.assertEqual(status, 429)

    def test_rede_nao_mostra_enderecos_hospedado(self):
        with mock.patch.dict(os.environ, {"VERCEL": "1"}):
            self.assertEqual(Cliente(self.base).get("/api/rede")[1]["enderecos"], [])
