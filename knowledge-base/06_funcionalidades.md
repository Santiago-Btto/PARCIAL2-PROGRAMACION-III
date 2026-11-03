# Funcionalidades

Organizadas por **épica** (alineadas con los bloques de implementación y los 10 ejercicios del parcial) y luego por **historia de usuario**.

## Épica 1: Configuración, Ciclo de Vida, Modelos y Migraciones (Ejercicios 1, 2 y 7)

### US-001 — Configuración segura y ciclo de vida de la aplicación
**Como** desarrollador del equipo
**Quiero** leer toda la configuración con `pydantic-settings` sin secretos por defecto y crear el motor, la fábrica de sesiones y el hash ficticio en el `lifespan`
**Para** que la aplicación falle rápido si faltan secretos, comparta el pool correctamente en `app.state` y exponga `/health/live` y `/health/ready` (`503` si cae la base).

**Criterios de aceptación**:
- [x] `Settings` arma `database_url` con `@computed_field` a partir de `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`.
- [x] `POSTGRES_PASSWORD` y `JWT_SECRET_KEY` no tienen valor por defecto.
- [x] `lifespan` crea motor, `session_factory` (`expire_on_commit=False`), semáforo `bcrypt` y `dummy_password_hash`, y ejecuta `motor.dispose()` al apagar.
- [x] `/health/live` devuelve `200` sin tocar la base y `/health/ready` ejecuta `SELECT 1` o devuelve `503`.

**Reglas relacionadas**: RN-08, RN-15

### US-002 — Evolución del esquema con Alembic (Migraciones 3 y 4)
**Como** administrador de base de datos
**Quiero** contar con los modelos nuevos (`Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad`, `MovimientoStock`), los cambios en `Cliente` y `Libro`, la 3ª migración autogenerada y la 4ª migración manual con el disparador append-only
**Para** que `alembic upgrade head` y `alembic downgrade base` construyan y reviertan el esquema completo con todas sus garantías en PostgreSQL.

**Criterios de aceptación**:
- [x] Índice único parcial `uq_asignacion_rol_usuario_rol_abierta` (`WHERE revocada_en IS NULL`) y `uq_libro_isbn_vigente` (`WHERE borrado_en IS NULL`).
- [x] Disparador `trg_movimiento_stock_solo_agregado` que rechaza cualquier `UPDATE` o `DELETE` sobre `movimiento_stock` (Caso `C-14`).

**Reglas relacionadas**: RN-01, RN-03, RN-12, RN-13

---

## Épica 2: Autenticación, Autorización y Administración de Usuarios (Ejercicios 4, 5 y 7)

### US-003 — Auto-registro de clientes web
**Como** visitante de la librería
**Quiero** registrarme en `POST /auth/registro` con mi nombre, email y contraseña
**Para** obtener en una sola transacción mi usuario, mi rol `CLIENTE` y mi ficha de `cliente`.

**Criterios de aceptación**:
- [ ] El hash `bcrypt` se calcula fuera del event loop (`to_thread` + semáforo) **antes** de abrir el `UnitOfWork`.
- [ ] Contraseñas de más de 72 bytes en UTF-8 se rechazan con `422`.
- [ ] Si el email ya existe en `usuario` o en `cliente`, responde `409` con mensaje propio y no queda ninguna fila suelta (Caso `C-02`).

**Reglas relacionadas**: RN-01, RN-02, RN-15

### US-004 — Inicio y cierre de sesión con cookie HttpOnly y límite de intentos
**Como** usuario registrado
**Quiero** iniciar sesión en `POST /auth/login`, consultar mi sesión en `GET /auth/yo` y cerrarla en `POST /auth/logout`
**Para** operar de forma segura mediante la cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`).

**Criterios de aceptación**:
- [ ] Primero verifica si hay 5 intentos fallidos en los últimos 60s para ese `(email, ip)` posteriores al último éxito; si se superó, responde `429` con `Retry-After` sin ejecutar `bcrypt` (Caso `C-05`).
- [ ] Si el correo no existe, verifica contra `app.state.dummy_password_hash` y devuelve el mismo `401` (Caso `C-04`).
- [ ] Cada intento se guarda en `intento_acceso` usando una sesión y transacción independientes con el comentario explicativo de 3 puntos exigido en el Ejercicio 7.
- [ ] El token viaja sólo en el header `Set-Cookie`, nunca en el cuerpo JSON, y no se acepta por `Authorization: Bearer` (Caso `C-03`).
- [ ] `GET /auth/yo` devuelve los datos del usuario, sus `roles_vigentes` en la base y los `roles_token` que dice el JWT (Caso `C-07`).

**Reglas relacionadas**: RN-04, RN-07, RN-08

### US-005 — Cambio obligatorio de contraseña y gestión de personal/roles
**Como** administrador (`ADMIN`)
**Quiero** dar de alta personal con contraseña provisoria (`POST /usuarios`), asignar y revocar roles con vigencia (`GET/POST/DELETE /usuarios/{id}/roles`) y consultar `GET /eventos`
**Para** administrar los permisos del personal en tiempo real y auditar cada acción en `evento_seguridad`.

**Criterios de aceptación**:
- [ ] Un usuario con `debe_cambiar_password=True` recibe `403` en todo el grupo protegido hasta que ejecute `POST /auth/cambiar-password`, tras lo cual su misma cookie sirve sin reloguear (Caso `C-09`).
- [ ] Revocar un rol escribe `revocada_en = now()` sin borrar la fila y quita el permiso en la petición siguiente aunque el JWT siga vigente (Caso `C-07`).
- [ ] El vencimiento (`vence_en`) sin zona horaria o en el pasado responde `422` (Caso `C-07`).
- [ ] Un admin no puede revocarse su propio `ADMIN` ni dejar al sistema sin admins vigentes (`409`, Caso `C-08`).
- [ ] Alta de personal, asignación/revocación de rol y cambio de contraseña dejan fila en `evento_seguridad` en el mismo UoW (RN-16).

**Reglas relacionadas**: RN-03, RN-04, RN-05, RN-06, RN-16

---

## Épica 3: Catálogo, Borrado Lógico y Movimientos de Stock (Ejercicios 3 y 6)

### US-006 — Gestión de catálogo paginada y con repositorios + UoW
**Como** usuario o administrador
**Quiero** listar editoriales, géneros, autores y libros con el envoltorio `{items, total, page, size, pages}` y administrar el catálogo mediante `UnitOfWork`
**Para** mantener contratos estrictos (`extra="forbid"`, `exclude_unset` en `PATCH`) y separación de capas.

**Criterios de aceptación**:
- [ ] Todos los listados usan `page` (desde 1) y `size` (1 a 100, default 20), devolviendo `422` si `page > pages` (Caso `C-16`).
- [ ] Búsqueda de libros por `titulo` insensible a mayúsculas con parámetros ligados (segura ante inyección SQL, Caso `C-16`).
- [ ] `POST` y `PATCH` de editoriales, géneros y autores exigen rol `ADMIN`.

**Reglas relacionadas**: RN-01, RN-04, RN-15

### US-007 — Alta, reposición, movimientos y baja lógica de libros
**Como** administrador (`ADMIN`)
**Quiero** crear libros con `stock_inicial`, reponer ejemplares (`POST /libros/{id}/reponer`), auditar `GET /libros/{id}/movimientos` y dar de baja libros (`DELETE /libros/{id}`)
**Para** que el stock sólo cambie a través de movimientos y los libros descatalogados conserven su historial de ventas liberando su ISBN.

**Criterios de aceptación**:
- [ ] `POST /libros` recibe `stock_inicial` y registra el movimiento `"Stock inicial"` usando el único método de escritura de stock.
- [ ] `PATCH /libros/{id}` permite editar `titulo` y `precio`, pero rechaza `stock` con `422` (Caso `C-16`).
- [ ] `DELETE /libros/{id}` devuelve `204`, marca `borrado_en`, oculta el libro del catálogo, impide venderlo o reponerlo (`409`), mantiene visible su título en ventas viejas y permite crear otro libro vigente con el mismo ISBN (Caso `C-13`).

**Reglas relacionadas**: RN-01, RN-11, RN-12, RN-13

---

## Épica 4: Clientes, Ventas Transaccionales, Seed y Casos C (Ejercicios 6 y 8)

### US-008 — Gestión de clientes y registro atómico de ventas
**Como** vendedor (`VENDEDOR` o `ADMIN`) y como cliente (`CLIENTE`)
**Quiero** administrar fichas de clientes, registrar ventas descontando stock con movimientos en un solo UoW y consultar ventas propias (`/mis-ventas` y `/ventas/{id}`)
**Para** garantizar que ninguna venta fallida deje datos a medias y que cada cliente vea únicamente sus compras sin consultas N+1.

**Criterios de aceptación**:
- [ ] `POST /ventas` crea venta, renglones, descuenta stock y agrega un `MovimientoStock` por renglón en un solo UoW; si un libro no alcanza, no existe o está dado de baja, responde `409` y revierte todo (Casos `C-10`, `C-11`, `C-12`).
- [ ] Tras confirmar la venta, `BackgroundTasks` ejecuta `await asyncio.sleep(0.5)` y escribe el aviso en consola con el logger visible en uvicorn.
- [ ] `GET /ventas/{id}` permite acceso al personal o al cliente dueño (`403` si es otro cliente, Caso `C-06`) y resuelve cliente + renglones + libros (incluidos dados de baja) en una cantidad fija de consultas (Caso `C-15`).
- [ ] `seed.py` y los archivos `.http` (`test/`) cubren los casos `C-01` a `C-16`.

**Reglas relacionadas**: RN-09, RN-10, RN-11, RN-13, RN-14

---

## Épica 5: Contenedor Docker y Despliegue en el VPS (Ejercicios 9 y 10)

### US-009 — Imagen Docker Alpine y despliegue en el VPS (`despliegue/`)
**Como** integrante del grupo
**Quiero** empaquetar el TP de los capítulos 1 a 4 en `despliegue/` con un `Dockerfile` basado en `python:3.12-alpine` y ponerlo en línea en el VPS de la cátedra
**Para** cumplir los casos `D-01` a `D-08` sin exponer secretos y con verificación automática de salud (`HEALTHCHECK`).

**Criterios de aceptación**:
- [ ] `Dockerfile` parte de `python:3.12-alpine`, instala `requirements.txt` con `--no-cache-dir` antes de copiar el código, corre con usuario sin privilegios (`USER`), declara `HEALTHCHECK` con `wget -qO- http://127.0.0.1:8000/health/ready` y ejecuta `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- [ ] `.dockerignore` excluye `.env`, `.venv`, `.git` y `__pycache__`.
- [ ] `DEPLOY.md` y `despliegue/evidencia/` documentan el despliegue en el VPS y las salidas de `D-01` a `D-08`.
