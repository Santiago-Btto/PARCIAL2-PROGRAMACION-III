# domain-schema-and-migrations Specification

## Purpose

Defines the relational schema, constraints, partial unique indexes, relationships, and Alembic migrations (including the append-only PL/pgSQL trigger on stock movements) for the bookstore domain.

## Requirements

### Requirement: Access Control, Audit, and Stock Movement Tables
The database schema SHALL include tables for `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`, and `movimiento_stock` with timezone-aware timestamps (`TIMESTAMPTZ`), explicit foreign key indexes, and domain `CHECK` constraints.

#### Scenario: Role assignment enforces valid role names and single open assignment per role
- **WHEN** a row is inserted into `asignacion_rol`
- **THEN** the database enforces `rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')` and rejects duplicate open assignments (`WHERE revocada_en IS NULL`) for the same `(usuario_id, rol)` via partial unique index `uq_asignacion_rol_usuario_rol_abierta`

#### Scenario: Stock movement rejects zero quantity
- **WHEN** a row with `cantidad = 0` is inserted into `movimiento_stock`
- **THEN** PostgreSQL rejects the write via check constraint `ck_movimiento_stock_cantidad_no_cero`

### Requirement: Optional Web User Link on Customer and Soft-Delete ISBN Uniqueness on Book
The `cliente` table SHALL support an optional unique reference to `usuario` (`usuario_id`), and the `libro` table SHALL support logical deletion (`borrado_en`) with ISBN uniqueness enforced exclusively among active books (`WHERE borrado_en IS NULL`).

#### Scenario: Deleted book ISBN can be reused by a new active book
- **WHEN** an existing book has `borrado_en IS NOT NULL` and a new book is inserted with the same `isbn` and `borrado_en IS NULL`
- **THEN** the partial unique index `uq_libro_isbn_vigente` allows the insert while rejecting a second active book with that same `isbn`

### Requirement: Append-Only Trigger on Stock Movements and Reversible Migrations
The schema SHALL be managed exclusively through four reversible Alembic migrations (`upgrade head` and `downgrade base`), with the fourth migration installing a database trigger that rejects any `UPDATE` or `DELETE` on `movimiento_stock`.

#### Scenario: Database trigger blocks UPDATE and DELETE on movimiento_stock
- **WHEN** any client or SQL session executes `UPDATE` or `DELETE` against rows in `movimiento_stock`
- **THEN** trigger `trg_movimiento_stock_solo_agregado` aborts the operation with an exception (`RN-12`)

#### Scenario: Full migration upgrade and downgrade cycle succeeds
- **WHEN** `alembic upgrade head`, `alembic downgrade base`, and `alembic upgrade head` are executed against an empty PostgreSQL database
- **THEN** all tables, partial unique indexes, foreign keys, and triggers are created, dropped, and recreated without errors
