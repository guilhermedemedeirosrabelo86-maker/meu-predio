"""Banco de dados SQLite: conexão e esquema."""
import sqlite3

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
    criado_em   TEXT NOT NULL DEFAULT (datetime('now'))
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

CREATE INDEX IF NOT EXISTS idx_ocorrencias_condominio ON ocorrencias (condominio_id, status);
CREATE INDEX IF NOT EXISTS idx_visitas_condominio ON visitas (condominio_id, data_inicio, data_fim);
CREATE INDEX IF NOT EXISTS idx_visitas_unidade ON visitas (unidade_id);
CREATE INDEX IF NOT EXISTS idx_reservas_unidade ON reservas (unidade_id, data);
CREATE INDEX IF NOT EXISTS idx_membros_condominio ON membros (condominio_id);
CREATE INDEX IF NOT EXISTS idx_avisos_condominio ON avisos (condominio_id, fixado, id);
CREATE INDEX IF NOT EXISTS idx_sessoes_usuario ON sessoes (usuario_id);
"""


def conectar(caminho):
    conn = sqlite3.connect(caminho, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar(caminho):
    conn = conectar(caminho)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(ESQUEMA)
        _migrar(conn)
        conn.commit()
    finally:
        conn.close()


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
