# Librería · catálogo, clientes y ventas

Trabajo práctico de Programación III (unidades 1 a 4): API asincrónica con FastAPI,
SQLModel, SQLAlchemy 2.0 asincrónico, PostgreSQL 16 y migraciones con Alembic.

## Levantar el proyecto desde cero

Requisitos: Python 3.12 o superior y PostgreSQL 16 en ejecución.

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

Crear una base vacía (por ejemplo con `psql`):

```sql
CREATE DATABASE libreria;
```

Copiar `env.example` como `.env` y completar usuario y contraseña:

```bash
cp env.example .env        # Windows: copy env.example .env
```

```
DATABASE_URL=postgresql+asyncpg://usuario:contraseña@localhost:5432/libreria
SQL_ECHO=true
```

El `.env` no se versiona (`.gitignore`). Ninguna credencial está en el código ni en `alembic.ini`:
`migrations/env.py` toma la URL de `DATABASE_URL`.

### 4. Esquema con Alembic

```bash
alembic upgrade head
```

El esquema se crea solo con migraciones (no se usa `create_all`). Para comprobar la reversibilidad:

```bash
alembic downgrade -1
alembic upgrade head
```

### 5. Datos iniciales

```bash
python -m scripts.seed
```

Vacía las tablas, reinicia los ids y carga un estado conocido:

| Recurso | Datos |
|---|---|
| Editoriales | 1 Sudamericana, 2 Anagrama, 3 Emecé |
| Géneros | 1 Novela, 2 Cuento, 3 Ensayo |
| Autores | 1 Cortázar, 2 Piglia, 3 Bioy Casares, 4 Silvina Ocampo, 5 Borges |
| Libros | 1 Rayuela ($25000), 2 Bestiario, 3 Ficciones, 4 Respiración artificial ($27000), 5 Antología de la literatura fantástica (sin género, 3 autores) |
| Clientes | 1 Ana Pérez (con perfil), 2 Tomás Ríos (sin perfil) |
| Ventas | 1 (Ana, un renglón) |

### 6. Servidor

```bash
fastapi dev app/main.py
# o bien
uvicorn app.main:app --reload
```

Documentación interactiva en http://localhost:8000/docs.

### 7. Casos de prueba

Los archivos de `test/` se ejecutan con la extensión **REST Client** de VS Code
(o el cliente HTTP de PyCharm). Cada petición indica en un comentario la respuesta esperada.

| Archivo | Contenido |
|---|---|
| `test/casos_minimos.http` | Casos C-01 a C-08 de la consigna. Correr primero, con la base recién cargada. |
| `test/00_health.http` | `/health/live` y `/health/ready` |
| `test/01_catalogo.http` | Editoriales, géneros, autores y libros: altas, 409, 422, 404, PATCH parcial, paginación, búsqueda |
| `test/02_clientes.http` | Clientes y perfil (uno a uno) |
| `test/03_ventas.http` | Ventas: RN-04 a RN-08, stock, precio congelado, tarea en segundo plano |

Orden sugerido: `python -m scripts.seed` → `casos_minimos.http` → los demás.

### 8. Evidencia del caso C-07

Con el seed cargado y `casos_minimos.http` ejecutado (C-06 crea la venta 2 con dos renglones):

```bash
python -m scripts.evidencia_c07
```

El script usa las mismas funciones del service que los endpoints, muestra cada SQL emitido
y lo guarda en `evidencia/C-07_consultas.txt` (ese archivo es la evidencia entregada):

| Lectura | Consultas |
|---|---|
| `GET /libros/1` (1 autor) | 2 |
| `GET /libros/5` (3 autores) | 2 |
| `GET /ventas/1` (1 renglón) | 2 |
| `GET /ventas/2` (2 renglones) | 2 |

También se ve en la consola del servidor con `SQL_ECHO=true` al ejecutar los GET de C-07.

## Estructura

```
app/
  main.py                 aplicación, lifespan, manejadores de error y routers
  core/
    config.py             lectura de DATABASE_URL / SQL_ECHO desde el entorno
    database.py           motor, fábrica de sesiones, get_session, convención de nombres
    errores.py            NoEncontrado / Conflicto y traducción de IntegrityError
    parametros.py         IdPath, LimitQuery, OffsetQuery
    modelos.py            importa todos los modelos (Alembic y relaciones)
  modules/<módulo>/       health, editoriales, generos, autores, libros, clientes, ventas
    models.py             tablas, restricciones y relaciones
    schemas.py            DTO Create / Update / Read
    service.py            lógica, traducción de errores, lecturas con precarga
    router.py             rutas HTTP
migrations/               Alembic (plantilla asincrónica) y sus dos versiones
scripts/                  seed.py y evidencia_c07.py
test/                     casos .http
```

`LibroAutor` vive en `libros`, `PerfilCliente` en `clientes` y `RenglonVenta` en `ventas`.

## Decisiones de diseño

### Lado de cada clave foránea

| Relación | FK | Por qué ahí |
|---|---|---|
| Libro — Editorial (agregación) | `libro.editorial_id` NOT NULL, `ON DELETE RESTRICT` | Lado "muchos": cada libro guarda el id de su editorial. La editorial existe por sí misma, por eso no se borra en cascada. |
| Libro — Género (agregación opcional) | `libro.genero_id` NULL, `ON DELETE SET NULL` | Igual que la editorial, pero optativa: el nulo expresa "sin género". |
| Libro — Autor (muchos a muchos con datos) | `libro_autor.libro_id` y `libro_autor.autor_id`, PK compuesta | Ninguna de las dos tablas puede guardar la FK. `libro_autor` es una entidad con clase propia porque tiene `rol` y `orden`. Se navega `libro.autorias[i].autor`. |
| Cliente — Perfil (uno a uno) | `perfil_cliente.cliente_id` UNIQUE, `ON DELETE CASCADE` | El perfil es el lado opcional y dependiente. El UNIQUE convierte el muchos a uno en uno a uno (RN-09). `Cliente.perfil` usa `uselist=False`: devuelve un objeto. |
| Venta — Cliente (asociación) | `venta.cliente_id`, `ON DELETE RESTRICT` | La venta conoce a su cliente; ninguno es parte del otro. |
| Venta — Renglón (composición) | `renglon_venta.venta_id`, `ON DELETE CASCADE` | La parte guarda la FK al todo. Los renglones nacen con la venta (cascade `all, delete-orphan` en el ORM). |
| Renglón — Libro (asociación) | `renglon_venta.libro_id`, `ON DELETE RESTRICT` | El renglón nombra un libro existente; no se puede borrar un libro vendido. |

### Índices de las claves foráneas

PostgreSQL no indexa las FK automáticamente. Cada FK tiene un índice cuya primera columna es la FK:
`ix_libro_editorial_id`, `ix_libro_genero_id`, `ix_libro_autor_autor_id`, `ix_perfil_cliente_cliente_id` (UNIQUE),
`ix_venta_cliente_id` e `ix_renglon_venta_libro_id`. Dos FK ya están cubiertas por otro índice y no se duplicaron:
`libro_autor.libro_id` (primera columna de la PK) y `renglon_venta.venta_id` (primera columna del UNIQUE `(venta_id, libro_id)`).

### Garantías delegadas a la base

| Regla | Restricción |
|---|---|
| RN-01 ISBN único | `uq_libro_isbn` |
| RN-02 email único | `uq_cliente_email` (el email se guarda en minúsculas) |
| RN-03 precio y stock | `ck_libro_precio_positivo`, `ck_libro_stock_no_negativo` (y validación del DTO) |
| RN-05 libro no repetido en la venta | `uq_renglon_venta_venta_id_libro_id` (y validación del DTO) |
| RN-09 un perfil por cliente | `ix_perfil_cliente_cliente_id` UNIQUE |
| Rol y orden de la autoría | `ck_libro_autor_rol_valido`, `ck_libro_autor_orden_positivo` |
| Totales y renglones | `ck_venta_total_no_negativo`, `ck_renglon_venta_cantidad_positiva`, `ck_renglon_venta_precio_unitario_positivo` |

No hay consultas previas para verificar unicidad ni existencia en el alta del libro: se escribe y,
si la base rechaza, el service traduce el `IntegrityError`. La convención de nombres
(`app/core/database.py`) da nombres fijos a todas las restricciones, y cada service tiene un mapa
`nombre de restricción → mensaje propio`. El texto de la base solo va al log (RN-12).

### Ventas

- `POST /ventas/` recibe `cliente_id` (asociación) y `renglones` con `libro_id` y `cantidad` (composición).
  `VentaCreate` prohíbe campos extra: si llegan `precio_unitario` o `total`, responde 422.
- Los libros de la venta se leen con `SELECT ... FOR UPDATE`: de ahí sale el precio copiado (RN-06) y el
  bloqueo evita que dos ventas simultáneas pisen el stock.
- El total se calcula en el servidor (RN-07) y el stock se descuenta; si no alcanza, el CHECK
  `stock >= 0` rechaza la escritura y se responde 409.
- No hay PATCH ni DELETE de ventas (RN-08).
- El aviso del comprobante se agenda con `BackgroundTasks`: `await asyncio.sleep(0.5)` y un mensaje en el
  log, después de enviar la respuesta. Recibe datos simples, no la sesión.

### Lecturas sin N+1

Todas las relaciones se declaran con `lazy="raise"`: si una lectura olvidara precargar una relación,
falla en lugar de emitir consultas ocultas. `joinedload` para relaciones a uno y `selectinload` para
colecciones. El detalle de libro y de venta usa `populate_existing` para refrescar objetos que ya
estuvieran en la sesión (por ejemplo, recién creados).

### Errores

| Código | Cuándo |
|---|---|
| 201 | Alta exitosa |
| 404 | El recurso de la ruta no existe (`NoEncontrado`) |
| 409 | La base rechaza la escritura (`Conflicto`, traducido del `IntegrityError`) |
| 422 | Cuerpo, ruta o query fuera de contrato (validación de FastAPI / Pydantic) |
| 500 | Error inesperado: mensaje genérico, la traza solo en el log |

## Endpoints

| Método | Ruta | Códigos |
|---|---|---|
| GET | `/health/live` | 200 |
| GET | `/health/ready` | 200, 503 |
| POST, GET | `/editoriales/` | 201, 409, 422 · 200, 422 |
| GET, PATCH | `/editoriales/{id}` | 200, 404, 409, 422 |
| GET | `/editoriales/{id}/libros` | 200, 404 |
| POST, GET | `/generos/` | 201, 409 · 200 |
| GET | `/generos/{id}/libros` | 200, 404 |
| POST, GET | `/autores/` | 201, 422 · 200 |
| GET, PATCH | `/autores/{id}` | 200, 404, 422 |
| GET | `/autores/{id}/libros` | 200, 404 |
| POST, GET | `/libros/` (`limit`, `offset`, `titulo`, `genero_id`) | 201, 409, 422 · 200, 422 |
| GET, PATCH | `/libros/{id}` | 200, 404, 409, 422 |
| POST, GET | `/clientes/` | 201, 409, 422 · 200 |
| GET, PATCH | `/clientes/{id}` | 200, 404, 409, 422 |
| POST | `/clientes/{id}/perfil` | 201, 404, 409 |
| GET | `/clientes/{id}/ventas` | 200, 404 |
| POST, GET | `/ventas/` | 201, 409, 422 · 200, 422 |
| GET | `/ventas/{id}` | 200, 404 |

Todos los listados aceptan `limit` (1 a 100, por defecto 20) y `offset` (desde 0).
