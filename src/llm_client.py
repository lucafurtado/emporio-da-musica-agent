"""Wrapper fino sobre o SDK da Anthropic: cria o client e trata erros de forma consistente."""

from __future__ import annotations

import sys

import anthropic

from . import config


def get_client() -> anthropic.Anthropic:
    if not config.ANTHROPIC_API_KEY:
        print(
            "ERRO: variável ANTHROPIC_API_KEY não encontrada.\n"
            "Copie .env.example para .env e preencha sua chave da Anthropic.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def criar_mensagem(client: anthropic.Anthropic, **kwargs):
    """Chama messages.create() com tratamento de erro amigável para o CLI."""
    try:
        return client.messages.create(**kwargs)
    except anthropic.AuthenticationError:
        print("ERRO: chave da Anthropic inválida. Confira o .env.", file=sys.stderr)
        raise SystemExit(1)
    except anthropic.RateLimitError as e:
        retry_after = e.response.headers.get("retry-after", "alguns segundos") if e.response else "alguns segundos"
        print(f"Limite de requisições atingido. Tente novamente em {retry_after}.", file=sys.stderr)
        raise
    except anthropic.APIConnectionError:
        print("ERRO: falha de conexão com a API da Anthropic. Confira sua internet.", file=sys.stderr)
        raise
    except anthropic.APIStatusError as e:
        print(f"ERRO da API da Anthropic ({e.status_code}): {e.message}", file=sys.stderr)
        raise
