"""Carrega e trata os CSVs da operação (produtos, categorias, clientes, pedidos, promoções).

Tratamento aplicado (ver README > "Tratamento de dados" para a justificativa de cada item):
- `specs` em products.csv vem como string JSON -> parseado para dict.
- `price_brl` / `total_brl` normalizados para float.
- Datas (`created_at`, `order_date`, `estimated_delivery`) normalizadas para datetime.
- `category_id` resolvido para o nome da categoria.
- `description` de products.csv é descartada ao montar o catálogo: em parte dos produtos
  (ids 131-144) o texto da descrição não bate com o nome/marca do produto (dado de teste
  proposital). Como o agente nunca pode inventar/city characteristics, optamos por usar só
  os campos estruturados (name, categoria, specs, preço, estoque), que são confiáveis.
"""

from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd

from . import config


def _parse_specs(raw: str) -> dict:
    try:
        return json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _load_categories() -> pd.DataFrame:
    df = pd.read_csv(config.CATEGORIES_CSV)
    df["name"] = df["name"].str.strip()
    return df


def _load_products(categories: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(config.PRODUCTS_CSV)

    df["name"] = df["name"].str.strip()
    df["price_brl"] = pd.to_numeric(df["price_brl"], errors="coerce")
    df["stock_quantity"] = pd.to_numeric(df["stock_quantity"], errors="coerce").fillna(0).astype(int)
    df["status"] = df["status"].str.strip().str.lower()
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["specs"] = df["specs"].apply(_parse_specs)

    df = df.merge(
        categories[["category_id", "name"]].rename(columns={"name": "category_name"}),
        on="category_id",
        how="left",
    )

    # Disponibilidade real: um produto "active" com estoque 0 está temporariamente
    # indisponível, não "fora de catálogo" (status cobre isso) nem "disponível".
    def _disponibilidade(row: pd.Series) -> str:
        if row["status"] == "discontinued":
            return "descontinuado"
        if row["status"] == "coming_soon":
            return "em breve"
        if row["stock_quantity"] <= 0:
            return "indisponível no momento (sem estoque)"
        return "disponível"

    df["disponibilidade"] = df.apply(_disponibilidade, axis=1)
    return df.drop(columns=["description"])


def _load_customers() -> pd.DataFrame:
    df = pd.read_csv(config.CUSTOMERS_CSV)
    df["name"] = df["name"].str.strip()
    df["phone_digits"] = df["phone"].str.replace(r"\D", "", regex=True)
    return df


def _load_orders() -> pd.DataFrame:
    df = pd.read_csv(config.ORDERS_CSV)
    df["total_brl"] = pd.to_numeric(df["total_brl"], errors="coerce")
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["estimated_delivery"] = pd.to_datetime(df["estimated_delivery"], errors="coerce")
    df["status"] = df["status"].str.strip().str.lower()
    df["notes"] = df["notes"].fillna("")
    return df


def _load_order_items() -> pd.DataFrame:
    return pd.read_csv(config.ORDER_ITEMS_CSV)


def _load_promotions() -> pd.DataFrame:
    df = pd.read_csv(config.PROMOTIONS_CSV)
    df["is_active"] = df["is_active"].astype(bool)
    df["discount_percent"] = pd.to_numeric(df["discount_percent"], errors="coerce")
    return df


class DataStore:
    """Agrupa as tabelas já tratadas. Carregada uma única vez por processo."""

    def __init__(self) -> None:
        self.categories = _load_categories()
        self.products = _load_products(self.categories)
        self.customers = _load_customers()
        self.orders = _load_orders()
        self.order_items = _load_order_items()
        self.promotions = _load_promotions()

    def active_promotion_for(self, product_id: int) -> dict | None:
        promos = self.promotions[
            (self.promotions["product_id"] == product_id) & (self.promotions["is_active"])
        ]
        if promos.empty:
            return None
        promo = promos.iloc[0]
        return {
            "descricao": promo["description"],
            "desconto_percent": float(promo["discount_percent"]),
        }


@lru_cache(maxsize=1)
def get_store() -> DataStore:
    return DataStore()
