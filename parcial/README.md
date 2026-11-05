# Librería · acceso, transacciones y capas (Parcial, capítulos 1 a 6)

Programación III · Tecnicatura Universitaria en Programación · UTN FRM

API asincrónica con FastAPI, SQLModel, SQLAlchemy 2.0 asincrónico, PostgreSQL 16 y
Alembic. Continúa el TP de la librería (catálogo, clientes y ventas) y le agrega
usuarios y roles, autenticación con cookie `HttpOnly`, repositorios con Unit of Work,
borrado lógico de libros y movimientos de stock de sólo agregado.

## Integrantes

- Santiago (completar apellido)
- Nicolás Uriel Moron Gutierrez
- Ignacio (completar apellido)
- Mateo Algañaraz

## Levantar el proyecto desde cero

Requisitos: Python 3.12 o superior y PostgreSQL 16 en ejecución. Todos los comandos
se ejecutan desde esta carpeta (`parcial/`).

### 1. Entorno virtual

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 2. Dependencias

```bash
pip install -r requirements.txt
```

### 3. Base de datos y archivo `.env`

Crear una base vacía:

```sql
CREATE DATABASE libreria;
```

Copiar `env.example` como `.env` y completar los valores:

```bash
cp env.example .env        # Windows: copy env.example .env
```

| Variable | Qué es |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` | Con estas variables se arma la dirección `postgresql+asyncpg://...` |
| `JWT_SECRET_KEY` | Clave de firma de los tokens |
| `JWT_EXPIRE_MINUTES` | Duración del token y de la cookie (por defecto 30) |
| `COOKIE_SECURE` | `true` sólo si se sirve por HTTPS |
| `BCRYPT_ROUNDS`, `BCRYPT_MAX_CONCURRENT` | Costo de bcrypt y cuántos hash corren a la vez |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | Tamaño del pool de conexiones |
| `SQL_ECHO` | `true` para ver cada consulta en la consola |

La clave de firma se genera con:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

`POSTGRES_PASSWORD` y `JWT_SECRET_KEY` no tienen valor por defecto en el código: si
faltan, la aplicación no arranca. El `.env` no se versiona.

### 4. Esquema con Alembic

```bash
alembic upgrade head
```

El esquema se crea sólo con migraciones (no se usa `create_all`). Son cuatro: las dos
del TP, la tercera autogenerada (tablas de acceso, `movimiento_stock` y los cambios de
`cliente` y `libro`) y la cuarta escrita a mano (el disparador de sólo agregado sobre
`movimiento_stock`). Para comprobar la reversibilidad:

```bash
alembic downgrade base
alembic upgrade head
```

### 5. Datos iniciales

```bash
python seed.py
```

Vacía las tablas, reinicia los ids y carga el estado que usan los casos de prueba:

| Recurso | Datos |
|---|---|
| Usuarios | 1 `admin@example.com` y 2 `admin2@example.com` (ADMIN), 3 `vendedor@example.com` (VENDEDOR), 4 `ana@example.com` (CLIENTE), 5 `nuevo@example.com` (VENDEDOR, con el cambio de contraseña obligatorio) |
| Editoriales | 1 Sudamericana, 2 Anagrama, 3 Emecé |
| Géneros | 1 Novela, 2 Cuento, 3 Ensayo |
| Autores | 1 Cortázar, 2 Piglia, 3 Bioy Casares, 4 Silvina Ocampo, 5 Borges, 6 Walsh |
| Libros | 1 Rayuela (stock 10), 2 Antología de la literatura fantástica (5), 3 Ficciones (8), 4 Respiración artificial (3), 5 Bestiario (1) |
| Clientes | 1 Lucía Fernández (con perfil), 2 Tomás Ríos, 3 Ana Paz (con el usuario `ana@example.com`) |
| Venta | 1, de Lucía, registrada por el vendedor: 1 Rayuela y 2 Ficciones, total 69000.00 |
| Movimientos | Un «Stock inicial» por libro (Rayuela 11 y Ficciones 10) y las dos salidas de la venta 1 (−1 y −2) |
| Seguridad | Una línea con el actor `SISTEMA`: «Carga de los datos iniciales» |

Contraseñas de mentira del seed: `admin1234`, `admin21234`, `vendedor1234`,
`ana12345` y `provisoria1234` (en ese orden). El stock no se escribe a mano: cada
libro recibe su stock inicial por el mismo punto único de escritura que usa la API,
y la venta 1 se registra con el mismo service que `POST /ventas`.

### 6. Servidor

```bash
uvicorn main:app --reload
```

Documentación interactiva en http://localhost:8000/docs.

### 7. Casos de prueba

Los archivos `.http` de `test/` se ejecutan con la extensión **REST Client** de VS Code,
en orden y después de `python seed.py`. Cada petición indica en un comentario la
respuesta esperada. Cada login se nombra con `# @name` y los pedidos de esa sesión
llevan `# @no-cookie-jar` y la cookie de esa respuesta, así conviven varias sesiones.

| Archivo | Casos |
|---|---|
| `test/01_salud_y_configuracion.http` | `/health/live`, `/health/ready` y C-01 |
| `test/02_autenticacion_y_usuarios.http` | C-02, C-03, C-04, C-05, C-07, C-08, C-09, personal e historial de seguridad |
| `test/03_catalogo_y_stock.http` | Catálogo público, C-06 (catálogo), alta con stock inicial, C-13 y C-16 |
| `test/04_clientes_y_ventas.http` | Clientes, C-06, C-10, C-11, C-12, C-15 y `/mis-ventas` |
| `test/solo_agregado.sql` | C-14: `UPDATE` y `DELETE` sobre `movimiento_stock` rechazados por el disparador |

Las pruebas unitarias (con dobles del Unit of Work) se corren con:

```bash
pip install pytest anyio
pytest test -q
```

Las de PostgreSQL (`test_catalogo_postgres.py`) se activan definiendo
`CATALOGO_TEST_DATABASE_URL` con una base local `*_test` ya migrada.

### 8. Evidencias (`evidencia/`)

**C-14** · con el seed cargado:

```bash
psql -U postgres -d libreria -f test/solo_agregado.sql > evidencia/C-14_psql.txt 2>&1
```

**C-15** · con el seed cargado y el caso C-15 de `04_clientes_y_ventas.http` ejecutado
(registra una venta de 4 renglones):

```bash
python -m scripts.evidencia_c15
```

El script usa el mismo método del repositorio que `GET /ventas/{id}`, muestra cada SQL
y lo guarda en `evidencia/C-15_consultas.txt`: el detalle de la venta de 2 renglones y
el de la de 4 se resuelven con la misma cantidad de consultas (2: venta con su cliente,
y renglones con su libro). También se ve en la consola con `SQL_ECHO=true`.

## Estructura

```
main.py                    aplicación, lifespan, manejadores de error y los dos grupos de rutas
seed.py                    deja la base en el estado inicial conocido
app/core/
  config.py                Settings con pydantic-settings
  database.py              motor y fábrica de sesiones (los crea el lifespan) y get_session
  security.py              bcrypt fuera del bucle con semáforo, emisión y verificación del token
  dependencies.py          usuario actual, roles vigentes, cambio obligatorio y requiere_rol
  repository.py            BaseRepository[T] y SoftDeleteRepository[T]
  paginacion.py            envoltorio {items, total, page, size, pages}
  unit_of_work.py          UnitOfWork base: confirma o revierte al salir; no cierra la sesión
  errores.py               errores de dominio y traducción del IntegrityError
app/modules/<módulo>/      health, usuarios, editoriales, generos, autores, libros, clientes, ventas
  models.py                tablas, restricciones y relaciones
  schemas.py               contratos de entrada (extra="forbid") y de salida
  repository.py            repositorios de cada entidad, con la precarga adentro del método
  unit_of_work.py          Unit of Work del módulo, con los repositorios que necesita
  service.py               reglas de negocio: recibe el Unit of Work y lo abre
  router.py                rutas HTTP: construyen el Unit of Work y llaman al service
migrations/                Alembic (plantilla asincrónica) y sus cuatro versiones
scripts/evidencia_c15.py   evidencia del caso C-15
test/                      casos .http, solo_agregado.sql y pruebas unitarias
```

`AsignacionRol`, `IntentoAcceso` y `EventoSeguridad` viven en `usuarios`;
`MovimientoStock` y `LibroAutor` en `libros`; `PerfilCliente` en `clientes` y
`RenglonVenta` en `ventas`.

## Decisiones de diseño

### Capas y transacciones

`Router → Service → UoW → Repository → Model`. El router construye el Unit of Work con
una dependencia y se lo pasa al service sin abrirlo; el service lo abre con
`async with` y nunca lo construye. Los repositorios hacen `flush()`, nunca `commit()`.
El Unit of Work confirma al salir del bloque, revierte si se sale con una excepción y no
cierra la sesión, porque la creó `get_session`. Las dependencias de autenticación usan
esa misma sesión: cada petición toma una sola conexión del pool.

La única escritura que no comparte la transacción de su petición es el registro de
`intento_acceso` en el login, que abre su propia sesión y siempre confirma: el fallo que
se quiere contar es el mismo que revierte la petición (el comentario está en
`app/modules/usuarios/repository.py`).

### Registro de una venta (RN-09 a RN-11)

`POST /ventas` recibe el cliente y los renglones; el precio, el total y la fecha no
viajan. Dentro de un solo bloque del Unit of Work:

1. Si el cliente no existe, 409.
2. Cada libro se bloquea con `SELECT ... FOR UPDATE` en orden de id. Si no existe, está
   dado de baja o no alcanza, 409 antes de escribir nada.
3. Se crea la venta con sus renglones, el precio copiado de cada libro y el total
   calculado por el servidor.
4. Cada renglón descuenta su stock por `cambiar_stock` (`app/modules/libros/stock.py`),
   el único punto que escribe `libro.stock`, que deja un movimiento negativo con la
   venta y el usuario que la registró.

Si algo falla en el medio, el Unit of Work revierte: no queda la venta, ni los
renglones, ni los descuentos, ni los movimientos. El mismo punto de stock lo usan el
alta del libro (`stock_inicial`) y la reposición, así que en todo libro
`stock == SUM(movimiento_stock.cantidad)`.

El aviso del comprobante se agenda con `BackgroundTasks` sólo después de que el service
devolvió la venta confirmada: corre después de enviar la respuesta, espera con
`await asyncio.sleep(0.5)` y escribe en el logger `uvicorn.error.ventas`, que se ve con
el arranque normal de uvicorn.

### Lo propio (RN-14)

`GET /mis-ventas` sólo pide estar autenticado y devuelve las ventas de la ficha de
cliente vinculada al usuario (vacía si no tiene ficha). `GET /ventas/{id}` no lleva
`requiere_rol`: el service resuelve primero quién es (personal con rol vigente, o el
cliente dueño de la venta) y responde 403 si no es ninguno de los dos.

### Lecturas sin N+1

Todas las relaciones se declaran con `lazy="raise"` y la precarga vive en el método del
repositorio que la necesita. El detalle de una venta usa `joinedload` para el cliente y
`selectinload(...).joinedload(...)` para los renglones y su libro: dos consultas, tenga
los renglones que tenga, y sin filtrar `borrado_en`, así una venta vieja sigue
mostrando un libro dado de baja. Los listados convierten cada item a su contrato de
salida leyendo por atributos, para que las relaciones precargadas lleguen a la respuesta.

### Garantías delegadas a la base

| Regla | Restricción |
|---|---|
| RN-01 correo de usuario y de cliente, nombre de editorial y de género | `UNIQUE` |
| RN-01 ISBN único entre los vigentes | índice único parcial `uq_libro_isbn_vigente` (`WHERE borrado_en IS NULL`) |
| RN-03 una asignación abierta por rol | índice único parcial `uq_asignacion_rol_usuario_rol_abierta` (`WHERE revocada_en IS NULL`) |
| Precio y stock del libro | `ck_libro_precio_positivo`, `ck_libro_stock_no_negativo` |
| Un libro por venta y cantidades positivas | `uq_renglon_venta_venta_id_libro_id`, `ck_renglon_venta_cantidad_positiva` |
| RN-12 movimientos de sólo agregado | disparador `trg_movimiento_stock_solo_agregado` (cuarta migración) |

No hay consultas previas para verificar unicidad: se escribe y, si la base rechaza, el
service traduce el `IntegrityError` por el nombre de la restricción a un 409 con mensaje
propio. El texto de la base sólo va al log (RN-15).

## Endpoints

| Grupo | Método | Ruta | Quién | Códigos |
|---|---|---|---|---|
| Abierto | GET | `/health/live` | Cualquiera | 200 |
| Abierto | GET | `/health/ready` | Cualquiera | 200, 503 |
| Abierto | POST | `/auth/registro` | Cualquiera | 201, 409, 422 |
| Abierto | POST | `/auth/login` | Cualquiera | 200, 401, 422, 429 |
| Abierto | POST | `/auth/logout` | Cualquiera | 200 |
| Abierto | GET | `/auth/yo` | Autenticado | 200, 401 |
| Abierto | POST | `/auth/cambiar-password` | Autenticado | 200, 401, 422 |
| Abierto | GET | `/libros` (`page`, `size`, `titulo`, `genero_id`) | Cualquiera | 200, 422 |
| Abierto | GET | `/libros/{id}` | Cualquiera | 200, 404, 422 |
| Abierto | GET | `/editoriales`, `/generos` (`page`, `size`) | Cualquiera | 200, 422 |
| Abierto | GET | `/editoriales/{id}/libros`, `/generos/{id}/libros`, `/autores/{id}/libros` | Cualquiera | 200, 404 |
| Protegido | POST | `/usuarios` | ADMIN | 201, 409, 422 |
| Protegido | GET | `/usuarios/{id}/roles` | ADMIN | 200, 404 |
| Protegido | POST | `/usuarios/{id}/roles` | ADMIN | 201, 404, 409, 422 |
| Protegido | DELETE | `/usuarios/{id}/roles/{rol}` | ADMIN | 200, 404, 409 |
| Protegido | GET | `/eventos` (`page`, `size`) | ADMIN | 200, 422 |
| Protegido | POST | `/editoriales`, `/generos`, `/autores` | ADMIN | 201, 409, 422 |
| Protegido | PATCH | `/editoriales/{id}`, `/autores/{id}` | ADMIN | 200, 404, 409, 422 |
| Protegido | POST | `/libros` (con `autores` y `stock_inicial`) | ADMIN | 201, 409, 422 |
| Protegido | PATCH | `/libros/{id}` (el stock no) | ADMIN | 200, 404, 409, 422 |
| Protegido | DELETE | `/libros/{id}` | ADMIN | 204, 404 |
| Protegido | POST | `/libros/{id}/reponer` | ADMIN | 200, 404, 409, 422 |
| Protegido | GET | `/libros/{id}/movimientos` | ADMIN | 200, 404 |
| Protegido | POST | `/clientes` | VENDEDOR, ADMIN | 201, 409, 422 |
| Protegido | GET, PATCH | `/clientes/{id}` (con su perfil) | VENDEDOR, ADMIN | 200, 404, 409, 422 |
| Protegido | POST | `/clientes/{id}/perfil` | VENDEDOR, ADMIN | 201, 404, 409 |
| Protegido | GET | `/clientes/{id}/ventas` | VENDEDOR, ADMIN | 200, 404 |
| Protegido | POST | `/ventas` (con `renglones`) | VENDEDOR, ADMIN | 201, 409, 422 |
| Protegido | GET | `/ventas` (`page`, `size`) | VENDEDOR, ADMIN | 200, 422 |
| Protegido | GET | `/ventas/{id}` | El personal, o el cliente dueño | 200, 403, 404 |
| Protegido | GET | `/mis-ventas` (`page`, `size`) | Autenticado | 200, 422 |

Toda ruta del grupo protegido responde además 401 sin sesión y 403 con el cambio de
contraseña pendiente.
