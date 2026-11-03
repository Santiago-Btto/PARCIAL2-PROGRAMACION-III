import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionDep
from app.modules.health.schemas import EstadoBase, EstadoVivo

logger = logging.getLogger("libreria.health")

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=EstadoVivo)
async def live():
    """El proceso responde. No toca la base."""
    return EstadoVivo(estado="vivo")


@router.get("/ready", response_model=EstadoBase, responses={503: {"model": EstadoBase}})
async def ready(session: SessionDep):
    """La base responde a SELECT 1."""
    try:
        await session.scalar(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        logger.exception("La base no responde")
        return JSONResponse(status_code=503, content={"estado": "no listo", "base": "sin conexión"})
    return EstadoBase(estado="listo", base="ok")
