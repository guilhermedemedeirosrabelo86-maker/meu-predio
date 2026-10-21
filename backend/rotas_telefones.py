"""Telefones úteis do prédio: o síndico mantém a lista e todos consultam."""
import re

from .comum import exigir_membro, texto
from .web import ErroHTTP, rota


def _campos(corpo):
    nome = texto(corpo, "nome", "Nome", maximo=80)
    descricao = texto(corpo, "descricao", "Função", obrigatorio=False, maximo=80)
    telefone = texto(corpo, "telefone", "Telefone", maximo=30)
    if len(re.sub(r"\D", "", telefone)) < 8:
        raise ErroHTTP(400, "Digite um telefone com DDD.")
    return nome, descricao, telefone


def _telefone(conn, cid, tid):
    linha = conn.execute("SELECT id FROM telefones WHERE id = ? AND condominio_id = ?", (tid, cid)).fetchone()
    if linha is None:
        raise ErroHTTP(404, "Contato não encontrado.")


@rota("GET", "/api/condominios/{cid:int}/telefones")
def listar_telefones(req, cid):
    exigir_membro(req, cid)
    linhas = req.conn.execute(
        "SELECT id, nome, descricao, telefone FROM telefones WHERE condominio_id = ? ORDER BY nome COLLATE NOCASE",
        (cid,),
    ).fetchall()
    return {"telefones": [dict(t) for t in linhas]}


@rota("POST", "/api/condominios/{cid:int}/telefones")
def adicionar_telefone(req, cid):
    exigir_membro(req, cid, sindico=True)
    tid = req.conn.execute(
        "INSERT INTO telefones (condominio_id, nome, descricao, telefone) VALUES (?, ?, ?, ?)", (cid, *_campos(req.corpo))
    ).lastrowid
    return 201, {"id": tid}


@rota("PATCH", "/api/condominios/{cid:int}/telefones/{tid:int}")
def editar_telefone(req, cid, tid):
    exigir_membro(req, cid, sindico=True)
    _telefone(req.conn, cid, tid)
    req.conn.execute("UPDATE telefones SET nome = ?, descricao = ?, telefone = ? WHERE id = ?", (*_campos(req.corpo), tid))
    return {"ok": True}


@rota("DELETE", "/api/condominios/{cid:int}/telefones/{tid:int}")
def excluir_telefone(req, cid, tid):
    exigir_membro(req, cid, sindico=True)
    _telefone(req.conn, cid, tid)
    req.conn.execute("DELETE FROM telefones WHERE id = ?", (tid,))
    return {"ok": True}
