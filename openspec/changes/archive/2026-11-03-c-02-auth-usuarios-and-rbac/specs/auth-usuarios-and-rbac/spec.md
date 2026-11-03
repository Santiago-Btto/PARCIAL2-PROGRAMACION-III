# auth-usuarios-and-rbac Specification

## Purpose

Proveer autenticación con `bcrypt` y JWT en cookie `HttpOnly`, auto-registro transaccional de clientes, control de intentos de acceso en sesión independiente, cambio obligatorio de contraseña, autorización por roles con vigencia en base de datos y auditoría transaccional en `evento_seguridad`.

## ADDED Requirements

### Requirement: Contratos de Entrada y Validación de Contraseñas y Vencimientos
Los contratos de entrada del módulo `usuarios` MUST rechazar campos no declarados (`extra="forbid"`), normalizar correos, validar contraseñas de hasta 72 bytes en UTF-8 (`422`) y exigir `vence_en` con zona horaria y en el futuro (`422`), sin exponer `password_hash` en las salidas.

#### Scenario: Contraseña mayor a 72 bytes en UTF-8 o vencimiento inválido
- **WHEN** un cliente envía una contraseña de más de 72 bytes en UTF-8 o un `vence_en` sin zona horaria o en el pasado
- **THEN** la aplicación responde `422 Unprocessable Entity` antes de ejecutar la lógica de negocio

### Requirement: Auto-registro Atómico de Clientes (`RN-02`)
`POST /auth/registro` MUST calcular el hash `bcrypt` antes de abrir la transacción y crear en un único `UnitOfWork` el `Usuario`, su `AsignacionRol(CLIENTE)` y su ficha `Cliente`, revirtiendo todo y respondiendo `409 Conflict` si el correo ya existe en `usuario` o `cliente`.

#### Scenario: Auto-registro exitoso y rechazo por correo duplicado en cliente
- **WHEN** una persona se registra en `POST /auth/registro` con un correo nuevo y luego intenta registrarse con un correo que ya pertenece a un `cliente` sin usuario
- **THEN** el primer pedido responde `201 Created` creando las tres filas y el segundo responde `409 Conflict` sin crear usuario ni asignación de rol

### Requirement: Login con Límite de Intentos, Tiempo Constante y Cookie HttpOnly (`RN-07`, `RN-08`, `Ejercicio 7`)
`POST /auth/login` MUST responder `429` con `Retry-After` sin ejecutar `bcrypt` tras 5 fallos en 60 segundos, verificar contra `dummy_password_hash` si el correo no existe, anotar cada intento en `intento_acceso` usando una sesión y transacción propias confirmadas, y emitir el JWT sólo en la cookie `HttpOnly` `access_token`.

#### Scenario: Bloqueo al sexto intento fallido y emisión de cookie en login válido
- **WHEN** se envían 5 intentos de login con clave errónea y un 6º intento dentro de los 60 segundos
- **THEN** los primeros 5 responden `401` dejando 5 filas en `intento_acceso` y el 6º responde `429` con `Retry-After` sin invocar `bcrypt`

### Requirement: Cambio Obligatorio de Contraseña y Grupos de Rutas (`RN-06`)
`parcial/main.py` MUST separar un grupo abierto y un grupo protegido con `Depends(verificar_cambio_password_resuelto)` que responde `403 Forbidden` cuando `debe_cambiar_password = True` hasta completar `POST /auth/cambiar-password`, conservando válida la cookie actual.

#### Scenario: Usuario con cambio pendiente desbloquea su sesión sin reloguear
- **WHEN** un usuario con `debe_cambiar_password = True` intenta acceder a una ruta protegida, luego cambia su clave en `POST /auth/cambiar-password` y reintenta con la misma cookie
- **THEN** el primer acceso responde `403`, el cambio de clave responde `200` registrando el evento de seguridad y el segundo acceso responde exitosamente

### Requirement: Administración de Personal, Vigencia de Roles, Autoprotección y Auditoría (`RN-03`, `RN-04`, `RN-05`, `RN-16`)
Las rutas `/usuarios` y `/eventos` MUST exigir rol `ADMIN` vigente en la base, cerrar asignaciones vencidas al reasignar (`409` si está vigente), revocar escribiendo `revocada_en = now()` impidiendo auto-revocación de `ADMIN` o dejar al sistema sin administradores vigentes (`409`), y registrar `evento_seguridad` en el mismo `UnitOfWork`.

#### Scenario: Revocación de rol con sesión abierta y autoprotección de ADMIN
- **WHEN** un administrador revoca el rol `VENDEDOR` de un usuario con sesión abierta o intenta revocar su propio rol `ADMIN`
- **THEN** el usuario revocado recibe `403` en su siguiente petición aunque su cookie no haya vencido, y el intento de auto-revocación de `ADMIN` responde `409 Conflict`
