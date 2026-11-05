# Design

## Context

Base: `36fc503` (C-01 a C-04 archivados). `despliegue/` es el TP de los capítulos 1 a 4 sin cambios: lee `DATABASE_URL` y `SQL_ECHO` del entorno (`app/core/config.py`, falla al arrancar si falta `DATABASE_URL`), aplica su esquema con dos migraciones de Alembic, expone `/health/live` y `/health/ready` (`SELECT 1`, 503 si la base no contesta) y carga los datos iniciales con `python -m scripts.seed`. El aviso del comprobante usa el logger `libreria.ventas` con `logging.basicConfig` en `app/main.py`, así que se ve en la salida estándar.

Antes de escribir el `Dockerfile` se comprobó, fuera de Docker y con Python 3.13 local, que el TP arranca contra un PostgreSQL 16 vacío (`alembic upgrade head`, seed, `/health/ready` 200, `GET /libros/` y `POST /ventas/` 201 con el aviso en el registro) y que sin `DATABASE_URL` termina con `RuntimeError`. No hubo que corregir nada del TP.

## Goals / Non-Goals

**Goals:** una imagen que cumpla cada punto del Ejercicio 9 con su razón escrita al lado; un `docker run` reproducible en el VPS; `DEPLOY.md` y evidencia para los casos `D-01` a `D-08`.

**Non-Goals:** Docker Compose, una base dentro del contenedor, proxy inverso o HTTPS, desplegar `parcial/`, CI, multi-stage (no hay nada que compilar, ver decisión 2).

## Decisions

### 1. Imagen base `python:3.12-alpine`

La consigna fija la base y el límite de 100 MB para la imagen base (74,7 MB). La imagen del proyecto, con las dependencias, es más grande y eso es esperado.

### 2. Sin compilador y sin multi-stage

Se verificó con `pip download --only-binary=:all: --platform musllinux_1_2_x86_64 --python-version 3.12 -r requirements.txt` (y lo mismo para `aarch64`) que todas las dependencias, incluidas `asyncpg`, `pydantic-core`, `uvloop`, `httptools`, `watchfiles`, `websockets`, `greenlet` y `rignore`, tienen ruedas `musllinux`. Con `pip install --no-cache-dir` no queda nada para descartar en una etapa de construcción, así que una sola etapa alcanza y es más fácil de leer.

### 3. Orden de capas

`COPY requirements.txt` → `pip install` → `COPY . .`. Un cambio de código sólo invalida la última capa.

### 4. Usuario sin privilegios y código de root

`adduser -S -G app -H app` y `USER app`. El código se copia sin `--chown`: queda de `root` y el proceso sólo lo puede leer, así que una vulneración tampoco puede reescribir la aplicación. `PYTHONDONTWRITEBYTECODE=1` evita que Python intente escribir `__pycache__` donde no puede.

### 5. Salida sin búfer

`PYTHONUNBUFFERED=1`: sin terminal, Python acumula la salida estándar en un búfer y el aviso del comprobante podría aparecer en `docker logs` mucho después (caso `D-08`).

### 6. Arranque

`CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]`. El `&&` hace que un fallo de Alembic (base caída, `DATABASE_URL` ausente) termine el contenedor con error en lugar de dejarlo atendiendo sin base; `--restart unless-stopped` lo vuelve a intentar. `exec` reemplaza al shell por uvicorn para que reciba la señal de `docker stop` y apague con el `lifespan` (cierra el pool). `0.0.0.0` porque `127.0.0.1` sólo es alcanzable desde adentro del contenedor. Alembic es idempotente: en el segundo arranque (`D-04`) no aplica nada.

### 7. Healthcheck

`HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD wget -qO- http://127.0.0.1:8000/health/ready > /dev/null || exit 1`. `127.0.0.1` y no `localhost` (el `wget` de BusyBox resuelve `localhost` a `::1` y uvicorn escucha sólo en IPv4). `/ready` y no `/live`: un contenedor sin base no está sano. `--start-period` cubre las migraciones y el arranque.

### 8. Configuración sólo por `--env-file`

Ni el `Dockerfile` ni la imagen tienen `ENV DATABASE_URL`; `.dockerignore` excluye `.env`. El archivo de variables vive en el servidor fuera del repositorio. Si la base corre en el propio VPS se usa `host.docker.internal` con `--add-host=host.docker.internal:host-gateway`; si la cátedra da otra dirección, esa.

### 9. Evidencia reproducible

`evidencia/casos_d.sh` tiene los comandos de cada caso y guarda la salida de cada uno en `evidencia/D-0N_*.txt`. Va en `evidencia/` y no en `scripts/` porque la consigna dice que al TP sólo se le agregan `Dockerfile` y `.dockerignore`.

## Risks / Trade-offs

- El entorno donde se escribió el change no puede descargar imágenes de Docker Hub, así que la construcción real, los casos D y el despliegue quedan para la máquina del grupo y el VPS (tareas abiertas en `tasks.md` y §Pendiente en `DEPLOY.md`). Lo que sí se verificó: el TP contra PostgreSQL 16, las ruedas musl y la sintaxis del `Dockerfile`.
- `pip` dentro de la imagen queda instalado (viene con la base); quitarlo ahorraría pocos MB a cambio de complicar las actualizaciones.
