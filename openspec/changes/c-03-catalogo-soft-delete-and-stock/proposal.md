# Proposal

## Why

El catálogo de `parcial/` conserva servicios con acceso directo a sesión, listados `limit/offset` y edición libre de stock, aunque C-01 y C-02 ya aportaron repositorios base, UoW, paginación y permisos. C-03 debe conectar esas bases con los ejercicios 3 y 6 sin invadir clientes, ventas, seed ni despliegue, asignados a otros integrantes.

## What Changes

- Refactorizar editoriales, géneros, autores y libros a `Router → Service → UoW → Repository → Model`, reutilizando las bases actuales.
- **BREAKING**: reemplazar listas y parámetros `limit/offset` del catálogo y sus colecciones relacionadas por `Pagina[T]` con `page/size`.
- **BREAKING**: sustituir `stock` de alta por `stock_inicial` y rechazar cambios de stock mediante PATCH y campos de entrada desconocidos.
- Mantener lecturas públicas y conectar las escrituras existentes de catálogo al grupo protegido y al rol `ADMIN`, sin modificar la implementación de autenticación.
- Incorporar baja lógica, reposición e historial paginado de movimientos, disponible incluso después de la baja.
- Crear un punto transaccional de cambio de stock compartible con C-04, con movimiento y actor por cada variación. C-03 lo utiliza para alta y reposición; la migración de ventas y seed corresponde a C-04.
- Mantener los demás campos actuales de PATCH de libro y las rutas existentes; no añadir PATCH de géneros ni alterar sus contratos por inferencia de ejemplos.

## Capabilities

### New Capabilities

- `catalogo`: catálogo público paginado, contratos de edición, capas de persistencia y administración protegida.
- `stock-y-baja-logica`: alta con stock inicial, modificación trazable de inventario, baja lógica e historial de movimientos.

### Modified Capabilities

Ninguna. Se consumen `core-lifecycle-and-architecture`, `domain-schema-and-migrations` y `auth-usuarios-and-rbac` sin cambiar sus requisitos ni las cuatro migraciones.

## Impact

Código afectado: los cuatro módulos de catálogo, su montaje en `parcial/main.py` y pruebas de catálogo. `core/repository.py` sólo admite una corrección mínima de resultados escalares si una reproducción con sesión real demuestra que impide reutilizarlo, con regresión de C-02 y revisión del defecto previo.

No se requieren dependencias de ejecución ni migraciones nuevas. Las restricciones y el disparador existentes se verificarán en PostgreSQL aislado mediante Alembic; los dobles de prueba no prueban esas garantías.

Límite de integración: `ventas/service.py` y `seed.py` todavía escriben stock directamente. C-03 deja listo el contrato que C-04 debe consumir; no certifica todavía RN-11 ni RN-13 completas en todo el sistema.

Revisión previa: C-03 tiene gobernanza ALTA. La propuesta queda pendiente de aprobación antes de aplicar. También quedan pendientes un baseline reproducible del entorno del repo y resolver la disponibilidad de las skills de dominio exigidas por `AGENTS.md`.
