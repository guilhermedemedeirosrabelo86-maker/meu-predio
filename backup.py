"""Backup do banco na nuvem (Turso) para um arquivo no computador, e a volta.

    python backup.py                       copia o banco do Turso para dados/backups/backup-AAAA-MM-DD-HHMM.db
    python backup.py restaurar ARQUIVO.db  envia um backup para um banco do Turso VAZIO (nunca sobrescreve)

O endereço e o token do Turso vêm das variáveis TURSO_DATABASE_URL e TURSO_AUTH_TOKEN ou do arquivo
dados/turso.json (criado na primeira vez, se você quiser). A pasta dados/ não vai para o GitHub.

O backup é um arquivo SQLite comum, com tudo: contas, condomínios, fotos e comprovantes. Para conferir
se ele está bom, abra o app em cima dele:  python rodar.py --banco dados/backups/ARQUIVO.db
"""
import getpass
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from backend import db, db_remoto

PASTA = Path(__file__).resolve().parent
CONFIG = PASTA / "dados" / "turso.json"
LOTE = 50  # linhas por pedido ao Turso (fotos vão em base64, então lotes pequenos)


# --- Cópia entre bancos ----------------------------------------------------------

def tabelas_em_ordem(conn):
    """Tabelas do app (sem as internas do SQLite), cada uma depois das que ela referencia."""
    nomes = [l[0] for l in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid")]
    dependencias = {n: {l[2] for l in conn.execute(f'PRAGMA foreign_key_list("{n}")')} & set(nomes) - {n}
                    for n in nomes}
    ordem = []
    while len(ordem) < len(nomes):
        prontas = [n for n in nomes if n not in ordem and dependencias[n] <= set(ordem)]
        if not prontas:  # dependência circular: segue na ordem de criação
            prontas = [n for n in nomes if n not in ordem]
        ordem.extend(prontas)
    return ordem


def copiar(origem, destino, ao_copiar=None):
    """Copia as linhas de todas as tabelas de `origem` para `destino` (as tabelas já precisam existir)."""
    totais = {}
    for tabela in tabelas_em_ordem(origem):
        colunas = [l[1] for l in origem.execute(f'PRAGMA table_info("{tabela}")')]
        lista = ", ".join(f'"{c}"' for c in colunas)
        inserir = f'INSERT INTO "{tabela}" ({lista}) VALUES ({", ".join("?" * len(colunas))})'
        copiadas, inicio = 0, 0
        while True:
            linhas = origem.execute(
                f'SELECT {lista} FROM "{tabela}" ORDER BY rowid LIMIT {LOTE} OFFSET {inicio}').fetchall()
            if not linhas:
                break
            destino.executemany(inserir, [tuple(l) for l in linhas])
            destino.commit()
            copiadas += len(linhas)
            inicio += LOTE
        totais[tabela] = copiadas
        if ao_copiar:
            ao_copiar(tabela, copiadas)
    return totais


def fazer_backup(url, token, arquivo, ao_copiar=None):
    """Cria `arquivo` (SQLite) com o mesmo esquema do app e copia tudo do banco remoto para ele."""
    arquivo = Path(arquivo)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    if arquivo.exists():
        raise SystemExit(f"Já existe {arquivo}; escolha outro nome.")
    remoto = db_remoto.conectar(url, token)
    local = sqlite3.connect(arquivo)
    try:
        for (sql,) in remoto.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid"):
            local.execute(sql)
        totais = copiar(remoto, local, ao_copiar)
        for (sql,) in remoto.execute("SELECT sql FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL"):
            local.execute(sql)
        local.commit()
    except BaseException:
        local.close()
        arquivo.unlink(missing_ok=True)  # nada de backup pela metade
        raise
    finally:
        remoto.close()
    local.close()
    return totais


def restaurar(arquivo, url, token, ao_copiar=None):
    """Envia um backup para um banco remoto vazio. Recusa se o destino já tiver dados."""
    if not Path(arquivo).is_file():
        raise SystemExit(f"Arquivo não encontrado: {arquivo}")
    db.inicializar(url)  # cria as tabelas no destino, se faltarem
    remoto = db_remoto.conectar(url, token)
    local = sqlite3.connect(arquivo)
    try:
        for tabela in tabelas_em_ordem(local):
            if remoto.execute(f'SELECT 1 FROM "{tabela}" LIMIT 1').fetchone():
                raise SystemExit(
                    f'O banco de destino já tem dados (tabela "{tabela}"). Por segurança, a restauração só vai '
                    "para um banco vazio: crie um banco novo no Turso e use o endereço dele.")
        return copiar(local, remoto, ao_copiar)
    finally:
        local.close()
        remoto.close()


# --- Linha de comando -------------------------------------------------------------

def limpar_token(token):
    """O campo do token não mostra o que se digita, então é fácil colar duas vezes. Um token tem 3 partes
    separadas por ponto; se vier "token+token" (5 partes, duas cópias iguais), fica uma só."""
    token = "".join(token.split())
    if token.lower().startswith("bearer"):
        token = token[6:]
    partes = token.split(".")
    if len(partes) == 5:
        cabecalho, conteudo, meio, conteudo2, assinatura2 = partes
        primeiro = f"{cabecalho}.{conteudo}.{meio[:len(assinatura2)]}"
        if primeiro == f"{meio[len(assinatura2):]}.{conteudo2}.{assinatura2}":
            return primeiro
    if len(partes) != 3:
        raise SystemExit("O token não parece certo (deveria ter 3 partes separadas por ponto). "
                         "Copie de novo no painel do Turso e cole uma vez só.")
    return token



def credenciais():
    url, token = os.environ.get("TURSO_DATABASE_URL"), os.environ.get("TURSO_AUTH_TOKEN")
    if url and token:
        return url, token
    if CONFIG.is_file():
        dados = json.loads(CONFIG.read_text(encoding="utf-8"))
        return dados["url"], limpar_token(dados["token"])
    print("Endereço e token do banco no Turso (painel do Turso, página do banco).")
    url = input("Endereço (libsql://...): ").strip()
    token = limpar_token(getpass.getpass("Token (não aparece enquanto digita; cole uma vez só): "))
    if input("Guardar em dados/turso.json para não perguntar de novo? (s/n) ").strip().lower().startswith("s"):
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps({"url": url, "token": token}), encoding="utf-8")
        print("Guardado. A pasta dados/ não vai para o GitHub; não envie esse arquivo para ninguém.")
    return url, token


def mostrar(tabela, linhas):
    print(f"  {tabela}: {linhas}")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "restaurar":
        if len(sys.argv) != 3:
            raise SystemExit("Use: python backup.py restaurar ARQUIVO.db")
        print("Restaurar vai para um banco do Turso VAZIO. Informe o endereço e o token do banco NOVO.")
        os.environ.pop("TURSO_DATABASE_URL", None)  # nunca usar o banco em uso sem perguntar
        url = input("Endereço do banco novo (libsql://...): ").strip()
        token = limpar_token(getpass.getpass("Token do banco novo (cole uma vez só): "))
        os.environ["TURSO_AUTH_TOKEN"] = token  # usado por db.inicializar
        totais = restaurar(sys.argv[2], url, token, mostrar)
        print(f"Pronto: {sum(totais.values())} linhas enviadas. Agora troque TURSO_DATABASE_URL e "
              "TURSO_AUTH_TOKEN na Vercel para este banco e faça um Redeploy.")
        return
    url, token = credenciais()
    arquivo = PASTA / "dados" / "backups" / f"backup-{datetime.now():%Y-%m-%d-%H%M}.db"
    print(f"Copiando o banco para {arquivo.relative_to(PASTA)} ...")
    totais = fazer_backup(url, token, arquivo, mostrar)
    print(f"Pronto: {sum(totais.values())} linhas em {len(totais)} tabelas.")
    print(f"Para conferir, abra o app em cima do backup:  python rodar.py --banco \"{arquivo}\"")


if __name__ == "__main__":
    main()
