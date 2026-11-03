import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import app.core.modelos  # noqa: F401  registra todas las tablas y relaciones
from app.core.database import crear_fabrica_sesiones, crear_motor
from app.core.errores import ErrorDominio
from app.modules.autores.router import router as autores_router
from app.modules.clientes.router import router as clientes_router
from app.modules.editoriales.router import router as editoriales_router
from app.modules.generos.router import router as generos_router
from app.modules.health.router import router as health_router
from app.modules.libros.router import router as libros_router
from app.modules.ventas.router import router as ventas_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("libreria")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Los recursos se crean una vez al arrancar y se comparten vía app.state.
    motor = crear_motor()
    app.state.engine = motor
    app.state.session_factory = crear_fabrica_sesiones(motor)
    logger.info("Motor de base de datos creado")
    try:
        yield
    finally:
        await motor.dispose()  # cierra el pool al apagar
        logger.info("Motor de base de datos cerrado")


app = FastAPI(
    title="Librería",
    description="Catálogo, clientes y ventas · Programación III",
    version="1.0.0",
    lifespan=lifespan,
)


# --- Errores: siempre mensajes propios, nunca texto de la base ni trazas (RN-12) ---

@app.exception_handler(ErrorDominio)
async def manejar_error_dominio(_: Request, exc: ErrorDominio) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.mensaje})


@app.exception_handler(IntegrityError)
async def manejar_integrity_no_traducido(_: Request, exc: IntegrityError) -> JSONResponse:
    # Red de seguridad: todo IntegrityError debería traducirse en el service.
    logger.warning("IntegrityError sin traducir en un service: %s", exc.orig)
    return JSONResponse(
        status_code=409, content={"detail": "La operación no respeta una regla de integridad de los datos."}
    )


@app.exception_handler(SQLAlchemyError)
async def manejar_error_base(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Error de base de datos")
    return JSONResponse(status_code=500, content={"detail": "Error interno al acceder a los datos."})


@app.exception_handler(Exception)
async def manejar_error_inesperado(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error inesperado")
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor."})


for router in (
    health_router,
    editoriales_router,
    generos_router,
    autores_router,
    libros_router,
    clientes_router,
    ventas_router,
):
    app.include_router(router)
