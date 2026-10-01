"""Validação de entrada e checagens de permissão usadas pelas rotas."""
import re
from datetime import date

from .web import ErroHTTP

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def texto(corpo, campo, rotulo, obrigatorio=True, maximo=200):
    valor = corpo.get(campo)
    if valor is None:
        valor = ""
    if not isinstance(valor, str):
        raise ErroHTTP(400, f'O campo "{rotulo}" é inválido.')
    valor = valor.strip()
    if obrigatorio and not valor:
        raise ErroHTTP(400, f'Preencha o campo "{rotulo}".')
    if len(valor) > maximo:
        raise ErroHTTP(400, f'O campo "{rotulo}" aceita no máximo {maximo} caracteres.')
    return valor


def inteiro(corpo, campo, rotulo, minimo=None, maximo=None):
    valor = corpo.get(campo)
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ErroHTTP(400, f'Escolha um valor válido para "{rotulo}".')
    if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
        raise ErroHTTP(400, f'O campo "{rotulo}" deve ficar entre {minimo} e {maximo}.')
    return valor


def booleano(corpo, campo, rotulo, padrao=False):
    valor = corpo.get(campo, padrao)
    if not isinstance(valor, bool):
        raise ErroHTTP(400, f'Valor inválido para "{rotulo}".')
    return valor


def unidade_do_condominio(conn, condominio_id, unidade_id):
    unidade = conn.execute(
        "SELECT * FROM unidades WHERE id = ? AND condominio_id = ?", (unidade_id, condominio_id)
    ).fetchone()
    if unidade is None:
        raise ErroHTTP(400, "Escolha uma unidade da lista.")
    return unidade


def ordem_natural(valor):
    """Chave de ordenação que põe "2" antes de "10" e "101" antes de "1001"."""
    return [(0, int(p), "") if p.isdigit() else (1, 0, p.casefold()) for p in re.split(r"(\d+)", valor) if p]


def exigir_login(req):
    if req.usuario is None:
        raise ErroHTTP(401, "Faça login para continuar.")
    return req.usuario


def hoje():
    """Data local do servidor. Os módulos importam esta função para os testes poderem trocá-la."""
    return date.today()


def data_iso(valor, rotulo="Data"):
    if not isinstance(valor, str):
        raise ErroHTTP(400, f'Escolha uma data válida para "{rotulo}".')
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ErroHTTP(400, f'Escolha uma data válida para "{rotulo}".')


def exigir_membro(req, condominio_id, sindico=False, papeis=None):
    usuario = exigir_login(req)
    membro = req.conn.execute(
        "SELECT * FROM membros WHERE usuario_id = ? AND condominio_id = ?",
        (usuario["id"], condominio_id),
    ).fetchone()
    if membro is None or membro["status"] != "ativo":
        raise ErroHTTP(403, "Você não tem acesso a este condomínio.")
    if sindico and membro["papel"] != "sindico":
        raise ErroHTTP(403, "Apenas o síndico pode fazer isso.")
    if papeis and membro["papel"] not in papeis:
        raise ErroHTTP(403, "Você não tem permissão para fazer isso.")
    return membro


def usuario_publico(usuario):
    return {
        "id": usuario["id"],
        "nome": usuario["nome"],
        "email": usuario["email"],
        "telefone": usuario["telefone"],
    }
