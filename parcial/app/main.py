"""Reexporta `app` desde `main.py` en la raíz del proyecto para compatibilidad."""

from main import app, lifespan

__all__ = ["app", "lifespan"]
