# Tasks

## 1. Clientes

- [ ] 1.1 `ClienteRepository` (detalle con perfil, ficha por usuario, página) y `PerfilClienteRepository`.
- [ ] 1.2 `ClientesUnitOfWork` con clientes, perfiles y ventas; `UsuariosUnitOfWork` reutiliza `ClienteRepository`.
- [ ] 1.3 Service con UoW: alta, detalle, PATCH parcial (`exclude_unset`), perfil (409 si repite, 404 si el cliente no existe) y ventas del cliente paginadas.
- [ ] 1.4 Contratos de entrada con `extra="forbid"`; `ClienteRead` con `usuario_id` y perfil como objeto.
- [ ] 1.5 Router protegido para `VENDEDOR` y `ADMIN`, con `Pagina[T]`.

## 2. Ventas

- [ ] 2.1 `VentaRepository`: detalle en dos consultas sin filtrar libros dados de baja y página con cliente, con los mismos filtros en total e items.
- [ ] 2.2 `VentasUnitOfWork` con ventas, clientes, libros y movimientos sobre una sesión.
- [ ] 2.3 `POST /ventas`: cliente, libros bloqueados en orden y validados antes de escribir (409), precio copiado, total del servidor y descuento por `cambiar_stock` con movimiento por renglón (RN-09, RN-10, RN-11).
- [ ] 2.4 Aviso con `BackgroundTasks` agendado sólo tras la confirmación, en logger visible con uvicorn.
- [ ] 2.5 `GET /ventas` paginado para el personal, `GET /mis-ventas` para cualquier autenticado y `GET /ventas/{id}` con control personal/dueño (403) sin `requiere_rol` (RN-14).
- [ ] 2.6 Montaje de clientes, ventas y `/mis-ventas` en el grupo protegido de `main.py`.
- [ ] 2.7 Pruebas unitarias del service con dobles del UoW: venta válida, cuatro rechazos sin escrituras, personal, dueño, ajena (403), inexistente (404) y lo propio.

## 3. Datos iniciales, documentación y casos

- [ ] 3.1 `seed.py` con los datos de la consigna: usuarios y roles, catálogo con seis autores, libros en el orden del ejemplo, tres clientes, venta 1 y evento `SISTEMA`; stock por `cambiar_stock` y venta por el service.
- [ ] 3.2 `README.md` del parcial: integrantes, puesta en marcha desde cero, seed, casos, evidencias, decisiones y endpoints.
- [ ] 3.3 Casos `.http` C-01 a C-16 en cuatro archivos, con la respuesta esperada en un comentario y varias sesiones por archivo.
- [ ] 3.4 `scripts/evidencia_c15.py` (reemplaza la evidencia C-07 del TP) e instrucción de la captura C-14 con `test/solo_agregado.sql`.

## 4. Verificación

- [ ] 4.1 Ninguna escritura de `Libro.stock` fuera de `cambiar_stock` (búsqueda en `app/` y `seed.py`).
- [ ] 4.2 Compilación de todos los módulos tocados.
- [ ] 4.3 Ejecutar en la máquina del grupo: `alembic upgrade head`, `python seed.py`, `pytest test -q`, los cuatro `.http` en orden y las evidencias C-14 y C-15.
