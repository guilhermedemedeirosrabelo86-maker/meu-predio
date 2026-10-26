"""Condomínios, convites, unidades, moradores e veículos."""
import re
import secrets
import sqlite3

from . import auth, db, historico, limites
from .comum import exigir_login, exigir_membro, inteiro, ordem_natural, texto, unidade_do_condominio
from .rotas_ocorrencias import _tipo_imagem
from .web import Arquivo, ErroHTTP, rota

MAX_UNIDADES = 500
MAX_VEICULOS_POR_UNIDADE = 10
PLACA_RE = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")  # ABC1234 e Mercosul ABC1D23


def _gerar_codigo(conn):
    while True:
        codigo = auth.novo_codigo_convite()
        if not conn.execute("SELECT 1 FROM condominios WHERE codigo_convite = ?", (codigo,)).fetchone():
            return codigo


def _lista_unidades(valor):
    if valor is None:
        return []
    if not isinstance(valor, list):
        raise ErroHTTP(400, "Lista de unidades inválida.")
    vistas, unidades = set(), []
    for item in valor:
        if not isinstance(item, str):
            raise ErroHTTP(400, "Lista de unidades inválida.")
        nome = item.strip()
        if not nome or nome.casefold() in vistas:
            continue
        if len(nome) > 30:
            raise ErroHTTP(400, f'Nome de unidade longo demais: "{nome[:30]}…".')
        vistas.add(nome.casefold())
        unidades.append(nome)
    return unidades


NOMES_PAPEL = {"sindico": "síndico", "morador": "morador", "portaria": "portaria"}


def _descrever_membro(conn, membro):
    """Ana Souza (unidade 102)"""
    linha = conn.execute(
        """SELECT u.nome, un.identificador FROM usuarios u LEFT JOIN unidades un ON un.id = ?
           WHERE u.id = ?""",
        (membro["unidade_id"], membro["usuario_id"]),
    ).fetchone()
    return f"{linha['nome']} (unidade {linha['identificador']})" if linha["identificador"] else linha["nome"]


def _membro_do_condominio(conn, condominio_id, membro_id):
    membro = conn.execute(
        "SELECT * FROM membros WHERE id = ? AND condominio_id = ?", (membro_id, condominio_id)
    ).fetchone()
    if membro is None:
        raise ErroHTTP(404, "Morador não encontrado.")
    return membro


def _garantir_outro_sindico(conn, condominio_id, membro_id):
    outros = conn.execute(
        """SELECT COUNT(*) FROM membros
           WHERE condominio_id = ? AND papel = 'sindico' AND status = 'ativo' AND id <> ?""",
        (condominio_id, membro_id),
    ).fetchone()[0]
    if outros == 0:
        raise ErroHTTP(409, "O condomínio precisa ter pelo menos um síndico. Nomeie outro síndico antes.")


# --- Condomínio -------------------------------------------------------------

@rota("POST", "/api/condominios")
def criar_condominio(req):
    usuario = exigir_login(req)
    nome = texto(req.corpo, "nome", "Nome do condomínio", maximo=100)
    endereco = texto(req.corpo, "endereco", "Endereço", obrigatorio=False, maximo=200)
    unidades = _lista_unidades(req.corpo.get("unidades"))
    minha_unidade = texto(req.corpo, "minha_unidade", "Sua unidade", obrigatorio=False, maximo=30)
    if minha_unidade and minha_unidade.casefold() not in {u.casefold() for u in unidades}:
        unidades.append(minha_unidade)
    if len(unidades) > MAX_UNIDADES:
        raise ErroHTTP(400, f"O limite é de {MAX_UNIDADES} unidades.")

    conn = req.conn
    condominio_id = conn.execute(
        "INSERT INTO condominios (nome, endereco, codigo_convite) VALUES (?, ?, ?)",
        (nome, endereco, _gerar_codigo(conn)),
    ).lastrowid
    ids = {}
    for identificador in unidades:
        ids[identificador.casefold()] = conn.execute(
            "INSERT INTO unidades (condominio_id, identificador) VALUES (?, ?)", (condominio_id, identificador)
        ).lastrowid
    conn.execute(
        "INSERT INTO membros (usuario_id, condominio_id, unidade_id, papel, status) VALUES (?, ?, ?, 'sindico', 'ativo')",
        (usuario["id"], condominio_id, ids.get(minha_unidade.casefold())),
    )
    return 201, {"id": condominio_id}


@rota("GET", "/api/condominios/{cid:int}")
def ver_condominio(req, cid):
    membro = exigir_membro(req, cid)
    condominio = req.conn.execute("SELECT * FROM condominios WHERE id = ?", (cid,)).fetchone()
    dados = {
        "id": condominio["id"],
        "nome": condominio["nome"],
        "endereco": condominio["endereco"],
        "plano": condominio["plano"],
        "papel": membro["papel"],
        "foto": condominio["foto"],
        "foto_noite": condominio["foto_noite"],
    }
    if membro["papel"] == "sindico":
        dados["codigo_convite"] = condominio["codigo_convite"]
    return dados


@rota("PATCH", "/api/condominios/{cid:int}")
def alterar_condominio(req, cid):
    exigir_membro(req, cid, sindico=True)
    nome = texto(req.corpo, "nome", "Nome do condomínio", maximo=100)
    endereco = texto(req.corpo, "endereco", "Endereço", obrigatorio=False, maximo=200)
    req.conn.execute("UPDATE condominios SET nome = ?, endereco = ? WHERE id = ?", (nome, endereco, cid))
    return {"ok": True}


@rota("POST", "/api/condominios/{cid:int}/convite")
def renovar_convite(req, cid):
    exigir_membro(req, cid, sindico=True)
    codigo = _gerar_codigo(req.conn)
    req.conn.execute("UPDATE condominios SET codigo_convite = ? WHERE id = ?", (codigo, cid))
    return {"codigo_convite": codigo}


# --- Foto do prédio ---------------------------------------------------------
# Aparece no topo do Início no lugar das fotos padrão. "dia" vale o dia todo; "noite" (opcional) substitui à noite.
# O nome do arquivo muda a cada envio, então o celular pode guardar a foto sem risco de mostrar a antiga.

COLUNA_FOTO = {"dia": "foto", "noite": "foto_noite"}


def _coluna_foto(periodo):
    if periodo not in COLUNA_FOTO:
        raise ErroHTTP(404, "Rota não encontrada.")
    return COLUNA_FOTO[periodo]


@rota("POST", "/api/condominios/{cid:int}/foto/{periodo}")
def enviar_foto_predio(req, cid, periodo):
    exigir_membro(req, cid, sindico=True)
    coluna = _coluna_foto(periodo)
    if not req.bruto:
        raise ErroHTTP(400, "Envie a foto do prédio.")
    _, extensao = _tipo_imagem(req.bruto)
    anterior = req.conn.execute(f"SELECT {coluna} FROM condominios WHERE id = ?", (cid,)).fetchone()[0]
    nome = secrets.token_hex(16) + extensao
    db.salvar_arquivo(req.conn, f"predios/{nome}", req.bruto)
    req.conn.execute(f"UPDATE condominios SET {coluna} = ? WHERE id = ?", (nome, cid))
    if anterior:
        db.apagar_arquivo(req.conn, f"predios/{anterior}")
    acao = "Trocou" if anterior else "Enviou"
    historico.anotar(req, cid, f"{acao} a foto do prédio" + ("" if periodo == "dia" else " à noite"))
    return 201, {"foto": nome}


@rota("DELETE", "/api/condominios/{cid:int}/foto/{periodo}")
def remover_foto_predio(req, cid, periodo):
    exigir_membro(req, cid, sindico=True)
    coluna = _coluna_foto(periodo)
    anterior = req.conn.execute(f"SELECT {coluna} FROM condominios WHERE id = ?", (cid,)).fetchone()[0]
    if anterior:
        req.conn.execute(f"UPDATE condominios SET {coluna} = NULL WHERE id = ?", (cid,))
        db.apagar_arquivo(req.conn, f"predios/{anterior}")
        historico.anotar(req, cid, "Removeu a foto do prédio" + ("" if periodo == "dia" else " à noite"))
    return {"ok": True}


@rota("GET", "/api/condominios/{cid:int}/fotos/{nome}")
def ver_foto_predio(req, cid, nome):
    """Só a foto atual do próprio condomínio (o nome precisa ser o que está no cadastro)."""
    exigir_membro(req, cid)
    condominio = req.conn.execute("SELECT foto, foto_noite FROM condominios WHERE id = ?", (cid,)).fetchone()
    if nome not in (condominio["foto"], condominio["foto_noite"]):
        raise ErroHTTP(404, "Foto não encontrada.")
    conteudo = db.ler_arquivo(req.conn, f"predios/{nome}")
    if conteudo is None:
        raise ErroHTTP(404, "Foto não encontrada.")
    tipo, _ = _tipo_imagem(conteudo)
    return Arquivo(conteudo, tipo)


# --- Convites ---------------------------------------------------------------

def _condominio_por_codigo(req, codigo):
    chave = f"convite-ip:{req.ip}"
    limites.conferir(req.conn, chave, limites.CONVITE_POR_IP)
    condominio = req.conn.execute(
        "SELECT * FROM condominios WHERE codigo_convite = ?", (codigo.strip().upper(),)
    ).fetchone()
    if condominio is None:
        limites.registrar(req.conn, chave)
        raise ErroHTTP(404, "Código de convite não encontrado. Confira com o síndico.")
    return condominio


@rota("GET", "/api/convites/{codigo}")
def ver_convite(req, codigo):
    exigir_login(req)
    condominio = _condominio_por_codigo(req, codigo)
    unidades = req.conn.execute(
        "SELECT id, identificador FROM unidades WHERE condominio_id = ?", (condominio["id"],)
    ).fetchall()
    return {
        "condominio": {"id": condominio["id"], "nome": condominio["nome"], "endereco": condominio["endereco"]},
        "unidades": sorted((dict(u) for u in unidades), key=lambda u: ordem_natural(u["identificador"])),
    }


@rota("POST", "/api/convites/{codigo}/entrar")
def pedir_entrada(req, codigo):
    """Morador escolhe a unidade; funcionário (portaria/zeladoria) entra sem unidade. O síndico aprova."""
    usuario = exigir_login(req)
    condominio = _condominio_por_codigo(req, codigo)
    if req.corpo.get("funcionario") is True:
        unidade_id, papel = None, "portaria"
    else:
        unidade_id = unidade_do_condominio(req.conn, condominio["id"], inteiro(req.corpo, "unidade_id", "Unidade"))["id"]
        papel = "morador"
    try:
        req.conn.execute(
            "INSERT INTO membros (usuario_id, condominio_id, unidade_id, papel, status) VALUES (?, ?, ?, ?, 'pendente')",
            (usuario["id"], condominio["id"], unidade_id, papel),
        )
    except sqlite3.IntegrityError:
        raise ErroHTTP(409, "Você já faz parte deste condomínio ou já pediu para entrar.")
    return 201, {"condominio_id": condominio["id"], "status": "pendente"}


# --- Unidades e cadastro ----------------------------------------------------

@rota("GET", "/api/condominios/{cid:int}/unidades")
def listar_unidades(req, cid):
    exigir_membro(req, cid)
    unidades = req.conn.execute(
        "SELECT id, identificador FROM unidades WHERE condominio_id = ?", (cid,)
    ).fetchall()
    return {"unidades": sorted((dict(u) for u in unidades), key=lambda u: ordem_natural(u["identificador"]))}


@rota("POST", "/api/condominios/{cid:int}/unidades")
def adicionar_unidade(req, cid):
    exigir_membro(req, cid, sindico=True)
    identificador = texto(req.corpo, "identificador", "Unidade", maximo=30)
    total = req.conn.execute("SELECT COUNT(*) FROM unidades WHERE condominio_id = ?", (cid,)).fetchone()[0]
    if total >= MAX_UNIDADES:
        raise ErroHTTP(400, f"O limite é de {MAX_UNIDADES} unidades.")
    try:
        cursor = req.conn.execute(
            "INSERT INTO unidades (condominio_id, identificador) VALUES (?, ?)", (cid, identificador)
        )
    except sqlite3.IntegrityError:
        raise ErroHTTP(409, "Essa unidade já existe.")
    return 201, {"id": cursor.lastrowid}


@rota("DELETE", "/api/condominios/{cid:int}/unidades/{uid:int}")
def remover_unidade(req, cid, uid):
    exigir_membro(req, cid, sindico=True)
    unidade = unidade_do_condominio(req.conn, cid, uid)
    if req.conn.execute("SELECT 1 FROM membros WHERE unidade_id = ?", (uid,)).fetchone():
        raise ErroHTTP(409, "Há moradores nesta unidade. Remova-os antes de excluí-la.")
    req.conn.execute("DELETE FROM unidades WHERE id = ?", (uid,))
    historico.anotar(req, cid, f"Excluiu a unidade {unidade['identificador']}")
    return {"ok": True}


@rota("GET", "/api/condominios/{cid:int}/cadastro")
def ver_cadastro(req, cid):
    """Visão completa do síndico: unidades, moradores, contatos de emergência, veículos e pedidos pendentes."""
    exigir_membro(req, cid, sindico=True)
    conn = req.conn
    unidades = {
        u["id"]: {"id": u["id"], "identificador": u["identificador"], "moradores": [], "veiculos": []}
        for u in conn.execute("SELECT id, identificador FROM unidades WHERE condominio_id = ?", (cid,))
    }
    contatos = {}
    for c in conn.execute(
        """SELECT c.id, c.usuario_id, c.nome, c.telefone, c.parentesco
           FROM contatos_emergencia c
           JOIN membros m ON m.usuario_id = c.usuario_id AND m.condominio_id = ? AND m.status = 'ativo'
           ORDER BY c.id""",
        (cid,),
    ):
        contatos.setdefault(c["usuario_id"], []).append(
            {"nome": c["nome"], "telefone": c["telefone"], "parentesco": c["parentesco"]}
        )

    pendentes, sem_unidade = [], []
    membros = conn.execute(
        """SELECT m.id, m.papel, m.status, m.unidade_id, m.criado_em,
                  u.id AS usuario_id, u.nome, u.email, u.telefone
           FROM membros m JOIN usuarios u ON u.id = m.usuario_id
           WHERE m.condominio_id = ?
           ORDER BY u.nome COLLATE NOCASE""",
        (cid,),
    )
    for m in membros:
        item = dict(m)
        unidade = unidades.get(m["unidade_id"])
        if m["status"] == "pendente":
            item["unidade"] = unidade["identificador"] if unidade else None
            pendentes.append(item)
            continue
        item["contatos"] = contatos.get(m["usuario_id"], [])
        if unidade:
            unidade["moradores"].append(item)
        else:
            sem_unidade.append(item)

    for v in conn.execute(
        """SELECT v.id, v.unidade_id, v.placa, v.modelo, v.cor
           FROM veiculos v JOIN unidades u ON u.id = v.unidade_id
           WHERE u.condominio_id = ? ORDER BY v.placa""",
        (cid,),
    ):
        unidades[v["unidade_id"]]["veiculos"].append(dict(v))

    return {
        "pendentes": pendentes,
        "unidades": sorted(unidades.values(), key=lambda u: ordem_natural(u["identificador"])),
        "sem_unidade": sem_unidade,
    }


# --- Moradores --------------------------------------------------------------

@rota("PATCH", "/api/condominios/{cid:int}/membros/{mid:int}")
def alterar_membro(req, cid, mid):
    """Aprovar pedido de entrada e/ou trocar o papel (síndico/morador)."""
    exigir_membro(req, cid, sindico=True)
    alvo = _membro_do_condominio(req.conn, cid, mid)
    status, papel = alvo["status"], alvo["papel"]
    if "status" in req.corpo:
        if req.corpo["status"] != "ativo":
            raise ErroHTTP(400, "Status inválido.")
        status = "ativo"
    if "papel" in req.corpo:
        if req.corpo["papel"] not in ("sindico", "morador", "portaria"):
            raise ErroHTTP(400, "Papel inválido.")
        papel = req.corpo["papel"]
    if papel == "sindico" and status != "ativo":
        raise ErroHTTP(400, "Aprove o morador antes de torná-lo síndico.")
    if alvo["papel"] == "sindico" and papel != "sindico":
        _garantir_outro_sindico(req.conn, cid, mid)
    req.conn.execute("UPDATE membros SET status = ?, papel = ? WHERE id = ?", (status, papel, mid))
    quem = _descrever_membro(req.conn, alvo)
    if status != alvo["status"]:
        historico.anotar(req, cid, f"Aprovou a entrada de {quem} como {NOMES_PAPEL[papel]}")
    elif papel != alvo["papel"]:
        historico.anotar(req, cid, f"Mudou {quem} de {NOMES_PAPEL[alvo['papel']]} para {NOMES_PAPEL[papel]}")
    return {"ok": True}


@rota("DELETE", "/api/condominios/{cid:int}/membros/{mid:int}")
def remover_membro(req, cid, mid):
    """O síndico remove um morador (ou recusa um pedido); o próprio morador pode sair ou cancelar o pedido."""
    usuario = exigir_login(req)
    alvo = req.conn.execute(
        "SELECT * FROM membros WHERE id = ? AND condominio_id = ?", (mid, cid)
    ).fetchone()
    if alvo is None or alvo["usuario_id"] != usuario["id"]:
        exigir_membro(req, cid, sindico=True)
        alvo = _membro_do_condominio(req.conn, cid, mid)
    if alvo["papel"] == "sindico" and alvo["status"] == "ativo":
        _garantir_outro_sindico(req.conn, cid, mid)
    quem = _descrever_membro(req.conn, alvo)
    req.conn.execute("DELETE FROM membros WHERE id = ?", (mid,))
    if alvo["usuario_id"] == usuario["id"]:
        historico.anotar(req, cid, "Saiu do condomínio" if alvo["status"] == "ativo" else "Cancelou o pedido de entrada")
    elif alvo["status"] == "ativo":
        historico.anotar(req, cid, f"Removeu {quem} do condomínio")
    else:
        historico.anotar(req, cid, f"Recusou o pedido de entrada de {quem}")
    return {"ok": True}


# --- Veículos ---------------------------------------------------------------

@rota("GET", "/api/condominios/{cid:int}/veiculos")
def listar_veiculos(req, cid):
    """Veículos da unidade de quem está logado."""
    membro = exigir_membro(req, cid)
    if membro["unidade_id"] is None:
        return {"veiculos": []}
    veiculos = req.conn.execute(
        "SELECT id, placa, modelo, cor FROM veiculos WHERE unidade_id = ? ORDER BY placa", (membro["unidade_id"],)
    ).fetchall()
    return {"veiculos": [dict(v) for v in veiculos]}


@rota("POST", "/api/condominios/{cid:int}/veiculos")
def adicionar_veiculo(req, cid):
    membro = exigir_membro(req, cid)
    unidade_id = membro["unidade_id"]
    if membro["papel"] == "sindico" and req.corpo.get("unidade_id") is not None:
        unidade_id = unidade_do_condominio(req.conn, cid, inteiro(req.corpo, "unidade_id", "Unidade"))["id"]
    if unidade_id is None:
        raise ErroHTTP(400, "Você precisa estar vinculado a uma unidade para cadastrar veículos.")
    placa = re.sub(r"[\s-]", "", texto(req.corpo, "placa", "Placa", maximo=10)).upper()
    if not PLACA_RE.match(placa):
        raise ErroHTTP(400, "Placa inválida. Use o formato ABC1234 ou ABC1D23.")
    modelo = texto(req.corpo, "modelo", "Modelo", obrigatorio=False, maximo=60)
    cor = texto(req.corpo, "cor", "Cor", obrigatorio=False, maximo=30)
    total = req.conn.execute("SELECT COUNT(*) FROM veiculos WHERE unidade_id = ?", (unidade_id,)).fetchone()[0]
    if total >= MAX_VEICULOS_POR_UNIDADE:
        raise ErroHTTP(400, f"Cada unidade pode ter até {MAX_VEICULOS_POR_UNIDADE} veículos.")
    try:
        cursor = req.conn.execute(
            "INSERT INTO veiculos (unidade_id, placa, modelo, cor) VALUES (?, ?, ?, ?)",
            (unidade_id, placa, modelo, cor),
        )
    except sqlite3.IntegrityError:
        raise ErroHTTP(409, "Este veículo já está cadastrado na unidade.")
    return 201, {"id": cursor.lastrowid}


@rota("DELETE", "/api/condominios/{cid:int}/veiculos/{vid:int}")
def remover_veiculo(req, cid, vid):
    membro = exigir_membro(req, cid)
    veiculo = req.conn.execute(
        """SELECT v.* FROM veiculos v JOIN unidades u ON u.id = v.unidade_id
           WHERE v.id = ? AND u.condominio_id = ?""",
        (vid, cid),
    ).fetchone()
    if veiculo is None:
        raise ErroHTTP(404, "Veículo não encontrado.")
    if membro["papel"] != "sindico" and veiculo["unidade_id"] != membro["unidade_id"]:
        raise ErroHTTP(403, "Você só pode remover veículos da sua unidade.")
    req.conn.execute("DELETE FROM veiculos WHERE id = ?", (vid,))
    return {"ok": True}
