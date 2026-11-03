# core-lifecycle-and-architecture Specification

## Purpose

Defines the core configuration, application lifecycle, health monitoring, generic persistence patterns (Repository and Unit of Work), standardized pagination contract, and security/authorization primitives required across the `parcial/` backend.

## ADDED Requirements

### Requirement: Environment Configuration Without Default Secrets
The system SHALL load all configuration values from environment variables or a non-versioned `.env` file, assemble the asynchronous database connection URL dynamically, and refuse to start if database credentials or token signing secrets are missing or blank.

#### Scenario: Application starts with complete environment configuration
- **WHEN** `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, and `JWT_SECRET_KEY` are provided with non-empty values
- **THEN** the system constructs a `postgresql+asyncpg://` connection URL and initializes the settings object

#### Scenario: Application refuses to start when secrets are missing
- **WHEN** `POSTGRES_PASSWORD` or `JWT_SECRET_KEY` is omitted or empty in the environment
- **THEN** settings validation fails at startup before accepting any HTTP requests

### Requirement: Application Lifespan Resource Management and Health Checks
The system SHALL create the database engine pool, session factory (`expire_on_commit=False`), password-hashing concurrency semaphore, and constant-time dummy password hash once during the application lifespan, dispose the engine on shutdown, and expose liveness and readiness endpoints.

#### Scenario: Liveness probe responds without touching the database
- **WHEN** a client requests `GET /health/live`
- **THEN** the system returns HTTP `200` with `{"estado": "vivo"}` without executing any database query

#### Scenario: Readiness probe verifies database connectivity
- **WHEN** a client requests `GET /health/ready` and PostgreSQL responds to `SELECT 1`
- **THEN** the system returns HTTP `200` with `{"estado": "listo", "base": "ok"}`

#### Scenario: Readiness probe reports service unavailable when database is down
- **WHEN** a client requests `GET /health/ready` and the database connection fails
- **THEN** the system returns HTTP `503` with `{"estado": "no listo", "base": "sin conexión"}`

### Requirement: Generic Repository and Soft-Delete Persistence Contract
Every repository SHALL flush pending writes to the database session without committing the transaction, and soft-delete repositories SHALL filter logically deleted records (`borrado_en IS NOT NULL`) from standard reads while preserving historical lookup and soft-deletion operations.

#### Scenario: Repository write operations flush without committing
- **WHEN** `add`, `update`, `delete`, or `soft_delete` is called on a repository
- **THEN** changes are flushed to the active session so constraints and primary keys are evaluated, but the transaction remains uncommitted until the Unit of Work exits

#### Scenario: Soft-delete repository hides deleted records from standard queries
- **WHEN** a record has a non-null `borrado_en` timestamp
- **THEN** `get_by_id`, `get_all`, and `count` exclude that record while `get_by_id_including_deleted` still returns it

### Requirement: Transactional Unit of Work Sharing the Request Session
The Unit of Work SHALL act as an asynchronous context manager over the request-scoped database session, committing on normal exit, rolling back on unhandled exceptions, and leaving session closure to the request dependency.

#### Scenario: Unit of Work commits atomic multi-write operations on success
- **WHEN** a service block exits `async with uow:` without raising an exception
- **THEN** the Unit of Work commits the shared session and keeps the session open for post-commit reads in the same request

#### Scenario: Unit of Work rolls back all writes when an exception occurs
- **WHEN** an exception is raised inside `async with uow:`
- **THEN** the Unit of Work rolls back all flushed writes in that transaction so no partial data remains

### Requirement: Standardized Page Envelope Validation
All paginated listings SHALL return `{items, total, page, size, pages}` with `page >= 1` and `1 <= size <= 100` (default `20`), returning `pages = 1` when `total = 0` and rejecting out-of-range page numbers with HTTP `422`.

#### Scenario: Requesting a page beyond the total available pages fails validation
- **WHEN** a client requests `page=4` on a collection that has only `3` pages of results
- **THEN** the system returns HTTP `422` with detail `"La página 4 no existe: hay 3"`

### Requirement: Off-Loop Password Hashing and Cookie-Only JWT Dependencies
Password hashing and verification SHALL run outside the event loop under a concurrency semaphore with a 72-byte UTF-8 maximum, and authentication/authorization dependencies SHALL read the JWT exclusively from the `HttpOnly` `access_token` cookie and verify active roles in the database per request.

#### Scenario: Missing or Bearer-only token is rejected with 401
- **WHEN** a protected endpoint is called without the `access_token` cookie (even if an `Authorization: Bearer` header is sent)
- **THEN** the authentication dependency returns HTTP `401`

#### Scenario: User with pending mandatory password change is blocked from protected routes
- **WHEN** an authenticated user with `debe_cambiar_password = True` requests a route in the protected router group
- **THEN** the dependency returns HTTP `403`
