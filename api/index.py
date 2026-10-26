"""Entrada da Vercel: cada pedido a /api/... chega aqui e usa o mesmo Manipulador do servidor local.

As telas (pasta web/) a Vercel entrega sozinha, sem passar por aqui (ver vercel.json).
O banco é o Turso: defina TURSO_DATABASE_URL (libsql://...) e TURSO_AUTH_TOKEN no painel da Vercel.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import db, db_remoto  # noqa: E402
from backend.servidor import Manipulador  # noqa: E402

BANCO = os.environ.get("TURSO_DATABASE_URL", "")
if not db_remoto.eh_remoto(BANCO):
    raise RuntimeError("Defina TURSO_DATABASE_URL (libsql://...) nas variáveis de ambiente da Vercel.")

# Cria as tabelas que faltarem; roda uma vez cada vez que a Vercel liga a função.
db.inicializar(BANCO)


class handler(Manipulador):  # a Vercel procura uma classe com este nome
    caminho_db = BANCO

    def ip_cliente(self):
        # A Vercel sobrescreve este cabeçalho com o endereço real; quem pede não consegue forjá-lo.
        encaminhado = self.headers.get("X-Forwarded-For") or ""
        return encaminhado.split(",")[0].strip() or super().ip_cliente()
