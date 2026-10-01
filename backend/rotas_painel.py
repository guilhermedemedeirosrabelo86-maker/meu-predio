"""Resumo para a tela inicial: um número por módulo, numa única chamada."""
from .comum import exigir_membro, hoje
from .web import rota


@rota("GET", "/api/condominios/{cid:int}/painel")
def painel(req, cid):
    membro = exigir_membro(req, cid)
    conn, uid, unidade = req.conn, req.usuario["id"], membro["unidade_id"]
    dia = hoje().isoformat()
    um = lambda sql, *params: conn.execute(sql, params).fetchone()  # noqa: E731

    ultimo = um(
        """SELECT a.id, a.titulo, a.criado_em,
                  NOT EXISTS (SELECT 1 FROM avisos_lidos l WHERE l.aviso_id = a.id AND l.usuario_id = ?) AS novo
           FROM avisos a WHERE a.condominio_id = ? ORDER BY a.id DESC LIMIT 1""",
        uid, cid,
    )
    resposta = {
        "hoje": dia,
        "avisos_nao_lidos": um(
            """SELECT COUNT(*) FROM avisos a WHERE a.condominio_id = ?
               AND NOT EXISTS (SELECT 1 FROM avisos_lidos l WHERE l.aviso_id = a.id AND l.usuario_id = ?)""",
            cid, uid,
        )[0],
        "ultimo_aviso": {**dict(ultimo), "novo": bool(ultimo["novo"])} if ultimo else None,
        "proxima_reserva": None,
        "visitas_hoje": 0,
        "ocorrencias_abertas": 0,
    }
    if unidade is not None:
        proxima = um(
            """SELECT r.data, r.status, a.nome AS area FROM reservas r JOIN areas a ON a.id = r.area_id
               WHERE r.unidade_id = ? AND r.data >= ? ORDER BY r.data LIMIT 1""",
            unidade, dia,
        )
        resposta["proxima_reserva"] = dict(proxima) if proxima else None
        resposta["visitas_hoje"] = um(
            """SELECT COUNT(*) FROM visitas WHERE unidade_id = ? AND cancelada = 0
               AND data_inicio <= ? AND data_fim >= ?""",
            unidade, dia, dia,
        )[0]

    if membro["papel"] == "sindico":
        resposta["ocorrencias_abertas"] = um(
            "SELECT COUNT(*) FROM ocorrencias WHERE condominio_id = ? AND status <> 'resolvida'", cid
        )[0]
        resposta["pendencias"] = {
            "pedidos_entrada": um("SELECT COUNT(*) FROM membros WHERE condominio_id = ? AND status = 'pendente'", cid)[0],
            "reservas": um(
                """SELECT COUNT(*) FROM reservas r JOIN areas a ON a.id = r.area_id
                   WHERE a.condominio_id = ? AND r.status = 'pendente' AND r.data >= ?""",
                cid, dia,
            )[0],
        }
    else:
        resposta["ocorrencias_abertas"] = um(
            """SELECT COUNT(*) FROM ocorrencias WHERE condominio_id = ? AND status <> 'resolvida'
               AND (autor_id = ? OR (unidade_id IS NOT NULL AND unidade_id = ?))""",
            cid, uid, unidade,
        )[0]

    if membro["papel"] in ("sindico", "portaria"):
        resposta["portaria"] = {
            "esperados": um(
                """SELECT COUNT(*) FROM visitas WHERE condominio_id = ? AND cancelada = 0
                   AND data_inicio <= ? AND data_fim >= ?""",
                cid, dia, dia,
            )[0],
            "entradas": um(
                """SELECT COUNT(*) FROM visita_entradas e JOIN visitas v ON v.id = e.visita_id
                   WHERE v.condominio_id = ? AND e.criado_em >= datetime('now', '-24 hours')""",
                cid,
            )[0],
        }
    return resposta
