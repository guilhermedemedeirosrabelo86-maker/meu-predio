"""Ocorrências (barulho, vazamento, garagem...) com fotos e conversa com o síndico."""
import secrets

from .comum import exigir_membro, texto
from .web import Arquivo, ErroHTTP, rota

CATEGORIAS = ("barulho", "vazamento", "garagem", "limpeza", "seguranca", "manutencao", "outro")
STATUS = ("aberta", "andamento", "resolvida")
MAX_FOTOS = 5
ASSINATURAS = (  # tipo real do arquivo pelos primeiros bytes, sem confiar no que o navegador declarou
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
)


def _tipo_imagem(conteudo):
    for assinatura, tipo, extensao in ASSINATURAS:
        if conteudo.startswith(assinatura):
            return tipo, extensao
    if conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return "image/webp", ".webp"
    raise ErroHTTP(415, "Envie uma foto em JPG, PNG ou WebP.")


def _visivel(req, cid, oid):
    """O síndico vê todas; os demais veem as da própria unidade ou as que abriram."""
    membro = exigir_membro(req, cid)
    ocorrencia = req.conn.execute(
        "SELECT * FROM ocorrencias WHERE id = ? AND condominio_id = ?", (oid, cid)
    ).fetchone()
    if ocorrencia is None or not _pode_ver(membro, ocorrencia, req.usuario["id"]):
        raise ErroHTTP(404, "Ocorrência não encontrada.")
    return membro, ocorrencia


def _pode_ver(membro, ocorrencia, usuario_id):
    if membro["papel"] == "sindico" or ocorrencia["autor_id"] == usuario_id:
        return True
    return membro["unidade_id"] is not None and ocorrencia["unidade_id"] == membro["unidade_id"]


@rota("GET", "/api/condominios/{cid:int}/ocorrencias")
def listar_ocorrencias(req, cid):
    membro = exigir_membro(req, cid)
    filtro, params = "", [cid]
    if membro["papel"] != "sindico":
        filtro = " AND (o.autor_id = ? OR (o.unidade_id IS NOT NULL AND o.unidade_id = ?))"
        params += [req.usuario["id"], membro["unidade_id"]]
    linhas = req.conn.execute(
        f"""
        SELECT o.id, o.categoria, o.titulo, o.local, o.status, o.criado_em, o.atualizado_em,
               un.identificador AS unidade, u.nome AS autor,
               (SELECT MIN(f.id) FROM ocorrencia_fotos f WHERE f.ocorrencia_id = o.id) AS foto_capa,
               (SELECT COUNT(*) FROM ocorrencia_fotos f WHERE f.ocorrencia_id = o.id) AS fotos,
               (SELECT COUNT(*) FROM ocorrencia_mensagens m WHERE m.ocorrencia_id = o.id) AS mensagens
        FROM ocorrencias o
        LEFT JOIN unidades un ON un.id = o.unidade_id
        LEFT JOIN usuarios u ON u.id = o.autor_id
        WHERE o.condominio_id = ?{filtro}
        ORDER BY o.status = 'resolvida', o.atualizado_em DESC, o.id DESC
        LIMIT 200
        """,
        params,
    ).fetchall()
    return {"ocorrencias": [dict(linha) for linha in linhas]}


@rota("POST", "/api/condominios/{cid:int}/ocorrencias")
def abrir_ocorrencia(req, cid):
    membro = exigir_membro(req, cid)
    categoria = req.corpo.get("categoria")
    if categoria not in CATEGORIAS:
        raise ErroHTTP(400, "Escolha uma categoria.")
    titulo = texto(req.corpo, "titulo", "Resumo", maximo=120)
    descricao = texto(req.corpo, "descricao", "Descrição", obrigatorio=False, maximo=3000)
    local = texto(req.corpo, "local", "Local", obrigatorio=False, maximo=80)
    cursor = req.conn.execute(
        """INSERT INTO ocorrencias (condominio_id, unidade_id, autor_id, categoria, titulo, descricao, local)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (cid, membro["unidade_id"], req.usuario["id"], categoria, titulo, descricao, local),
    )
    return 201, {"id": cursor.lastrowid}


@rota("GET", "/api/condominios/{cid:int}/ocorrencias/{oid:int}")
def ver_ocorrencia(req, cid, oid):
    membro, ocorrencia = _visivel(req, cid, oid)
    detalhe = req.conn.execute(
        """SELECT o.id, o.categoria, o.titulo, o.descricao, o.local, o.status, o.criado_em, o.atualizado_em,
                  o.autor_id, un.identificador AS unidade, u.nome AS autor
           FROM ocorrencias o
           LEFT JOIN unidades un ON un.id = o.unidade_id
           LEFT JOIN usuarios u ON u.id = o.autor_id
           WHERE o.id = ?""",
        (oid,),
    ).fetchone()
    fotos = req.conn.execute("SELECT id FROM ocorrencia_fotos WHERE ocorrencia_id = ? ORDER BY id", (oid,)).fetchall()
    mensagens = req.conn.execute(
        """SELECT m.id, m.texto, m.status_novo, m.criado_em, u.nome AS autor, m.autor_id,
                  COALESCE(mb.papel = 'sindico', 0) AS do_sindico
           FROM ocorrencia_mensagens m
           LEFT JOIN usuarios u ON u.id = m.autor_id
           LEFT JOIN membros mb ON mb.usuario_id = m.autor_id AND mb.condominio_id = ?
           WHERE m.ocorrencia_id = ? ORDER BY m.id""",
        (cid, oid),
    ).fetchall()
    resposta = dict(detalhe)
    resposta["fotos"] = [f["id"] for f in fotos]
    resposta["mensagens"] = [{**dict(m), "do_sindico": bool(m["do_sindico"])} for m in mensagens]
    return {"ocorrencia": resposta}


@rota("POST", "/api/condominios/{cid:int}/ocorrencias/{oid:int}/fotos")
def anexar_foto(req, cid, oid):
    _visivel(req, cid, oid)
    if not req.bruto:
        raise ErroHTTP(400, "Envie a foto.")
    tipo, extensao = _tipo_imagem(req.bruto)
    total = req.conn.execute("SELECT COUNT(*) FROM ocorrencia_fotos WHERE ocorrencia_id = ?", (oid,)).fetchone()[0]
    if total >= MAX_FOTOS:
        raise ErroHTTP(400, f"Cada ocorrência aceita até {MAX_FOTOS} fotos.")
    nome = secrets.token_hex(16) + extensao
    cursor = req.conn.execute(
        "INSERT INTO ocorrencia_fotos (ocorrencia_id, arquivo, tipo) VALUES (?, ?, ?)", (oid, nome, tipo)
    )
    pasta = req.pasta_arquivos / "ocorrencias"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / nome).write_bytes(req.bruto)
    return 201, {"id": cursor.lastrowid}


@rota("GET", "/api/condominios/{cid:int}/ocorrencias/fotos/{fid:int}")
def ver_foto(req, cid, fid):
    foto = req.conn.execute("SELECT * FROM ocorrencia_fotos WHERE id = ?", (fid,)).fetchone()
    if foto is None:
        raise ErroHTTP(404, "Foto não encontrada.")
    _visivel(req, cid, foto["ocorrencia_id"])
    caminho = req.pasta_arquivos / "ocorrencias" / foto["arquivo"]
    if not caminho.is_file():
        raise ErroHTTP(404, "Foto não encontrada.")
    return Arquivo(caminho.read_bytes(), foto["tipo"])


@rota("POST", "/api/condominios/{cid:int}/ocorrencias/{oid:int}/mensagens")
def responder(req, cid, oid):
    """Comentário de quem abriu ou do síndico. Só o síndico muda o status."""
    membro, ocorrencia = _visivel(req, cid, oid)
    mensagem = texto(req.corpo, "texto", "Mensagem", obrigatorio=False, maximo=2000)
    status = req.corpo.get("status")
    if status is not None:
        if membro["papel"] != "sindico":
            raise ErroHTTP(403, "Apenas o síndico muda o andamento da ocorrência.")
        if status not in STATUS:
            raise ErroHTTP(400, "Status inválido.")
        if status == ocorrencia["status"]:
            status = None
    if not mensagem and status is None:
        raise ErroHTTP(400, "Escreva uma mensagem.")
    req.conn.execute(
        "INSERT INTO ocorrencia_mensagens (ocorrencia_id, autor_id, texto, status_novo) VALUES (?, ?, ?, ?)",
        (oid, req.usuario["id"], mensagem, status),
    )
    req.conn.execute(
        "UPDATE ocorrencias SET status = COALESCE(?, status), atualizado_em = datetime('now') WHERE id = ?",
        (status, oid),
    )
    return 201, {"ok": True}
