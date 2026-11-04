"""Ferramentas de dados que o agente pode chamar via function calling.

Princípio central: o LLM NUNCA calcula ou "lembra" preço, estoque ou status de pedido.
Essas funções leem direto do pandas e devolvem o resultado pronto; o LLM só decide
quando chamar cada uma e como apresentar o resultado em texto.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .data_loader import get_store


def _produto_para_dict(row, store) -> dict[str, Any]:
    promo = store.active_promotion_for(int(row["product_id"]))
    preco_tabela = float(row["price_brl"])
    produto = {
        "nome": row["name"],
        "categoria": row["category_name"],
        "preco_tabela_brl": round(preco_tabela, 2),
        "disponibilidade": row["disponibilidade"],
        "especificacoes": row["specs"],
    }
    if promo:
        preco_final = round(preco_tabela * (1 - promo["desconto_percent"] / 100), 2)
        produto["promocao_ativa"] = {
            "descricao": promo["descricao"],
            "desconto_percent": promo["desconto_percent"],
            "preco_com_desconto_brl": preco_final,
        }
    return produto


def buscar_produtos(
    nome: str | None = None,
    categoria: str | None = None,
    preco_maximo: float | None = None,
    somente_disponiveis: bool = False,
) -> dict[str, Any]:
    """Busca produtos no catálogo por nome (parcial), categoria e/ou preço máximo.

    Args:
        nome: trecho do nome do produto a buscar (ex.: "Takamine GD20"). Opcional.
        categoria: nome da categoria (ex.: "Violões", "Guitarras", "Ukuleles"). Opcional.
        preco_maximo: filtra produtos com preço de tabela até esse valor em reais. Opcional.
        somente_disponiveis: se True, exclui produtos sem estoque, descontinuados ou "em breve".
    """
    store = get_store()
    df = store.products

    if nome:
        df = df[df["name"].str.contains(nome, case=False, na=False, regex=False)]
    if categoria:
        df = df[df["category_name"].str.contains(categoria, case=False, na=False, regex=False)]
    if preco_maximo is not None:
        df = df[df["price_brl"] <= float(preco_maximo)]
    if somente_disponiveis:
        df = df[df["disponibilidade"] == "disponível"]

    df = df.sort_values("price_brl")

    if df.empty:
        return {"total_encontrado": 0, "produtos": []}

    produtos = [_produto_para_dict(row, store) for _, row in df.iterrows()]
    return {"total_encontrado": len(produtos), "produtos": produtos}


def consultar_pedido(pedido_id: int, confirmacao_cliente: str) -> dict[str, Any]:
    """Consulta o status de um pedido. Exige confirmação de identidade do cliente.

    Por política da loja, status de pedido só pode ser informado depois de confirmar
    um dado do cliente dono do pedido (nome completo ou telefone cadastrado).

    Args:
        pedido_id: número do pedido informado pelo cliente.
        confirmacao_cliente: nome completo OU telefone que o cliente informou para
            confirmar que o pedido é dele.
    """
    store = get_store()
    pedido = store.orders[store.orders["order_id"] == int(pedido_id)]
    if pedido.empty:
        return {"encontrado": False, "erro": "Pedido não encontrado."}
    pedido = pedido.iloc[0]

    cliente = store.customers[store.customers["customer_id"] == pedido["customer_id"]]
    if cliente.empty:
        return {"encontrado": False, "erro": "Pedido não encontrado."}
    cliente = cliente.iloc[0]

    confirmacao_norm = confirmacao_cliente.strip().lower()
    confirmacao_digits = "".join(ch for ch in confirmacao_cliente if ch.isdigit())

    nome_confere = confirmacao_norm and confirmacao_norm in cliente["name"].strip().lower()
    telefone_confere = confirmacao_digits and confirmacao_digits in cliente["phone_digits"]

    if not (nome_confere or telefone_confere):
        return {
            "encontrado": True,
            "identidade_confirmada": False,
            "erro": (
                "O nome ou telefone informado não confere com o cadastro do pedido. "
                "Peça para o cliente confirmar o nome completo ou telefone usados na compra "
                "antes de revelar qualquer detalhe do pedido."
            ),
        }

    itens = store.order_items[store.order_items["order_id"] == pedido["order_id"]]
    produtos = store.products.set_index("product_id")
    itens_detalhados = []
    for _, item in itens.iterrows():
        prod = produtos.loc[item["product_id"]] if item["product_id"] in produtos.index else None
        itens_detalhados.append(
            {
                "produto": prod["name"] if prod is not None else f"produto #{item['product_id']}",
                "quantidade": int(item["quantity"]),
            }
        )

    return {
        "encontrado": True,
        "identidade_confirmada": True,
        "pedido_id": int(pedido["order_id"]),
        "status": pedido["status"],
        "data_pedido": pedido["order_date"].strftime("%d/%m/%Y") if pd.notna(pedido["order_date"]) else None,
        "total_brl": round(float(pedido["total_brl"]), 2),
        "forma_pagamento": pedido["payment_method"],
        "codigo_rastreio": pedido["tracking_code"] if pd.notna(pedido["tracking_code"]) else None,
        "previsao_entrega": (
            pedido["estimated_delivery"].strftime("%d/%m/%Y")
            if pd.notna(pedido["estimated_delivery"])
            else None
        ),
        "itens": itens_detalhados,
        "observacoes": pedido["notes"] or None,
    }


def listar_promocoes() -> dict[str, Any]:
    """Lista as promoções ativas no momento, com produto, desconto e preço final."""
    store = get_store()
    ativas = store.promotions[store.promotions["is_active"]]
    if ativas.empty:
        return {"total_ativas": 0, "promocoes": []}

    produtos = store.products.set_index("product_id")
    promocoes = []
    for _, promo in ativas.iterrows():
        if promo["product_id"] not in produtos.index:
            continue
        prod = produtos.loc[promo["product_id"]]
        preco_tabela = float(prod["price_brl"])
        desconto = float(promo["discount_percent"])
        promocoes.append(
            {
                "produto": prod["name"],
                "descricao_promocao": promo["description"],
                "desconto_percent": desconto,
                "preco_tabela_brl": round(preco_tabela, 2),
                "preco_com_desconto_brl": round(preco_tabela * (1 - desconto / 100), 2),
                "disponibilidade": prod["disponibilidade"],
            }
        )
    return {"total_ativas": len(promocoes), "promocoes": promocoes}


TOOL_DEFINITIONS = [
    {
        "name": "buscar_produtos",
        "description": (
            "Busca instrumentos no catálogo da loja por nome, categoria e/ou preço máximo. "
            "Use sempre que o cliente perguntar sobre produtos disponíveis, preço de um "
            "instrumento específico, ou pedir recomendações dentro de um orçamento."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nome": {
                    "type": "string",
                    "description": "Trecho do nome do produto, ex.: 'Takamine GD20'.",
                },
                "categoria": {
                    "type": "string",
                    "description": "Categoria do instrumento, ex.: 'Violões', 'Guitarras', 'Ukuleles'.",
                },
                "preco_maximo": {
                    "type": "number",
                    "description": "Preço máximo em reais (preço de tabela, sem considerar desconto PIX).",
                },
                "somente_disponiveis": {
                    "type": "boolean",
                    "description": "Se true, mostra só produtos com estoque disponível agora.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "consultar_pedido",
        "description": (
            "Consulta o status, itens e rastreio de um pedido pelo número. Exige que o "
            "cliente já tenha informado o nome completo ou telefone cadastrado para "
            "confirmar que o pedido é dele - nunca chame sem essa confirmação."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pedido_id": {"type": "integer", "description": "Número do pedido."},
                "confirmacao_cliente": {
                    "type": "string",
                    "description": "Nome completo ou telefone que o cliente informou.",
                },
            },
            "required": ["pedido_id", "confirmacao_cliente"],
            "additionalProperties": False,
        },
    },
    {
        "name": "listar_promocoes",
        "description": "Lista todas as promoções ativas no momento, com produto e preço com desconto.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
]

TOOL_HANDLERS = {
    "buscar_produtos": buscar_produtos,
    "consultar_pedido": consultar_pedido,
    "listar_promocoes": listar_promocoes,
}
