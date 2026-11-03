# Flujos Principales

## Flujo 1: Inicio de Sesión (`POST /auth/login`)
**Disparador**: El usuario envía `{ "email": "...", "password": "..." }` a `POST /auth/login`.
**Actor**: Cualquier usuario (registrado o no).

**Pasos**:
1. **Validación de contrato (`Router` / `Schema`):** Pydantic valida formato de email, `extra="forbid"` y que `password.encode("utf-8")` tenga entre 1 y 72 bytes (`422` si supera 72 bytes).
2. **Control de límite de intentos (RN-07):** El servicio consulta en `intento_acceso` los intentos para `(email, ip)` en los últimos 60 segundos posteriores al último intento con `exito = True`.
   - Si hay **5 o más intentos fallidos**, responde inmediatamente `429 Too Many Requests` con cabecera `Retry-After` **sin ejecutar `bcrypt`**.
3. **Búsqueda de usuario y verificación en tiempo constante (RN-08):**
   - Se busca el usuario por `email` (en minúsculas).
   - Si existe, se toma `usuario.password_hash`; si no existe, se toma `request.app.state.dummy_password_hash`.
   - Se ejecuta `verificar_password(password, hash_objetivo)` fuera del event loop (`asyncio.to_thread`) y bajo el `asyncio.Semaphore`.
4. **Registro del intento en sesión independiente (Ejercicio 7):**
   - Se abre una **sesión y transacción propias** desde `session_factory` y se inserta la fila en `intento_acceso(email, ip, exito=...)` haciendo `commit()` inmediato, para que el intento sobreviva aunque la petición falle con `401`.
5. **Resultado:**
   - Si las credenciales son inválidas o `usuario.activo == False`, se lanza `NoAutenticado` (`401`) con el mismo mensaje `"Credenciales inválidas."`.
   - Si son válidas, se consultan los roles vigentes del usuario en `asignacion_rol`, se firma el JWT (`sub`, `exp`, `roles`) y se lo escribe en la cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`), devolviendo `{ "mensaje": "Sesión iniciada", "debe_cambiar_password": ..., "expira_en_segundos": ... }`.

---

## Flujo 2: Auto-registro de Cliente (`POST /auth/registro`)
**Disparador**: Un visitante envía `{ "nombre": "...", "email": "...", "password": "..." }` a `POST /auth/registro`.
**Actor**: Visitante público.

**Pasos**:
1. **Validación y Hash previo (Ejercicio 4):** Se valida el contrato (contraseña <= 72 bytes) y se calcula `password_hash = await hashear_password(...)` **antes** de abrir la transacción para no retener la conexión del pool durante los ~300 ms de `bcrypt`.
2. **Transacción única (`async with uow:`, RN-02):**
   - `uow.usuarios.add(Usuario(email=..., nombre=..., password_hash=..., activo=True, debe_cambiar_password=False))` (`flush()` obtiene `usuario.id`).
   - `uow.asignaciones_rol.add(AsignacionRol(usuario_id=usuario.id, rol="CLIENTE"))`.
   - `uow.clientes.add(Cliente(nombre=..., email=..., usuario_id=usuario.id))`.
3. **Confirmación o Rollback:**
   - Si el correo ya existía en `usuario` (`uq_usuario_email`) o en `cliente` (`uq_cliente_email`), PostgreSQL lanza `IntegrityError`, el `UnitOfWork` hace `rollback()` de las tres tablas y el servicio lo traduce a `409 Conflicto` sin dejar filas huérfanas ni apropiarse de una ficha previa.
   - Si todo es válido, el `UnitOfWork` hace `commit()` al salir del bloque y devuelve `201 Created`.

---

## Flujo 3: Registro de una Venta (`POST /ventas`)
**Disparador**: Un vendedor o administrador envía `cliente_id` y la lista de `renglones` (`[{ "libro_id": 1, "cantidad": 2 }, ...]`) a `POST /ventas`.
**Actor**: `VENDEDOR` o `ADMIN` (con cambio de contraseña resuelto).

**Pasos**:
1. **Autorización previa:** Las dependencias verifican cookie/JWT (`401`), `debe_cambiar_password == False` (`403`) y rol vigente en `asignacion_rol` (`403`), compartiendo la misma `AsyncSession` que recibirá el `VentasUnitOfWork`.
2. **Transacción única (`async with uow:`, RN-09, RN-10, RN-11):**
   - Se verifica que el `cliente` exista (`409` si no existe, Caso `C-12`).
   - Se obtienen los libros vigentes (`borrado_en IS NULL`) solicitados en los renglones. Si alguno no existe o está dado de baja, se lanza `Conflicto` (`409`, Caso `C-12`).
   - Si algún libro tiene `libro.stock < renglon.cantidad`, se lanza `Conflicto` (`409`, Caso `C-11`) y el `UnitOfWork` revierte toda la operación.
   - Se calcula el `total` sumando `libro.precio * cantidad` de cada renglón y se crea la `Venta` con sus `RenglonVenta` (copiando `precio_unitario = libro.precio`).
   - Por cada renglón, se invoca el **punto único de modificación de stock** (`cambiar_stock`), que descuenta `libro.stock -= cantidad` y registra un `MovimientoStock(libro_id=..., venta_id=venta.id, usuario_id=usuario_actual.id, cantidad=-cantidad, motivo=f"Venta #{venta.id}")`.
3. **Confirmación y Precarga:** Al salir del `async with uow:`, se confirma la transacción (`commit()`). Luego se lee la venta completa con precarga (`joinedload(Venta.cliente)` y `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)`).
4. **Aviso en segundo plano (Ejercicio 8):** Se agenda en `BackgroundTasks` la corrutina `enviar_aviso_venta(venta.id, cliente.email, venta.total)` que ejecuta `await asyncio.sleep(0.5)` y registra el comprobante en el logger después de enviar la respuesta `201`.

---

## Flujo 4: Baja Lógica de un Libro y Reutilización de ISBN (RN-01, RN-13)
**Disparador**: El administrador ejecuta `DELETE /libros/{id}` y posteriormente crea un nuevo libro con el mismo `isbn`.
**Actor**: `ADMIN`.

**Pasos**:
1. `DELETE /libros/{id}` abre el `UnitOfWork`, busca el libro vigente con `SoftDeleteRepository.get_by_id(id)` (`404` si no existe o ya estaba dado de baja) y ejecuta `soft_delete(libro)`, escribiendo `borrado_en = now()`. Responde `204 No Content`.
2. El libro deja de aparecer en `GET /libros` y responde `404` en `GET /libros/{id}`. Si se intenta vender o reponer, responde `409`.
3. Al consultar una venta histórica (`GET /ventas/{id}`) que incluía ese libro, la precarga de `RenglonVenta.libro` no filtra `borrado_en`, por lo que la venta vieja sigue mostrando el título y datos del libro.
4. Al ejecutar `POST /libros` con el mismo `isbn`, el índice único parcial `uq_libro_isbn_vigente` (`WHERE borrado_en IS NULL`) permite la inserción (`201 Created`), pero rechaza con `409` si se intenta dar de alta un segundo ejemplar vigente con ese mismo `isbn` (Caso `C-13`).
