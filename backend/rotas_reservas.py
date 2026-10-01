"""Áreas comuns (salão, churrasqueira...) e reservas por dia."""
import re
import sqlite3
from datetime import timedelta

from .comum import booleano, data_iso, exigir_membro, hoje, inteiro, texto, unidade_do_condominio
from .web import ErroHTTP, rota

MAX_AREAS = 20
MES_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _area_publica(area):
    return {
        "id": area["id"],
        "nome": area["nome"],
        "regras": area["regras"],
        "exige_aprovacao": bool(area["exige_aprovacao"]),
        "antecedencia_dias": area["antecedencia_dias"],
        "limite_por_unidade": area["limite_por_unidade"],
    }


def _area_do_condominio(conn, cid, area_id):
    area = conn.execute("SELECT * FROM areas WHERE id = ? AND condominio_id = ?", (area_id, cid)).fetchone()
    if area is None:
        raise ErroHTTP(404, "Área não encontrada.")
    return area


def _campos_area(corpo):
    return (
        texto(corpo, "nome", "Nome", maximo=60),
        texto(corpo, "regras", "Regras de uso", obrigatorio=False, maximo=2000),
        booleano(corpo, "exige_aprovacao", "Exige aprovação"),
        inteiro(corpo, "antecedencia_dias", "Antecedência máxima (dias)", 1, 365),
        inteiro(corpo, "limite_por_unidade", "Reservas futuras por unidade", 1, 20),
    )


def _reserva_do_condominio(conn, cid, rid):
    reserva = conn.execute(
        """SELECT r.* FROM reservas r JOIN areas a ON a.id = r.area_id
           WHERE r.id = ? AND a.condominio_id = ?""",
        (rid, cid),
    ).fetchone()
    if reserva is None:
        raise ErroHTTP(404, "Reserva não encontrada.")
    return reserva


SELECT_RESERVA = """
    SELECT r.id, r.data, r.status, r.observacao, r.unidade_id, r.area_id,
           a.nome AS area, un.identificador AS unidade, u.nome AS reservado_por
    FROM reservas r
    JOIN areas a ON a.id = r.area_id
    JOIN unidades un ON un.id = r.unidade_id
    LEFT JOIN usuarios u ON u.id = r.usuario_id
"""


def _reserva_publica(linha, membro):
    """O síndico e a própria unidade veem tudo; os vizinhos veem só qual unidade reservou."""
    reserva = dict(linha)
    reserva["minha"] = linha["unidade_id"] == membro["unidade_id"]
    if membro["papel"] != "sindico" and not reserva["minha"]:
        del reserva["reservado_por"], reserva["observacao"]
    return reserva


# --- Áreas -------------------------------------------------------------------

@rota("GET", "/api/condominios/{cid:int}/areas")
def listar_areas(req, cid):
    exigir_membro(req, cid)
    areas = req.conn.execute("SELECT * FROM areas WHERE condominio_id = ? ORDER BY nome", (cid,)).fetchall()
    return {"areas": [_area_publica(a) for a in areas], "hoje": hoje().isoformat()}


@rota("POST", "/api/condominios/{cid:int}/areas")
def criar_area(req, cid):
    exigir_membro(req, cid, sindico=True)
    campos = _campos_area(req.corpo)
    total = req.conn.execute("SELECT COUNT(*) FROM areas WHERE condominio_id = ?", (cid,)).fetchone()[0]
    if total >= MAX_AREAS:
        raise ErroHTTP(400, f"O limite é de {MAX_AREAS} áreas.")
    try:
        cursor = req.conn.execute(
            """INSERT INTO areas (condominio_id, nome, regras, exige_aprovacao, antecedencia_dias, limite_por_unidade)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (cid, *campos),
        )
    except sqlite3.IntegrityError:
        raise ErroHTTP(409, "Já existe uma área com esse nome.")
    return 201, {"id": cursor.lastrowid}


@rota("PATCH", "/api/condominios/{cid:int}/areas/{aid:int}")
def alterar_area(req, cid, aid):
    exigir_membro(req, cid, sindico=True)
    _area_do_condominio(req.conn, cid, aid)
    try:
        req.conn.execute(
            """UPDATE areas SET nome = ?, regras = ?, exige_aprovacao = ?, antecedencia_dias = ?, limite_por_unidade = ?
               WHERE id = ?""",
            (*_campos_area(req.corpo), aid),
        )
    except sqlite3.IntegrityError:
        raise ErroHTTP(409, "Já existe uma área com esse nome.")
    return {"ok": True}


@rota("DELETE", "/api/condominios/{cid:int}/areas/{aid:int}")
def excluir_area(req, cid, aid):
    exigir_membro(req, cid, sindico=True)
    _area_do_condominio(req.conn, cid, aid)
    req.conn.execute("DELETE FROM areas WHERE id = ?", (aid,))
    return {"ok": True}


# --- Reservas ----------------------------------------------------------------

@rota("GET", "/api/condominios/{cid:int}/reservas")
def listar_reservas(req, cid):
    """Reservas de uma área num mês: ?area_id=1&mes=2026-10"""
    membro = exigir_membro(req, cid)
    area_id = req.query.get("area_id", "")
    mes = req.query.get("mes", "")
    if not area_id.isdigit() or not MES_RE.match(mes):
        raise ErroHTTP(400, "Informe a área e o mês (AAAA-MM).")
    _area_do_condominio(req.conn, cid, int(area_id))
    linhas = req.conn.execute(
        SELECT_RESERVA + " WHERE r.area_id = ? AND r.data LIKE ? ORDER BY r.data",
        (int(area_id), f"{mes}-%"),
    ).fetchall()
    return {"reservas": [_reserva_publica(r, membro) for r in linhas], "hoje": hoje().isoformat()}


@rota("GET", "/api/condominios/{cid:int}/reservas/proximas")
def proximas_reservas(req, cid):
    """Próximas reservas da unidade de quem está logado e, para o síndico, os pedidos a aprovar."""
    membro = exigir_membro(req, cid)
    dia = hoje().isoformat()
    minhas = req.conn.execute(
        SELECT_RESERVA + " WHERE r.unidade_id = ? AND r.data >= ? ORDER BY r.data",
        (membro["unidade_id"], dia),
    ).fetchall()
    resposta = {"minhas": [_reserva_publica(r, membro) for r in minhas]}
    if membro["papel"] == "sindico":
        pendentes = req.conn.execute(
            SELECT_RESERVA + " WHERE a.condominio_id = ? AND r.status = 'pendente' AND r.data >= ? ORDER BY r.data",
            (cid, dia),
        ).fetchall()
        resposta["pendentes"] = [_reserva_publica(r, membro) for r in pendentes]
    return resposta


@rota("POST", "/api/condominios/{cid:int}/reservas")
def reservar(req, cid):
    membro = exigir_membro(req, cid)
    sindico = membro["papel"] == "sindico"
    area = _area_do_condominio(req.conn, cid, inteiro(req.corpo, "area_id", "Área"))
    unidade_id = membro["unidade_id"]
    if sindico and req.corpo.get("unidade_id") is not None:
        unidade_id = unidade_do_condominio(req.conn, cid, inteiro(req.corpo, "unidade_id", "Unidade"))["id"]
    if unidade_id is None:
        raise ErroHTTP(400, "Escolha para qual unidade é a reserva.")
    dia = data_iso(req.corpo.get("data"))
    observacao = texto(req.corpo, "observacao", "Observação", obrigatorio=False, maximo=300)

    # As regras da área valem para os moradores; o síndico pode abrir exceções.
    if dia < hoje():
        raise ErroHTTP(400, "Escolha uma data a partir de hoje.")
    if not sindico:
        if dia > hoje() + timedelta(days=area["antecedencia_dias"]):
            raise ErroHTTP(400, f"Esta área só pode ser reservada com até {area['antecedencia_dias']} dias de antecedência.")
        futuras = req.conn.execute(
            "SELECT COUNT(*) FROM reservas WHERE area_id = ? AND unidade_id = ? AND data >= ?",
            (area["id"], unidade_id, hoje().isoformat()),
        ).fetchone()[0]
        if futuras >= area["limite_por_unidade"]:
            raise ErroHTTP(400, f"Sua unidade já tem {futuras} reserva(s) futura(s) nesta área, que é o limite. "
                                "Cancele uma ou aguarde a data passar.")

    status = "pendente" if area["exige_aprovacao"] and not sindico else "confirmada"
    try:
        cursor = req.conn.execute(
            "INSERT INTO reservas (area_id, unidade_id, usuario_id, data, status, observacao) VALUES (?, ?, ?, ?, ?, ?)",
            (area["id"], unidade_id, req.usuario["id"], dia.isoformat(), status, observacao),
        )
    except sqlite3.IntegrityError:
        raise ErroHTTP(409, "Esta data já está reservada. Escolha outro dia.")
    return 201, {"id": cursor.lastrowid, "status": status}


@rota("PATCH", "/api/condominios/{cid:int}/reservas/{rid:int}")
def aprovar_reserva(req, cid, rid):
    exigir_membro(req, cid, sindico=True)
    _reserva_do_condominio(req.conn, cid, rid)
    if req.corpo.get("status") != "confirmada":
        raise ErroHTTP(400, "Status inválido.")
    req.conn.execute("UPDATE reservas SET status = 'confirmada' WHERE id = ?", (rid,))
    return {"ok": True}


@rota("DELETE", "/api/condominios/{cid:int}/reservas/{rid:int}")
def cancelar_reserva(req, cid, rid):
    """A unidade cancela a própria reserva futura; o síndico cancela ou recusa qualquer uma."""
    membro = exigir_membro(req, cid)
    reserva = _reserva_do_condominio(req.conn, cid, rid)
    if membro["papel"] != "sindico":
        if reserva["unidade_id"] != membro["unidade_id"]:
            raise ErroHTTP(403, "Você só pode cancelar reservas da sua unidade.")
        if reserva["data"] < hoje().isoformat():
            raise ErroHTTP(400, "Esta reserva já passou.")
    req.conn.execute("DELETE FROM reservas WHERE id = ?", (rid,))
    return {"ok": True}
