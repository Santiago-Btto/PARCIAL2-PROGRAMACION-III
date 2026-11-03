# Tasks

Aplicar sólo después de revisión del alcance ALTO. No hay implementación realizada por el hecho de que OpenSpec reconozca los artifacts.

**Ciclo obligatorio por tarea de código:** ejecutar baseline relevante antes de editar archivos existentes; si falla, detener e informar el fallo previo sin corregirlo silenciosamente. Escribir test de comportamiento que falle (RED), ejecutar y registrar; implementar el mínimo (GREEN), triangular al menos dos casos distintos y todos los escenarios aplicables, y refactorizar manteniendo verde. Registrar archivo, capa, comandos y resultados en la tabla TDD del reporte. No usar aserciones triviales ni mocks como prueba de garantías PostgreSQL.

## 1. Prerrequisitos y base reutilizable

- [ ] 1.1 Obtener revisión de la propuesta y resolver las skills de dominio faltantes exigidas por AGENTS; verificar autorización y fuentes cargadas antes de tocar producción.
- [ ] 1.2 Preparar entorno aislado del repo compatible con `parcial/requirements.txt` y runner de tests, sin modificar instalaciones globales; ejecutar y registrar baseline completo. Reproducir el fallo previo de `test_main_montaje_grupos_abierto_y_protegido` del entorno prestado (31 pass/1 fail); si persiste, detener apply e informar sin arreglar C-02 dentro de C-03.
- [ ] 1.3 Verificar PostgreSQL 16 aislado con datos sintéticos y las cuatro migraciones Alembic, sin `metadata.create_all`; registrar versión, destino de prueba y `alembic current` antes de pruebas reales. No usar bases de usuarios ni ejecutar seed legado para acreditar inventario.
- [ ] 1.4 Reproducir con sesión real la forma de resultados de `BaseRepository` y `SoftDeleteRepository` (`get_by_id`, `get_all`, count e histórico). Si se confirma el defecto `select/exec`, reportarlo y revisar el ajuste mínimo antes de corregir; verificar RED/GREEN de modelos frente a Rows y regresión C-02 sin modificar sus repositorios.

## 2. Editoriales, géneros y autores

- [ ] 2.1 Refactorizar editoriales a repositorio y UoW compartido; contratos estrictos y PATCH parcial; verificar alta, edición, campos omitidos/nulos, conflicto único y rollback sin commit en repositorio mediante tests y casos nuevos con TDD.
- [ ] 2.2 Refactorizar géneros con las rutas actuales (sin inventar PATCH) a repositorio/UoW y entrada estricta; verificar alta válida, campos extra y conflicto de nombre con TDD.
- [ ] 2.3 Refactorizar autores a repositorio/UoW, conservando datos y validaciones actuales; verificar alta, PATCH parcial, nulos y campos extra con TDD.
- [ ] 2.4 Aplicar `Pagina` a las colecciones de estas entidades y sus libros relacionados, reutilizando paginación y filtros del repositorio de libros; verificar segunda página, vacío, fuera de rango, padre inexistente y exclusión de bajas de items/total. Conservar rol/orden en libros por autor; documentar ejemplos ejecutables de estos contratos en un archivo de pruebas HTTP propio de C-03.

## 3. Libros y lectura pública

- [ ] 3.1 Crear `LibroRepository`, `MovimientoStockRepository` y `LibrosUnitOfWork` sobre las bases; trasladar consultas y precarga usando `Libro.autorias`; verificar sesión compartida, flush sin commit, detalle con una y varias autorías y relaciones sin carga implícita con TDD y consultas reales.
- [ ] 3.2 Paginar libros con filtros ligados por título y género; conservar el escape literal de `%`, `_` y barra inversa; verificar combinación de filtros, total correcto, títulos con texto SQL, tamaños/páginas inválidas y catálogo vacío con TDD.
- [ ] 3.3 Ajustar DTOs de libros y autorías: `stock_inicial` en alta, rechazo de stock en PATCH, `extra="forbid"` y `exclude_unset`; verificar stock negativo, DTO anidado con extras, duplicación de autorías, precio/ISBN inválidos, PATCH compatible de campos actuales y null explícito sólo en género con TDD.

## 4. Stock inicial y contrato compartido

- [ ] 4.1 Implementar el contrato `cambiar_stock` dentro del UoW del llamador y bloqueo simple de fila con estado actualizado; verificar variaciones positivas/negativas, actor/venta, falta de stock, cantidad cero y rollback si falla el movimiento con TDD. Rechazar resultado mayor al máximo INTEGER mediante conflicto sin escrituras; entrada fuera de límites devuelve `422`.
- [ ] 4.2 Refactorizar alta libro/autorías para iniciar en cero y usar el punto único sólo con stock inicial positivo; verificar alta con cero sin movimiento, alta positiva con un movimiento `Stock inicial`, igualdad stock/suma y rollback completo ante referencia inválida o error al confirmar con TDD y PostgreSQL.
- [ ] 4.3 Implementar reposición con cantidad positiva, motivo no vacío/espacios y máximo 200, actor de sesión y sin venta; verificar respuesta actualizada, `404` inexistente, `409` baja y validaciones `422` con TDD. Registrar ejemplo HTTP reproducible junto a sus pruebas.
- [ ] 4.4 Verificar con dos sesiones de PostgreSQL que dos reposiciones sobre un mismo libro no pierden stock ni movimientos y comparten política de bloqueo con baja; usar una prueba acotada, sin introducir infraestructura de concurrencia adicional. Registrar la limitación de escritor legado de ventas en el handoff C-04.

## 5. Baja lógica, ISBN e historial

- [ ] 5.1 Implementar DELETE lógico bajo UoW y bloqueo; verificar `204` sin cuerpo, fecha con zona horaria, conservación física de relaciones, `404` de baja repetida y ocultamiento público/relacionado con TDD.
- [ ] 5.2 Actualizar la traducción de `uq_libro_isbn_vigente` y restricciones aplicables sin SELECT previo de unicidad; verificar en PostgreSQL nuevo libro con ISBN liberado (`201`) y duplicación vigente (`409`) sin detalles internos ni restos parciales con TDD.
- [ ] 5.3 Incorporar DTO e historial paginado de movimientos incluyendo libros dados de baja; verificar campos de salida, orden, vacío, páginas inválidas, inexistente y separación de historiales tras reutilizar ISBN con TDD. Documentar ejemplos de DELETE e historial junto a sus pruebas.

## 6. Montaje de catálogo e integración

- [ ] 6.1 Separar routers públicos/protegidos de los cuatro módulos y montar sólo el catálogo en los grupos existentes de `main.py`, reutilizando `requiere_rol("ADMIN")`; verificar lecturas sin cookie, escrituras ADMIN, `401`, roles insuficientes y cambio obligatorio `403` mediante tests HTTP de comportamiento con TDD, preservando `/auth` y sin editar usuarios/clientes/ventas.
- [ ] 6.2 Ejecutar regresión completa y pruebas PostgreSQL de catálogo, integridad, rollback, queries acotadas y locking; reportar resultados reales separados de mocks, sin acreditar trigger/índices si no fueron ejecutados. Revisar diff para excluir auth, ventas, seed, despliegue, secretos y cambios de migración no autorizados.
- [ ] 6.3 Entregar handoff C-04 con firma del helper, repositorios requeridos, campos HTTP nuevos, orden de bloqueos y escrituras legadas pendientes; verificar ejemplos contra los tests y señalar que RN-11/RN-13 globales no están cerradas hasta migrar ventas/seed. Registrar tabla de evidencia TDD por tarea y commit local únicamente cuando las validaciones aplicables pasen.

## Workflow follow-up

- Presentar primero esta propuesta y esperar el pedido de apply conforme la skill `openspec-propose`.
- No marcar C-03 completado en CHANGES ni archivar durante planificación; al finalizar implementación, solicitar el cierre sólo si corresponde al pedido del usuario.
- No hacer push ni publicar sin autorización explícita. La entrega completa de evidencias C-01 a C-16 y documentación general pertenece a C-04.
