# Tasks

## 1. Comprobaciones previas

- [x] 1.1 Correr el TP fuera de Docker contra un PostgreSQL 16 vacío: `alembic upgrade head`, `python -m scripts.seed`, `/health/live`, `/health/ready`, `GET /libros/`, `POST /ventas/` y el aviso del comprobante en el registro.
- [x] 1.2 Comprobar que sin `DATABASE_URL` el TP no arranca (`RuntimeError`).
- [x] 1.3 Comprobar que todas las dependencias tienen ruedas `musllinux` para Python 3.12 (x86_64 y aarch64): no hace falta compilador.

## 2. Imagen

- [x] 2.1 `despliegue/Dockerfile` desde `python:3.12-alpine`, con el comentario de la razón de cada punto.
- [x] 2.2 Dependencias antes del código, con `--no-cache-dir`.
- [x] 2.3 Usuario sin privilegios con `USER`; código de `root`, sólo lectura para el proceso.
- [x] 2.4 Arranque `alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- [x] 2.5 `HEALTHCHECK` con `wget` contra `http://127.0.0.1:8000/health/ready`.
- [x] 2.6 `despliegue/.dockerignore` (`.env`, `.venv`, `venv`, `.git`, `__pycache__`, `*.pyc`, `test/`, `evidencia/`, `*.md`, `Dockerfile`).
- [x] 2.7 `despliegue/env.example` con la forma de `DATABASE_URL` para el contenedor y `SQL_ECHO=false`, sin valores reales.

## 3. Documentación y evidencia

- [x] 3.1 `despliegue/DEPLOY.md`: URL, fecha y hora, `docker build`, `docker run`, carga del seed, cambios al TP, actualización y pendientes.
- [x] 3.2 `despliegue/evidencia/casos_d.sh` con los comandos de `D-01` a `D-08` y salida por caso en `evidencia/`.
- [x] 3.3 Corregir la entrada C-05 de `CHANGES.md`.

## 4. En la máquina del grupo y en el VPS

- [ ] 4.1 `docker build -t libreria .` en `despliegue/` y `bash evidencia/casos_d.sh local` (D-01, D-05, D-06 y D-07 sin VPS).
- [ ] 4.2 En el VPS: crear el archivo de variables, `docker build`, `docker run`, `docker exec libreria python -m scripts.seed`.
- [ ] 4.3 En el VPS: `bash evidencia/casos_d.sh vps <url-pública>` (D-01 a D-08) y completar URL, fecha y hora en `DEPLOY.md`.
- [ ] 4.4 Desde otra máquina: el bloque D-03 de `casos_d.sh` contra la URL pública.
