# Design: C-02 Auth, Usuarios, and RBAC

## Context

El Push 2 (`C-02: auth-usuarios-and-rbac`) implementa los capítulos 5 y parte del 6 del parcial en `parcial/app/modules/usuarios/` y `parcial/main.py` (Ejercicios 4, 5, 6 y 7). Las primitivas base (`security.py`, `dependencies.py`, `BaseRepository`, `UnitOfWork`, `Pagina` y los modelos `Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad`, `Cliente`) ya fueron creadas en `C-01`.

## Goals / Non-Goals

**Goals:**
- Implementar la arquitectura en capas `Router → Service → UsuariosUnitOfWork → Repository → Model` para todo el módulo `usuarios`.
- Garantizar que todo cálculo `bcrypt` ocurra fuera del bucle de eventos (`asyncio.to_thread` + `asyncio.Semaphore`) y **antes** de abrir el `UnitOfWork` para no retener conexiones del pool durante ~300 ms.
- Garantizar la atomicidad de las operaciones multi-tabla:
  - Auto-registro (`POST /auth/registro`): `Usuario` + `AsignacionRol(CLIENTE)` + `Cliente` en un solo `UnitOfWork` (`RN-02`).
  - Alta de personal (`POST /usuarios`), asignación (`POST /usuarios/{id}/roles`), revocación (`DELETE /usuarios/{id}/roles/{rol}`) y cambio de contraseña (`POST /auth/cambiar-password`): cambio principal + fila en `EventoSeguridad` en un solo `UnitOfWork` (`RN-16`).
- Registrar cada intento de login en `intento_acceso` desde una **sesión y transacción propias** que confirman siempre (`Ejercicio 7`, `RN-07`).
- Separar en `parcial/main.py` el `grupo_abierto` (`/health`, `/auth`, lecturas públicas) del `grupo_protegido` (`Depends(verificar_cambio_password_resuelto)`).

**Non-Goals:**
- Refactorizar los módulos de catálogo (`editoriales`, `generos`, `autores`, `libros`) o de `clientes` y `ventas` (corresponden a `C-03` y `C-04`).

## Decisions

1. **Sesión independiente exclusiva para `IntentoAcceso` (`Ejercicio 7`)**:
   - *Decisión*: En `parcial/app/modules/usuarios/repository.py`, proveer la función `registrar_intento_acceso_independiente(session_factory, email, ip, exito)` que abre `async with session_factory() as sesion_propia:`, inserta `IntentoAcceso` y ejecuta `await sesion_propia.commit()`, acompañada del comentario obligatorio de 3 puntos (qué hace distinto, por qué no puede compartir la transacción de la petición y cuál es su costo).
   - *Racional*: Si el intento fallido compartiera la sesión/transacción de la petición, al devolver `401` o revertirse la transacción se perdería el registro del fallo y nunca se alcanzaría el límite de 5 intentos en 60 segundos (`RN-07`).

2. **Reasignación de rol vencido vs. rol abierto vigente (`Ejercicio 5`, `RN-03`)**:
   - *Decisión*: El índice único parcial `uq_asignacion_rol_usuario_rol_abierta` filtra `WHERE revocada_en IS NULL`. Cuando un administrador envía `POST /usuarios/{id}/roles` para un rol que tiene una fila con `revocada_en IS NULL`:
     - Si la fila está vigente (`vence_en IS NULL` o `vence_en > ahora`), se rechaza con `409 Conflicto` (o se deja que el índice único parcial / comprobación lo rechace con `409`).
     - Si la fila ya venció (`vence_en is not None and vence_en <= ahora`), el servicio primero cierra esa fila anterior asignando `revocada_en = ahora` (`flush()`) y a continuación inserta la nueva `AsignacionRol` junto con el `EventoSeguridad` dentro del mismo `UsuariosUnitOfWork`.
   - *Racional*: Cumple literalmente la consigna del Ejercicio 5 (pág. 11): *"reasignar un rol vencido cierra la fila anterior y abre una nueva"*, respetando el índice único parcial en PostgreSQL.

3. **Conteo de intentos fallidos tras el último éxito (`RN-07`)**:
   - *Decisión*: Para `(email, ip)` en la ventana `[ahora - 60s, ahora]`, buscar primero `MAX(cuando)` donde `exito = True` y `cuando >= ventana_inicio`. El conteo de fallos cuenta las filas con `exito = False` y `cuando >= ventana_inicio` (y `cuando > ultimo_exito` si hubo un login exitoso dentro de los últimos 60 segundos).
   - *Racional*: Cumple `RN-07` (*"Un login correcto reinicia la cuenta: los fallos anteriores siguen en la tabla, pero dejan de contar"*) sin modificar ni borrar filas históricas.

## UI Mockups

Decision: no (no UI)
