# Tasks

## 1. Contratos de Entrada y Salida (`Ejercicio 3, 4 y 5`)

- [x] 1.1 Crear `parcial/app/modules/usuarios/schemas.py` con `ConfigDict(extra="forbid")` en todos los DTOs de entrada (`RegistroIn`, `LoginIn`, `CambiarPasswordIn`, `UsuarioCreateIn`, `AsignarRolIn`), normalización de email, validación de contraseñas entre 1 y 72 bytes en UTF-8 (`422`), validación de `rol` (`ADMIN`, `VENDEDOR`, `CLIENTE`), validación de `vence_en` con zona horaria y fecha futura (`422`), y esquemas de salida sin `password_hash` (`UsuarioOut`, `LoginOut`, `YoOut`, `AsignacionRolOut`, `EventoSeguridadOut`).

## 2. Repositorios y Unit of Work del Módulo (`Ejercicio 6 y 7`)

- [x] 2.1 Crear `parcial/app/modules/usuarios/repository.py` con `UsuarioRepository`, `AsignacionRolRepository` (consulta de roles vigentes, asignaciones abiertas y conteo de administradores vigentes), `IntentoAccesoRepository` (conteo de fallos recientes tras el último éxito y función `registrar_intento_acceso_independiente` en sesión/transacción propia con el comentario obligatorio de 3 puntos del Ejercicio 7) y `EventoSeguridadRepository`.
- [x] 2.2 Crear `parcial/app/modules/usuarios/unit_of_work.py` con `UsuariosUnitOfWork(UnitOfWork)` componiendo `usuarios`, `asignaciones_rol`, `intentos_acceso`, `eventos_seguridad` y `clientes` (`BaseRepository[Cliente]`) sobre la misma `AsyncSession` de la petición, más su dependencia `get_usuarios_uow`.

## 3. Servicio de Autenticación, Autorización y Auditoría (`Ejercicio 4, 5, 6 y 7`)

- [x] 3.1 Implementar `parcial/app/modules/usuarios/service.py` con las operaciones de `/auth` (`registrar_cliente` creando `Usuario` + `AsignacionRol(CLIENTE)` + `Cliente` en un solo UoW tras hashear fuera del bloque; `iniciar_sesion` con límite de 5 intentos en 60s devolviendo `429` con `Retry-After` sin invocar `bcrypt`, verificación constante con `dummy_password_hash`, registro de intento en sesión propia y emisión de JWT; `obtener_perfil_yo`; y `cambiar_password` actualizando clave, limpiando `debe_cambiar_password` y anotando en `evento_seguridad` en el mismo UoW).
- [x] 3.2 Implementar en `parcial/app/modules/usuarios/service.py` las operaciones de `/usuarios` y `/eventos` (`crear_personal` con `debe_cambiar_password=True`, rol inicial y `evento_seguridad`; `listar_roles_usuario`; `asignar_rol` cerrando asignación vencida previa si existe o rechazando con `409` si está vigente + `evento_seguridad`; `revocar_rol` escribiendo `revocada_en = now()` y cumpliendo `RN-05` de autoprotección y último `ADMIN` vigente + `evento_seguridad`; y `listar_eventos` paginado con `Pagina[EventoSeguridadOut]`).

## 4. Routers, Grupos de Rutas en `main.py` y Verificación TDD (`Casos C-01 a C-09`)

- [x] 4.1 Crear `parcial/app/modules/usuarios/router.py` con `auth_router` (`/auth`), `usuarios_router` (`/usuarios` con `Depends(requiere_rol("ADMIN"))`) y `eventos_router` (`/eventos` con `Depends(requiere_rol("ADMIN"))`), y conectarlos en `parcial/main.py` (`auth_router` en `grupo_abierto`, `usuarios_router` y `eventos_router` en `grupo_protegido`).
- [x] 4.2 Verificar con tests automatizados todos los escenarios de `C-02` (contratos de 72 bytes y `vence_en`, auto-registro atómico y conflicto `409` con cliente previo, login con cookie `HttpOnly` sin token en body, tiempo constante con correo inexistente, bloqueo `429` con `Retry-After` al 6º intento y persistencia de `intento_acceso`, cambio obligatorio de contraseña `403` → `200`, revocación en vivo y autoprotección `RN-05`).
