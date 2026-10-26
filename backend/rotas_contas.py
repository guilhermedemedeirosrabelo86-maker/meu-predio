"""Prestação de contas: o síndico lança entradas e saídas; síndico e moradores acompanham."""
import re
import secrets
from datetime import date

from . import db, historico
from .comum import data_iso, exigir_membro, hoje, inteiro, texto
from .rotas_ocorrencias import _tipo_imagem
from .web import Arquivo, ErroHTTP, rota

CATEGORIAS = {
    "receita": ("taxa", "multa", "aluguel", "receita_outra"),
    "despesa": ("agua", "energia", "limpeza", "manutencao", "seguranca", "administrativo", "obras", "despesa_outra"),
}
MES_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
MESES_HISTORICO = 6
VALOR_MAXIMO = 100_000_000_00  # R$ 100 milhões, em centavos
PODEM_VER = ("sindico", "morador")  # a portaria não vê as finanças


def _somar_meses(mes, meses):
    ano, m = map(int, mes.split("-"))
    total = ano * 12 + (m - 1) + meses
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _lancamento(req, cid, lid):
    linha = req.conn.execute(
        "SELECT * FROM lancamentos WHERE id = ? AND condominio_id = ?", (lid, cid)
    ).fetchone()
    if linha is None:
        raise ErroHTTP(404, "Lançamento não encontrado.")
    return linha


def _publico(linha):
    return {
        "id": linha["id"],
        "tipo": linha["tipo"],
        "categoria": linha["categoria"],
        "descricao": linha["descricao"],
        "valor_centavos": linha["valor_centavos"],
        "data": linha["data"],
        "comprovante": linha["comprovante"] is not None,
        "autor": linha["autor"] if "autor" in linha.keys() else None,
        "criado_em": linha["criado_em"],
    }


def _validar(corpo):
    tipo = corpo.get("tipo")
    if tipo not in CATEGORIAS:
        raise ErroHTTP(400, "Escolha se é entrada ou saída.")
    categoria = corpo.get("categoria")
    if categoria not in CATEGORIAS[tipo]:
        raise ErroHTTP(400, "Escolha uma categoria.")
    descricao = texto(corpo, "descricao", "Descrição", maximo=120)
    valor = inteiro(corpo, "valor_centavos", "Valor", minimo=1, maximo=VALOR_MAXIMO)
    dia = data_iso(corpo.get("data"))
    if not date(2000, 1, 1) <= dia <= date(hoje().year + 1, 12, 31):
        raise ErroHTTP(400, "Escolha uma data válida.")
    return tipo, categoria, descricao, valor, dia.isoformat()


@rota("GET", "/api/condominios/{cid:int}/contas")
def resumo_do_mes(req, cid):
    """Resumo, despesas por categoria, lançamentos e histórico de um mês: ?mes=2026-10"""
    exigir_membro(req, cid, papeis=PODEM_VER)
    mes = req.query.get("mes") or hoje().isoformat()[:7]
    if not MES_RE.match(mes):
        raise ErroHTTP(400, "Mês inválido.")
    conn = req.conn

    def totais(filtro, params):
        linha = conn.execute(
            f"""SELECT COALESCE(SUM(CASE WHEN tipo = 'receita' THEN valor_centavos END), 0) AS entradas,
                       COALESCE(SUM(CASE WHEN tipo = 'despesa' THEN valor_centavos END), 0) AS saidas
                FROM lancamentos WHERE condominio_id = ? AND {filtro}""",
            (cid, *params),
        ).fetchone()
        return linha["entradas"], linha["saidas"]

    entradas, saidas = totais("data LIKE ?", (f"{mes}-%",))
    # Saldo em caixa ao fim do mês: tudo o que entrou menos tudo o que saiu até lá.
    proximo = _somar_meses(mes, 1)
    caixa_entradas, caixa_saidas = totais("data < ?", (f"{proximo}-01",))

    categorias = conn.execute(
        """SELECT categoria, SUM(valor_centavos) AS total FROM lancamentos
           WHERE condominio_id = ? AND tipo = 'despesa' AND data LIKE ?
           GROUP BY categoria ORDER BY total DESC""",
        (cid, f"{mes}-%"),
    ).fetchall()
    lancamentos = conn.execute(
        """SELECT l.*, u.nome AS autor FROM lancamentos l LEFT JOIN usuarios u ON u.id = l.autor_id
           WHERE l.condominio_id = ? AND l.data LIKE ? ORDER BY l.data DESC, l.id DESC""",
        (cid, f"{mes}-%"),
    ).fetchall()

    historico = []
    for passo in range(-(MESES_HISTORICO - 1), 1):
        outro = _somar_meses(mes, passo)
        e, s = totais("data LIKE ?", (f"{outro}-%",))
        historico.append({"mes": outro, "entradas": e, "saidas": s})

    return {
        "mes": mes,
        "hoje": hoje().isoformat(),
        "resumo": {"entradas": entradas, "saidas": saidas, "saldo_caixa": caixa_entradas - caixa_saidas},
        "categorias": [dict(c) for c in categorias],
        "lancamentos": [_publico(l) for l in lancamentos],
        "historico": historico,
    }


@rota("POST", "/api/condominios/{cid:int}/contas")
def lancar(req, cid):
    exigir_membro(req, cid, sindico=True)
    tipo, categoria, descricao, valor, dia = _validar(req.corpo)
    cursor = req.conn.execute(
        """INSERT INTO lancamentos (condominio_id, tipo, categoria, descricao, valor_centavos, data, autor_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (cid, tipo, categoria, descricao, valor, dia, req.usuario["id"]),
    )
    historico.anotar(req, cid, f'Lançou {_nome_tipo(tipo)} "{descricao}" de {historico.reais(valor)} em {historico.data_br(dia)}')
    return 201, {"id": cursor.lastrowid}


@rota("GET", "/api/condominios/{cid:int}/contas/{lid:int}")
def ver_lancamento(req, cid, lid):
    exigir_membro(req, cid, papeis=PODEM_VER)
    linha = req.conn.execute(
        """SELECT l.*, u.nome AS autor FROM lancamentos l LEFT JOIN usuarios u ON u.id = l.autor_id
           WHERE l.id = ? AND l.condominio_id = ?""",
        (lid, cid),
    ).fetchone()
    if linha is None:
        raise ErroHTTP(404, "Lançamento não encontrado.")
    return {"lancamento": _publico(linha)}


@rota("PATCH", "/api/condominios/{cid:int}/contas/{lid:int}")
def editar_lancamento(req, cid, lid):
    exigir_membro(req, cid, sindico=True)
    antes = _lancamento(req, cid, lid)
    tipo, categoria, descricao, valor, dia = _validar(req.corpo)
    req.conn.execute(
        """UPDATE lancamentos SET tipo = ?, categoria = ?, descricao = ?, valor_centavos = ?, data = ?
           WHERE id = ?""",
        (tipo, categoria, descricao, valor, dia, lid),
    )
    historico.anotar(req, cid, f'Editou o lançamento "{antes["descricao"]}": era {_resumo(antes)}, ficou '
                               f'{_resumo({"tipo": tipo, "descricao": descricao, "valor_centavos": valor, "data": dia})}')
    return {"ok": True}


def _nome_tipo(tipo):
    return "a receita" if tipo == "receita" else "a despesa"


def _resumo(lancamento):
    """"Conta de luz" (despesa de R$ 312,40 em 05/10/2026)"""
    return (f'"{lancamento["descricao"]}" ({lancamento["tipo"]} de {historico.reais(lancamento["valor_centavos"])} '
            f'em {historico.data_br(lancamento["data"])})')


def _apagar_arquivo(req, nome):
    if nome:
        db.apagar_arquivo(req.conn, f"contas/{nome}")


@rota("DELETE", "/api/condominios/{cid:int}/contas/{lid:int}")
def excluir_lancamento(req, cid, lid):
    exigir_membro(req, cid, sindico=True)
    linha = _lancamento(req, cid, lid)
    req.conn.execute("DELETE FROM lancamentos WHERE id = ?", (lid,))
    _apagar_arquivo(req, linha["comprovante"])
    historico.anotar(req, cid, f'Excluiu o lançamento {_resumo(linha)}')
    return {"ok": True}


@rota("POST", "/api/condominios/{cid:int}/contas/{lid:int}/comprovante")
def anexar_comprovante(req, cid, lid):
    """Foto da nota ou do recibo. Enviar outra substitui a anterior."""
    exigir_membro(req, cid, sindico=True)
    linha = _lancamento(req, cid, lid)
    if not req.bruto:
        raise ErroHTTP(400, "Envie a foto do comprovante.")
    tipo, extensao = _tipo_imagem(req.bruto)
    nome = secrets.token_hex(16) + extensao
    db.salvar_arquivo(req.conn, f"contas/{nome}", req.bruto)
    req.conn.execute(
        "UPDATE lancamentos SET comprovante = ?, comprovante_tipo = ? WHERE id = ?", (nome, tipo, lid)
    )
    _apagar_arquivo(req, linha["comprovante"])
    acao = "Trocou o comprovante" if linha["comprovante"] else "Anexou comprovante"
    historico.anotar(req, cid, f'{acao} do lançamento {_resumo(linha)}')
    return 201, {"ok": True}


@rota("DELETE", "/api/condominios/{cid:int}/contas/{lid:int}/comprovante")
def remover_comprovante(req, cid, lid):
    exigir_membro(req, cid, sindico=True)
    linha = _lancamento(req, cid, lid)
    req.conn.execute("UPDATE lancamentos SET comprovante = NULL, comprovante_tipo = NULL WHERE id = ?", (lid,))
    _apagar_arquivo(req, linha["comprovante"])
    historico.anotar(req, cid, f'Removeu o comprovante do lançamento {_resumo(linha)}')
    return {"ok": True}


@rota("GET", "/api/condominios/{cid:int}/contas/{lid:int}/comprovante")
def ver_comprovante(req, cid, lid):
    exigir_membro(req, cid, papeis=PODEM_VER)
    linha = _lancamento(req, cid, lid)
    conteudo = db.ler_arquivo(req.conn, f"contas/{linha['comprovante']}") if linha["comprovante"] else None
    if conteudo is None:
        raise ErroHTTP(404, "Comprovante não encontrado.")
    return Arquivo(conteudo, linha["comprovante_tipo"])
