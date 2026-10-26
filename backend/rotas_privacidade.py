"""LGPD: a pessoa baixa os próprios dados e exclui a conta; dados antigos de terceiros são apagados.

O que é do condomínio (avisos, lançamentos, ocorrências, histórico) continua lá depois da exclusão,
sem o vínculo com a conta: é registro do prédio, e a prestação de contas precisa ser guardada.
"""
import hmac
import os

from . import auth, historico
from .comum import exigir_login
from .web import ErroHTTP, rota

DIAS_VISITAS = 180     # visitas (nome do visitante) depois do fim da liberação
DIAS_ENCOMENDAS = 180  # encomendas depois de retiradas


def _linhas(conn, sql, params):
    return [dict(l) for l in conn.execute(sql, params).fetchall()]


@rota("GET", "/api/eu/dados")
def exportar(req):
    """Tudo o que está ligado à conta, em JSON, para a pessoa guardar."""
    usuario = exigir_login(req)
    uid = usuario["id"]
    conn = req.conn
    return {
        "conta": {c: usuario[c] for c in ("nome", "email", "telefone", "criado_em", "termos_aceitos_em")},
        "contatos_emergencia": _linhas(conn, "SELECT nome, telefone, parentesco FROM contatos_emergencia WHERE usuario_id = ?", (uid,)),
        "condominios": _linhas(conn, """
            SELECT c.nome AS condominio, u.identificador AS unidade, m.papel, m.status, m.criado_em
            FROM membros m JOIN condominios c ON c.id = m.condominio_id LEFT JOIN unidades u ON u.id = m.unidade_id
            WHERE m.usuario_id = ?""", (uid,)),
        "veiculos_da_unidade": _linhas(conn, """
            SELECT v.placa, v.modelo, v.cor FROM veiculos v JOIN membros m ON m.unidade_id = v.unidade_id
            WHERE m.usuario_id = ?""", (uid,)),
        "visitas_liberadas": _linhas(conn, """
            SELECT nome, tipo, data_inicio, data_fim, observacao, cancelada, criado_em FROM visitas
            WHERE autor_id = ?""", (uid,)),
        "reservas": _linhas(conn, """
            SELECT a.nome AS area, r.data, r.status, r.observacao, r.criado_em
            FROM reservas r JOIN areas a ON a.id = r.area_id WHERE r.usuario_id = ?""", (uid,)),
        "ocorrencias": _linhas(conn, """
            SELECT categoria, titulo, descricao, local, status, criado_em FROM ocorrencias WHERE autor_id = ?""", (uid,)),
        "mensagens_em_ocorrencias": _linhas(conn, """
            SELECT o.titulo AS ocorrencia, m.texto, m.criado_em
            FROM ocorrencia_mensagens m JOIN ocorrencias o ON o.id = m.ocorrencia_id WHERE m.autor_id = ?""", (uid,)),
        "votos": _linhas(conn, """
            SELECT e.pergunta, o.texto AS opcao, v.criado_em
            FROM enquete_votos v JOIN enquetes e ON e.id = v.enquete_id JOIN enquete_opcoes o ON o.id = v.opcao_id
            WHERE v.usuario_id = ?""", (uid,)),
    }


def _apagar_condominio(conn, cid):
    """Apaga um condomínio inteiro (só quando quem sai é a única pessoa nele), com as fotos."""
    nomes = [f"ocorrencias/{l[0]}" for l in conn.execute(
        "SELECT f.arquivo FROM ocorrencia_fotos f JOIN ocorrencias o ON o.id = f.ocorrencia_id WHERE o.condominio_id = ?",
        (cid,))]
    nomes += [f"contas/{l[0]}" for l in conn.execute(
        "SELECT comprovante FROM lancamentos WHERE condominio_id = ? AND comprovante IS NOT NULL", (cid,))]
    conn.executemany("DELETE FROM arquivos WHERE nome = ?", [(n,) for n in nomes])
    conn.execute("DELETE FROM condominios WHERE id = ?", (cid,))


@rota("POST", "/api/eu/excluir")
def excluir_conta(req):
    usuario = exigir_login(req)
    senha = req.corpo.get("senha")
    if not isinstance(senha, str) or not auth.conferir_senha(senha, usuario["senha_hash"]):
        raise ErroHTTP(400, "Senha incorreta.")
    conn = req.conn
    vinculos = conn.execute(
        "SELECT m.condominio_id, m.papel, m.status, c.nome FROM membros m JOIN condominios c ON c.id = m.condominio_id "
        "WHERE m.usuario_id = ?", (usuario["id"],),
    ).fetchall()
    sozinho = []
    for v in vinculos:
        outros = conn.execute(
            "SELECT COUNT(*) FROM membros WHERE condominio_id = ? AND usuario_id != ?", (v["condominio_id"], usuario["id"])
        ).fetchone()[0]
        if outros == 0:
            sozinho.append(v["condominio_id"])
            continue
        if v["papel"] == "sindico" and v["status"] == "ativo":
            outro_sindico = conn.execute(
                "SELECT 1 FROM membros WHERE condominio_id = ? AND usuario_id != ? AND papel = 'sindico' AND status = 'ativo'",
                (v["condominio_id"], usuario["id"]),
            ).fetchone()
            if not outro_sindico:
                raise ErroHTTP(409, f'Você é o único síndico de "{v["nome"]}". Passe o cargo para outra pessoa antes de excluir a conta.')
        if v["status"] == "ativo":
            historico.anotar(req, v["condominio_id"], "Excluiu a própria conta e saiu do condomínio")
    for cid in sozinho:
        _apagar_condominio(conn, cid)
    conn.execute("DELETE FROM usuarios WHERE id = ?", (usuario["id"],))  # o resto sai junto (ver db.py)
    req.cookies_saida.append("sessao=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0")
    return {"ok": True}


def limpar_dados_antigos(conn):
    """Apaga o que não precisa mais ser guardado. Roda ao ligar o servidor e, na Vercel, uma vez por dia."""
    apagados = {
        "visitas": conn.execute(
            "DELETE FROM visitas WHERE data_fim < date('now', ?)", (f"-{DIAS_VISITAS} days",)).rowcount,
        "encomendas": conn.execute(
            "DELETE FROM encomendas WHERE retirada_em IS NOT NULL AND retirada_em < datetime('now', ?)",
            (f"-{DIAS_ENCOMENDAS} days",)).rowcount,
        "sessoes": conn.execute("DELETE FROM sessoes WHERE expira_em <= datetime('now')").rowcount,
        "links_de_senha": conn.execute("DELETE FROM recuperacoes WHERE expira_em <= datetime('now')").rowcount,
        "tentativas": conn.execute("DELETE FROM tentativas WHERE criado_em <= datetime('now', '-1 day')").rowcount,
    }
    conn.commit()
    return apagados


@rota("GET", "/api/sistema/limpeza")
def limpeza_agendada(req):
    """Chamada pelo agendador da Vercel (vercel.json → crons), que manda o CRON_SECRET."""
    segredo = os.environ.get("CRON_SECRET")
    if not segredo or not hmac.compare_digest(req.autorizacao, f"Bearer {segredo}"):
        raise ErroHTTP(404, "Rota não encontrada.")
    return {"apagados": limpar_dados_antigos(req.conn)}
