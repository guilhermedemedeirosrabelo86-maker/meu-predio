"""Resumo para a tela inicial: um número por módulo, numa única chamada."""
from .comum import exigir_membro, hoje
from .rotas_enquetes import sem_voto
from .rotas_taxas import situacao_da_unidade, unidades_atrasadas
from .web import rota

# Ninguém é avisado do que fez: o que a própria pessoa registrou não entra nas contagens.
NAO_REGISTREI = "registrado_por IS NOT ?"


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
        "taxa": None,
        "encomendas": 0,
        "enquetes_sem_voto": 0,
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
        resposta["encomendas"] = um(
            f"SELECT COUNT(*) FROM encomendas WHERE unidade_id = ? AND retirada_em IS NULL AND {NAO_REGISTREI}",
            unidade, uid,
        )[0]
        if membro["papel"] in ("sindico", "morador"):
            resposta["enquetes_sem_voto"] = sem_voto(conn, cid, unidade, dia, uid)
            resposta["taxa"] = situacao_da_unidade(conn, cid, unidade, hoje())

    if membro["papel"] in ("sindico", "morador"):
        # Caixa do condomínio e o movimento do mês, os mesmos números da prestação de contas.
        mes = dia[:7]
        caixa = um(
            """SELECT COALESCE(SUM(CASE WHEN tipo = 'receita' THEN valor_centavos ELSE -valor_centavos END), 0) AS saldo,
                      COALESCE(SUM(CASE WHEN tipo = 'receita' AND data LIKE ? THEN valor_centavos END), 0) AS entradas,
                      COALESCE(SUM(CASE WHEN tipo = 'despesa' AND data LIKE ? THEN valor_centavos END), 0) AS saidas
               FROM lancamentos WHERE condominio_id = ? AND data <= ?""",
            f"{mes}-%", f"{mes}-%", cid, f"{mes}-31",
        )
        resposta["caixa"] = dict(caixa)

    if membro["papel"] == "sindico":
        resposta["ocorrencias_abertas"] = um(
            "SELECT COUNT(*) FROM ocorrencias WHERE condominio_id = ? AND status <> 'resolvida' AND autor_id IS NOT ?",
            cid, uid,
        )[0]
        resposta["pendencias"] = {
            "pedidos_entrada": um("SELECT COUNT(*) FROM membros WHERE condominio_id = ? AND status = 'pendente'", cid)[0],
            "reservas": um(
                """SELECT COUNT(*) FROM reservas r JOIN areas a ON a.id = r.area_id
                   WHERE a.condominio_id = ? AND r.status = 'pendente' AND r.data >= ? AND r.usuario_id IS NOT ?""",
                cid, dia, uid,
            )[0],
            "taxas_atrasadas": unidades_atrasadas(conn, cid, hoje()),
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
            "encomendas": um(
                f"SELECT COUNT(*) FROM encomendas WHERE condominio_id = ? AND retirada_em IS NULL AND {NAO_REGISTREI}",
                cid, uid,
            )[0],
        }
    return resposta


@rota("GET", "/api/condominios/{cid:int}/contadores")
def contadores(req, cid):
    """Números das abas do menu (o que pede atenção), consultados pelo app a cada poucos segundos.
    Só contagens leves; o último aviso não lido vai junto para a notificação do celular."""
    membro = exigir_membro(req, cid)
    conn, uid, unidade, papel = req.conn, req.usuario["id"], membro["unidade_id"], membro["papel"]
    dia = hoje().isoformat()
    um = lambda sql, *params: conn.execute(sql, params).fetchone()  # noqa: E731

    ultimo = um(
        """SELECT a.id, a.titulo FROM avisos a WHERE a.condominio_id = ?
             AND NOT EXISTS (SELECT 1 FROM avisos_lidos l WHERE l.aviso_id = a.id AND l.usuario_id = ?)
           ORDER BY a.id DESC LIMIT 1""",
        cid, uid,
    )
    abas = {
        "avisos": um(
            """SELECT COUNT(*) FROM avisos a WHERE a.condominio_id = ?
               AND NOT EXISTS (SELECT 1 FROM avisos_lidos l WHERE l.aviso_id = a.id AND l.usuario_id = ?)""",
            cid, uid,
        )[0],
    }
    if papel == "portaria":
        abas["encomendas"] = um(
            f"SELECT COUNT(*) FROM encomendas WHERE condominio_id = ? AND retirada_em IS NULL AND {NAO_REGISTREI}", cid, uid
        )[0]
    elif unidade is not None:
        abas["encomendas"] = um(
            f"SELECT COUNT(*) FROM encomendas WHERE unidade_id = ? AND retirada_em IS NULL AND {NAO_REGISTREI}", unidade, uid
        )[0]
    if papel in ("sindico", "morador") and unidade is not None:
        abas["enquetes"] = sem_voto(conn, cid, unidade, dia, uid)
    if papel == "sindico":
        abas["moradores"] = um("SELECT COUNT(*) FROM membros WHERE condominio_id = ? AND status = 'pendente'", cid)[0]
        abas["reservas"] = um(
            """SELECT COUNT(*) FROM reservas r JOIN areas a ON a.id = r.area_id
               WHERE a.condominio_id = ? AND r.status = 'pendente' AND r.data >= ? AND r.usuario_id IS NOT ?""",
            cid, dia, uid,
        )[0]
        abas["ocorrencias"] = um(
            "SELECT COUNT(*) FROM ocorrencias WHERE condominio_id = ? AND status = 'aberta' AND autor_id IS NOT ?", cid, uid
        )[0]
        abas["contas"] = unidades_atrasadas(conn, cid, hoje())
    elif papel == "morador" and unidade is not None:
        taxa = situacao_da_unidade(conn, cid, unidade, hoje())
        abas["contas"] = 1 if taxa and (taxa["situacao"] == "atrasada" or taxa.get("meses_atrasados")) else 0
    return {"abas": abas, "ultimo_aviso": dict(ultimo) if ultimo else None}
