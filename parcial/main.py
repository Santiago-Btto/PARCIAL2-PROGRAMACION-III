import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import app.core.modelos  # noqa: F401  registra todas las tablas y relaciones
from app.core.database import crear_fabrica_sesiones, crear_motor
from app.core.dependencies import verificar_cambio_password_resuelto
from app.core.errores import ErrorDominio
from app.core.security import generar_hash_ficticio, obtener_semaforo_bcrypt
from app.modules.autores.router import router as autores_router
from app.modules.clientes.router import router as clientes_router
from app.modules.editoriales.router import router as editoriales_router
from app.modules.generos.router import router as generos_router
from app.modules.health.router import router as health_router
from app.modules.libros.router import router as libros_router
from app.modules.ventas.router import router as ventas_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("libreria")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Ciclo de vida de la aplicación (Ejercicio 1):
    - Crea el motor asincrónico (con el tamaño del pool de Settings) y la fábrica
      de sesiones y los guarda en app.state.
    - Calcula una única vez el hash ficticio de bcrypt para igualar los tiempos
      del login cuando el correo no existe (RN-08).
    - Al apagar, cierra el motor con dispose().
    """
    motor = crear_motor()
    app.state.engine = motor
    app.state.session_factory = crear_fabrica_sesiones(motor)
    app.state.bcrypt_semaphore = obtener_semaforo_bcrypt()
    app.state.dummy_password_hash = await generar_hash_ficticio()
    logger.info("Motor de base de datos y hash ficticio inicializados")
    try:
        yield
    finally:
        await motor.dispose()
        logger.info("Motor de base de datos cerrado")


app = FastAPI(
    title="Librería",
    description="Catálogo, clientes, ventas, acceso y transacciones · Programación III",
    version="2.0.0",
    lifespan=lifespan,
)


# --- Errores: siempre mensajes propios, nunca texto de la base ni trazas (RN-15) ---

@app.exception_handler(ErrorDominio)
async def manejar_error_dominio(_: Request, exc: ErrorDominio) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.mensaje},
        headers=exc.headers,
    )


@app.exception_handler(IntegrityError)
async def manejar_integrity_no_traducido(_: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("IntegrityError sin traducir en un service: %s", exc.orig)
    return JSONResponse(
        status_code=409,
        content={"detail": "La operación no respeta una regla de integridad de los datos."},
    )


@app.exception_handler(SQLAlchemyError)
async def manejar_error_base(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Error de base de datos")
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno al acceder a los datos."},
    )


@app.exception_handler(Exception)
async def manejar_error_inesperado(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error inesperado")
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor."},
    )


# --- Dos grupos de rutas (Ejercicio 1 y Ejercicio 5, sección 5.10) ---
# 1. Grupo abierto: no pide sesión (o son rutas de /auth para iniciarla o cambiar clave).
grupo_abierto = APIRouter()
grupo_abierto.include_router(health_router)

# 2. Grupo protegido: lleva montado una sola vez el control de cambio obligatorio de contraseña (RN-06).
grupo_protegido = APIRouter(dependencies=[Depends(verificar_cambio_password_resuelto)])

# Temporalmente se incluyen los routers actuales hasta separar sus rutas abiertas/protegidas en Push 2 y 3.
for router in (
    editoriales_router,
    generos_router,
    autores_router,
    libros_router,
    clientes_router,
    ventas_router,
):
    grupo_abierto.include_router(router)

app.include_router(grupo_abierto)
app.include_router(grupo_protegido)
