"""Cadastro, login, perfil e contatos de emergência."""
import sqlite3
import sys

from . import auth, correio, limites
from .comum import EMAIL_RE, exigir_login, texto, usuario_publico
from .web import ErroHTTP, rota

DURACAO_SESSAO = 30 * 24 * 3600
MAX_CONTATOS = 5


def _senha(corpo):
    senha = corpo.get("senha")
    if not isinstance(senha, str) or len(senha) < 8:
        raise ErroHTTP(400, "A senha precisa ter pelo menos 8 caracteres.")
    if len(senha) > 200:
        raise ErroHTTP(400, "Senha longa demais.")
    return senha


def _abrir_sessao(req, usuario_id):
    token = auth.novo_token()
    req.conn.execute(
        "INSERT INTO sessoes (token_hash, usuario_id, expira_em) VALUES (?, ?, datetime('now', ?))",
        (auth.hash_token(token), usuario_id, f"+{DURACAO_SESSAO} seconds"),
    )
    req.cookies_saida.append(f"sessao={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={DURACAO_SESSAO}")


@rota("POST", "/api/auth/cadastro")
def cadastrar(req):
    nome = texto(req.corpo, "nome", "Nome", maximo=100)
    email = texto(req.corpo, "email", "E-mail", maximo=254).lower()
    if not EMAIL_RE.match(email):
        raise ErroHTTP(400, "Informe um e-mail válido.")
    senha = _senha(req.corpo)
    telefone = texto(req.corpo, "telefone", "Telefone", obrigatorio=False, maximo=30)
    if req.corpo.get("aceito_termos") is not True:
        raise ErroHTTP(400, "Para criar a conta, aceite os termos de uso e a política de privacidade.")
    chave_ip = f"cadastro-ip:{req.ip}"
    limites.conferir(req.conn, chave_ip, limites.CADASTRO_POR_IP)
    try:
        cursor = req.conn.execute(
            "INSERT INTO usuarios (nome, email, telefone, senha_hash, termos_aceitos_em) VALUES (?, ?, ?, ?, datetime('now'))",
            (nome, email, telefone, auth.hash_senha(senha)),
        )
    except sqlite3.IntegrityError:
        raise ErroHTTP(409, "Já existe uma conta com este e-mail.")
    limites.registrar(req.conn, chave_ip)
    _abrir_sessao(req, cursor.lastrowid)
    usuario = req.conn.execute("SELECT * FROM usuarios WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return 201, {"usuario": usuario_publico(usuario)}


@rota("POST", "/api/auth/login")
def entrar(req):
    email = texto(req.corpo, "email", "E-mail", maximo=254).lower()
    senha = req.corpo.get("senha")
    if not isinstance(senha, str) or not senha:
        raise ErroHTTP(400, 'Preencha o campo "Senha".')
    chave_email, chave_ip = f"login:{email}", f"login-ip:{req.ip}"
    limites.conferir(req.conn, chave_email, limites.LOGIN_POR_EMAIL)
    limites.conferir(req.conn, chave_ip, limites.LOGIN_POR_IP)
    usuario = req.conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    if usuario is None or not auth.conferir_senha(senha, usuario["senha_hash"]):
        limites.registrar(req.conn, chave_email, chave_ip)
        raise ErroHTTP(401, "E-mail ou senha incorretos.")
    limites.esquecer(req.conn, chave_email)
    if auth.precisa_refazer(usuario["senha_hash"]):  # senha guardada com a força antiga
        req.conn.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (auth.hash_senha(senha), usuario["id"]))
    req.conn.execute("DELETE FROM sessoes WHERE expira_em <= datetime('now')")
    _abrir_sessao(req, usuario["id"])
    return {"usuario": usuario_publico(usuario)}


@rota("POST", "/api/auth/logout")
def sair(req):
    if req.token_hash:
        req.conn.execute("DELETE FROM sessoes WHERE token_hash = ?", (req.token_hash,))
    req.cookies_saida.append("sessao=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0")
    return {"ok": True}


@rota("GET", "/api/eu")
def ver_eu(req):
    usuario = exigir_login(req)
    condominios = req.conn.execute(
        """
        SELECT m.id AS membro_id, m.papel, m.status,
               c.id AS condominio_id, c.nome AS condominio, c.foto, c.foto_noite,
               u.id AS unidade_id, u.identificador AS unidade
        FROM membros m
        JOIN condominios c ON c.id = m.condominio_id
        LEFT JOIN unidades u ON u.id = m.unidade_id
        WHERE m.usuario_id = ?
        ORDER BY c.nome
        """,
        (usuario["id"],),
    ).fetchall()
    return {"usuario": usuario_publico(usuario), "condominios": [dict(c) for c in condominios]}


@rota("PATCH", "/api/eu")
def alterar_eu(req):
    usuario = exigir_login(req)
    nome = texto(req.corpo, "nome", "Nome", maximo=100)
    telefone = texto(req.corpo, "telefone", "Telefone", obrigatorio=False, maximo=30)
    req.conn.execute("UPDATE usuarios SET nome = ?, telefone = ? WHERE id = ?", (nome, telefone, usuario["id"]))
    return {"ok": True}


@rota("POST", "/api/eu/senha")
def trocar_senha(req):
    """Troca a senha sabendo a atual. Os outros aparelhos saem da conta; este continua conectado."""
    usuario = exigir_login(req)
    atual = req.corpo.get("senha_atual")
    chave = f"login:{usuario['email']}"
    limites.conferir(req.conn, chave, limites.LOGIN_POR_EMAIL)
    if not isinstance(atual, str) or not auth.conferir_senha(atual, usuario["senha_hash"]):
        limites.registrar(req.conn, chave)
        raise ErroHTTP(400, "A senha atual está incorreta.")
    nova = _senha({"senha": req.corpo.get("senha_nova")})
    req.conn.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (auth.hash_senha(nova), usuario["id"]))
    req.conn.execute("DELETE FROM sessoes WHERE usuario_id = ? AND token_hash <> ?", (usuario["id"], req.token_hash))
    return {"ok": True}


@rota("GET", "/api/eu/contatos")
def listar_contatos(req):
    usuario = exigir_login(req)
    contatos = req.conn.execute(
        "SELECT id, nome, telefone, parentesco FROM contatos_emergencia WHERE usuario_id = ? ORDER BY id",
        (usuario["id"],),
    ).fetchall()
    return {"contatos": [dict(c) for c in contatos]}


@rota("POST", "/api/eu/contatos")
def adicionar_contato(req):
    usuario = exigir_login(req)
    nome = texto(req.corpo, "nome", "Nome", maximo=100)
    telefone = texto(req.corpo, "telefone", "Telefone", maximo=30)
    parentesco = texto(req.corpo, "parentesco", "Parentesco", obrigatorio=False, maximo=40)
    total = req.conn.execute(
        "SELECT COUNT(*) FROM contatos_emergencia WHERE usuario_id = ?", (usuario["id"],)
    ).fetchone()[0]
    if total >= MAX_CONTATOS:
        raise ErroHTTP(400, f"Você pode cadastrar até {MAX_CONTATOS} contatos de emergência.")
    cursor = req.conn.execute(
        "INSERT INTO contatos_emergencia (usuario_id, nome, telefone, parentesco) VALUES (?, ?, ?, ?)",
        (usuario["id"], nome, telefone, parentesco),
    )
    return 201, {"id": cursor.lastrowid}


@rota("DELETE", "/api/eu/contatos/{contato_id:int}")
def remover_contato(req, contato_id):
    usuario = exigir_login(req)
    cursor = req.conn.execute(
        "DELETE FROM contatos_emergencia WHERE id = ? AND usuario_id = ?", (contato_id, usuario["id"])
    )
    if cursor.rowcount == 0:
        raise ErroHTTP(404, "Contato não encontrado.")
    return {"ok": True}


# --- Esqueci minha senha ----------------------------------------------------

VALIDADE_LINK_MINUTOS = 60
RESPOSTA_ESQUECI = "Se houver uma conta com este e-mail, enviamos um link para criar uma nova senha."


@rota("POST", "/api/auth/esqueci")
def esqueci_senha(req):
    """A resposta é a mesma exista ou não a conta, para não revelar quem usa o app."""
    email = texto(req.corpo, "email", "E-mail", maximo=254).lower()
    chave_email, chave_ip = f"esqueci:{email}", f"esqueci-ip:{req.ip}"
    limites.conferir(req.conn, chave_email, limites.ESQUECI_POR_EMAIL)
    limites.conferir(req.conn, chave_ip, limites.ESQUECI_POR_IP)
    limites.registrar(req.conn, chave_email, chave_ip)
    usuario = req.conn.execute("SELECT id, nome FROM usuarios WHERE email = ?", (email,)).fetchone()
    if usuario is None:
        return {"mensagem": RESPOSTA_ESQUECI}
    token = auth.novo_token()
    req.conn.execute("DELETE FROM recuperacoes WHERE usuario_id = ? OR expira_em <= datetime('now')", (usuario["id"],))
    req.conn.execute(
        "INSERT INTO recuperacoes (token_hash, usuario_id, expira_em) VALUES (?, ?, datetime('now', ?))",
        (auth.hash_token(token), usuario["id"], f"+{VALIDADE_LINK_MINUTOS} minutes"),
    )
    req.conn.commit()  # o link só sai por e-mail se já estiver guardado
    link = f"{req.endereco}/#/nova-senha/{token}"
    try:
        correio.enviar(email, "Criar uma nova senha no Meu Prédio", (
            f"Olá, {usuario['nome'].split(' ')[0]}!\n\n"
            f"Para criar uma nova senha, abra o link abaixo. Ele vale por {VALIDADE_LINK_MINUTOS} minutos e só uma vez.\n\n"
            f"{link}\n\n"
            "Se não foi você que pediu, ignore este e-mail: sua senha continua a mesma."
        ))
    except correio.ErroEnvio as erro:
        print(f"Falha ao enviar e-mail de nova senha: {erro}", file=sys.stderr, flush=True)
        raise ErroHTTP(503, "Não conseguimos enviar o e-mail agora. Tente de novo em alguns minutos.")
    return {"mensagem": RESPOSTA_ESQUECI}


@rota("POST", "/api/auth/nova-senha")
def nova_senha(req):
    token = texto(req.corpo, "token", "Link", maximo=100)
    senha = _senha(req.corpo)
    chave_ip = f"link-ip:{req.ip}"
    limites.conferir(req.conn, chave_ip, limites.LINK_INVALIDO_POR_IP)
    pedido = req.conn.execute(
        "SELECT usuario_id FROM recuperacoes WHERE token_hash = ? AND expira_em > datetime('now')",
        (auth.hash_token(token),),
    ).fetchone()
    if pedido is None:
        limites.registrar(req.conn, chave_ip)
        raise ErroHTTP(400, 'Este link venceu ou já foi usado. Peça outro em "Esqueci minha senha".')
    usuario_id = pedido["usuario_id"]
    req.conn.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (auth.hash_senha(senha), usuario_id))
    req.conn.execute("DELETE FROM recuperacoes WHERE usuario_id = ?", (usuario_id,))
    req.conn.execute("DELETE FROM sessoes WHERE usuario_id = ?", (usuario_id,))  # sai de todos os aparelhos
    email = req.conn.execute("SELECT email FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()["email"]
    limites.esquecer(req.conn, f"login:{email}")
    _abrir_sessao(req, usuario_id)
    usuario = req.conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return {"usuario": usuario_publico(usuario)}
