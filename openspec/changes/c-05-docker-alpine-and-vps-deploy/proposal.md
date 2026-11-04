# Proposal

## Why

Los Ejercicios 9 y 10 piden que el TP de los capítulos 1 a 4, tal como se entregó, corra dentro de un contenedor y quede en línea en el VPS de la cátedra. `despliegue/` tiene hoy el código del TP pero ningún `Dockerfile`, ni `.dockerignore`, ni `DEPLOY.md`, ni evidencia de los casos D. Además, la entrada de C-05 en `CHANGES.md` describía los casos D con otra numeración que la consigna y aplicaba el límite de 100 MB a la imagen del proyecto en lugar de a la imagen base.

## What Changes

- Agregar `despliegue/Dockerfile` sobre `python:3.12-alpine`: dependencias antes que el código y con `--no-cache-dir`, usuario sin privilegios, sin secretos, `alembic upgrade head` al arrancar seguido de uvicorn en `0.0.0.0:8000`, y `HEALTHCHECK` contra `http://127.0.0.1:8000/health/ready`.
- Agregar `despliegue/.dockerignore` que deja afuera `.env`, `.venv`, `.git`, `__pycache__` y lo que no hace falta para correr.
- Reescribir `despliegue/env.example` como la plantilla del archivo de variables del contenedor (`DATABASE_URL` con `postgresql+asyncpg` apuntando a la base del servidor, `SQL_ECHO=false`).
- Agregar `despliegue/DEPLOY.md` con todo lo que pide el Ejercicio 10.
- Agregar `despliegue/evidencia/casos_d.sh` con los comandos de `D-01` a `D-08` y las salidas que se pueden obtener fuera del VPS.
- Corregir la entrada C-05 de `CHANGES.md` (numeración de los casos D según la consigna, límite de tamaño de la imagen base, `--add-host`, aviso en `docker logs`).

La lógica del TP no cambia: no hizo falta corregir ningún defecto para que arranque en el contenedor.

## Capabilities

### New Capabilities

- `despliegue-contenedor`: imagen Docker del TP de los capítulos 1 a 4, su ejecución con `docker run` contra la base del servidor y la documentación y evidencia del despliegue en el VPS.

### Modified Capabilities

Ninguna. `parcial/` no se toca.

## Impact

Archivos nuevos o modificados sólo en `despliegue/` (`Dockerfile`, `.dockerignore`, `env.example`, `DEPLOY.md`, `evidencia/`) y en `CHANGES.md`. Sin migraciones, sin dependencias nuevas, sin cambios de código Python.
