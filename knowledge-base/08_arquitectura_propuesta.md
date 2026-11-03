# Arquitectura Propuesta

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|---|---|---|
| **Layered Architecture (`Router → Service → UoW → Repository → Model`)** | Todos los módulos de `parcial/app/modules/` | Cada capa tiene una única responsabilidad: HTTP en el router, reglas de negocio en el service, atomicidad transaccional en el UoW y consultas/precarga en el repositorio |
| **Generic Repository (`BaseRepository[T]`)** | `app/core/repository.py` y `app/modules/*/repository.py` | Centraliza `get_by_id`, `get_all`, `count`, `add`, `update`, `delete` haciendo `flush()` y nunca `commit()` |
| **Soft Delete Repository (`SoftDeleteRepository[T]`)** | `app/core/repository.py` y `LibroRepository` | Filtra transparentemente `borrado_en IS NULL` en lecturas normales y expone `get_by_id_including_deleted` y `soft_delete` |
| **Unit of Work (`UnitOfWork`)** | `app/core/unit_of_work.py` y `app/modules/*/unit_of_work.py` | Agrupa múltiples escrituras de una operación de negocio en una sola transacción (`commit` al salir del `async with`, `rollback` ante excepción, sin cerrar la sesión) |
| **Single Point of Stock Mutation** | Servicio/Repositorio de `libros` compartido con `ventas` | Garantiza la invariante `libro.stock == SUM(movimiento_stock.cantidad)` en alta, reposición y venta (RN-11) |
| **Independent Audit Session** | Registro de `IntentoAcceso` en login | Permite que el conteo de intentos fallidos sobreviva al rollback de un login rechazado (Ejercicio 7) |

## Estructura obligatoria de directorios

```
libreria-tp/
├── parcial/                        # Proyecto ampliado (Capítulos 1 a 6 — Ejercicios 1 a 8)
│   ├── main.py                     # Aplicación FastAPI, lifespan y los dos grupos de rutas
│   ├── seed.py                     # Deja la base en el estado inicial conocido
│   ├── alembic.ini                 # Configuración de Alembic (sin credenciales)
│   ├── env.example                 # Plantilla de variables de entorno sin secretos
│   ├── requirements.txt            # Dependencias del parcial
│   ├── README.md                   # Integrantes e instrucciones de puesta en marcha
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py           # Settings con pydantic-settings y @computed_field
│   │   │   ├── database.py         # crear_motor, crear_fabrica_sesiones y get_session
│   │   │   ├── security.py         # Hash bcrypt (to_thread + semáforo) y JWT en cookie
│   │   │   ├── dependencies.py     # get_usuario_actual, cambio obligatorio y requiere_rol
│   │   │   ├── repository.py       # BaseRepository[T] y SoftDeleteRepository[T]
│   │   │   ├── paginacion.py       # Pagina[T] {items, total, page, size, pages}
│   │   │   ├── unit_of_work.py     # UnitOfWork base (confirma o revierte, no cierra sesión)
│   │   │   ├── errores.py          # Excepciones de dominio y traducción de IntegrityError
│   │   │   ├── parametros.py       # IdPath y constantes de validación
│   │   │   └── modelos.py          # Registro de todos los modelos para Alembic
│   │   └── modules/
│   │       ├── health/             # Sólo router.py (/health/live y /health/ready)
│   │       ├── usuarios/           # Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad
│   │       ├── editoriales/        # models, schemas, repository, unit_of_work, service, router
│   │       ├── generos/            # models, schemas, repository, unit_of_work, service, router
│   │       ├── autores/            # models, schemas, repository, unit_of_work, service, router
│   │       ├── libros/             # Libro, LibroAutor, MovimientoStock + UoW/Repository
│   │       ├── clientes/           # Cliente, PerfilCliente + UoW/Repository
│   │       └── ventas/             # Venta, RenglonVenta + UoW/Repository
│   ├── migrations/                 # 4 migraciones de Alembic (2 del TP + 3ª auto + 4ª manual)
│   ├── test/                       # Archivos .http (C-01 a C-16) y solo_agregado.sql (C-14)
│   └── evidencia/                  # Evidencias de C-14 (psql) y C-15 (consultas fijas)
│
└── despliegue/                     # TP Capítulos 1 a 4 empaquetado para el VPS (Ejercicios 9 y 10)
    ├── Dockerfile                  # python:3.12-alpine, non-root, HEALTHCHECK, alembic + uvicorn
    ├── .dockerignore               # Excluye .env, .venv, .git, __pycache__
    ├── DEPLOY.md                   # URL pública, comandos docker build/run y actualización
    ├── env.example                 # DATABASE_URL y SQL_ECHO de ejemplo
    ├── evidencia/                  # Salidas de los casos D-01 a D-08
    └── ...                         # Código intacto del TP Capítulos 1 a 4
```

## Seguridad
- **Autenticación:** Contraseñas hasheadas con `bcrypt` (costo configurable en `BCRYPT_ROUNDS`), ejecutado siempre fuera del bucle de eventos con `asyncio.to_thread` y acotado por un `asyncio.Semaphore(BCRYPT_MAX_CONCURRENT)`. Límite estricto de 72 bytes en todos los contratos de contraseña.
- **Transporte de sesión:** JWT firmado con `HS256` (`sub`, `exp`, `roles`) enviado exclusivamente en la cookie `access_token` con `HttpOnly`, `SameSite=Lax`, `Max-Age` igual a la expiración del token y `Secure` configurable (`COOKIE_SECURE`). Nunca viaja en el cuerpo JSON ni se lee del header `Authorization`.
- **Autorización:** Dos grupos de rutas en `main.py` (abierto vs. protegido con `verificar_cambio_password_resuelto`) y dependencia `requiere_rol` que consulta `asignacion_rol` en la base en cada petición usando la misma sesión del `UnitOfWork`.
- **Validación de entrada y ocultamiento de errores:** Todos los DTOs de entrada declaran `extra="forbid"`. Los `IntegrityError` se traducen por nombre de restricción a mensajes propios (`409`), sin exponer nombres de tablas ni trazas al cliente.

## Variables de entorno

### En `parcial/.env` (`pydantic-settings`)
| Variable | Descripción | Ejemplo | Sensible | Valor por defecto en código |
|---|---|---|---|---|
| `POSTGRES_USER` | Usuario de PostgreSQL | `postgres` | No | **Ninguno (obligatoria)** |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL | `secreto123` | **Sí** | **Ninguno (obligatoria)** |
| `POSTGRES_DB` | Nombre de la base de datos | `libreria` | No | **Ninguno (obligatoria)** |
| `POSTGRES_HOST` | Host del servidor PostgreSQL | `localhost` | No | `"localhost"` |
| `POSTGRES_PORT` | Puerto de PostgreSQL | `5432` | No | `5432` |
| `DB_POOL_SIZE` | Tamaño base del pool de conexiones | `5` | No | `5` |
| `DB_MAX_OVERFLOW` | Conexiones adicionales permitidas en el pool | `10` | No | `10` |
| `SQL_ECHO` | Muestra las consultas SQL en consola | `true` | No | `False` |
| `JWT_SECRET_KEY` | Clave secreta para firmar tokens JWT | `<64 hex chars>` | **Sí** | **Ninguno (obligatoria)** |
| `JWT_ALGORITHM` | Algoritmo de firma JWT | `HS256` | No | `"HS256"` |
| `JWT_EXPIRE_MINUTES` | Duración de la sesión en minutos | `30` | No | `30` |
| `COOKIE_SECURE` | Marca `Secure` en la cookie `access_token` | `false` | No | `False` |
| `BCRYPT_ROUNDS` | Factor de costo de `bcrypt` | `12` | No | `12` |
| `BCRYPT_MAX_CONCURRENT` | Máximo de hashes `bcrypt` simultáneos | `4` | No | `4` |

### En `despliegue/` (Contenedor del TP Cap. 1–4)
| Variable | Descripción | Ejemplo | Sensible |
|---|---|---|---|
| `DATABASE_URL` | URL completa con driver `postgresql+asyncpg://` | `postgresql+asyncpg://user:pass@host.docker.internal:5432/db` | **Sí** |
| `SQL_ECHO` | Desactiva o activa log de consultas SQL en producción | `false` | No |
