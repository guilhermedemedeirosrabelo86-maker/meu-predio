"""Encomendas: a portaria registra o pacote que chegou e marca quando a unidade retirou."""
from .comum import exigir_membro, inteiro, ordem_natural, texto, unidade_do_condominio
from .web import ErroHTTP, rota

EQUIPE = ("sindico", "portaria")

SELECT_ENCOMENDA = """
    SELECT e.id, e.descricao, e.criado_em, e.retirada_em, e.retirada_por, e.unidade_id,
           un.identificador AS unidade, r.nome AS registrado_por, en.nome AS entregue_por
    FROM encomendas e
    JOIN unidades un ON un.id = e.unidade_id
    LEFT JOIN usuarios r ON r.id = e.registrado_por
    LEFT JOIN usuarios en ON en.id = e.entregue_por
"""


def _encomenda(conn, cid, eid):
    encomenda = conn.execute("SELECT * FROM encomendas WHERE id = ? AND condominio_id = ?", (eid, cid)).fetchone()
    if encomenda is None:
        raise ErroHTTP(404, "Encomenda não encontrada.")
    return encomenda


@rota("GET", "/api/condominios/{cid:int}/encomendas")
def listar_encomendas(req, cid):
    """Equipe: tudo o que está na portaria e as últimas retiradas. Morador: só a própria unidade."""
    membro = exigir_membro(req, cid)
    equipe = membro["papel"] in EQUIPE
    if equipe:
        filtro, params = "e.condominio_id = ?", (cid,)
    elif membro["unidade_id"] is not None:
        filtro, params = "e.condominio_id = ? AND e.unidade_id = ?", (cid, membro["unidade_id"])
    else:
        return {"aguardando": [], "retiradas": [], "unidades": []}
    aguardando = req.conn.execute(
        SELECT_ENCOMENDA + f" WHERE {filtro} AND e.retirada_em IS NULL ORDER BY e.id DESC", params
    ).fetchall()
    retiradas = req.conn.execute(
        SELECT_ENCOMENDA + f" WHERE {filtro} AND e.retirada_em IS NOT NULL ORDER BY e.retirada_em DESC, e.id DESC LIMIT 30",
        params,
    ).fetchall()
    unidades = []
    if equipe:
        linhas = req.conn.execute("SELECT id, identificador FROM unidades WHERE condominio_id = ?", (cid,)).fetchall()
        unidades = sorted((dict(u) for u in linhas), key=lambda u: ordem_natural(u["identificador"]))
    return {
        "aguardando": [dict(e) for e in aguardando],
        "retiradas": [dict(e) for e in retiradas],
        "unidades": unidades,
    }


@rota("POST", "/api/condominios/{cid:int}/encomendas")
def registrar_encomenda(req, cid):
    exigir_membro(req, cid, papeis=EQUIPE)
    unidade = unidade_do_condominio(req.conn, cid, inteiro(req.corpo, "unidade_id", "Unidade"))
    descricao = texto(req.corpo, "descricao", "Descrição", maximo=120)
    eid = req.conn.execute(
        "INSERT INTO encomendas (condominio_id, unidade_id, descricao, registrado_por) VALUES (?, ?, ?, ?)",
        (cid, unidade["id"], descricao, req.usuario["id"]),
    ).lastrowid
    return 201, {"id": eid}


@rota("POST", "/api/condominios/{cid:int}/encomendas/{eid:int}/retirada")
def registrar_retirada(req, cid, eid):
    exigir_membro(req, cid, papeis=EQUIPE)
    encomenda = _encomenda(req.conn, cid, eid)
    if encomenda["retirada_em"] is not None:
        raise ErroHTTP(409, "Esta encomenda já foi retirada.")
    quem = texto(req.corpo, "retirada_por", "Quem retirou", obrigatorio=False, maximo=80)
    req.conn.execute(
        "UPDATE encomendas SET retirada_em = datetime('now'), retirada_por = ?, entregue_por = ? WHERE id = ?",
        (quem, req.usuario["id"], eid),
    )
    return {"ok": True}


@rota("DELETE", "/api/condominios/{cid:int}/encomendas/{eid:int}")
def excluir_encomenda(req, cid, eid):
    """Para corrigir um registro feito por engano."""
    exigir_membro(req, cid, papeis=EQUIPE)
    _encomenda(req.conn, cid, eid)
    req.conn.execute("DELETE FROM encomendas WHERE id = ?", (eid,))
    return {"ok": True}
