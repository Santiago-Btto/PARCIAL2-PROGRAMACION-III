from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar

from app.core.errores import Conflicto, MapaRestricciones, NoEncontrado, traducir_integrity_error
from app.modules.libros.models import Libro, LibroAutor
from app.modules.libros.schemas import LibroCreate, LibroUpdate

# Cada restricción de la base se traduce a un mensaje propio (RN-12).
ERRORES: MapaRestricciones = {
    "uq_libro_isbn": (Conflicto, "Ya existe un libro con ese ISBN."),
    "fk_libro_editorial_id_editorial": (Conflicto, "La editorial indicada no existe."),
    "fk_libro_genero_id_genero": (Conflicto, "El género indicado no existe."),
    "fk_libro_autor_autor_id_autor": (Conflicto, "Alguno de los autores indicados no existe."),
    "pk_libro_autor": (Conflicto, "Un mismo autor no puede figurar dos veces en el libro."),
    "ck_libro_precio_positivo": (Conflicto, "El precio debe ser mayor que cero."),
    "ck_libro_stock_no_negativo": (Conflicto, "El stock no puede ser negativo."),
    "ck_libro_autor_orden_positivo": (Conflicto, "El orden de cada autoría empieza en 1."),
    "ck_libro_autor_rol_valido": (Conflicto, "El rol de la autoría no es válido."),
}


def consulta_listado() -> SelectOfScalar[Libro]:
    """Libros con editorial y género: relaciones a uno -> joinedload (una sola consulta)."""
    return (
        select(Libro)
        .options(
            joinedload(Libro.editorial),  # type: ignore[arg-type]
            joinedload(Libro.genero),  # type: ignore[arg-type]
        )
        .order_by(col(Libro.id))
    )


def _escapar_like(texto: str) -> str:
    # % y _ del usuario se buscan literalmente, no como comodines.
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def listar(
    session: AsyncSession,
    limit: int,
    offset: int,
    titulo: str | None = None,
    genero_id: int | None = None,
) -> list[Libro]:
    consulta = consulta_listado()
    if titulo:
        # RN-11: ILIKE con parámetro ligado. El texto del usuario viaja como valor,
        # nunca se concatena al SQL; "' OR '1'='1" se busca como texto literal.
        consulta = consulta.where(col(Libro.titulo).ilike(f"%{_escapar_like(titulo)}%", escape="\\"))
    if genero_id is not None:
        consulta = consulta.where(Libro.genero_id == genero_id)
    consulta = consulta.limit(limit).offset(offset)
    return list((await session.exec(consulta)).all())


async def obtener_detalle(session: AsyncSession, libro_id: int) -> Libro:
    """Libro con editorial, género y autores en un número FIJO de consultas (2):

    1. libro JOIN editorial LEFT JOIN genero            (joinedload, relaciones a uno)
    2. libro_autor JOIN autor WHERE libro_id IN (...)    (selectinload de la colección
                                                          + joinedload del autor)
    No crece con la cantidad de autores (caso C-07).
    """
    consulta = (
        select(Libro)
        .where(Libro.id == libro_id)
        .options(
            joinedload(Libro.editorial),  # type: ignore[arg-type]
            joinedload(Libro.genero),  # type: ignore[arg-type]
            selectinload(Libro.autorias).joinedload(LibroAutor.autor),  # type: ignore[arg-type]
        )
        # Refresca también los objetos que ya estaban en la sesión (p. ej. recién creados).
        .execution_options(populate_existing=True)
    )
    libro = (await session.exec(consulta)).first()
    if libro is None:
        raise NoEncontrado("El libro no existe.")
    return libro


async def crear(session: AsyncSession, datos: LibroCreate) -> Libro:
    """Alta con relaciones.

    - editorial_id y genero_id: agregación, viaja el id de algo que ya existe.
    - autores: muchos a muchos con datos; cada autoría trae autor_id + rol + orden.

    Ningún if consulta antes si los ids existen: se escribe y, si la base rechaza
    una clave foránea, el IntegrityError se traduce a 409.
    """
    libro = Libro.model_validate(datos.model_dump(exclude={"autores"}))
    for autoria in datos.autores:
        libro.autorias.append(
            LibroAutor(autor_id=autoria.autor_id, rol=autoria.rol, orden=autoria.orden)
        )
    session.add(libro)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc, ERRORES) from None
    return await obtener_detalle(session, libro.id)  # type: ignore[arg-type]


async def actualizar(session: AsyncSession, libro_id: int, datos: LibroUpdate) -> Libro:
    libro = await session.get(Libro, libro_id)
    if libro is None:
        raise NoEncontrado("El libro no existe.")
    libro.sqlmodel_update(datos.model_dump(exclude_unset=True))  # PATCH parcial
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc, ERRORES) from None
    return await obtener_detalle(session, libro_id)
