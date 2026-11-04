"""Persistência do histórico de conversa por sessão, em SQLite.

Decisão: SQLite em vez de JSON puro porque permite várias sessões simultâneas sem
risco de condição de corrida na escrita do arquivo, e porque já fica pronto para
consultas (ex.: "quantas conversas o Rico teve hoje") sem precisar reescrever nada.
Para o volume de uma loja pequena, um arquivo .sqlite3 local é suficiente - não há
necessidade de um banco de dados de verdade neste estágio.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS mensagens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sessao_id TEXT NOT NULL,
    papel TEXT NOT NULL,
    conteudo TEXT NOT NULL,
    criado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mensagens_sessao ON mensagens (sessao_id);
"""


def _conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(config.HISTORY_DB)
    conn.executescript(_SCHEMA)
    return conn


def salvar_mensagem(sessao_id: str, papel: str, conteudo: list | str) -> None:
    """Grava uma mensagem (role + content, no formato da API da Anthropic)."""
    conteudo_json = json.dumps(conteudo, ensure_ascii=False, default=str)
    with _conectar() as conn:
        conn.execute(
            "INSERT INTO mensagens (sessao_id, papel, conteudo, criado_em) VALUES (?, ?, ?, ?)",
            (sessao_id, papel, conteudo_json, datetime.now(timezone.utc).isoformat()),
        )


def carregar_sessao(sessao_id: str) -> list[dict]:
    """Recarrega o histórico de uma sessão no formato esperado por messages.create()."""
    with _conectar() as conn:
        linhas = conn.execute(
            "SELECT papel, conteudo FROM mensagens WHERE sessao_id = ? ORDER BY id ASC",
            (sessao_id,),
        ).fetchall()
    return [{"role": papel, "content": json.loads(conteudo)} for papel, conteudo in linhas]


def listar_sessoes() -> list[str]:
    with _conectar() as conn:
        linhas = conn.execute(
            "SELECT sessao_id FROM mensagens GROUP BY sessao_id ORDER BY MAX(criado_em) DESC"
        ).fetchall()
    return [linha[0] for linha in linhas]
