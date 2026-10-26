"""Histórico do condomínio: quem mexeu no dinheiro, nos moradores ou apagou algo, e quando.

Guarda o nome de quem fez e um texto pronto, para continuar legível mesmo depois que a pessoa,
o lançamento ou a unidade deixarem de existir. Ninguém edita nem apaga o histórico pelo app.
"""
from .comum import exigir_membro
from .web import rota

POR_PAGINA = 50


def anotar(req, cid, texto):
    req.conn.execute(
        "INSERT INTO historico (condominio_id, usuario_id, autor, texto) VALUES (?, ?, ?, ?)",
        (cid, req.usuario["id"], req.usuario["nome"], texto),
    )


def reais(centavos):
    """31240 -> R$ 312,40"""
    inteiro, resto = divmod(centavos, 100)
    return f"R$ {inteiro:,}".replace(",", ".") + f",{resto:02d}"


def data_br(iso):
    """2026-10-05 -> 05/10/2026"""
    ano, mes, dia = iso[:10].split("-")
    return f"{dia}/{mes}/{ano}"


@rota("GET", "/api/condominios/{cid:int}/historico")
def listar(req, cid):
    """Mais recentes primeiro, de 50 em 50: ?antes=<id> traz a página seguinte."""
    exigir_membro(req, cid, sindico=True)
    antes = req.query.get("antes", "")
    filtro, params = ("AND id < ?", (cid, int(antes))) if antes.isdigit() else ("", (cid,))
    linhas = req.conn.execute(
        f"SELECT id, autor, texto, criado_em FROM historico WHERE condominio_id = ? {filtro} "
        f"ORDER BY id DESC LIMIT {POR_PAGINA + 1}",
        params,
    ).fetchall()
    return {"itens": [dict(l) for l in linhas[:POR_PAGINA]], "tem_mais": len(linhas) > POR_PAGINA}
