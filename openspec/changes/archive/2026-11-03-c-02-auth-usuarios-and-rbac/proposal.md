# Proposal

## Why

Con el esquema de base de datos, las migraciones y las primitivas transversales de `parcial/app/core/` ya construidas en `C-01`, la librería necesita incorporar en `parcial/` el módulo completo de acceso, usuarios, roles y auditoría de seguridad (`Ejercicios 4, 5, 6 y 7`, `RN-01` a `RN-08`, `RN-15`, `RN-16`). Sin este módulo no es posible autenticar clientes ni personal mediante cookies `HttpOnly`, proteger las rutas de escritura según roles vigentes en la base de datos ni auditar los intentos de acceso e historial de seguridad.

## What Changes

- **Contratos de entrada y salida de acceso y usuarios (`parcial/app/modules/usuarios/schemas.py`)**:
  - Esquemas de entrada con `ConfigDict(extra="forbid")`, normalización de email (`strip().lower()`), validación estricta de longitud de contraseña entre 1 y 72 bytes en UTF-8 (`422` si supera 72 bytes, evitando errores de `bcrypt`), validación de `rol` dentro de `ADMIN`, `VENDEDOR`, `CLIENTE`, y validación de `vence_en` con zona horaria obligatoria (`tzinfo` no nulo) y fecha futura (`422` si es naive o está en el pasado).
  - Esquemas de salida sin exponer `password_hash` (`UsuarioOut`, `LoginOut`, `YoOut` con `roles_vigentes` y `roles_token`, `AsignacionRolOut`, `EventoSeguridadOut`).
- **Repositorios y Unit of Work del módulo (`parcial/app/modules/usuarios/repository.py`, `unit_of_work.py`)**:
  - `UsuarioRepository(BaseRepository[Usuario])` con búsqueda por email.
  - `AsignacionRolRepository(BaseRepository[AsignacionRol])` con listado por usuario, consulta de nombres de roles vigentes (`revocada_en IS NULL AND (vence_en IS NULL OR vence_en > now())`), búsqueda de asignación abierta (`revocada_en IS NULL`) para `(usuario_id, rol)` y conteo de administradores vigentes activos.
  - `IntentoAccesoRepository(BaseRepository[IntentoAcceso])` con conteo de fallos recientes posteriores al último éxito para `(email, ip)` y función `registrar_intento_acceso_independiente` que abre su propia sesión y transacción desde `session_factory` y confirma siempre (`commit()`), con el comentario obligatorio de 3 puntos del Ejercicio 7.
  - `EventoSeguridadRepository(BaseRepository[EventoSeguridad])` para auditoría y listado paginado.
  - `UsuariosUnitOfWork(UnitOfWork)` que agrupa `usuarios`, `asignaciones_rol`, `intentos_acceso`, `eventos_seguridad` y `clientes` (`BaseRepository[Cliente]`) sobre la misma `AsyncSession` de la petición.
- **Lógica de negocio de autenticación, autorización y auditoría (`parcial/app/modules/usuarios/service.py`)**:
  - `POST /auth/registro`: calcula el hash `bcrypt` fuera del bucle de eventos **antes** de abrir el `UnitOfWork` y crea en una sola transacción `Usuario`, `AsignacionRol(rol="CLIENTE")` y `Cliente` (`RN-02`, Caso `C-02`).
  - `POST /auth/login`: verifica primero el límite de 5 intentos fallidos en 60 segundos (`429` con `Retry-After` sin ejecutar `bcrypt`, `RN-07`, Caso `C-05`), compara contra el hash real o el hash ficticio (`app.state.dummy_password_hash`) para mantener tiempo y mensaje constantes (`RN-08`, Caso `C-04`), registra el intento en sesión propia (`Ejercicio 7`) y emite el JWT en la cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`, `Secure` configurable) sin enviar el token en el cuerpo JSON (Caso `C-03`).
  - `POST /auth/logout`, `GET /auth/yo` y `POST /auth/cambiar-password` (verifica contraseña actual, actualiza `password_hash`, pasa `debe_cambiar_password = False` y registra `EventoSeguridad` en el mismo `UnitOfWork`, Caso `C-09`).
  - Gestión de personal y roles (`ADMIN`): `POST /usuarios` (alta con `debe_cambiar_password = True`, rol inicial y `EventoSeguridad`), `GET /usuarios/{id}/roles`, `POST /usuarios/{id}/roles` (cierra asignación vencida previa si existe o responde `409` si ya hay una vigente, `RN-03`, Caso `C-07`), `DELETE /usuarios/{id}/roles/{rol}` (escribe `revocada_en = now()`, impide auto-revocación de `ADMIN` y evita dejar al sistema sin administradores vigentes, `RN-05`, Casos `C-07` y `C-08`) y `GET /eventos` paginado con `Pagina[EventoSeguridadOut]`.
- **Rutas HTTP y montaje en los dos grupos (`parcial/app/modules/usuarios/router.py`, `parcial/main.py`)**:
  - `auth_router` (`/auth`) montado en `grupo_abierto`.
  - `usuarios_router` (`/usuarios`) y `eventos_router` (`/eventos`) montados en `grupo_protegido` (`Depends(verificar_cambio_password_resuelto)` + `Depends(requiere_rol("ADMIN"))`).

## Capabilities

### New Capabilities
- `auth-usuarios-and-rbac`: Auto-registro atómico de clientes, inicio/cierre de sesión con cookie `HttpOnly`, límite de intentos en sesión independiente, cambio obligatorio de contraseña, administración de personal y roles con vigencia y auditoría en `evento_seguridad`.

### Modified Capabilities
<!-- No existing specs modified -->

## Impact

- **Código afectado**: `parcial/app/modules/usuarios/schemas.py`, `parcial/app/modules/usuarios/repository.py`, `parcial/app/modules/usuarios/unit_of_work.py`, `parcial/app/modules/usuarios/service.py`, `parcial/app/modules/usuarios/router.py`, `parcial/main.py` y `CHANGES.md`.
