"""Senhas, tokens de sessão e códigos de convite."""
import hashlib
import hmac
import secrets

ITERACOES = 200_000
ALFABETO_CONVITE = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem 0/O e 1/I, que confundem


def hash_senha(senha):
    sal = secrets.token_bytes(16)
    chave = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, ITERACOES)
    return f"pbkdf2_sha256${ITERACOES}${sal.hex()}${chave.hex()}"


def conferir_senha(senha, armazenado):
    _, iteracoes, sal, chave = armazenado.split("$")
    calculada = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal), int(iteracoes))
    return hmac.compare_digest(calculada.hex(), chave)


def novo_token():
    return secrets.token_urlsafe(32)


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def novo_codigo_convite():
    return "".join(secrets.choice(ALFABETO_CONVITE) for _ in range(6))
