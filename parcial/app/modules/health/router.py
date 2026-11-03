import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionDep

logger = logging.getLogger("libreria.health")

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    """El proceso responde. No toca la base (Ejercicio 1)."""
    return {"estado": "vivo"}


@router.get("/ready")
async def ready(session: SessionDep):
    """Ejecuta SELECT 1 y responde 503 si la base no contesta (Ejercicio 1)."""
    try:
        await session.scalar(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        logger.exception("La base no responde")
        return JSONResponse(
            status_code=503,
            content={"estado": "no listo", "base": "sin conexión"},
        )
    return {"estado": "listo", "base": "ok"}
