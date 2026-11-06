"""Deja la base en el estado inicial conocido que usan los casos de prueba de test/.

Uso (con el esquema ya creado por `alembic upgrade head`):
    python seed.py

Vacía todas las tablas, reinicia los contadores de id y carga:

- Usuarios: admin@example.com y admin2@example.com (ADMIN), vendedor@example.com
  (VENDEDOR), ana@example.com (CLIENTE) y nuevo@example.com (VENDEDOR, con el
  cambio de contraseña obligatorio).
- Editoriales 1-3, géneros 1-3 y autores 1-6.
- Libros 1-5: Rayuela, Antología de la literatura fantástica, Ficciones,
  Respiración artificial y Bestiario.
- Clientes 1-3: Lucía Fernández (con perfil), Tomás Ríos y Ana Paz (con el usuario
  ana@example.com).
- La venta 1, de Lucía, registrada por vendedor@example.com.
- Una línea de evento_seguridad con el actor SISTEMA.

El stock NO se escribe a mano: cada libro nace con stock 0 y recibe su «Stock
inicial» por `cambiar_stock`, y la venta 1 se registra con el mismo service que
usa POST /ventas. Así, en los cinco libros, stock == suma de sus movimientos.

Las contraseñas son de mentira y viven sólo en este archivo. No se usa create_all.
"""

import asyncio
from decimal import Decimal

from sqlalchemy import text

import app.core.modelos  # noqa: F401  registra todas las tablas y relaciones
from app.core.database import crear_fabrica_sesiones, crear_motor
from app.core.modelos import (
    AsignacionRol,
    Autor,
    Cliente,
    Editorial,
    EventoSeguridad,
    Genero,
    Libro,
    LibroAutor,
    PerfilCliente,
    Usuario,
)
from app.core.security import hashear_password
from app.modules.libros.service import cambiar_stock
from app.modules.ventas import service as ventas_service
from app.modules.ventas.schemas import RenglonCreate, VentaCreate
from app.modules.ventas.unit_of_work import VentasUnitOfWork

TABLAS = (
    "movimiento_stock, renglon_venta, venta, perfil_cliente, cliente, libro_autor, libro, "
    "autor, genero, editorial, asignacion_rol, intento_acceso, evento_seguridad, usuario"
)

# (email, nombre, contraseña de mentira, rol, debe_cambiar_password)
USUARIOS = (
    ("admin@example.com", "Administración", "admin1234", "ADMIN", False),
    ("admin2@example.com", "Administración 2", "admin21234", "ADMIN", False),
    ("vendedor@example.com", "Vendedor de mostrador", "vendedor1234", "VENDEDOR", False),
    ("ana@example.com", "Ana Paz", "ana12345", "CLIENTE", False),
    ("nuevo@example.com", "Vendedor nuevo", "provisoria1234", "VENDEDOR", True),
)


async def cargar() -> None:
    # bcrypt corre fuera del bucle (to_thread + semáforo) y ANTES de abrir la transacción.
    hashes = await asyncio.gather(*(hashear_password(clave) for _, _, clave, _, _ in USUARIOS))

    motor = crear_motor(echo=False)
    fabrica = crear_fabrica_sesiones(motor)
    # TRUNCATE no dispara el disparador de sólo agregado (que es FOR EACH ROW sobre
    # UPDATE y DELETE): vaciar la base para el estado inicial no modifica filas.
    async with motor.begin() as conexion:
        await conexion.execute(text(f"TRUNCATE {TABLAS} RESTART IDENTITY CASCADE"))

    async with fabrica() as session:
        uow = VentasUnitOfWork(session)
        async with uow:
            # Usuarios y roles. De a uno con flush: los ids siguen el orden de la lista.
            usuarios: dict[str, Usuario] = {}
            for (email, nombre, _, rol, debe_cambiar), pwd_hash in zip(USUARIOS, hashes, strict=True):
                usuario = Usuario(
                    email=email,
                    nombre=nombre,
                    password_hash=pwd_hash,
                    debe_cambiar_password=debe_cambiar,
                )
                session.add(usuario)
                await session.flush()
                session.add(AsignacionRol(usuario_id=usuario.id, rol=rol))  # type: ignore[arg-type]
                usuarios[email] = usuario
            await session.flush()

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
                Autor(nombre="Rodolfo Walsh", nacionalidad="argentina"),
            ]
            for grupo in (editoriales, generos, autores):
                for entidad in grupo:
                    session.add(entidad)
                    await session.flush()

            cortazar, piglia, bioy, ocampo, borges, _walsh = autores
            novela, cuento, _ensayo = generos
            sudamericana, anagrama, emece = editoriales

            # (isbn, título, precio, stock inicial, editorial, género, autorías)
            catalogo = (
                ("978-950-00-0001-1", "Rayuela", "25000.00", 11, sudamericana, novela,
                 [(cortazar, "autor")]),
                # Sin género (agregación opcional) y con tres autorías.
                ("978-950-00-0002-8", "Antología de la literatura fantástica", "30000.00", 5,
                 emece, None, [(borges, "autor"), (ocampo, "coautor"), (bioy, "coautor")]),
                ("978-950-00-0003-4", "Ficciones", "22000.00", 10, emece, cuento,
                 [(borges, "autor")]),
                ("978-950-00-0004-1", "Respiración artificial", "27000.00", 3, anagrama, novela,
                 [(piglia, "autor")]),
                ("978-950-00-0005-9", "Bestiario", "18000.00", 1, sudamericana, cuento,
                 [(cortazar, "autor")]),
            )
            admin = usuarios["admin@example.com"]
            libros: list[Libro] = []
            for isbn, titulo, precio, stock_inicial, editorial, genero, autorias in catalogo:
                libro = Libro(
                    isbn=isbn,
                    titulo=titulo,
                    precio=Decimal(precio),
                    stock=0,
                    editorial_id=editorial.id,  # type: ignore[arg-type]
                    genero_id=genero.id if genero else None,
                    autorias=[
                        LibroAutor(autor_id=autor.id, rol=rol, orden=orden)  # type: ignore[arg-type]
                        for orden, (autor, rol) in enumerate(autorias, start=1)
                    ],
                )
                libro = await uow.libros.add(libro)
                await cambiar_stock(
                    uow,
                    libro_id=libro.id,  # type: ignore[arg-type]
                    cantidad=stock_inicial,
                    usuario_id=admin.id,  # type: ignore[arg-type]
                    motivo="Stock inicial",
                )
                libros.append(libro)

            lucia = Cliente(nombre="Lucía Fernández", email="lucia@example.com")
            tomas = Cliente(nombre="Tomás Ríos", email="tomas@example.com")
            ana = Cliente(
                nombre="Ana Paz",
                email="ana@example.com",
                usuario_id=usuarios["ana@example.com"].id,
            )
            for cliente in (lucia, tomas, ana):
                await uow.clientes.add(cliente)
            session.add(
                PerfilCliente(
                    cliente_id=lucia.id,  # type: ignore[arg-type]
                    telefono="261 555-0101",
                    direccion="San Martín 1200, Mendoza",
                )
            )
            session.add(EventoSeguridad(actor="SISTEMA", accion="Carga de los datos iniciales"))

        # Venta 1: la misma operación que POST /ventas (precio copiado, total calculado,
        # descuento de stock y un movimiento por renglón, en una sola transacción).
        rayuela, _antologia, ficciones, _respiracion, _bestiario = libros
        venta = await ventas_service.crear(
            VentasUnitOfWork(session),
            VentaCreate(
                cliente_id=lucia.id,  # type: ignore[arg-type]
                renglones=[
                    RenglonCreate(libro_id=rayuela.id, cantidad=1),  # type: ignore[arg-type]
                    RenglonCreate(libro_id=ficciones.id, cantidad=2),  # type: ignore[arg-type]
                ],
            ),
            usuario_id=usuarios["vendedor@example.com"].id,  # type: ignore[arg-type]
        )

    await motor.dispose()
    print(
        "Datos iniciales cargados: 5 usuarios, 3 editoriales, 3 géneros, 6 autores, 5 libros, "
        f"3 clientes y la venta {venta.id} (total {venta.total})."
    )


if __name__ == "__main__":
    asyncio.run(cargar())
