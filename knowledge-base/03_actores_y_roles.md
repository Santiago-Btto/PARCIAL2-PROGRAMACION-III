# Actores y Roles

## Actores del sistema

| Actor | Rol en Base (`asignacion_rol`) | Descripción | Cómo interactúa |
|---|---|---|---|
| **Anónimo / Visitante** | Ninguno | Cualquier persona que navega la web sin sesión iniciada | Consulta catálogo vigente (`/libros`, `/editoriales`, `/generos`, `/autores/{id}/libros`) y puede registrarse (`/auth/registro`) o iniciar sesión (`/auth/login`) |
| **Usuario con cambio pendiente** | Cualquiera (`debe_cambiar_password=True`) | Personal recién dado de alta con contraseña provisoria | Sólo puede invocar rutas del grupo abierto (`/auth/yo`, `/auth/cambiar-password`, `/auth/logout` y catálogo público). Cualquier ruta protegida le responde `403` (RN-06) |
| **Cliente (`CLIENTE`)** | `CLIENTE` | Persona registrada por la web vinculada 1 a 1 con su ficha `cliente` | Consulta sus propias ventas en `/mis-ventas` y el detalle en `/ventas/{id}` (sólo si la venta le pertenece, RN-14) |
| **Vendedor (`VENDEDOR`)** | `VENDEDOR` | Personal de mostrador de la librería | Gestiona clientes (`/clientes`, `/clientes/{id}/perfil`), registra ventas (`POST /ventas`) y consulta cualquier venta (`/ventas`, `/ventas/{id}`, `/clientes/{id}/ventas`) |
| **Administrador (`ADMIN`)** | `ADMIN` | Responsable del catálogo, stock y seguridad | Posee todos los permisos de catálogo (alta, edición, baja lógica y reposición de libros), gestión de personal (`POST /usuarios`), asignación/revocación de roles y auditoría (`GET /eventos`), además de las operaciones de clientes y ventas |

## RBAC — Matriz de permisos

Los permisos se deciden **en cada petición consultando las filas vigentes de `asignacion_rol` en la base de datos** (`revocada_en IS NULL AND (vence_en IS NULL OR vence_en > now())`), nunca confiando en los roles informativos del token JWT (RN-04).

| Recurso / Operación | Anónimo | `CLIENTE` | `VENDEDOR` | `ADMIN` |
|---|---|---|---|---|
| Salud (`/health/live`, `/health/ready`) | ✅ | ✅ | ✅ | ✅ |
| Catálogo lectura (`GET /libros`, `/editoriales`, `/generos`, etc.) | ✅ | ✅ | ✅ | ✅ |
| Auth (`/auth/registro`, `/auth/login`, `/auth/logout`) | ✅ | ✅ | ✅ | ✅ |
| Sesión propia (`GET /auth/yo`, `POST /auth/cambiar-password`) | ❌ (`401`) | ✅ | ✅ | ✅ |
| Mis ventas (`GET /mis-ventas`) | ❌ (`401`) | ✅ (propias) | ✅ (propias si tiene ficha) | ✅ (propias si tiene ficha) |
| Detalle de venta (`GET /ventas/{id}`) | ❌ (`401`) | ✅ Sólo si es dueño (`403` si es ajena) | ✅ Todas | ✅ Todas |
| Clientes y Ventas (`POST/GET/PATCH /clientes`, `POST/GET /ventas`) | ❌ (`401`) | ❌ (`403`) | ✅ | ✅ |
| Catálogo escritura (`POST/PATCH` editoriales, géneros, autores, libros) | ❌ (`401`) | ❌ (`403`) | ❌ (`403`) | ✅ |
| Stock y baja de libros (`DELETE /libros/{id}`, `reponer`, `movimientos`) | ❌ (`401`) | ❌ (`403`) | ❌ (`403`) | ✅ |
| Usuarios, Roles y Eventos (`/usuarios`, `/usuarios/{id}/roles`, `/eventos`) | ❌ (`401`) | ❌ (`403`) | ❌ (`403`) | ✅ |

## Reglas especiales de Autorización
1. **Distinción estricta 401 vs 403:**
   - `401 Unauthorized`: No hay cookie `access_token`, se envió por cabecera `Authorization: Bearer` en vez de cookie, el JWT es inválido o expiró, el usuario no existe o tiene `activo = False`.
   - `403 Forbidden`: El usuario está autenticado, pero tiene `debe_cambiar_password = True` (en rutas protegidas), no posee el rol vigente requerido en `asignacion_rol`, o intenta ver una venta ajena sin ser personal.
2. **Detalle de venta sin `requiere_rol` en el router:**
   - `GET /ventas/{id}` sólo pide usuario autenticado (con cambio de clave resuelto). El servicio evalúa primero la relación del usuario con la venta (personal `ADMIN`/`VENDEDOR` o cliente dueño) antes de devolver `403` o `404`.
3. **Autoprotección de Administradores (RN-05):**
   - Un administrador no puede revocarse a sí mismo su propio rol `ADMIN` (`409`).
   - El sistema nunca puede quedar sin al menos un administrador vigente (`409`).

## Rutas públicas (sin sesión)
- `GET /health/live`
- `GET /health/ready`
- `POST /auth/registro`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /libros` y `GET /libros/{id}`
- `GET /editoriales` y `GET /editoriales/{id}/libros`
- `GET /generos` y `GET /generos/{id}/libros`
- `GET /autores/{id}/libros`
