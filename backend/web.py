"""Roteador mínimo da API JSON."""
import re


class ErroHTTP(Exception):
    def __init__(self, status, mensagem):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


class Requisicao:
    def __init__(self, conn, corpo, usuario, token_hash, query=None, bruto=None, tipo_conteudo="", ip="", endereco=""):
        self.conn = conn
        self.corpo = corpo
        self.query = query or {}
        self.bruto = bruto  # corpo binário (upload de foto)
        self.tipo_conteudo = tipo_conteudo
        self.usuario = usuario
        self.token_hash = token_hash
        self.ip = ip  # endereço de quem pediu, para o limite de tentativas
        self.endereco = endereco  # endereço do app (ex.: https://meupredio.com.br), para links em e-mails
        self.autorizacao = ""  # cabeçalho Authorization (só o agendador da Vercel usa)
        self.cookies_saida = []


class Arquivo:
    """Resposta binária (ex.: foto) em vez de JSON."""

    def __init__(self, conteudo, tipo):
        self.conteudo = conteudo
        self.tipo = tipo


_ROTAS = []


def rota(metodo, padrao):
    """Registra uma rota. Parâmetros: {nome} casa um segmento, {nome:int} casa só dígitos."""
    conversores = {}

    def trocar(achado):
        nome, tipo = achado.group(1), achado.group(2)
        conversores[nome] = int if tipo == "int" else str
        return rf"(?P<{nome}>\d+)" if tipo == "int" else rf"(?P<{nome}>[^/]+)"

    regex = re.compile("^" + re.sub(r"\{(\w+)(?::(\w+))?\}", trocar, padrao) + "$")

    def decorador(funcao):
        _ROTAS.append((metodo, regex, conversores, funcao))
        return funcao

    return decorador


def encontrar(metodo, caminho):
    """Devolve (função, parâmetros) da rota, ou lança 404/405."""
    caminho_existe = False
    for metodo_rota, regex, conversores, funcao in _ROTAS:
        achado = regex.match(caminho)
        if not achado:
            continue
        caminho_existe = True
        if metodo_rota == metodo:
            return funcao, {k: conversores[k](v) for k, v in achado.groupdict().items()}
    if caminho_existe:
        raise ErroHTTP(405, "Método não permitido.")
    raise ErroHTTP(404, "Rota não encontrada.")
