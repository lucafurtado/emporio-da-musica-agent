"""Configuração central do projeto: caminhos e variáveis de ambiente."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")

PRODUCTS_CSV = DATA_DIR / "products.csv"
CATEGORIES_CSV = DATA_DIR / "categories.csv"
CUSTOMERS_CSV = DATA_DIR / "customers.csv"
ORDERS_CSV = DATA_DIR / "orders.csv"
ORDER_ITEMS_CSV = DATA_DIR / "order_items.csv"
PROMOTIONS_CSV = DATA_DIR / "promotions.csv"
POLICIES_PDF = DATA_DIR / "políticas_da_loja.pdf"
POLICIES_CACHE_TXT = DATA_DIR / "politicas_extraidas.txt"

HISTORY_DB = DATA_DIR / "historico.sqlite3"

STORE_NAME = "Empório da Música"
