"""Registro de todos los modelos de tabla.

Importar este módulo garantiza que SQLModel.metadata conozca todas las tablas y
que SQLAlchemy pueda resolver las relaciones declaradas con nombres en texto
("Libro", "Cliente", ...). Lo usan app/main.py, migrations/env.py y los scripts.
"""

from sqlmodel import SQLModel

from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor
from app.modules.ventas.models import RenglonVenta, Venta

metadata = SQLModel.metadata

__all__ = [
    "Autor",
    "Cliente",
    "Editorial",
    "Genero",
    "Libro",
    "LibroAutor",
    "PerfilCliente",
    "RenglonVenta",
    "Venta",
    "metadata",
]
