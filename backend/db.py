"""Banco de dados SQLite: conexão e esquema. No computador é um arquivo; hospedado, é o Turso."""
import os
import sqlite3
from pathlib import Path

from . import db_remoto

# Definida à parte porque a migração recria esta tabela (o papel 'portaria' entrou depois).
MEMBROS = """
CREATE TABLE IF NOT EXISTS {nome} (
    id              INTEGER PRIMARY KEY,
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    condominio_id   INTEGER NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    unidade_id      INTEGER REFERENCES unidades(id) ON DELETE SET NULL,
    papel           TEXT NOT NULL CHECK (papel IN ('sindico', 'morador', 'portaria')),
    status          TEXT NOT NULL CHECK (status IN ('pendente', 'ativo')),
    criado_em       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (usuario_id, condominio_id)
);
"""

ESQUEMA = MEMBROS.format(nome="membros") + """
CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY,
    nome        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE COLLATE NOCASE,
    telefone    TEXT NOT NULL DEFAULT '',
    senha_hash  TEXT NOT NULL,
    criado_em   TEXT NOT NULL DEFAULT (datetime('now')),
    termos_aceitos_em TEXT  -- quando aceitou os termos de uso e a política de privacidade
);

CREATE TABLE IF NOT EXISTS sessoes (
    token_hash  TEXT PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    expira_em   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS condominios (
    id              INTEGER PRIMARY KEY,
    nome            TEXT NOT NULL,
    endereco        TEXT NOT NULL DEFAULT '',
    codigo_convite  TEXT NOT NULL UNIQUE,
    plano           TEXT NOT NULL DEFAULT 'gratis',
    taxa_centavos   INTEGER NOT NULL DEFAULT 0,   -- valor da taxa mensal; 0 = ainda não definido
    taxa_vencimento INTEGER NOT NULL DEFAULT 10,  -- dia do mês
    foto            TEXT,  -- foto do prédio (nome em arquivos, pasta "predios/"); vale o dia todo
    foto_noite      TEXT,  -- foto opcional para a noite
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS unidades (
    id              INTEGER PRIMARY KEY,
    condominio_id   INTEGER NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    identificador   TEXT NOT NULL COLLATE NOCASE,
    UNIQUE (condominio_id, identificador)
);

CREATE TABLE IF NOT EXISTS contatos_emergencia (
    id          INTEGER PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    nome        TEXT NOT NULL,
    telefone    TEXT NOT NULL,
    parentesco  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS veiculos (
    id          INTEGER PRIMARY KEY,
    unidade_id  INTEGER NOT NULL REFERENCES unidades(id) ON DELETE CASCADE,
    placa       TEXT NOT NULL,
    modelo      TEXT NOT NULL DEFAULT '',
    cor         TEXT NOT NULL DEFAULT '',
    UNIQUE (unidade_id, placa)
);

CREATE TABLE IF NOT EXISTS avisos (
    id              INTEGER PRIMARY KEY,
    condominio_id   INTEGER NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    autor_id        INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    titulo          TEXT NOT NULL,
    corpo           TEXT NOT NULL,
    fixado          INTEGER NOT NULL DEFAULT 0,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now')),
    editado_em      TEXT
);

CREATE TABLE IF NOT EXISTS avisos_lidos (
    aviso_id    INTEGER NOT NULL REFERENCES avisos(id) ON DELETE CASCADE,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    lido_em     TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (aviso_id, usuario_id)
);

CREATE TABLE IF NOT EXISTS areas (
    id                  INTEGER PRIMARY KEY,
    condominio_id       INTEGER NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    nome                TEXT NOT NULL COLLATE NOCASE,
    regras              TEXT NOT NULL DEFAULT '',
    exige_aprovacao     INTEGER NOT NULL DEFAULT 0,
    antecedencia_dias   INTEGER NOT NULL DEFAULT 60,
    limite_por_unidade  INTEGER NOT NULL DEFAULT 2,
    UNIQUE (condominio_id, nome)
);

-- Uma reserva ocupa a área no dia inteiro. Cancelar ou recusar apaga a linha.
CREATE TABLE IF NOT EXISTS reservas (
    id          INTEGER PRIMARY KEY,
    area_id     INTEGER NOT NULL REFERENCES areas(id) ON DELETE CASCADE,
    unidade_id  INTEGER NOT NULL REFERENCES unidades(id) ON DELETE CASCADE,
    usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    data        TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('pendente', 'confirmada')),
    observacao  TEXT NOT NULL DEFAULT '',
    criado_em   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (area_id, data)
);

CREATE TABLE IF NOT EXISTS ocorrencias (
    id              INTEGER PRIMARY KEY,
    condominio_id   INTEGER NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    unidade_id      INTEGER REFERENCES unidades(id) ON DELETE SET NULL,
    autor_id        INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    categoria       TEXT NOT NULL,
    titulo          TEXT NOT NULL,
    descricao       TEXT NOT NULL DEFAULT '',
    local           TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'aberta' CHECK (status IN ('aberta', 'andamento', 'resolvida')),
    criado_em       TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ocorrencia_fotos (
    id              INTEGER PRIMARY KEY,
    ocorrencia_id   INTEGER NOT NULL REFERENCES ocorrencias(id) ON DELETE CASCADE,
    arquivo         TEXT NOT NULL,
    tipo            TEXT NOT NULL,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ocorrencia_mensagens (
    id              INTEGER PRIMARY KEY,
    ocorrencia_id   INTEGER NOT NULL REFERENCES ocorrencias(id) ON DELETE CASCADE,
    autor_id        INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    texto           TEXT NOT NULL DEFAULT '',
    status_novo     TEXT,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Visita liberada por um morador. O token vai no QR Code; o código curto é para digitar na portaria.
CREATE TABLE IF NOT EXISTS visitas (
    id              INTEGER PRIMARY KEY,
    condominio_id   INTEGER NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    unidade_id      INTEGER NOT NULL REFERENCES unidades(id) ON DELETE CASCADE,
    autor_id        INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    nome            TEXT NOT NULL,
    tipo            TEXT NOT NULL CHECK (tipo IN ('visita', 'prestador', 'entrega')),
    data_inicio     TEXT NOT NULL,
    data_fim        TEXT NOT NULL,
    observacao      TEXT NOT NULL DEFAULT '',
    token           TEXT NOT NULL UNIQUE,
    codigo          TEXT NOT NULL,
    cancelada       INTEGER NOT NULL DEFAULT 0,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (condominio_id, codigo)
);

CREATE TABLE IF NOT EXISTS visita_entradas (
    id              INTEGER PRIMARY KEY,
    visita_id       INTEGER NOT NULL REFERENCES visitas(id) ON DELETE CASCADE,
    registrado_por  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Prestação de contas: cada entrada (receita) ou saída (despesa), em centavos, com comprovante opcional.
CREATE TABLE IF NOT EXISTS lancamentos (
    id                  INTEGER PRIMARY KEY,
    condominio_id       INTEGER NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    tipo                TEXT NOT NULL CHECK (tipo IN ('receita', 'despesa')),
    categoria           TEXT NOT NULL,
    descricao           TEXT NOT NULL,
    valor_centavos      INTEGER NOT NULL CHECK (valor_centavos > 0),
    data                TEXT NOT NULL,
    comprovante         TEXT,
    comprovante_tipo    TEXT,
    autor_id            INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em           TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Taxa paga por uma unidade num mês. O valor e a data ficam no lançamento de entrada que o
-- pagamento cria; excluir o lançamento na prestação de contas desfaz o pagamento.
CREATE TABLE IF NOT EXISTS pagamentos (
    id              INTEGER PRIMARY KEY,
    unidade_id      INTEGER NOT NULL REFERENCES unidades(id) ON DELETE CASCADE,
    mes             TEXT NOT NULL,
    lancamento_id   INTEGER NOT NULL UNIQUE REFERENCES lancamentos(id) ON DELETE CASCADE,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (unidade_id, mes)
);

-- Pacote que chegou na portaria para uma unidade. retirada_em vazio = ainda está na portaria.
CREATE TABLE IF NOT EXISTS encomendas (
    id              INTEGER PRIMARY KEY,
    condominio_id   INTEGER NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    unidade_id      INTEGER NOT NULL REFERENCES unidades(id) ON DELETE CASCADE,
    descricao       TEXT NOT NULL,
    registrado_por  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now')),
    retirada_em     TEXT,
    retirada_por    TEXT NOT NULL DEFAULT '',
    entregue_por    INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);

-- Contatos úteis do prédio (zelador, encanador, administradora...), mantidos pelo síndico.
CREATE TABLE IF NOT EXISTS telefones (
    id              INTEGER PRIMARY KEY,
    condominio_id   INTEGER NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    nome            TEXT NOT NULL,
    descricao       TEXT NOT NULL DEFAULT '',
    telefone        TEXT NOT NULL
);

-- Enquete do síndico: cada unidade vota uma vez (e pode mudar o voto enquanto estiver aberta).
CREATE TABLE IF NOT EXISTS enquetes (
    id              INTEGER PRIMARY KEY,
    condominio_id   INTEGER NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    autor_id        INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    pergunta        TEXT NOT NULL,
    descricao       TEXT NOT NULL DEFAULT '',
    encerra_em      TEXT,
    encerrada       INTEGER NOT NULL DEFAULT 0,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS enquete_opcoes (
    id          INTEGER PRIMARY KEY,
    enquete_id  INTEGER NOT NULL REFERENCES enquetes(id) ON DELETE CASCADE,
    texto       TEXT NOT NULL,
    ordem       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS enquete_votos (
    enquete_id  INTEGER NOT NULL REFERENCES enquetes(id) ON DELETE CASCADE,
    unidade_id  INTEGER NOT NULL REFERENCES unidades(id) ON DELETE CASCADE,
    opcao_id    INTEGER NOT NULL REFERENCES enquete_opcoes(id) ON DELETE CASCADE,
    usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (enquete_id, unidade_id)
);

-- Fotos e comprovantes. O nome tem a pasta de origem, como "contas/9f2c....jpg".
CREATE TABLE IF NOT EXISTS arquivos (
    nome        TEXT PRIMARY KEY,
    conteudo    BLOB NOT NULL
);

-- Histórico de ações do síndico (ver historico.py). O autor fica em texto para sobreviver à exclusão da conta.
CREATE TABLE IF NOT EXISTS historico (
    id              INTEGER PRIMARY KEY,
    condominio_id   INTEGER NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    usuario_id      INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    autor           TEXT NOT NULL,
    texto           TEXT NOT NULL,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_historico ON historico (condominio_id, id);

-- Links de "esqueci minha senha": valem uma vez e por pouco tempo. Só o hash do token fica guardado.
CREATE TABLE IF NOT EXISTS recuperacoes (
    token_hash  TEXT PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    expira_em   TEXT NOT NULL
);

-- Erros de login e de código de convite, para o limite de tentativas (ver limites.py).
CREATE TABLE IF NOT EXISTS tentativas (
    chave       TEXT NOT NULL,
    criado_em   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tentativas ON tentativas (chave, criado_em);
CREATE INDEX IF NOT EXISTS idx_encomendas_condominio ON encomendas (condominio_id, retirada_em);
CREATE INDEX IF NOT EXISTS idx_encomendas_unidade ON encomendas (unidade_id, retirada_em);
CREATE INDEX IF NOT EXISTS idx_enquetes_condominio ON enquetes (condominio_id, encerrada);
CREATE INDEX IF NOT EXISTS idx_ocorrencias_condominio ON ocorrencias (condominio_id, status);
CREATE INDEX IF NOT EXISTS idx_visitas_condominio ON visitas (condominio_id, data_inicio, data_fim);
CREATE INDEX IF NOT EXISTS idx_visitas_unidade ON visitas (unidade_id);
CREATE INDEX IF NOT EXISTS idx_reservas_unidade ON reservas (unidade_id, data);
CREATE INDEX IF NOT EXISTS idx_membros_condominio ON membros (condominio_id);
CREATE INDEX IF NOT EXISTS idx_avisos_condominio ON avisos (condominio_id, fixado, id);
CREATE INDEX IF NOT EXISTS idx_sessoes_usuario ON sessoes (usuario_id);
CREATE INDEX IF NOT EXISTS idx_lancamentos_condominio ON lancamentos (condominio_id, data);
"""


def conectar(caminho):
    """Um caminho de arquivo abre o SQLite local; um endereço (libsql://...) abre o banco no Turso."""
    if db_remoto.eh_remoto(caminho):
        return db_remoto.conectar(caminho, os.environ.get("TURSO_AUTH_TOKEN"))
    conn = sqlite3.connect(caminho, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar(caminho):
    conn = conectar(caminho)
    try:
        if not db_remoto.eh_remoto(caminho):
            conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(ESQUEMA)
        _migrar(conn)
        conn.commit()
        if not db_remoto.eh_remoto(caminho):
            _importar_pasta_de_arquivos(conn, Path(caminho).resolve().parent / "arquivos")
    finally:
        conn.close()


def _importar_pasta_de_arquivos(conn, pasta):
    """Versões anteriores guardavam fotos e comprovantes em dados/arquivos/. Elas passam para o
    banco e a pasta é renomeada para arquivos-importados (nada é apagado)."""
    if not pasta.is_dir():
        return
    for arquivo in pasta.glob("*/*"):
        if arquivo.is_file():
            conn.execute(
                "INSERT OR IGNORE INTO arquivos (nome, conteudo) VALUES (?, ?)",
                (f"{arquivo.parent.name}/{arquivo.name}", arquivo.read_bytes()),
            )
    conn.commit()
    destino = pasta.with_name("arquivos-importados")
    if not destino.exists():
        pasta.rename(destino)


def _migrar(conn):
    """Atualiza bancos criados por versões anteriores. Cada passo verifica se já foi aplicado."""
    sql_membros = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'membros'").fetchone()[0]
    if "'portaria'" not in sql_membros:
        # SQLite não altera CHECK de uma tabela existente: recria e copia os dados.
        conn.commit()
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.executescript(
            "BEGIN;"
            + MEMBROS.format(nome="membros_novo")
            + """
            INSERT INTO membros_novo (id, usuario_id, condominio_id, unidade_id, papel, status, criado_em)
                SELECT id, usuario_id, condominio_id, unidade_id, papel, status, criado_em FROM membros;
            DROP TABLE membros;
            ALTER TABLE membros_novo RENAME TO membros;
            CREATE INDEX IF NOT EXISTS idx_membros_condominio ON membros (condominio_id);
            COMMIT;
            """
        )
        conn.execute("PRAGMA foreign_keys = ON")

    colunas = {linha["name"] for linha in conn.execute("PRAGMA table_info(condominios)")}
    if "taxa_centavos" not in colunas:
        conn.execute("ALTER TABLE condominios ADD COLUMN taxa_centavos INTEGER NOT NULL DEFAULT 0")
        conn.execute("ALTER TABLE condominios ADD COLUMN taxa_vencimento INTEGER NOT NULL DEFAULT 10")

    if "foto" not in colunas:
        conn.execute("ALTER TABLE condominios ADD COLUMN foto TEXT")
        conn.execute("ALTER TABLE condominios ADD COLUMN foto_noite TEXT")

    colunas = {linha["name"] for linha in conn.execute("PRAGMA table_info(usuarios)")}
    if "termos_aceitos_em" not in colunas:
        conn.execute("ALTER TABLE usuarios ADD COLUMN termos_aceitos_em TEXT")


def salvar_arquivo(conn, nome, conteudo):
    conn.execute("INSERT OR REPLACE INTO arquivos (nome, conteudo) VALUES (?, ?)", (nome, conteudo))


def ler_arquivo(conn, nome):
    linha = conn.execute("SELECT conteudo FROM arquivos WHERE nome = ?", (nome,)).fetchone()
    return bytes(linha[0]) if linha else None


def apagar_arquivo(conn, nome):
    conn.execute("DELETE FROM arquivos WHERE nome = ?", (nome,))
