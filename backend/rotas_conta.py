"""Cadastro, login, perfil e contatos de emergência."""
import sqlite3

from . import auth
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
    try:
        cursor = req.conn.execute(
            "INSERT INTO usuarios (nome, email, telefone, senha_hash) VALUES (?, ?, ?, ?)",
            (nome, email, telefone, auth.hash_senha(senha)),
        )
    except sqlite3.IntegrityError:
        raise ErroHTTP(409, "Já existe uma conta com este e-mail.")
    _abrir_sessao(req, cursor.lastrowid)
    usuario = req.conn.execute("SELECT * FROM usuarios WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return 201, {"usuario": usuario_publico(usuario)}


@rota("POST", "/api/auth/login")
def entrar(req):
    email = texto(req.corpo, "email", "E-mail", maximo=254).lower()
    senha = req.corpo.get("senha")
    if not isinstance(senha, str) or not senha:
        raise ErroHTTP(400, 'Preencha o campo "Senha".')
    usuario = req.conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    if usuario is None or not auth.conferir_senha(senha, usuario["senha_hash"]):
        raise ErroHTTP(401, "E-mail ou senha incorretos.")
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
               c.id AS condominio_id, c.nome AS condominio,
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
