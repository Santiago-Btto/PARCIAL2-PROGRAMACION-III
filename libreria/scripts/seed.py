"""Deja la base en un estado inicial conocido (los .http de test/ asumen estos ids).

Uso (con el esquema ya creado por `alembic upgrade head`):
    python -m scripts.seed

Vacía todas las tablas, reinicia los contadores de id y carga:
  editoriales 1-3, géneros 1-3, autores 1-5, libros 1-5, clientes 1-2
  (el 1 con perfil, el 2 sin perfil) y la venta 1. No usa create_all.
"""

import asyncio
from decimal import Decimal

from sqlalchemy import text

from app.core.database import crear_fabrica_sesiones, crear_motor
from app.core.modelos import (
    Autor,
    Cliente,
    Editorial,
    Genero,
    Libro,
    LibroAutor,
    PerfilCliente,
    RenglonVenta,
    Venta,
)

TABLAS = (
    "renglon_venta, venta, perfil_cliente, cliente, libro_autor, libro, autor, genero, editorial"
)


async def cargar() -> None:
    motor = crear_motor(echo=False)
    fabrica = crear_fabrica_sesiones(motor)
    async with motor.begin() as conexion:
        await conexion.execute(text(f"TRUNCATE {TABLAS} RESTART IDENTITY CASCADE"))

    async with fabrica() as session:

        editoriales = [
            Editorial(nombre="Sudamericana", pais="Argentina"),
            Editorial(nombre="Anagrama", pais="España"),
            Editorial(nombre="Emecé", pais="Argentina"),
        ]
        generos = [Genero(nombre="Novela"), Genero(nombre="Cuento"), Genero(nombre="Ensayo")]
        autores = [
            Autor(nombre="Julio Cortázar", nacionalidad="argentina"),
            Autor(nombre="Ricardo Piglia", nacionalidad="argentina"),
            Autor(nombre="Adolfo Bioy Casares", nacionalidad="argentina"),
            Autor(nombre="Silvina Ocampo", nacionalidad="argentina"),
            Autor(nombre="Jorge Luis Borges", nacionalidad="argentina"),
        ]
        # add + flush de a un grupo: los ids quedan 1, 2, 3... en el orden de las listas.
        for grupo in (editoriales, generos, autores):
            session.add_all(grupo)
            await session.flush()

        def libro(isbn, titulo, precio, stock, editorial, genero, autorias):
            nuevo = Libro(
                isbn=isbn,
                titulo=titulo,
                precio=Decimal(precio),
                stock=stock,
                editorial_id=editorial.id,
                genero_id=genero.id if genero else None,
            )
            for orden, (autor, rol) in enumerate(autorias, start=1):
                nuevo.autorias.append(LibroAutor(autor_id=autor.id, rol=rol, orden=orden))
            return nuevo

        cortazar, piglia, bioy, ocampo, borges = autores
        novela, cuento, _ensayo = generos
        sudamericana, anagrama, emece = editoriales
        libros = [
            libro("978-950-07-0386-1", "Rayuela", "25000.00", 10, sudamericana, novela,
                  [(cortazar, "autor")]),
            libro("978-950-07-0001-3", "Bestiario", "18000.00", 5, sudamericana, cuento,
                  [(cortazar, "autor")]),
            libro("978-950-04-0001-9", "Ficciones", "22000.00", 7, emece, cuento,
                  [(borges, "autor")]),
            libro("978-84-339-0002-0", "Respiración artificial", "27000.00", 6, anagrama, novela,
                  [(piglia, "autor")]),
            # Sin género (agregación opcional) y con tres autorías: sirve para el caso C-07.
            libro("978-950-04-0002-6", "Antología de la literatura fantástica", "30000.00", 3,
                  emece, None, [(borges, "autor"), (ocampo, "coautor"), (bioy, "coautor")]),
        ]
        for nuevo in libros:  # de a uno para que los ids sigan el orden de la lista
            session.add(nuevo)
            await session.flush()

        ana = Cliente(nombre="Ana Pérez", email="ana@example.com")
        tomas = Cliente(nombre="Tomás Ríos", email="tomas@example.com")
        for cliente in (ana, tomas):
            session.add(cliente)
            await session.flush()
        session.add(PerfilCliente(cliente_id=ana.id, telefono="261 555-0101", direccion="San Martín 1200, Mendoza"))

        # Venta 1 (de Ana): un renglón. La venta creada en el caso C-06 tendrá el id 2.
        ficciones = libros[2]
        venta = Venta(cliente_id=ana.id, total=ficciones.precio)
        venta.renglones.append(
            RenglonVenta(libro_id=ficciones.id, cantidad=1, precio_unitario=ficciones.precio)
        )
        ficciones.stock -= 1
        session.add(venta)

        await session.commit()
    await motor.dispose()
    print("Datos iniciales cargados: 3 editoriales, 3 géneros, 5 autores, 5 libros, 2 clientes, 1 venta.")


if __name__ == "__main__":
    asyncio.run(cargar())
