"""Limite de tentativas: barra quem tenta adivinhar senhas ou códigos de convite.

Cada erro vira uma linha em `tentativas`. Se a mesma chave (e-mail ou endereço IP) errar demais
dentro da janela, os próximos pedidos recebem 429 até a janela passar. Fica no banco, e não na
memória, porque na Vercel cada pedido pode cair numa cópia diferente do servidor.
"""
from .web import ErroHTTP

JANELA_MINUTOS = 15
LOGIN_POR_EMAIL = 5     # senhas erradas para a mesma conta
LOGIN_POR_IP = 30       # senhas erradas vindas do mesmo endereço (várias contas)
CONVITE_POR_IP = 20     # códigos de convite inexistentes
ESQUECI_POR_EMAIL = 3   # pedidos de "esqueci minha senha" (cada um manda um e-mail)
ESQUECI_POR_IP = 10
LINK_INVALIDO_POR_IP = 10  # links de nova senha inválidos ou vencidos


def conferir(conn, chave, maximo):
    total = conn.execute(
        "SELECT COUNT(*) FROM tentativas WHERE chave = ? AND criado_em > datetime('now', ?)",
        (chave, f"-{JANELA_MINUTOS} minutes"),
    ).fetchone()[0]
    if total >= maximo:
        raise ErroHTTP(429, f"Muitas tentativas. Espere {JANELA_MINUTOS} minutos e tente de novo.")


def registrar(conn, *chaves):
    """Grava a tentativa e confirma na hora: o erro HTTP que vem em seguida desfaz o resto do pedido."""
    conn.execute("DELETE FROM tentativas WHERE criado_em <= datetime('now', '-1 day')")
    conn.executemany("INSERT INTO tentativas (chave) VALUES (?)", [(chave,) for chave in chaves])
    conn.commit()


def esquecer(conn, chave):
    conn.execute("DELETE FROM tentativas WHERE chave = ?", (chave,))
