"""Taxa condominial: o síndico marca quem pagou em cada mês e cada morador acompanha a própria unidade.

Marcar como paga cria a entrada na prestação de contas; desfazer apaga a entrada (e vice-versa).
"""
import sqlite3

from .comum import data_iso, exigir_membro, hoje, inteiro, ordem_natural, unidade_do_condominio
from .rotas_contas import MES_RE, VALOR_MAXIMO, _somar_meses
from .web import ErroHTTP, rota

MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro")
MESES_HISTORICO = 6
MESES_ATRASO = 12  # quantos meses para trás contam como atraso no painel do síndico


def _mes_curto(mes):
    """2026-10 -> out/2026"""
    ano, m = mes.split("-")
    return f"{MESES[int(m) - 1][:3]}/{ano}"


def _config(conn, cid):
    linha = conn.execute(
        "SELECT taxa_centavos, taxa_vencimento, substr(criado_em, 1, 7) AS inicio FROM condominios WHERE id = ?",
        (cid,),
    ).fetchone()
    return {"valor_centavos": linha["taxa_centavos"], "vencimento": linha["taxa_vencimento"], "inicio": linha["inicio"]}


def situacao(mes, pago, config, dia):
    """paga | pendente (ainda no prazo) | atrasada. Meses antes do condomínio entrar no app não atrasam."""
    if pago:
        return "paga"
    atual = dia.isoformat()[:7]
    if mes < config["inicio"]:
        return "pendente"
    if mes < atual or (mes == atual and dia.day > config["vencimento"]):
        return "atrasada"
    return "pendente"


def _pagamentos(conn, cid, meses):
    """{(unidade_id, mes): pagamento} dos meses pedidos."""
    marcas = ",".join("?" * len(meses))
    linhas = conn.execute(
        f"""SELECT p.id, p.unidade_id, p.mes, l.valor_centavos, l.data AS pago_em
            FROM pagamentos p JOIN lancamentos l ON l.id = p.lancamento_id
            WHERE l.condominio_id = ? AND p.mes IN ({marcas})""",
        (cid, *meses),
    ).fetchall()
    return {(p["unidade_id"], p["mes"]): {"id": p["id"], "valor_centavos": p["valor_centavos"], "pago_em": p["pago_em"]}
            for p in linhas}


def unidades_atrasadas(conn, cid, dia):
    """Quantas unidades têm ao menos um mês em atraso (painel do síndico). Sem valor definido, não cobra."""
    config = _config(conn, cid)
    if not config["valor_centavos"]:
        return 0
    atual = dia.isoformat()[:7]
    meses = [m for m in (_somar_meses(atual, -i) for i in range(MESES_ATRASO)) if m >= config["inicio"]]
    if not meses:
        return 0
    pagos = _pagamentos(conn, cid, meses)
    unidades = conn.execute("SELECT id FROM unidades WHERE condominio_id = ?", (cid,)).fetchall()
    return sum(
        any(situacao(m, (u["id"], m) in pagos, config, dia) == "atrasada" for m in meses) for u in unidades
    )


def situacao_da_unidade(conn, cid, unidade_id, dia):
    """Mês atual e meses em atraso de uma unidade (painel do morador)."""
    config = _config(conn, cid)
    if not config["valor_centavos"] or unidade_id is None:
        return None
    atual = dia.isoformat()[:7]
    meses = [m for m in (_somar_meses(atual, -i) for i in range(MESES_ATRASO)) if m >= config["inicio"]]
    pagos = _pagamentos(conn, cid, meses) if meses else {}
    estados = {m: situacao(m, (unidade_id, m) in pagos, config, dia) for m in meses}
    return {
        "mes": atual,
        "situacao": estados.get(atual, "pendente"),
        "meses_atrasados": sum(1 for e in estados.values() if e == "atrasada"),
        "vencimento": config["vencimento"],
        "valor_centavos": config["valor_centavos"],
    }


@rota("GET", "/api/condominios/{cid:int}/taxas")
def taxas_do_mes(req, cid):
    """Síndico: situação de todas as unidades num mês (?mes=2026-10)."""
    exigir_membro(req, cid, sindico=True)
    dia = hoje()
    mes = req.query.get("mes") or dia.isoformat()[:7]
    if not MES_RE.match(mes):
        raise ErroHTTP(400, "Mês inválido.")
    config = _config(req.conn, cid)
    pagos = _pagamentos(req.conn, cid, [mes])
    unidades = req.conn.execute(
        """SELECT un.id, un.identificador,
                  (SELECT GROUP_CONCAT(u.nome, ', ') FROM membros m JOIN usuarios u ON u.id = m.usuario_id
                   WHERE m.unidade_id = un.id AND m.status = 'ativo') AS moradores
           FROM unidades un WHERE un.condominio_id = ?""",
        (cid,),
    ).fetchall()
    lista = []
    for u in sorted(unidades, key=lambda u: ordem_natural(u["identificador"])):
        pagamento = pagos.get((u["id"], mes))
        lista.append({
            "id": u["id"],
            "unidade": u["identificador"],
            "moradores": u["moradores"] or "",
            "pagamento": pagamento,
            "situacao": situacao(mes, pagamento is not None, config, dia),
        })
    return {
        "mes": mes,
        "hoje": dia.isoformat(),
        "config": config,
        "unidades": lista,
        "totais": {
            "unidades": len(lista),
            "pagas": sum(1 for u in lista if u["pagamento"]),
            "atrasadas": sum(1 for u in lista if u["situacao"] == "atrasada"),
            "recebido": sum(u["pagamento"]["valor_centavos"] for u in lista if u["pagamento"]),
        },
    }


@rota("GET", "/api/condominios/{cid:int}/taxas/minha")
def minha_taxa(req, cid):
    """Morador (ou síndico com unidade): a própria unidade nos últimos meses."""
    membro = exigir_membro(req, cid, papeis=("sindico", "morador"))
    dia = hoje()
    config = _config(req.conn, cid)
    resposta = {"hoje": dia.isoformat(), "config": config, "unidade": None, "meses": []}
    if membro["unidade_id"] is None:
        return resposta
    unidade = unidade_do_condominio(req.conn, cid, membro["unidade_id"])
    atual = dia.isoformat()[:7]
    meses = [m for m in (_somar_meses(atual, -i) for i in range(MESES_HISTORICO)) if m >= config["inicio"]]
    pagos = _pagamentos(req.conn, cid, meses) if meses else {}
    resposta["unidade"] = unidade["identificador"]
    resposta["meses"] = [
        {"mes": m, "pagamento": pagos.get((unidade["id"], m)),
         "situacao": situacao(m, (unidade["id"], m) in pagos, config, dia)}
        for m in meses
    ]
    return resposta


@rota("PATCH", "/api/condominios/{cid:int}/taxas/config")
def configurar(req, cid):
    exigir_membro(req, cid, sindico=True)
    valor = inteiro(req.corpo, "valor_centavos", "Valor da taxa", minimo=1, maximo=VALOR_MAXIMO)
    vencimento = inteiro(req.corpo, "vencimento", "Dia do vencimento", minimo=1, maximo=28)
    req.conn.execute(
        "UPDATE condominios SET taxa_centavos = ?, taxa_vencimento = ? WHERE id = ?", (valor, vencimento, cid)
    )
    return {"ok": True}


@rota("POST", "/api/condominios/{cid:int}/taxas/pagamentos")
def registrar_pagamento(req, cid):
    """Marca a taxa de uma unidade como paga e lança a entrada na prestação de contas."""
    exigir_membro(req, cid, sindico=True)
    unidade_id = req.corpo.get("unidade_id")
    if not isinstance(unidade_id, int) or isinstance(unidade_id, bool):
        raise ErroHTTP(400, "Escolha uma unidade da lista.")
    unidade = unidade_do_condominio(req.conn, cid, unidade_id)
    mes = req.corpo.get("mes")
    if not isinstance(mes, str) or not MES_RE.match(mes):
        raise ErroHTTP(400, "Mês inválido.")
    if mes > _somar_meses(hoje().isoformat()[:7], 1):
        raise ErroHTTP(400, "Dá para registrar no máximo a taxa do mês que vem.")
    valor = inteiro(req.corpo, "valor_centavos", "Valor", minimo=1, maximo=VALOR_MAXIMO)
    pago_em = data_iso(req.corpo.get("pago_em"), "Data do pagamento")
    if pago_em > hoje():
        raise ErroHTTP(400, "A data do pagamento não pode ser no futuro.")
    if req.conn.execute("SELECT 1 FROM pagamentos WHERE unidade_id = ? AND mes = ?", (unidade_id, mes)).fetchone():
        raise ErroHTTP(409, "Esta unidade já está com a taxa paga neste mês.")
    lancamento = req.conn.execute(
        """INSERT INTO lancamentos (condominio_id, tipo, categoria, descricao, valor_centavos, data, autor_id)
           VALUES (?, 'receita', 'taxa', ?, ?, ?, ?)""",
        (cid, f"Taxa {_mes_curto(mes)} · unidade {unidade['identificador']}", valor, pago_em.isoformat(),
         req.usuario["id"]),
    ).lastrowid
    try:
        cursor = req.conn.execute(
            "INSERT INTO pagamentos (unidade_id, mes, lancamento_id) VALUES (?, ?, ?)", (unidade_id, mes, lancamento)
        )
    except sqlite3.IntegrityError:  # dois cliques ao mesmo tempo; o erro desfaz também o lançamento
        raise ErroHTTP(409, "Esta unidade já está com a taxa paga neste mês.")
    return 201, {"id": cursor.lastrowid, "lancamento_id": lancamento}


@rota("DELETE", "/api/condominios/{cid:int}/taxas/pagamentos/{pid:int}")
def desfazer_pagamento(req, cid, pid):
    """Desmarca o pagamento; a entrada correspondente sai da prestação de contas."""
    exigir_membro(req, cid, sindico=True)
    pagamento = req.conn.execute(
        """SELECT p.lancamento_id FROM pagamentos p JOIN lancamentos l ON l.id = p.lancamento_id
           WHERE p.id = ? AND l.condominio_id = ?""",
        (pid, cid),
    ).fetchone()
    if pagamento is None:
        raise ErroHTTP(404, "Pagamento não encontrado.")
    req.conn.execute("DELETE FROM lancamentos WHERE id = ?", (pagamento["lancamento_id"],))  # leva o pagamento junto
    return {"ok": True}
