"""Configuración leída del entorno.

La dirección de la base nunca se escribe en el código: se lee de la variable
DATABASE_URL, que en desarrollo viene del archivo .env (no versionado).
"""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    sql_echo: bool


def _a_bool(valor: str | None) -> bool:
    return (valor or "").strip().lower() in {"1", "true", "si", "sí", "yes", "on"}


@lru_cache
def get_settings() -> Settings:
    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "Falta la variable DATABASE_URL. Copiá env.example a .env y completala."
        )
    if not url.startswith("postgresql+asyncpg://"):
        raise RuntimeError(
            "DATABASE_URL debe usar el controlador asincrónico: postgresql+asyncpg://..."
        )
    # SQL_ECHO=true muestra en la consola cada consulta emitida (diagnóstico, caso C-07).
    return Settings(database_url=url, sql_echo=_a_bool(os.getenv("SQL_ECHO")))
