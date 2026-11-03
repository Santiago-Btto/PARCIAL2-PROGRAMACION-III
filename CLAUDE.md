# Librería (Parcial Programación III — Unidades 1 a 6) — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

---

## Stack Tecnológico

| Capa | Tecnología | Versión mínima | Uso en el proyecto |
|------|------------|----------------|--------------------|
| Lenguaje | Python | 3.12 | Tipado moderno, `asyncio`, `TypeVar` y gestores de contexto asincrónicos |
| Framework Web | FastAPI | 0.111 | API REST asincrónica (`async def` en todos los handlers), inyección de dependencias y validación |
| Modelos y ORM | SQLModel + SQLAlchemy | 0.0.24 / 2.0 (async) | Modelos de tabla, `AsyncSession`, `selectinload`/`joinedload` y `lazy="raise"` |
| Driver DB | asyncpg | 0.30 | Controlador asincrónico de PostgreSQL (`postgresql+asyncpg://`) |
| Base de Datos | PostgreSQL | 16 | Motor relacional con índices únicos parciales, `CHECK`, `timestamptz` y triggers PL/pgSQL |
| Migraciones | Alembic | 1.13 (async) | Versionado de esquema (`--autogenerate` y migraciones manuales) |
| Configuración | pydantic-settings | 2.0 | Lectura y validación de variables de entorno (`.env`) y `@computed_field` |
| Hashing | bcrypt | 4.0 | Hash de contraseñas ejecutado con `asyncio.to_thread` y `asyncio.Semaphore` |
| Tokens | PyJWT | 2.8 | Emisión y verificación de JWT (`HS256`) transportado en cookie `HttpOnly` |
| Servidor ASGI | Uvicorn | `fastapi[standard]` | Ejecución del servidor en desarrollo y producción |
| Contenedores | Docker | 20.10 (`python:3.12-alpine`) | Empaquetado del TP (cap. 1 a 4) en `despliegue/` y ejecución en el VPS |

Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Entender propósito y alcance (`parcial/` vs `despliegue/`) |
| [02_descripcion_general.md](knowledge-base/02_descripcion_general.md) | Stack, arquitectura en 5 capas y tabla completa de endpoints |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Auth, RBAC (`ADMIN`, `VENDEDOR`, `CLIENTE`), `401` vs `403`, rutas públicas |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Entidades, ERD, restricciones, trigger append-only y datos de `seed.py` |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas codificadas oficiales (`RN-01` a `RN-16`) y garantes esperados |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias de usuario (`US-001` a `US-009`) por épica |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos E2E: Login, Auto-registro, Venta transaccional y Baja lógica |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones (`Repository`, `SoftDeleteRepository`, `UnitOfWork`), estructura y `.env` |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones de diseño (`DD-01` a `DD-04`) y supuestos del seed |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | Detalles de atención (`IN-01`, `IN-02`) y datos del VPS |

---

## Skills Disponibles

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend Core** | FastAPI / Capas (`Router → Service → UoW → Repository`) / Contratos | `fastapi`, `fastapi-templates` |
| **Database & ORM** | SQLModel / SQLAlchemy 2.0 async / Migraciones Alembic / PostgreSQL 16 | `sqlalchemy-alembic-expert-best-practices-code-review`, `postgresql-table-design` |
| **DevOps & VPS** | Contenedorización Alpine (`despliegue/Dockerfile`) y despliegue en VPS | `multi-stage-dockerfile` |
| **Orquestación** | SDD / OPSX / Fundación y mantenimiento de documentación | `active-orchestrator`, `kb-creator`, `roadmap-generator`, `agents-md-generator`, `skill-registry`, `find-skills` |

Cargá la skill correspondiente al contexto ANTES de escribir código.

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; no versionado — no está en el repo). Esta tabla solo mapea skill→rol.

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 5 changes en 5 fases (alineados a los 5 bloques/pushes del grupo).
- **Camino crítico** (4): `C-01 → C-02 → C-03 → C-04*` (con `C-01 → C-05*` en paralelo sobre `despliegue/`).
- **Primer change**: `C-01` (`core-models-and-migrations` — ya implementado en el Push 1); siguiente en cola: `C-02` (`auth-usuarios-and-rbac`) y/o `C-05` (`docker-alpine-and-vps-deploy`).

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y los archivos de "Leer antes".

---

## Reglas Duras (específicas del proyecto)

> Reglas globales ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD, engram): el proyecto las hereda. Acá viven solo las reglas **específicas de este proyecto** + las universales que el global no cubra.

1. **Capas y Transacciones (`Router → Service → UoW → Repository → Model`)**:
   - **NUNCA** hacer `commit()` dentro de un `Repository` (`add`, `update` y `delete`/`soft_delete` sólo ejecutan `flush()`).
   - **NUNCA** construir el `UnitOfWork` adentro de un `Service` ni abrirlo en el `Router` → el `Router` lo inyecta por dependencia y se lo pasa sin abrir al `Service`; el `Service` lo abre con `async with uow:`.
   - **NUNCA** cerrar la `AsyncSession` en `UnitOfWork.__aexit__` → el `UnitOfWork` comparte la misma sesión (`SessionDep`) que las dependencias de autenticación/autorización (`get_usuario_actual` / `requiere_rol`), y sólo `get_session` la cierra al terminar la petición.
   - **EXCEPCIÓN ÚNICA**: El registro de `IntentoAcceso` en el login es la única escritura de todo el sistema que abre su propia sesión y transacción y hace `commit()` siempre (con el comentario obligatorio de 3 puntos del Ejercicio 7) para sobrevivir al rollback de un login fallido.
2. **Esquema, Migraciones y Garantías en Base de Datos**:
   - **NUNCA** usar `SQLModel.metadata.create_all` → el esquema se gestiona exclusivamente con las 4 migraciones de Alembic (`474a246cb918`, `f3bb61a7b792`, `9a4e7c2b1d80` autogenerada y `c8e31f5a9021` manual con el trigger de sólo agregado), verificando que `alembic upgrade head`, `alembic downgrade base` y `alembic upgrade head` funcionen sin errores.
   - **NUNCA** verificar unicidad con un `SELECT` previo → delegar en las restricciones `UNIQUE` e índices únicos parciales (`uq_asignacion_rol_usuario_rol_abierta` y `uq_libro_isbn_vigente` con `WHERE ... IS NULL`) y traducir el `IntegrityError` a `409 Conflicto` con mensaje propio.
   - **NUNCA** usar `float` para dinero ni fechas sin zona horaria → usar siempre `Decimal` / `NUMERIC` y `datetime` con `timezone=True` (`TIMESTAMPTZ`).
3. **Asincronía, Precarga y Bcrypt**:
   - **NUNCA** escribir un handler sin `async def`, ni ejecutar llamadas bloqueantes en el bucle de eventos, ni depender de carga perezosa → todas las relaciones llevan `lazy="raise"` y la precarga (`selectinload` / `joinedload`) se declara adentro del método del repositorio que la necesita.
   - **NUNCA** invocar `bcrypt` en el hilo del bucle de eventos ni dentro de una transacción abierta → correr siempre con `asyncio.to_thread` bajo `asyncio.Semaphore`, calcular el hash **antes** de abrir el `UnitOfWork`, y validar el límite máximo de **72 bytes** en UTF-8 en todo contrato de contraseña (`422` si se excede).
4. **Contratos, Errores y Paginación**:
   - **NUNCA** permitir campos no declarados en los DTOs de entrada → todos los schemas de entrada usan `ConfigDict(extra="forbid")` y los `PATCH` aplican `model_dump(exclude_unset=True)`.
   - **NUNCA** incluir `password_hash` en un schema de salida ni devolver texto crudo de PostgreSQL/SQLAlchemy o trazas al cliente (`RN-15`).
   - **NUNCA** paginar con `limit/offset` en `parcial/` → todos los listados devuelven `Pagina[T]` (`{items, total, page, size, pages}` con `page >= 1`, `1 <= size <= 100`, default `20`, y `422` si `page > pages`).
5. **Autenticación, Cookies y Autorización (RBAC)**:
   - **NUNCA** devolver el JWT en el cuerpo JSON del login ni leerlo de la cabecera `Authorization: Bearer` → el token viaja exclusivamente en la cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`, `Secure` configurable).
   - **NUNCA** decidir permisos por los roles del token ni mezclar `401` con `403` → `get_usuario_actual` responde `401`; `requiere_rol` consulta `asignacion_rol` vigente en la base en cada petición y responde `403`; el control de cambio obligatorio (`debe_cambiar_password`) va montado una sola vez en `grupo_protegido` en `main.py` (`403`).
6. **Stock, Movimientos y Borrado Lógico**:
   - **NUNCA** modificar `libro.stock` por `PATCH` ni fuera del único punto de escritura de stock → sólo cambia en el alta con `stock_inicial`, la reposición (`POST /libros/{id}/reponer`) y la venta (`POST /ventas`), dejando siempre su fila correspondiente en `movimiento_stock` (`RN-11`) protegida por el disparador `trg_movimiento_stock_solo_agregado` (`RN-12`).
   - **NUNCA** borrar físicamente un `Libro` → usar borrado lógico (`borrado_en = now()`, `204 No Content`).
7. **Contenedor Docker y Despliegue en VPS (`despliegue/`)**:
   - **NUNCA** modificar la lógica de negocio del TP de los capítulos 1 a 4 dentro de `despliegue/`, ni usar una imagen base distinta de `python:3.12-alpine`, ni correr el contenedor como `root`, ni hornear secretos/URLs en el `Dockerfile` → instalar `requirements.txt` con `--no-cache-dir` antes de copiar el código, usar usuario sin privilegios (`USER`), aplicar `alembic upgrade head` al arrancar y declarar `HEALTHCHECK` con `wget -qO- http://127.0.0.1:8000/health/ready`.
8. **Git, Credenciales y Formato de Entrega**:
   - **NUNCA** poner valores por defecto en el código para `POSTGRES_PASSWORD` ni `JWT_SECRET_KEY`, ni versionar `.env`, `.venv` o `__pycache__/`.
   - Realizar los commits con el autor `Santiago-Btto <santiagobtto30@gmail.com>`, sin líneas de co-autoría IA.

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)        → entender el dominio y las RN-01..RN-16
2. Identificar el change en CHANGES.md           → respetar dependencias y gates
3. /opsx:propose C-NN-nombre                     → proposal + design + specs + tasks
4. Implementar las tasks (cargando skills)       → respetando las reglas duras
5. /opsx:archive C-NN-nombre + marcar [x]        → cerrar el change
```

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
