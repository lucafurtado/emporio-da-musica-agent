"""Interface de linha de comando do agente."""

from __future__ import annotations

import argparse
import sys
import uuid

from .agent import Agente
from .history import listar_sessoes


def main() -> None:
    # Garante saída em UTF-8 mesmo em consoles Windows configurados com outro codepage.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Chat com o Rico, atendente da Empório da Música.")
    parser.add_argument(
        "--sessao",
        help="ID de uma sessão existente para continuar a conversa de onde parou.",
    )
    parser.add_argument(
        "--listar-sessoes",
        action="store_true",
        help="Lista os IDs de sessões salvas e sai.",
    )
    args = parser.parse_args()

    if args.listar_sessoes:
        sessoes = listar_sessoes()
        if not sessoes:
            print("Nenhuma sessão salva ainda.")
        for sessao_id in sessoes:
            print(sessao_id)
        return

    sessao_id = args.sessao or str(uuid.uuid4())
    agente = Agente(sessao_id)

    print("=" * 60)
    print("Empório da Música - atendimento via chat")
    print(f"Sessão: {sessao_id}")
    print("(pra continuar depois, rode com --sessao " + sessao_id + ")")
    print("Digite 'sair' para encerrar.")
    print("=" * 60)

    while True:
        try:
            entrada = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté mais!")
            break

        if not entrada:
            continue
        if entrada.lower() in {"sair", "exit", "quit"}:
            print("Rico: Falou! Qualquer coisa é só chamar. 🎸")
            break

        resposta = agente.responder(entrada)
        print(f"\nRico: {resposta}")


if __name__ == "__main__":
    main()
