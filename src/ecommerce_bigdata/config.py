"""Cau hinh ket noi va tham so sinh du lieu, doc tu file .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = PROJECT_ROOT / "sql"
ASSETS_DIR = PROJECT_ROOT / "assets"
DOCS_DIR = PROJECT_ROOT / "docs"
EXPORT_DIR = PROJECT_ROOT / "data" / "export"

load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class PostgresConfig:
    host: str = os.getenv("PG_HOST", "127.0.0.1")
    port: int = int(os.getenv("PG_PORT", "5432"))
    dbname: str = os.getenv("PG_DB", "ecommerce_db")
    user: str = os.getenv("PG_USER", "ecom")
    password: str = os.getenv("PG_PASSWORD", "ecom_pass")

    @property
    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.dbname} "
            f"user={self.user} password={self.password}"
        )


@dataclass(frozen=True)
class MongoConfig:
    uri: str = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
    database: str = os.getenv("MONGO_DB", "ecommerce_logs")


@dataclass(frozen=True)
class SeedConfig:
    customers: int = int(os.getenv("SEED_CUSTOMERS", "500"))
    sellers: int = int(os.getenv("SEED_SELLERS", "40"))
    products: int = int(os.getenv("SEED_PRODUCTS", "300"))
    orders: int = int(os.getenv("SEED_ORDERS", "5000"))
    log_events: int = int(os.getenv("SEED_LOG_EVENTS", "50000"))
    random_seed: int = int(os.getenv("RANDOM_SEED", "2026"))


PG = PostgresConfig()
MONGO = MongoConfig()
SEED = SeedConfig()
