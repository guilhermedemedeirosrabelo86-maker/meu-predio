"""Enquetes: o síndico pergunta, cada unidade vota uma vez e todos veem o resultado."""
from . import historico
from .comum import data_iso, exigir_membro, hoje, inteiro, texto
from .web import ErroHTTP, rota

MORADORES = ("sindico", "morador")
MAX_OPCOES = 6


def _aberta(enquete, dia):
    return not enquete["encerrada"] and (enquete["encerra_em"] is None or enquete["encerra_em"] >= dia)


def _enquete(conn, cid, eid):
    enquete = conn.execute("SELECT * FROM enquetes WHERE id = ? AND condominio_id = ?", (eid, cid)).fetchone()
    if enquete is None:
        raise ErroHTTP(404, "Enquete não encontrada.")
    return enquete


def _completa(conn, enquete, unidade_id, dia):
    opcoes = conn.execute(
        """SELECT o.id, o.texto, (SELECT COUNT(*) FROM enquete_votos v WHERE v.opcao_id = o.id) AS votos
           FROM enquete_opcoes o WHERE o.enquete_id = ? ORDER BY o.ordem""",
        (enquete["id"],),
    ).fetchall()
    meu = None
    if unidade_id is not None:
        voto = conn.execute(
            "SELECT opcao_id FROM enquete_votos WHERE enquete_id = ? AND unidade_id = ?", (enquete["id"], unidade_id)
        ).fetchone()
        meu = voto["opcao_id"] if voto else None
    return {
        "id": enquete["id"],
        "pergunta": enquete["pergunta"],
        "descricao": enquete["descricao"],
        "encerra_em": enquete["encerra_em"],
        "criado_em": enquete["criado_em"],
        "aberta": _aberta(enquete, dia),
        "opcoes": [dict(o) for o in opcoes],
        "total_votos": sum(o["votos"] for o in opcoes),
        "meu_voto": meu,
    }


@rota("GET", "/api/condominios/{cid:int}/enquetes")
def listar_enquetes(req, cid):
    membro = exigir_membro(req, cid, papeis=MORADORES)
    dia = hoje().isoformat()
    linhas = req.conn.execute(
        "SELECT * FROM enquetes WHERE condominio_id = ? ORDER BY id DESC LIMIT 50", (cid,)
    ).fetchall()
    enquetes = [_completa(req.conn, e, membro["unidade_id"], dia) for e in linhas]
    enquetes.sort(key=lambda e: not e["aberta"])  # abertas primeiro, cada grupo da mais nova para a mais antiga
    total = req.conn.execute("SELECT COUNT(*) FROM unidades WHERE condominio_id = ?", (cid,)).fetchone()[0]
    return {"enquetes": enquetes, "total_unidades": total, "pode_votar": membro["unidade_id"] is not None}


@rota("POST", "/api/condominios/{cid:int}/enquetes")
def criar_enquete(req, cid):
    exigir_membro(req, cid, sindico=True)
    pergunta = texto(req.corpo, "pergunta", "Pergunta", maximo=160)
    descricao = texto(req.corpo, "descricao", "Detalhes", obrigatorio=False, maximo=2000)
    bruto = req.corpo.get("opcoes")
    if not isinstance(bruto, list):
        raise ErroHTTP(400, "Escreva as opções de resposta.")
    opcoes = [texto({"o": o}, "o", "Opção", obrigatorio=False, maximo=80) for o in bruto]
    opcoes = [o for o in opcoes if o]
    if len(opcoes) < 2:
        raise ErroHTTP(400, "Escreva pelo menos duas opções.")
    if len(opcoes) > MAX_OPCOES:
        raise ErroHTTP(400, f"Use no máximo {MAX_OPCOES} opções.")
    if len({o.casefold() for o in opcoes}) != len(opcoes):
        raise ErroHTTP(400, "As opções precisam ser diferentes.")
    encerra = None
    if req.corpo.get("encerra_em"):
        dia = data_iso(req.corpo["encerra_em"], "Encerra em")
        if dia < hoje():
            raise ErroHTTP(400, "A data de encerramento já passou.")
        encerra = dia.isoformat()
    eid = req.conn.execute(
        "INSERT INTO enquetes (condominio_id, autor_id, pergunta, descricao, encerra_em) VALUES (?, ?, ?, ?, ?)",
        (cid, req.usuario["id"], pergunta, descricao, encerra),
    ).lastrowid
    req.conn.executemany(
        "INSERT INTO enquete_opcoes (enquete_id, texto, ordem) VALUES (?, ?, ?)",
        [(eid, o, i) for i, o in enumerate(opcoes)],
    )
    return 201, {"id": eid}


@rota("POST", "/api/condominios/{cid:int}/enquetes/{eid:int}/voto")
def votar(req, cid, eid):
    membro = exigir_membro(req, cid, papeis=MORADORES)
    enquete = _enquete(req.conn, cid, eid)
    if membro["unidade_id"] is None:
        raise ErroHTTP(403, "Só quem mora numa unidade pode votar.")
    if not _aberta(enquete, hoje().isoformat()):
        raise ErroHTTP(409, "Esta enquete já foi encerrada.")
    opcao_id = inteiro(req.corpo, "opcao_id", "Opção")
    if req.conn.execute("SELECT 1 FROM enquete_opcoes WHERE id = ? AND enquete_id = ?", (opcao_id, eid)).fetchone() is None:
        raise ErroHTTP(400, "Escolha uma das opções.")
    req.conn.execute(
        """INSERT INTO enquete_votos (enquete_id, unidade_id, opcao_id, usuario_id) VALUES (?, ?, ?, ?)
           ON CONFLICT (enquete_id, unidade_id)
           DO UPDATE SET opcao_id = excluded.opcao_id, usuario_id = excluded.usuario_id, criado_em = datetime('now')""",
        (eid, membro["unidade_id"], opcao_id, req.usuario["id"]),
    )
    return {"ok": True}


@rota("POST", "/api/condominios/{cid:int}/enquetes/{eid:int}/encerrar")
def encerrar_enquete(req, cid, eid):
    exigir_membro(req, cid, sindico=True)
    enquete = _enquete(req.conn, cid, eid)
    req.conn.execute("UPDATE enquetes SET encerrada = 1 WHERE id = ?", (eid,))
    historico.anotar(req, cid, f'Encerrou a enquete "{enquete["pergunta"]}"')
    return {"ok": True}


@rota("DELETE", "/api/condominios/{cid:int}/enquetes/{eid:int}")
def excluir_enquete(req, cid, eid):
    exigir_membro(req, cid, sindico=True)
    enquete = _enquete(req.conn, cid, eid)
    req.conn.execute("DELETE FROM enquetes WHERE id = ?", (eid,))
    historico.anotar(req, cid, f'Excluiu a enquete "{enquete["pergunta"]}"')
    return {"ok": True}


def sem_voto(conn, cid, unidade_id, dia):
    """Enquetes abertas em que a unidade ainda não votou (para o Início)."""
    if unidade_id is None:
        return 0
    return conn.execute(
        """SELECT COUNT(*) FROM enquetes e WHERE e.condominio_id = ? AND e.encerrada = 0
           AND (e.encerra_em IS NULL OR e.encerra_em >= ?)
           AND NOT EXISTS (SELECT 1 FROM enquete_votos v WHERE v.enquete_id = e.id AND v.unidade_id = ?)""",
        (cid, dia, unidade_id),
    ).fetchone()[0]
