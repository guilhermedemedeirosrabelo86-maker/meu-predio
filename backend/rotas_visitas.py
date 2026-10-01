"""Liberação de visitantes por QR Code e registro de entradas na portaria."""
import secrets
import sqlite3
from datetime import timedelta

from . import auth
from .comum import data_iso, exigir_login, exigir_membro, hoje, inteiro, texto, unidade_do_condominio
from .web import ErroHTTP, rota

TIPOS = ("visita", "prestador", "entrega")
EQUIPE = ("sindico", "portaria")  # quem valida o QR e registra entradas
MAX_DIAS = 30
ANTECEDENCIA_MAXIMA = 60
MAX_ATIVAS_POR_UNIDADE = 30


def situacao(visita, dia=None):
    dia = (dia or hoje()).isoformat()
    if visita["cancelada"]:
        return "cancelada"
    if dia < visita["data_inicio"]:
        return "futura"
    if dia > visita["data_fim"]:
        return "expirada"
    return "valida"


SELECT_VISITA = """
    SELECT v.id, v.nome, v.tipo, v.data_inicio, v.data_fim, v.observacao, v.token, v.codigo, v.cancelada,
           v.criado_em, v.condominio_id, v.unidade_id, un.identificador AS unidade,
           u.nome AS morador, u.telefone AS telefone_morador,
           (SELECT COUNT(*) FROM visita_entradas e WHERE e.visita_id = v.id) AS entradas,
           (SELECT MAX(e.criado_em) FROM visita_entradas e WHERE e.visita_id = v.id) AS ultima_entrada
    FROM visitas v
    JOIN unidades un ON un.id = v.unidade_id
    LEFT JOIN usuarios u ON u.id = v.autor_id
"""


def _visita_publica(linha, completa=False):
    visita = dict(linha)
    visita["cancelada"] = bool(visita["cancelada"])
    visita["situacao"] = situacao(linha)
    if not completa:
        del visita["telefone_morador"]
    return visita


def _por_token(conn, token):
    visita = conn.execute(SELECT_VISITA + " WHERE v.token = ?", (token,)).fetchone()
    if visita is None:
        raise ErroHTTP(404, "QR Code inválido ou não encontrado.")
    return visita


def _novo_codigo(conn, cid):
    while True:
        codigo = auth.novo_codigo_convite()
        if not conn.execute("SELECT 1 FROM visitas WHERE condominio_id = ? AND codigo = ?", (cid, codigo)).fetchone():
            return codigo


# --- Morador ---------------------------------------------------------------------

@rota("GET", "/api/condominios/{cid:int}/visitas")
def listar_visitas(req, cid):
    """Visitas da unidade: as válidas e futuras, mais as da última semana."""
    membro = exigir_membro(req, cid)
    if membro["unidade_id"] is None:
        return {"visitas": []}
    desde = (hoje() - timedelta(days=7)).isoformat()
    linhas = req.conn.execute(
        SELECT_VISITA + " WHERE v.unidade_id = ? AND v.data_fim >= ? ORDER BY v.data_inicio, v.id",
        (membro["unidade_id"], desde),
    ).fetchall()
    return {"visitas": [_visita_publica(v) for v in linhas]}


@rota("POST", "/api/condominios/{cid:int}/visitas")
def liberar_visita(req, cid):
    membro = exigir_membro(req, cid, papeis=("sindico", "morador"))
    unidade_id = membro["unidade_id"]
    if membro["papel"] == "sindico" and req.corpo.get("unidade_id") is not None:
        unidade_id = unidade_do_condominio(req.conn, cid, inteiro(req.corpo, "unidade_id", "Unidade"))["id"]
    if unidade_id is None:
        raise ErroHTTP(400, "Você precisa estar vinculado a uma unidade para liberar visitantes.")
    nome = texto(req.corpo, "nome", "Nome do visitante", maximo=100)
    tipo = req.corpo.get("tipo", "visita")
    if tipo not in TIPOS:
        raise ErroHTTP(400, "Tipo de visita inválido.")
    inicio = data_iso(req.corpo.get("data_inicio"), "Data")
    fim = data_iso(req.corpo.get("data_fim") or req.corpo.get("data_inicio"), "Até")
    observacao = texto(req.corpo, "observacao", "Observação", obrigatorio=False, maximo=300)

    if inicio < hoje():
        raise ErroHTTP(400, "A visita não pode começar no passado.")
    if inicio > hoje() + timedelta(days=ANTECEDENCIA_MAXIMA):
        raise ErroHTTP(400, f"Libere visitas com até {ANTECEDENCIA_MAXIMA} dias de antecedência.")
    if fim < inicio:
        raise ErroHTTP(400, "A data final precisa ser igual ou depois da inicial.")
    if (fim - inicio).days >= MAX_DIAS:
        raise ErroHTTP(400, f"Uma liberação vale por no máximo {MAX_DIAS} dias.")
    ativas = req.conn.execute(
        "SELECT COUNT(*) FROM visitas WHERE unidade_id = ? AND cancelada = 0 AND data_fim >= ?",
        (unidade_id, hoje().isoformat()),
    ).fetchone()[0]
    if ativas >= MAX_ATIVAS_POR_UNIDADE:
        raise ErroHTTP(400, "Sua unidade já tem muitas visitas liberadas. Cancele as que não vão mais acontecer.")

    token = secrets.token_urlsafe(24)
    for _ in range(5):
        try:
            cursor = req.conn.execute(
                """INSERT INTO visitas (condominio_id, unidade_id, autor_id, nome, tipo, data_inicio, data_fim,
                                        observacao, token, codigo)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (cid, unidade_id, req.usuario["id"], nome, tipo, inicio.isoformat(), fim.isoformat(),
                 observacao, token, _novo_codigo(req.conn, cid)),
            )
            break
        except sqlite3.IntegrityError:  # corrida rara no código curto
            continue
    else:
        raise ErroHTTP(500, "Não foi possível gerar o código. Tente novamente.")
    visita = req.conn.execute(SELECT_VISITA + " WHERE v.id = ?", (cursor.lastrowid,)).fetchone()
    return 201, {"visita": _visita_publica(visita)}


@rota("DELETE", "/api/condominios/{cid:int}/visitas/{vid:int}")
def cancelar_visita(req, cid, vid):
    membro = exigir_membro(req, cid)
    visita = req.conn.execute("SELECT * FROM visitas WHERE id = ? AND condominio_id = ?", (vid, cid)).fetchone()
    if visita is None:
        raise ErroHTTP(404, "Visita não encontrada.")
    if membro["papel"] != "sindico" and visita["unidade_id"] != membro["unidade_id"]:
        raise ErroHTTP(403, "Você só pode cancelar visitas da sua unidade.")
    req.conn.execute("UPDATE visitas SET cancelada = 1 WHERE id = ?", (vid,))
    return {"ok": True}


# --- Passe do visitante (público: é o link que o morador manda) -------------------

@rota("GET", "/api/passes/{token}")
def ver_passe(req, token):
    visita = _por_token(req.conn, token)
    condominio = req.conn.execute(
        "SELECT nome, endereco FROM condominios WHERE id = ?", (visita["condominio_id"],)
    ).fetchone()
    return {
        "passe": {
            "nome": visita["nome"],
            "tipo": visita["tipo"],
            "data_inicio": visita["data_inicio"],
            "data_fim": visita["data_fim"],
            "codigo": visita["codigo"],
            "situacao": situacao(visita),
            "condominio": condominio["nome"],
            "endereco": condominio["endereco"],
        }
    }


# --- Portaria ------------------------------------------------------------------------

def _equipe_da_visita(req, token):
    exigir_login(req)
    visita = _por_token(req.conn, token)
    membro = req.conn.execute(
        "SELECT * FROM membros WHERE usuario_id = ? AND condominio_id = ? AND status = 'ativo'",
        (req.usuario["id"], visita["condominio_id"]),
    ).fetchone()
    if membro is None or membro["papel"] not in EQUIPE:
        raise ErroHTTP(403, "Só a portaria ou o síndico deste condomínio podem validar este QR Code.")
    return visita


@rota("GET", "/api/passes/{token}/portaria")
def validar_passe(req, token):
    visita = _equipe_da_visita(req, token)
    entradas = req.conn.execute(
        """SELECT e.criado_em, u.nome AS registrado_por FROM visita_entradas e
           LEFT JOIN usuarios u ON u.id = e.registrado_por
           WHERE e.visita_id = ? ORDER BY e.id DESC LIMIT 20""",
        (visita["id"],),
    ).fetchall()
    return {"visita": _visita_publica(visita, completa=True), "historico": [dict(e) for e in entradas]}


@rota("POST", "/api/passes/{token}/entradas")
def registrar_entrada(req, token):
    visita = _equipe_da_visita(req, token)
    estado = situacao(visita)
    mensagens = {
        "cancelada": "Esta liberação foi cancelada pelo morador.",
        "futura": "Esta liberação ainda não vale para hoje.",
        "expirada": "Esta liberação já expirou.",
    }
    if estado != "valida":
        raise ErroHTTP(409, mensagens[estado])
    req.conn.execute(
        "INSERT INTO visita_entradas (visita_id, registrado_por) VALUES (?, ?)", (visita["id"], req.usuario["id"])
    )
    return 201, {"ok": True}


@rota("GET", "/api/condominios/{cid:int}/portaria")
def painel_portaria(req, cid):
    """Visitantes esperados hoje e entradas registradas hoje."""
    exigir_membro(req, cid, papeis=EQUIPE)
    dia = hoje().isoformat()
    esperados = req.conn.execute(
        SELECT_VISITA + """ WHERE v.condominio_id = ? AND v.cancelada = 0 AND v.data_inicio <= ? AND v.data_fim >= ?
                            ORDER BY un.identificador, v.nome""",
        (cid, dia, dia),
    ).fetchall()
    entradas = req.conn.execute(
        """SELECT e.id, e.criado_em, v.nome, v.tipo, v.token, un.identificador AS unidade, u.nome AS registrado_por
           FROM visita_entradas e
           JOIN visitas v ON v.id = e.visita_id
           JOIN unidades un ON un.id = v.unidade_id
           LEFT JOIN usuarios u ON u.id = e.registrado_por
           WHERE v.condominio_id = ? AND e.criado_em >= datetime('now', '-24 hours')
           ORDER BY e.id DESC LIMIT 100""",
        (cid,),
    ).fetchall()
    return {
        "esperados": [_visita_publica(v, completa=True) for v in esperados],
        "entradas": [dict(e) for e in entradas],
    }


@rota("GET", "/api/condominios/{cid:int}/portaria/codigo/{codigo}")
def buscar_codigo(req, cid, codigo):
    exigir_membro(req, cid, papeis=EQUIPE)
    visita = req.conn.execute(
        "SELECT token FROM visitas WHERE condominio_id = ? AND codigo = ?", (cid, codigo.strip().upper())
    ).fetchone()
    if visita is None:
        raise ErroHTTP(404, "Código não encontrado. Confira com o visitante.")
    return {"token": visita["token"]}
