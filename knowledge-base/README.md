# Librería (Parcial Programación III — Unidades 1 a 6) — Base de Conocimiento

Base de conocimiento canónica generada a partir del enunciado oficial del Parcial (*"Parcial: la librería con acceso, transacciones y despliegue en el VPS"*) y del código base del Trabajo Práctico (Capítulos 1 a 4).

## Índice de Archivos

| Archivo | Contenido |
|---|---|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito del parcial, objetivos por actor, alcance (`parcial/` y `despliegue/`) y exclusiones |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack tecnológico, arquitectura en 5 capas y tabla completa de endpoints abiertos y protegidos |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores, matriz RBAC (`ADMIN`, `VENDEDOR`, `CLIENTE`), distinción `401` vs `403` y rutas públicas |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | Diagrama ERD, especificación de las 13 tablas, índices únicos parciales, trigger append-only y seed data |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | Reglas de negocio oficiales `RN-01` a `RN-16` y sus garantes esperados |
| [06_funcionalidades.md](06_funcionalidades.md) | Historias de usuario (`US-001` a `US-009`) organizadas en 5 épicas alineadas con los pushes del grupo |
| [07_flujos_principales.md](07_flujos_principales.md) | Flujos extremo a extremo: Login con rate-limit, Auto-registro, Venta con UoW y Baja lógica de libros |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Patrones (`BaseRepository`, `SoftDeleteRepository`, `UnitOfWork`), estructura obligatoria y variables `.env` |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | Decisiones de diseño (`DD-01` a `DD-04`) y supuestos del seed y casos de prueba |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | Detalles de atención detectados entre el TP y el Parcial (`IN-01`, `IN-02`) y datos pendientes del VPS |

## Quick Start para Desarrolladores

1. **Entender el dominio y permisos** → [01_vision_y_objetivos.md](01_vision_y_objetivos.md), [03_actores_y_roles.md](03_actores_y_roles.md)
2. **Entender las tablas y el seed** → [04_modelo_de_datos.md](04_modelo_de_datos.md)
3. **Entender las invariantes (`RN-01` a `RN-16`)** → [05_reglas_de_negocio.md](05_reglas_de_negocio.md)
4. **Entender las capas (`Router → Service → UoW → Repository → Model`)** → [02_descripcion_general.md](02_descripcion_general.md), [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md)
5. **Implementar los módulos y flujos** → [06_funcionalidades.md](06_funcionalidades.md), [07_flujos_principales.md](07_flujos_principales.md)
6. **Revisar detalles del seed y VPS** → [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md), [10_preguntas_abiertas.md](10_preguntas_abiertas.md)

## Resumen Ejecutivo

El proyecto consta de dos entregables independientes: **`parcial/`**, que extiende la API asincrónica de la librería con autenticación `bcrypt` + JWT en cookie `HttpOnly`, autorización por roles vigentes en base de datos, arquitectura en capas con `Repository` y `UnitOfWork`, borrado lógico de libros y movimientos de stock de sólo agregado protegidos por trigger en PostgreSQL; y **`despliegue/`**, que empaqueta el TP de los capítulos 1 a 4 en una imagen Docker `python:3.12-alpine` sin privilegios y la pone en línea en el VPS de la cátedra.
