# Descripción General

## Stack tecnológico

| Capa | Tecnología | Versión mínima | Uso en el proyecto |
|---|---|---|---|
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

## Arquitectura general

```
Petición HTTP (con o sin Cookie access_token)
   │
   ▼
┌─────────────────────────────────────────────────────────────┐
│ main.py (FastAPI + Lifespan + Manejadores de Error)         │
│  ├─ Grupo Abierto (/health, /auth, GET catálogo)            │
│  └─ Grupo Protegido (Depends(verificar_cambio_password))    │
└─────────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────────────────┐
│ Router (app/modules/<módulo>/router.py)                     │
│  - Valida contratos de entrada/salida (schemas.py)          │
│  - Inyecta Dependencias (UsuarioActual, RequiereRol, UoW)   │
│  - Construye el UnitOfWork del módulo (sin abrirlo)         │
└─────────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────────────────┐
│ Service (app/modules/<módulo>/service.py)                   │
│  - Contiene las reglas de negocio                           │
│  - Abre el UoW con `async with uow:` (nunca lo construye)   │
│  - Traduce IntegrityError a errores de dominio (409/404)    │
└─────────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────────────────┐
│ Unit of Work (app/modules/<módulo>/unit_of_work.py)         │
│  - Compone los repositorios necesarios con la MISMA sesión  │
│  - Confirma (commit) al salir o revierte (rollback) si falla│
│  - Nunca cierra la sesión (la cierra get_session)           │
└─────────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────────────────┐
│ Repository (app/modules/<módulo>/repository.py)             │
│  - Hereda de BaseRepository[T] o SoftDeleteRepository[T]    │
│  - Declara la precarga (selectinload/joinedload)            │
│  - Ejecuta flush(), NUNCA commit()                          │
└─────────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────────────────┐
│ PostgreSQL 16 (Modelos SQLModel + Triggers + Constraints)   │
└─────────────────────────────────────────────────────────────┘
```

## Integraciones externas
- **PostgreSQL 16 (Local y en VPS):** Única dependencia de infraestructura externa. En el despliegue del VPS (`despliegue/`), el contenedor se conecta al PostgreSQL ya instalado en el servidor host (vía `host.docker.internal` o dirección provista por la cátedra).
- **Notificación de comprobante (Simulada):** Se ejecuta en segundo plano mediante `FastAPI.BackgroundTasks` con `await asyncio.sleep(0.5)` e impresión en el logger configurado tras confirmar una venta.

## API REST — Resumen de Endpoints de Referencia

### Grupo Abierto (No exige el bloqueo de cambio de contraseña)
| Método | Ruta | Acceso | Códigos |
|---|---|---|---|
| `GET` | `/health/live` | Cualquiera | `200` |
| `GET` | `/health/ready` | Cualquiera | `200`, `503` |
| `POST` | `/auth/registro` | Cualquiera | `201`, `409`, `422` |
| `POST` | `/auth/login` | Cualquiera | `200`, `401`, `422`, `429` |
| `POST` | `/auth/logout` | Cualquiera | `200` |
| `GET` | `/auth/yo` | Autenticado | `200`, `401` |
| `POST` | `/auth/cambiar-password` | Autenticado | `200`, `401`, `422` |
| `GET` | `/libros` (`page`, `size`, `titulo`, `genero_id`) | Cualquiera | `200`, `422` |
| `GET` | `/libros/{id}` | Cualquiera | `200`, `404`, `422` |
| `GET` | `/editoriales`, `/generos` (`page`, `size`) | Cualquiera | `200`, `422` |
| `GET` | `/editoriales/{id}/libros`, `/generos/{id}/libros`, `/autores/{id}/libros` | Cualquiera | `200`, `404` |

### Grupo Protegido (Responde `401` sin sesión y `403` si `debe_cambiar_password=True`)
| Método | Ruta | Rol requerido | Códigos |
|---|---|---|---|
| `POST` | `/usuarios` | `ADMIN` | `201`, `409`, `422` |
| `GET` | `/usuarios/{id}/roles` | `ADMIN` | `200`, `404` |
| `POST` | `/usuarios/{id}/roles` | `ADMIN` | `201`, `404`, `409`, `422` |
| `DELETE` | `/usuarios/{id}/roles/{rol}` | `ADMIN` | `200`, `404`, `409` |
| `GET` | `/eventos` (`page`, `size`) | `ADMIN` | `200`, `422` |
| `POST` | `/editoriales`, `/generos`, `/autores` | `ADMIN` | `201`, `409`, `422` |
| `PATCH` | `/editoriales/{id}`, `/autores/{id}` | `ADMIN` | `200`, `404`, `409`, `422` |
| `POST` | `/libros` (con `autores` y `stock_inicial`) | `ADMIN` | `201`, `409`, `422` |
| `PATCH` | `/libros/{id}` (`titulo` y `precio`; sin `stock`) | `ADMIN` | `200`, `404`, `409`, `422` |
| `DELETE` | `/libros/{id}` (borrado lógico) | `ADMIN` | `204`, `404` |
| `POST` | `/libros/{id}/reponer` | `ADMIN` | `200`, `404`, `409`, `422` |
| `GET` | `/libros/{id}/movimientos` | `ADMIN` | `200`, `404` |
| `POST` | `/clientes` | `VENDEDOR`, `ADMIN` | `201`, `409`, `422` |
| `GET`, `PATCH` | `/clientes/{id}` (con su perfil) | `VENDEDOR`, `ADMIN` | `200`, `404`, `409`, `422` |
| `POST` | `/clientes/{id}/perfil` | `VENDEDOR`, `ADMIN` | `201`, `404`, `409` |
| `GET` | `/clientes/{id}/ventas` | `VENDEDOR`, `ADMIN` | `200`, `404` |
| `POST` | `/ventas` (con `renglones`) | `VENDEDOR`, `ADMIN` | `201`, `409`, `422` |
| `GET` | `/ventas` (`page`, `size`) | `VENDEDOR`, `ADMIN` | `200`, `422` |
| `GET` | `/ventas/{id}` | Personal (`VENDEDOR`/`ADMIN`) o Cliente dueño | `200`, `403`, `404` |
| `GET` | `/mis-ventas` (`page`, `size`) | Autenticado (sin cambio de clave pendiente) | `200`, `422` |
