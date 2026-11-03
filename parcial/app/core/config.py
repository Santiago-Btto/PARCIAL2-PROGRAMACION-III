"""Configuración leída del entorno con pydantic-settings.

Ni la contraseña de la base ni la clave de firma de los tokens tienen un valor
por defecto en el código: si faltan en el entorno o en el archivo .env, la
aplicación no arranca. La dirección de la base se arma con un @computed_field
a partir de las variables sueltas POSTGRES_* usando el driver postgresql+asyncpg.
"""

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # Variables de conexión a PostgreSQL (sin secreto por defecto en POSTGRES_PASSWORD)
    POSTGRES_USER: str = Field(min_length=1)
    POSTGRES_PASSWORD: str = Field(min_length=1)
    POSTGRES_DB: str = Field(min_length=1)
    POSTGRES_HOST: str = Field(default="localhost", min_length=1)
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)

    # Tamaño del pool declarado en la configuración (Ejercicio 1)
    DB_POOL_SIZE: int = Field(default=5, ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=10, ge=0, le=100)
    SQL_ECHO: bool = Field(default=False)

    # Seguridad y autenticación (sin secreto por defecto en JWT_SECRET_KEY)
    JWT_SECRET_KEY: str = Field(min_length=16)
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRE_MINUTES: int = Field(default=30, ge=1)
    COOKIE_SECURE: bool = Field(default=False)

    # Costo de bcrypt declarado en la configuración y límite del semáforo (Ejercicio 4)
    BCRYPT_ROUNDS: int = Field(default=12, ge=4, le=31)
    BCRYPT_MAX_CONCURRENT: int = Field(default=4, ge=1, le=64)

    @field_validator("POSTGRES_PASSWORD", "JWT_SECRET_KEY")
    @classmethod
    def _no_vacio_ni_espacios(cls, valor: str) -> str:
        if not valor or not valor.strip():
            raise ValueError("El secreto no puede estar vacío.")
        return valor

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        usuario = quote_plus(self.POSTGRES_USER)
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+asyncpg://{usuario}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
