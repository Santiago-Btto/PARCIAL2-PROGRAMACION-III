"""Seguridad: hash con bcrypt fuera del bucle de eventos y tokens JWT (Ejercicio 4).

- El costo de bcrypt y el límite del semáforo salen de Settings (no están fijos).
- Toda llamada a bcrypt corre en un hilo aparte (asyncio.to_thread) bajo un
  asyncio.Semaphore que limita cuántas corren a la vez.
- Todo campo que termina en bcrypt acepta como máximo 72 bytes.
- El token JWT se firma con sub, exp y los roles vigentes al emitirlo. Viaja
  únicamente en la cookie HttpOnly `access_token`.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from fastapi import Response

from app.core.config import get_settings
from app.core.errores import NoAutenticado

COOKIE_NAME = "access_token"
MAX_PASSWORD_BYTES = 72

_semaforo_bcrypt: asyncio.Semaphore | None = None


def obtener_semaforo_bcrypt() -> asyncio.Semaphore:
    global _semaforo_bcrypt
    if _semaforo_bcrypt is None:
        settings = get_settings()
        _semaforo_bcrypt = asyncio.Semaphore(settings.BCRYPT_MAX_CONCURRENT)
    return _semaforo_bcrypt


def _hash_password_sync(password: str, rounds: int) -> str:
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > MAX_PASSWORD_BYTES:
        raise ValueError("La contraseña no puede superar los 72 bytes.")
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def _verificar_password_sync(password: str, password_hash: str) -> bool:
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(pwd_bytes, password_hash.encode("utf-8"))


async def hashear_password(password: str) -> str:
    """Calcula el hash bcrypt fuera del bucle de eventos y bajo semáforo."""
    settings = get_settings()
    semaforo = obtener_semaforo_bcrypt()
    async with semaforo:
        return await asyncio.to_thread(_hash_password_sync, password, settings.BCRYPT_ROUNDS)


async def verificar_password(password: str, password_hash: str) -> bool:
    """Verifica la contraseña con bcrypt fuera del bucle de eventos y bajo semáforo."""
    semaforo = obtener_semaforo_bcrypt()
    async with semaforo:
        return await asyncio.to_thread(_verificar_password_sync, password, password_hash)


async def generar_hash_ficticio() -> str:
    """Se llama una sola vez en el lifespan (Ejercicio 1 y RN-08) para igualar
    el tiempo de respuesta cuando el correo del login no existe.
    """
    return await hashear_password("clave_ficticia_para_tiempo_constante_libreria")


def crear_token_acceso(usuario_id: int, roles: list[str]) -> tuple[str, int]:
    """Emite un JWT firmado con sub, exp y roles (informativos).
    Devuelve (token, expira_en_segundos).
    """
    settings = get_settings()
    expira_en_segundos = settings.JWT_EXPIRE_MINUTES * 60
    ahora = datetime.now(UTC)
    expira = ahora + timedelta(seconds=expira_en_segundos)
    payload: dict[str, Any] = {
        "sub": str(usuario_id),
        "roles": list(roles),
        "iat": int(ahora.timestamp()),
        "exp": int(expira.timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expira_en_segundos


def decodificar_token_acceso(token: str) -> dict[str, Any]:
    """Verifica firma y expiración del JWT. Lanza NoAutenticado (401) si falla."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise NoAutenticado("La sesión expiró. Iniciá sesión nuevamente.") from exc
    except jwt.InvalidTokenError as exc:
        raise NoAutenticado("Token de sesión inválido.") from exc


def setear_cookie_acceso(response: Response, token: str, max_age: int) -> None:
    """Coloca el JWT en la cookie HttpOnly `access_token` (Ejercicio 4)."""
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=max_age,
        secure=settings.COOKIE_SECURE,
        path="/",
    )


def borrar_cookie_acceso(response: Response) -> None:
    """Elimina la cookie `access_token` al cerrar sesión."""
    settings = get_settings()
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )
