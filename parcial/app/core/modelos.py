"""Registro de todos los modelos de tabla.

Importar este módulo garantiza que SQLModel.metadata conozca todas las tablas y
que SQLAlchemy pueda resolver las relaciones declaradas con nombres en texto
("Libro", "Cliente", "Usuario", ...). Lo usan main.py, migrations/env.py y seed.py.
"""

from sqlmodel import SQLModel

from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Usuario,
)
from app.modules.ventas.models import RenglonVenta, Venta

metadata = SQLModel.metadata

__all__ = [
    "AsignacionRol",
    "Autor",
    "Cliente",
    "Editorial",
    "EventoSeguridad",
    "Genero",
    "IntentoAcceso",
    "Libro",
    "LibroAutor",
    "MovimientoStock",
    "PerfilCliente",
    "RenglonVenta",
    "Usuario",
    "Venta",
    "metadata",
]
