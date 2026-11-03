# Evidencia TDD de C-03

| Tarea | Prueba/capa | Safety net | RED | GREEN y triangulación |
|---|---|---|---|---|
| 1.1 | Revisión de propuesta, AGENTS y skills | No aplica | No aplica | Alcance y reglas cargados antes de código |
| 1.2 | Cuatro módulos de pruebas originales | Python 3.13.5 / FastAPI 0.136.3: 32/32 | N/A: baseline | Repetido en la suite final |
| 1.3 | Alembic / PostgreSQL | PostgreSQL 16.15 sintético, loopback; head `c8e31f5a9021` | N/A: entorno | `upgrade head → downgrade base → upgrade head` |
| 1.4 | BaseRepository y SoftDeleteRepository / PostgreSQL | 32 pruebas originales | SELECT SQLAlchemy devolvió `Row`, no modelo | Cambio a `sqlmodel.select`; regresión C-02 de 30 pruebas pasó |
| 2.1 | Editoriales / servicio, UoW, unitarias y verificación final PostgreSQL | 32 originales | La suite de entidades falló antes del nuevo repository de libros requerido | CREATE/PATCH parcial, paginación, conflicto/rollback y campos omitidos/nulos pasan |
| 2.2 | Géneros / servicio, UoW, unitarias y verificación final PostgreSQL | 32 originales | Suite de entidades RED antes de completar capas | Alta, conflicto, DTO estricto; sólo rutas existentes |
| 2.3 | Autores / servicio, UoW, unitarias y verificación final PostgreSQL | 32 originales | Suite de entidades RED antes de completar capas | Alta/PATCH/autoría y DTO estricto pasan |
| 2.4 | Colecciones relacionadas / PostgreSQL | 32 originales | Suite de entidades RED antes de completar repositorios | Páginas, totales, libros dados de baja excluidos y rol/orden conservados |
| 3.1 | LibroRepository/UoW / PostgreSQL | 32 originales | Repo y UoW no existían al redactar pruebas | Modelo, sesión compartida, carga previa, historial; consulta de detalle = 2 SELECT tanto para 1 como para 4 autores |
| 3.2 | Listado / PostgreSQL | 32 originales | Repo inexistente | 25 resultados paginados, filtros y 4 términos LIKE literales pasan |
| 3.3 | DTO / unitarias | 32 originales | `ReposicionCreate` y contratos de stock ausentes | 47 casos de schema pasan; stock desconocido en PATCH devuelve 422 |
| 4.1 | `cambiar_stock` / unitarias y PostgreSQL | 32 originales | Helper/consulta de bloqueo ausentes | 10 casos unitarios e integración con saldo, actor, venta, rollback y límites pasan |
| 4.2 | Alta / PostgreSQL | 32 originales | Servicio aún aceptaba `AsyncSession`, no stock inicial/UoW | Stock cero o positivo, autorías/movimiento atómicos y rollback por FK pasan |
| 4.3 | Reposición / PostgreSQL y HTTP | 32 originales | Reposición no existía | 404, baja 409, validación 422, movimiento y respuesta actualizada pasan |
| 4.4 | Bloqueo / PostgreSQL 16, sesiones concurrentes | 32 originales | Reposición bloqueada aún no estaba implementada | Dos reposiciones simultáneas preservan ambos incrementos/movimientos |
| 5.1 | Baja lógica / PostgreSQL y HTTP | 32 originales | DELETE lógico no existía | 204, ocultamiento del catálogo, historial/relaciones conservados y repetición 404 pasan |
| 5.2 | ISBN / PostgreSQL | 32 originales | Manejo de índice parcial no estaba en el servicio nuevo | ISBN reutilizable tras baja y duplicado vigente 409 pasan |
| 5.3 | Movimientos / PostgreSQL y HTTP | 32 originales | Endpoint/historial paginado no existía | Historial conserva el libro dado de baja; páginas separan IDs/libros |
| 6.1 | Rutas HTTP del catálogo / ASGI y PostgreSQL | 32 originales | `main` aún importaba routers ya separados | Montaje, 401, 403 de rol y cambio de clave, alta, PATCH 422, reposición, baja e historial pasan con overrides explícitos de auth |
| 6.2 | Regresión completa | 32 originales | Suite C-03 incremental | `pytest test`: 135/135 en PostgreSQL 16.15; la verificación de auth queda aislada, no es E2E de C-02 |
| 6.3 | Ejemplos HTTP y handoff | N/A: documentación | N/A | Comandos y firma del helper C-04 documentados en `05_catalogo_y_stock.http` y `C03_C04_HANDOFF.md` |

El baseline con FastAPI 0.162 conserva un fallo previo (31 pasan y falla
`test_main_montaje_grupos_abierto_y_protegido`, que inspecciona un atributo
interno del router). FastAPI 0.136.3 es compatible con el test existente; no se
cambiaron ni el pin de ejecución ni ese test.
