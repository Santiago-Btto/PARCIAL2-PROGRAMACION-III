# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **Librería TP — Parcial Capítulos 1 a 6**.
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas) y corresponde a uno de los 5 bloques/pushes del parcial.
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

---

## Cómo usar este documento

1. Identificar el change a implementar (verificar que sus dependencias están en `openspec/changes/archive/`).
2. Leer los docs de la knowledge-base indicados en "Leer antes".
3. Ejecutar `/opsx:propose <nombre-del-change>`.
4. Al terminar el change, archivarlo con `/opsx:archive <nombre-del-change>`.
5. Marcar el checkbox `[x]` en este archivo.

---

## Árbol de dependencias

```
C-01 core-models-and-migrations
  │
  ├── C-02 auth-usuarios-and-rbac              ← desbloquea rutas protegidas y auditoría
  │     └── C-03 catalogo-soft-delete-and-stock
  │           └── C-04 clientes-ventas-seed-and-tests
  │
  └── C-05 docker-alpine-and-vps-deploy        ← paralelo en carpeta despliegue/ (sólo requiere C-01)
```

### Paralelismo por fase

> Cada "gate" es un punto de sincronización. Los changes dentro de un grupo pueden ejecutarse en paralelo.

```
GATE 0: ninguna
  → C-01 core-models-and-migrations            [Agente A]

GATE 1: C-01 ✓                                 ← PRIMER FORK (parcial/ vs despliegue/ + adelanto de repositorios)
  → C-02 auth-usuarios-and-rbac                [Agente A]
  → C-05 docker-alpine-and-vps-deploy          [Agente C]

GATE 2: C-02 ✓
  → C-03 catalogo-soft-delete-and-stock        [Agente B — con C-01 ✓]

GATE 3: C-02 + C-03 ✓
  → C-04 clientes-ventas-seed-and-tests        [Agente A / Agente B]
```

### Camino crítico (4 changes — mínimo irreducible)

```
C-01 → C-02 → C-03 → C-04* (y C-01 → C-05* en paralelo para el bloque de despliegue)
```

### Plan óptimo con 3 agentes

```
Paso │ Agente A (Backend Core)               │ Agente B (Backend Aux)                │ Agente C (Frontend / Infraestructura)
─────┼───────────────────────────────────────┼───────────────────────────────────────┼──────────────────────────────────────
  1  │ C-01 core-models-and-migrations       │                 —                     │                 —
  2  │ C-02 auth-usuarios-and-rbac           │                 —                     │ C-05 docker-alpine-and-vps-deploy
  3  │                 —                     │ C-03 catalogo-soft-delete-and-stock   │                 —
  4  │ C-04 clientes-ventas-seed-and-tests   │                 —                     │                 —
```

---

## FASE 0 — Cimientos, Modelos Core y Migraciones (Push 1)

### [C-01] `core-models-and-migrations`
- **Estado**: `[x]` completado y archivado (`openspec/changes/archive/2026-11-03-c-01-core-models-and-migrations/`)
- **Scope**: Separación de carpetas `parcial/` y `despliegue/`, infraestructura transversal en `parcial/app/core/`, modelos de datos completos y migraciones 3 y 4 de Alembic (Ejercicios 1, 2, base del 6 y 7)
  - Estructura obligatoria de directorios: `parcial/` (Ejercicios 1 a 8) y `despliegue/` (copia congelada del TP Capítulos 1 a 4 para Ejercicios 9 y 10)
  - `parcial/app/core/config.py`: `Settings(BaseSettings)` sin secretos ni valores por defecto en `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` ni `JWT_SECRET_KEY`; construcción de `database_url` (`postgresql+asyncpg://...`) mediante `@computed_field`
  - `parcial/app/core/database.py` y `parcial/main.py`: `crear_motor`, `crear_fabrica_sesiones` (`expire_on_commit=False`), `get_session` y `lifespan` que inicializa `app.state.engine`, `app.state.session_factory`, `app.state.bcrypt_semaphore` y `app.state.dummy_password_hash`, cerrando el pool con `await motor.dispose()` al apagar
  - Endpoints de salud en `parcial/app/modules/health/router.py`: `GET /health/live` (`200` sin tocar la base) y `GET /health/ready` (`SELECT 1` con `200` o `503` si PostgreSQL no responde)
  - Patrones base en `parcial/app/core/`: `BaseRepository[T]` y `SoftDeleteRepository[T]` (`flush()` sin `commit()`), `UnitOfWork` (comparte la `AsyncSession` de `get_session`, confirma al salir o hace `rollback` sin cerrar la sesión), `Pagina[T]` (`{items, total, page, size, pages}` con `422` si `page > pages`), `errores.py` (traducción de `IntegrityError` por nombre de constraint a `409` sin filtrar detalles internos)
  - Primitivas de seguridad en `parcial/app/core/security.py` y `dependencies.py`: hash y verificación `bcrypt` con `asyncio.to_thread` + `asyncio.Semaphore`, límite de 72 bytes en UTF-8, emisión/lectura de JWT (`HS256`) exclusivamente desde la cookie `HttpOnly` `access_token`, dependencias `get_usuario_actual`, `verificar_cambio_password_resuelto` y `requiere_rol(*roles)`
  - Modelos en `parcial/app/modules/` y registro en `parcial/app/core/modelos.py`: nuevos modelos `Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad`, `MovimientoStock`; evolución de `Cliente` (`usuario_id` nullable `UNIQUE` `ON DELETE SET NULL`, relaciones 1:1 con `uselist=False`) y `Libro` (`borrado_en`, índice único parcial `uq_libro_isbn_vigente` con `WHERE borrado_en IS NULL`)
  - Migración 3 autogenerada (`9a4e7c2b1d80_acceso_roles_borrado_logico_y_movimiento_stock.py`): crea tablas de acceso y `movimiento_stock`, agrega `cliente.usuario_id` y `libro.borrado_en`, e instala los índices únicos parciales `uq_asignacion_rol_usuario_rol_abierta` (`WHERE revocada_en IS NULL`) y `uq_libro_isbn_vigente` (`WHERE borrado_en IS NULL`)
  - Migración 4 manual (`c8e31f5a9021_disparador_solo_agregado_movimiento_stock.py`): crea e instala en PostgreSQL la función PL/pgSQL `impedir_modificacion_movimiento_stock()` y el disparador `trg_movimiento_stock_solo_agregado` (`BEFORE UPDATE OR DELETE ON movimiento_stock FOR EACH ROW`) con su reversión exacta en `downgrade()`
  - Verificación de esquema: ciclo completo `alembic upgrade head`, `alembic downgrade base` y `alembic upgrade head` sin errores y sin credenciales en `alembic.ini`
- **Dependencias**: ninguna
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/01_vision_y_objetivos.md` §Alcance v2.0
  - `knowledge-base/04_modelo_de_datos.md` §Entidades
  - `knowledge-base/06_funcionalidades.md` §Épica 1
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados y §Variables de entorno
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-01, §DD-02 y §DD-03

---

## FASE 1 — Autenticación, Autorización y Seguridad (Push 2)

### [C-02] `auth-usuarios-and-rbac`
- **Estado**: `[x]` completado y archivado (`openspec/changes/archive/2026-11-03-c-02-auth-usuarios-and-rbac/`)
- **Scope**: Módulo `usuarios` completo (`/auth`, `/usuarios`, `/eventos`), separación de los dos grupos de rutas en `main.py`, registro de `IntentoAcceso` en sesión independiente y auditoría transaccional en `EventoSeguridad` (Ejercicios 4, 5 y 7)
  - Esquemas en `parcial/app/modules/usuarios/schemas.py`: DTOs con `extra="forbid"`, normalización de email, validación de contraseña entre 1 y 72 bytes en UTF-8 (`422` si supera 72 bytes, Caso `C-01`), validación de `rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')` y de `vence_en` con zona horaria obligatoria y fecha futura (`422` si es naive o pasado, Caso `C-07`)
  - Repositorios y `UsuariosUnitOfWork` (`parcial/app/modules/usuarios/repository.py` y `unit_of_work.py`): `UsuarioRepository`, `AsignacionRolRepository` (consulta de roles vigentes con `revocada_en IS NULL AND (vence_en IS NULL OR vence_en > now())`, conteo de administradores vigentes y cierre de asignación vencida al reasignar), `IntentoAccesoRepository`, `EventoSeguridadRepository` y `ClienteRepository` compartido para el auto-registro
  - `POST /auth/registro` (`201`, `409`, `422`): calcula el hash `bcrypt` fuera del event loop **antes** de entrar al `async with uow:` y crea atómicamente `Usuario`, `AsignacionRol(rol="CLIENTE")` y `Cliente` en un solo `UnitOfWork` (RN-02); si el email ya existe en `usuario` o en `cliente`, revierte todo y responde `409` sin apropiarse de fichas previas (Caso `C-02`)
  - `POST /auth/login` (`200`, `401`, `422`, `429`): verifica primero en `intento_acceso` si hay 5 intentos fallidos en los últimos 60 segundos desde el mismo `(email, ip)` posteriores al último éxito y responde `429` con cabecera `Retry-After` **sin ejecutar `bcrypt`** (RN-07, Caso `C-05`); si el email no existe, verifica contra `app.state.dummy_password_hash` para mantener tiempo constante y mismo mensaje `401` (RN-08, Caso `C-04`); registra cada intento en `intento_acceso` abriendo una **sesión y transacción propias** desde `session_factory` con el comentario obligatorio de 3 puntos (Ejercicio 7); emite el JWT en la cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`, `Secure` según `COOKIE_SECURE`) sin incluir el token en el cuerpo JSON (Caso `C-03`)
  - `POST /auth/logout` (`200`), `GET /auth/yo` (`200`, `401` — devuelve datos del usuario, `roles_vigentes` leídos de BD y `roles_token` leídos del JWT) y `POST /auth/cambiar-password` (`200`, `401`, `422` — verifica clave actual, actualiza `password_hash`, pasa `debe_cambiar_password = False` y registra fila en `evento_seguridad` en el mismo UoW, permitiendo seguir operando con la misma cookie sin reloguear, Caso `C-09`)
  - Administración de personal y roles (sólo `ADMIN`): `POST /usuarios` (`201`, `409`, `422` — alta de personal con `debe_cambiar_password = True`, rol inicial y `evento_seguridad`), `GET /usuarios/{id}/roles` (`200`, `404`), `POST /usuarios/{id}/roles` (`201`, `404`, `409`, `422` — cierra asignación vencida previa si existe o responde `409` si ya hay una abierta, RN-03), `DELETE /usuarios/{id}/roles/{rol}` (`200`, `404`, `409` — escribe `revocada_en = now()`, impide auto-revocación de `ADMIN` y evita dejar al sistema sin administradores vigentes, RN-05, Casos `C-07` y `C-08`) y `GET /eventos` paginado (`200`, `422`)
  - Dos grupos de rutas en `parcial/main.py`: Grupo Abierto (`/health`, `/auth`, `GET` de catálogo) y Grupo Protegido con `Depends(verificar_cambio_password_resuelto)` que bloquea con `403` a todo usuario con `debe_cambiar_password = True` (RN-06)
- **Dependencias**: C-01
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos y §Reglas especiales de Autorización
  - `knowledge-base/04_modelo_de_datos.md` §1. `usuario`, §2. `asignacion_rol`, §3. `intento_acceso` y §4. `evento_seguridad`
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Autenticación, Usuarios y Seguridad (RN-02 a RN-08, RN-16)
  - `knowledge-base/06_funcionalidades.md` §Épica 2 (US-003, US-004, US-005)
  - `knowledge-base/07_flujos_principales.md` §Flujo 1: Inicio de Sesión y §Flujo 2: Auto-registro de Cliente

---

## FASE 2 — Catálogo, Borrado Lógico y Trazabilidad de Stock (Push 3)

### [C-03] `catalogo-soft-delete-and-stock`
- **Estado**: `[ ]` pendiente
- **Scope**: Refactorización de `editoriales`, `generos`, `autores` y `libros` al patrón `Router → Service → UoW → Repository → Model`, paginación estandarizada, borrado lógico de libros y punto único de modificación de stock con `MovimientoStock` (Ejercicios 3 y 6)
  - Refactor en capas de `parcial/app/modules/editoriales/`, `generos/` y `autores/`: `repository.py`, `unit_of_work.py`, `service.py`, `schemas.py` (`extra="forbid"`, `exclude_unset=True` en `PATCH`) y `router.py`; listados `GET /editoriales` y `GET /generos` paginados con `Pagina[T]` (`{items, total, page, size, pages}`, `422` si `page > pages`); lecturas de libros por entidad (`GET /editoriales/{id}/libros`, `GET /generos/{id}/libros`, `GET /autores/{id}/libros`) filtrando libros dados de baja; escrituras (`POST` y `PATCH`) protegidas con `RequiereRol("ADMIN")`
  - `LibroRepository(SoftDeleteRepository[Libro])` y `MovimientoStockRepository(BaseRepository[MovimientoStock])` en `parcial/app/modules/libros/repository.py`: precarga declarada con `joinedload(Libro.editorial)`, `joinedload(Libro.genero)` y `selectinload(Libro.autores_asociados).joinedload(LibroAutor.autor)` para evitar `N+1` con `lazy="raise"`; filtro automático `borrado_en IS NULL` en catálogo público y método `get_by_id_including_deleted` para historial
  - Punto único de escritura de stock (`cambiar_stock` en `parcial/app/modules/libros/`): único lugar de todo el código autorizado a modificar `libro.stock`, insertando simultáneamente la fila en `MovimientoStock(libro_id, venta_id, usuario_id, cantidad, motivo)` y garantizando que `libro.stock == SUM(movimiento_stock.cantidad)` (RN-11)
  - Endpoints de libros en `parcial/app/modules/libros/router.py`:
    - `GET /libros` (`page`, `size`, filtro `titulo` insensible a mayúsculas con parámetros ligados seguro ante inyección SQL y `genero_id`) y `GET /libros/{id}` (`404` si está dado de baja) en el grupo abierto
    - `POST /libros` (`ADMIN`, `201`, `409`, `422`): recibe `stock_inicial` (`>= 0`) y `autores`, crea el libro con `stock = 0` y, si `stock_inicial > 0`, invoca el punto único de stock con motivo `"Stock inicial"` en el mismo `LibrosUnitOfWork`
    - `PATCH /libros/{id}` (`ADMIN`, `200`, `404`, `409`, `422`): permite actualizar `titulo` y `precio`, rechazando el campo `stock` en el esquema de entrada con `422` (RN-11, Caso `C-16`)
    - `DELETE /libros/{id}` (`ADMIN`, `204`, `404`): ejecuta borrado lógico (`borrado_en = now()`), oculta el libro del catálogo y libera su ISBN en `uq_libro_isbn_vigente` para poder reutilizarlo en un libro nuevo (RN-01, RN-13, Caso `C-13`)
    - `POST /libros/{id}/reponer` (`ADMIN`, `200`, `404`, `409`, `422`): exige `cantidad > 0` y `motivo` no vacío, rechaza con `409` si el libro está dado de baja, e incrementa el stock mediante el punto único creando el `MovimientoStock`
    - `GET /libros/{id}/movimientos` (`ADMIN`, `200`, `404`): lista el historial de movimientos del libro (incluso si fue dado de baja lógicamente)
- **Dependencias**: C-01, C-02
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/02_descripcion_general.md` §API REST — Resumen de Endpoints de Referencia
  - `knowledge-base/04_modelo_de_datos.md` §6. `editorial`, `genero`, `autor`, `libro` y `libro_autor` y §7. `movimiento_stock`
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Unicidad e Integridad de Datos (RN-01, RN-15) y §Dominio: Catálogo, Stock y Ventas (RN-11, RN-12, RN-13)
  - `knowledge-base/06_funcionalidades.md` §Épica 3 (US-006, US-007)
  - `knowledge-base/07_flujos_principales.md` §Flujo 4: Baja Lógica de un Libro y Reutilización de ISBN

---

## FASE 3 — Clientes, Ventas Transaccionales y Suite de Pruebas (Push 4)

### [C-04] `clientes-ventas-seed-and-tests`
- **Estado**: `[ ]` pendiente
- **Scope**: Refactor de `clientes` y `ventas` a `Repository + UnitOfWork`, registro atómico de ventas con descuento de stock y `BackgroundTasks`, consulta de compras propias (`/mis-ventas` y `/ventas/{id}`), `seed.py` definitivo y suite completa `test/*.http` + evidencias `C-01` a `C-16` (Ejercicios 6 y 8)
  - Refactor de `parcial/app/modules/clientes/`: `ClienteRepository`, `PerfilClienteRepository`, `ClientesUnitOfWork`, `service.py`, `schemas.py` y `router.py` protegidos para `VENDEDOR` y `ADMIN` (`POST /clientes`, `GET /clientes/{id}`, `PATCH /clientes/{id}`, `POST /clientes/{id}/perfil` y `GET /clientes/{id}/ventas` con precarga sin `N+1`)
  - Refactor de `parcial/app/modules/ventas/`: `VentaRepository` (con `joinedload(Venta.cliente)` y `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)` sin filtrar `borrado_en` para preservar libros dados de baja en ventas históricas) y `VentasUnitOfWork` que compone `VentaRepository`, `ClienteRepository`, `LibroRepository` y `MovimientoStockRepository` sobre la misma `AsyncSession`
  - `POST /ventas` (`VENDEDOR` o `ADMIN`, `201`, `409`, `422`): valida renglones (`cantidad > 0`, sin libros repetidos, sin aceptar `precio_unitario` ni `total` en el payload); dentro de un único `async with uow:` verifica existencia del cliente (`409` si no existe, Caso `C-12`), vigencia y stock suficiente de cada libro (`409` si no existe, está dado de baja o `stock < cantidad`, revirtiendo toda la transacción sin dejar ventas ni movimientos parciales, Casos `C-11`, `C-12`, `C-13`), copia `precio_unitario = libro.precio`, calcula `total`, e invoca el punto único `cambiar_stock` por cada renglón dejando los `MovimientoStock` negativos con `venta_id` y `usuario_id` (RN-09, RN-10, RN-11, Caso `C-10`)
  - Notificación en segundo plano (Ejercicio 8): al confirmar `POST /ventas`, agenda en `BackgroundTasks` la función asincrónica que espera `await asyncio.sleep(0.5)` y registra el envío del comprobante con `logging` visible en la consola de uvicorn después de devolver `201`
  - Consultas de ventas y control de dueño (RN-14):
    - `GET /ventas` (`VENDEDOR` o `ADMIN`, paginado con `Pagina[VentaRead]`)
    - `GET /mis-ventas` (cualquier usuario autenticado con cambio de clave resuelto, paginado; devuelve las ventas del cliente vinculado a `usuario_actual.id` o lista vacía si el usuario no tiene ficha de cliente)
    - `GET /ventas/{id}` (autenticado con cambio de clave resuelto, sin `RequiereRol` fijo en el router): el servicio permite el acceso si el usuario tiene rol vigente `VENDEDOR`/`ADMIN` o si la venta pertenece a su ficha `cliente`, y responde `403` cuando un cliente intenta ver la venta de otro (Caso `C-06`), ejecutando siempre una cantidad fija de consultas SQL sin importar la cantidad de renglones (Caso `C-15`)
  - `parcial/seed.py`: limpia e inicializa la base de datos con los 5 usuarios (`admin@example.com`, `admin2@example.com`, `vendedor@example.com`, `ana@example.com`, `nuevo@example.com` con `debe_cambiar_password=True`), 3 editoriales, 3 géneros, 6 autores, 5 libros (*Rayuela* stock 10, *Antología de la literatura fantástica* stock 5, *Ficciones* stock 8, *Respiración artificial* stock 3, *Bestiario* stock 1), 3 clientes (Lucía Fernández con perfil, Tomás Ríos, Ana Paz vinculada a `ana@example.com`), la Venta 1 de Lucía ($69.000: 1 *Rayuela* + 2 *Ficciones*), los 7 movimientos de stock (5 de `"Stock inicial"` + 2 de salida por la Venta 1 cumpliendo `libro.stock == SUM(movimiento_stock.cantidad)`) y el evento inicial `"Carga de los datos iniciales"`
  - Suite de pruebas y evidencias en `parcial/test/` y `parcial/evidencia/`: archivos `.http` numerados (`01_salud_y_configuracion.http`, `02_autenticacion_y_usuarios.http`, `03_catalogo_y_stock.http`, `04_clientes_y_ventas.http`), script `parcial/test/solo_agregado.sql` y capturas/salidas en `parcial/evidencia/` demostrando los casos `C-01` a `C-16`
- **Dependencias**: C-02, C-03
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §5. `cliente` y `perfil_cliente`, §8. `venta` y `renglon_venta` y §Seed data inicial
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Catálogo, Stock y Ventas (RN-09, RN-10, RN-11, RN-13, RN-14)
  - `knowledge-base/06_funcionalidades.md` §Épica 4 (US-008)
  - `knowledge-base/07_flujos_principales.md` §Flujo 3: Registro de una Venta (`POST /ventas`)
  - `knowledge-base/10_preguntas_abiertas.md` §IN-01 y §IN-02 (orden exacto de IDs en `seed.py`)

---

## FASE 4 — Contenedorización Docker y Despliegue en VPS (Push 5)

> Este change trabaja exclusivamente sobre la carpeta `despliegue/` (TP Capítulos 1 a 4) y puede ejecutarse en paralelo a `C-02`, `C-03` y `C-04`.

### [C-05] `docker-alpine-and-vps-deploy`
- **Estado**: `[ ]` pendiente
- **Scope**: Empaquetado en Docker Alpine del TP original (Capítulos 1 a 4) en `despliegue/`, configuración de seguridad de contenedor, documentación de despliegue y evidencias `D-01` a `D-08` en el VPS de la cátedra (Ejercicios 9 y 10)
  - `despliegue/Dockerfile`: imagen base `python:3.12-alpine` (tamaño final `< 100 MB`, Caso `D-03`); copia e instalación de `requirements.txt` con `pip install --no-cache-dir` antes de copiar el código para aprovechar la caché de capas; creación y uso de usuario de sistema sin privilegios (`addgroup`/`adduser` + `USER`, `whoami != root`, Caso `D-04`); `EXPOSE 8000`; `HEALTHCHECK` usando `wget -qO- http://127.0.0.1:8000/health/ready || exit 1` para que el contenedor llegue a estado `(healthy)` (Caso `D-02`); comando de arranque que ejecuta `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`
  - `despliegue/.dockerignore` y `despliegue/env.example`: exclusión explícita de `.env`, `.venv`, `venv`, `.git`, `__pycache__` y artefactos locales para garantizar que ningún secreto quede horneado en las capas (`docker history`, Caso `D-08`); plantilla `env.example` documentando `DATABASE_URL` y `SQL_ECHO`
  - `despliegue/DEPLOY.md`: documentación completa con la dirección pública y puerto asignado en el VPS de la cátedra, comandos exactos de `docker build` y `docker run --env-file .env --restart unless-stopped`, conexión al PostgreSQL del VPS y procedimiento paso a paso para desplegar una nueva versión con `git pull`, `docker build` y reemplazo del contenedor corriendo migraciones
  - Verificación y evidencias en `despliegue/evidencia/`: salidas y capturas de los 8 casos de prueba de despliegue (`D-01` build limpio desde cero, `D-02` `docker ps` en estado `healthy`, `D-03` `docker images` `< 100 MB`, `D-04` `docker exec ... whoami` sin privilegios, `D-05` `GET /health/ready` público en el VPS, `D-06` `GET /libros` público con datos del seed, `D-07` `POST /ventas` público descontando stock y `D-08` ausencia de secretos en `git log -p` y `docker history`)
- **Dependencias**: C-01
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/01_vision_y_objetivos.md` §Alcance v2.0 (`despliegue/`) y §Métricas de éxito
  - `knowledge-base/02_descripcion_general.md` §Stack tecnológico y §Integraciones externas
  - `knowledge-base/06_funcionalidades.md` §Épica 5 (US-009)
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura obligatoria de directorios y §En `despliegue/`
  - `knowledge-base/10_preguntas_abiertas.md` §Preguntas abiertas (datos de conexión al VPS)
