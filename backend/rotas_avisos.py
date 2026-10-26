"""Mural de avisos."""
from . import historico
from .comum import booleano, exigir_membro, texto
from .web import ErroHTTP, rota


def _campos_aviso(corpo):
    titulo = texto(corpo, "titulo", "Título", maximo=120)
    mensagem = texto(corpo, "corpo", "Mensagem", maximo=5000)
    return titulo, mensagem, booleano(corpo, "fixado", "Fixado")


def _aviso_do_condominio(conn, cid, aid):
    aviso = conn.execute(
        """SELECT a.id, a.titulo, a.corpo, a.fixado, a.criado_em, a.editado_em, u.nome AS autor
           FROM avisos a LEFT JOIN usuarios u ON u.id = a.autor_id
           WHERE a.id = ? AND a.condominio_id = ?""",
        (aid, cid),
    ).fetchone()
    if aviso is None:
        raise ErroHTTP(404, "Aviso não encontrado.")
    return aviso


@rota("GET", "/api/condominios/{cid:int}/avisos")
def listar_avisos(req, cid):
    membro = exigir_membro(req, cid)
    sindico = membro["papel"] == "sindico"
    linhas = req.conn.execute(
        """
        SELECT a.id, a.titulo, a.corpo, a.fixado, a.criado_em, a.editado_em, u.nome AS autor,
               EXISTS (SELECT 1 FROM avisos_lidos l WHERE l.aviso_id = a.id AND l.usuario_id = ?) AS lido,
               (SELECT COUNT(*) FROM avisos_lidos l
                JOIN membros m ON m.usuario_id = l.usuario_id
                                AND m.condominio_id = a.condominio_id AND m.status = 'ativo'
                WHERE l.aviso_id = a.id) AS leituras
        FROM avisos a LEFT JOIN usuarios u ON u.id = a.autor_id
        WHERE a.condominio_id = ?
        ORDER BY a.fixado DESC, a.id DESC
        LIMIT 200
        """,
        (req.usuario["id"], cid),
    ).fetchall()
    avisos = []
    for linha in linhas:
        aviso = dict(linha)
        aviso["fixado"] = bool(aviso["fixado"])
        aviso["lido"] = bool(aviso["lido"])
        if not sindico:
            del aviso["leituras"]
        avisos.append(aviso)
    resposta = {"avisos": avisos}
    if sindico:
        resposta["total_moradores"] = req.conn.execute(
            "SELECT COUNT(*) FROM membros WHERE condominio_id = ? AND status = 'ativo'", (cid,)
        ).fetchone()[0]
    return resposta


@rota("GET", "/api/condominios/{cid:int}/avisos/resumo")
def resumo_avisos(req, cid):
    """Usado pelo app para atualizar o contador e disparar notificações."""
    exigir_membro(req, cid)
    nao_lidos = req.conn.execute(
        """SELECT a.id, a.titulo FROM avisos a
           WHERE a.condominio_id = ?
             AND NOT EXISTS (SELECT 1 FROM avisos_lidos l WHERE l.aviso_id = a.id AND l.usuario_id = ?)
           ORDER BY a.id DESC""",
        (cid, req.usuario["id"]),
    ).fetchall()
    ultimo = {"id": nao_lidos[0]["id"], "titulo": nao_lidos[0]["titulo"]} if nao_lidos else None
    return {"nao_lidos": len(nao_lidos), "ultimo": ultimo}


@rota("GET", "/api/condominios/{cid:int}/avisos/{aid:int}")
def ver_aviso(req, cid, aid):
    exigir_membro(req, cid)
    aviso = dict(_aviso_do_condominio(req.conn, cid, aid))
    aviso["fixado"] = bool(aviso["fixado"])
    return {"aviso": aviso}


@rota("POST", "/api/condominios/{cid:int}/avisos")
def publicar_aviso(req, cid):
    exigir_membro(req, cid, sindico=True)
    titulo, mensagem, fixado = _campos_aviso(req.corpo)
    aviso_id = req.conn.execute(
        "INSERT INTO avisos (condominio_id, autor_id, titulo, corpo, fixado) VALUES (?, ?, ?, ?, ?)",
        (cid, req.usuario["id"], titulo, mensagem, int(fixado)),
    ).lastrowid
    req.conn.execute("INSERT INTO avisos_lidos (aviso_id, usuario_id) VALUES (?, ?)", (aviso_id, req.usuario["id"]))
    return 201, {"id": aviso_id}


@rota("PATCH", "/api/condominios/{cid:int}/avisos/{aid:int}")
def editar_aviso(req, cid, aid):
    exigir_membro(req, cid, sindico=True)
    _aviso_do_condominio(req.conn, cid, aid)
    titulo, mensagem, fixado = _campos_aviso(req.corpo)
    req.conn.execute(
        "UPDATE avisos SET titulo = ?, corpo = ?, fixado = ?, editado_em = datetime('now') WHERE id = ?",
        (titulo, mensagem, int(fixado), aid),
    )
    return {"ok": True}


@rota("DELETE", "/api/condominios/{cid:int}/avisos/{aid:int}")
def excluir_aviso(req, cid, aid):
    exigir_membro(req, cid, sindico=True)
    aviso = _aviso_do_condominio(req.conn, cid, aid)
    req.conn.execute("DELETE FROM avisos WHERE id = ?", (aid,))
    historico.anotar(req, cid, f'Excluiu o aviso "{aviso["titulo"]}"')
    return {"ok": True}


@rota("POST", "/api/condominios/{cid:int}/avisos/lidos")
def marcar_todos_lidos(req, cid):
    exigir_membro(req, cid)
    req.conn.execute(
        """INSERT OR IGNORE INTO avisos_lidos (aviso_id, usuario_id)
           SELECT id, ? FROM avisos WHERE condominio_id = ?""",
        (req.usuario["id"], cid),
    )
    return {"ok": True}
