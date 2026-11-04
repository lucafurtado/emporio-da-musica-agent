"""Roda uma conversa fixa contra o agente de verdade e salva como .md em examples/.

Uso: python scripts/gerar_exemplo.py <nome_arquivo> "pergunta 1" "pergunta 2" ...
As perguntas são enviadas em sequência, na mesma sessão, simulando uma conversa real.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent import Agente  # noqa: E402


def main() -> None:
    if len(sys.argv) < 3:
        print('Uso: python scripts/gerar_exemplo.py <nome_arquivo.md> "pergunta 1" "pergunta 2" ...')
        raise SystemExit(1)

    nome_arquivo = sys.argv[1]
    perguntas = sys.argv[2:]

    sessao_id = str(uuid.uuid4())
    agente = Agente(sessao_id)

    linhas = []
    for pergunta in perguntas:
        resposta = agente.responder(pergunta)
        linhas.append(f"**Cliente:** {pergunta}\n")
        linhas.append(f"**Rico:** {resposta}\n")
        print(f"Cliente: {pergunta}")
        print(f"Rico: {resposta}")
        print()

    destino = Path(__file__).resolve().parent.parent / "examples" / nome_arquivo
    destino.write_text("\n".join(linhas), encoding="utf-8")
    print(f"Salvo em {destino}")


if __name__ == "__main__":
    main()
