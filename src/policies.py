"""Extrai o texto do manual de políticas (PDF) para injetar no system prompt.

Decisão: o PDF tem ~1.500 palavras (8 páginas curtas) - cabe inteiro no prompt sem
estourar contexto nem custo relevante. Por isso não implementamos RAG/embeddings:
seria complexidade sem benefício para um documento desse tamanho. Ver README para
a justificativa completa e o que mudaria se o manual fosse muito maior.

O texto é extraído uma vez com pypdf e cacheado em disco (arquivo fora do git) para
não reprocessar o PDF a cada execução do CLI.
"""

from __future__ import annotations

import re

from pypdf import PdfReader

from . import config


def _limpar_texto_pagina(texto: str) -> str:
    """pypdf extrai esse PDF com uma palavra por linha (o PDF posiciona cada palavra
    como um elemento de texto separado). Colapsamos todo espaço em branco em espaço
    simples; como resultado cada página vira um bloco de texto corrido, o que ainda é
    perfeitamente legível para o modelo (os títulos numerados continuam no texto)."""
    return re.sub(r"\s+", " ", texto).strip()


def _extrair_do_pdf() -> str:
    reader = PdfReader(str(config.POLICIES_PDF))
    paginas = [_limpar_texto_pagina(page.extract_text() or "") for page in reader.pages]
    return "\n\n".join(paginas).strip()


def carregar_politicas() -> str:
    if config.POLICIES_CACHE_TXT.exists():
        return config.POLICIES_CACHE_TXT.read_text(encoding="utf-8")

    texto = _extrair_do_pdf()
    config.POLICIES_CACHE_TXT.write_text(texto, encoding="utf-8")
    return texto
