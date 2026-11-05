# Despliegue del TP de la librería en el VPS

Ejercicios 9 y 10 del parcial. Lo que se despliega es el **TP de los capítulos 1 a 4 tal como se
entregó** (catálogo, clientes y ventas, sin usuarios ni roles), empaquetado en una imagen de Docker y
corrido con `docker run`. No se usa Docker Compose: la base es el PostgreSQL que ya tiene el servidor.

## Datos del despliegue

| Dato | Valor |
|---|---|
| URL pública | `http://<ip-o-dominio-del-vps>:<puerto>` · **completar al desplegar** |
| Documentación interactiva | `<url-pública>/docs` |
| Día y hora del despliegue | **completar al desplegar** (fecha, hora y zona horaria) |
| Puerto asignado por la cátedra | **completar** |
| Archivo de variables en el servidor | `/opt/libreria/libreria.env` (fuera del repositorio y de la imagen) |
| Imagen | `libreria`, construida **en el VPS** desde esta carpeta |

El despliegue tiene que seguir en línea hasta que se publiquen las notas.

## Cambios hechos al TP para que corra en el contenedor

**Ninguno en la lógica.** Antes de escribir el `Dockerfile` se corrió el TP contra un PostgreSQL 16
vacío: las dos migraciones, el seed, `/health/live` y `/health/ready` (200; 503 sin base), `GET /libros/`,
`POST /ventas/` (201) y el aviso del comprobante en el registro funcionan como pedía su consigna, y sin
`DATABASE_URL` la aplicación no arranca. Se agregaron sólo:

| Archivo | Para qué |
|---|---|
| `Dockerfile` | La imagen (cada punto lleva su razón en un comentario) |
| `.dockerignore` | Deja afuera `.env`, `.venv`, `.git`, `__pycache__`, `test/`, `evidencia/` y los `.md` |
| `env.example` | Ahora es la plantilla del archivo de variables del contenedor (sin valores reales) |
| `DEPLOY.md` | Este archivo |
| `evidencia/casos_d.sh` y `evidencia/D-0N_*.txt` | Los comandos y las salidas de los casos D |

## La imagen

- Base `python:3.12-alpine` (74,7 MB; el límite de 100 MB es de la imagen base, la del proyecto con sus
  dependencias es más grande). No se instala compilador: se verificó con
  `pip download --only-binary=:all: --platform musllinux_1_2_x86_64 --python-version 3.12 -r requirements.txt`
  (y lo mismo con `aarch64`) que todas las dependencias tienen ruedas para Alpine.
- `requirements.txt` se copia e instala con `--no-cache-dir` **antes** del código: un cambio de código
  no reinstala las dependencias.
- Corre con el usuario `app`, sin privilegios. El código es de `root` y el proceso sólo puede leerlo.
- Ningún secreto: ni la dirección de la base ni su contraseña están en el `Dockerfile`; entran con `--env-file`.
- Al arrancar: `alembic upgrade head` y, si funcionó, `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
  Si la base no responde, Alembic falla y el contenedor termina con error; `--restart unless-stopped`
  lo vuelve a intentar.
- `HEALTHCHECK` con `wget -qO- http://127.0.0.1:8000/health/ready` (con `localhost`, el `wget` de Alpine
  probaría `::1` y uvicorn escucha sólo en IPv4).

## Puesta en marcha en el VPS

Todo se corre en el VPS, en la carpeta `despliegue/` del repositorio (la imagen se construye en el
servidor, no se trae de otro lado).

### 1. Código

```bash
git clone https://github.com/Santiago-Btto/PARCIAL2-PROGRAMACION-III.git
cd PARCIAL2-PROGRAMACION-III/despliegue
```

### 2. Archivo de variables (una sola vez)

Se crea en el servidor, fuera del repositorio, a partir de `env.example`, con los datos de la base que
da la cátedra, y sólo lo puede leer el usuario que despliega:

```bash
sudo mkdir -p /opt/libreria
sudo cp env.example /opt/libreria/libreria.env
sudo nano /opt/libreria/libreria.env          # completar DATABASE_URL; SQL_ECHO=false
sudo chown "$USER" /opt/libreria/libreria.env && chmod 600 /opt/libreria/libreria.env
```

`DATABASE_URL` usa el driver `postgresql+asyncpg` y **nunca `localhost`**: dentro del contenedor,
`localhost` es el propio contenedor. Si PostgreSQL corre en el mismo VPS, el host es
`host.docker.internal` (habilitado con el `--add-host` del `docker run`); si la cátedra da otra
dirección, se usa esa. Ejemplo de la forma, sin valores reales:

```
DATABASE_URL=postgresql+asyncpg://<usuario>:<contraseña>@host.docker.internal:5432/<base>
SQL_ECHO=false
```

### 3. Construir la imagen

```bash
docker build -t libreria .
```

### 4. Correr el contenedor

```bash
docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  --env-file /opt/libreria/libreria.env libreria
```

- `-p <puerto>:8000` publica sólo la aplicación, en el puerto que asigna la cátedra.
- `--restart unless-stopped` la vuelve a levantar si termina (reinicio del servidor, base que todavía no respondía).
- `--add-host` sólo hace falta si la base está en el propio VPS (`host.docker.internal`).
- `--env-file` entrega la configuración sin que pase por la imagen ni por el repositorio.

Comprobar que quedó sana y que aplicó las migraciones:

```bash
docker ps --filter name=libreria          # STATUS: Up ... (healthy)
docker logs libreria                      # "Running upgrade ..." y luego "Uvicorn running on http://0.0.0.0:8000"
docker exec libreria wget -qO- http://127.0.0.1:8000/health/live
```

### 5. Datos iniciales

Con el contenedor arriba, se carga la base con el comando del README del TP, ejecutado adentro:

```bash
docker exec libreria python -m scripts.seed
```

Vacía las tablas y carga 3 editoriales, 3 géneros, 5 autores, 5 libros, 2 clientes y la venta 1.

### 6. Probar desde afuera

```bash
curl http://<ip-del-vps>:<puerto>/health/ready
curl http://<ip-del-vps>:<puerto>/libros/
curl -X POST http://<ip-del-vps>:<puerto>/ventas/ -H 'Content-Type: application/json' \
  -d '{"cliente_id": 2, "renglones": [{"libro_id": 1, "cantidad": 2}, {"libro_id": 4, "cantidad": 1}]}'
```

## Actualizar la aplicación

Se construye la imagen de nuevo, se elimina el contenedor y se lo vuelve a correr con el mismo comando:

```bash
cd PARCIAL2-PROGRAMACION-III && git pull && cd despliegue
docker build -t libreria .
docker rm -f libreria
docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  --env-file /opt/libreria/libreria.env libreria
```

Los datos no se pierden: viven en la base del servidor, no en el contenedor. Al arrancar, Alembic sólo
aplica las migraciones que falten (ninguna, si el esquema no cambió). No se vuelve a correr el seed: lo
vaciaría todo.

## Casos D y evidencia

`evidencia/casos_d.sh` tiene los comandos de cada caso y guarda comando y salida en
`evidencia/D-0N_<caso>.txt`. El orden importa: D-08 lee el registro del contenedor antes de que D-04 lo
reemplace.

| Paso | Dónde | Comando | Casos |
|---|---|---|---|
| 1 | Máquina del grupo, sin base | `docker build -t libreria . && bash evidencia/casos_d.sh local` | D-01, D-05, D-06, D-07 |
| 2 | VPS | `PUERTO=<puerto> bash evidencia/casos_d.sh vps` | D-01, D-02 (+ seed), D-05, D-06, D-07 |
| 3 | Otra máquina, fuera del VPS | `bash evidencia/casos_d.sh afuera http://<ip>:<puerto>` | D-03 |
| 4 | VPS | `PUERTO=<puerto> bash evidencia/casos_d.sh vps-final` | D-08, D-04 |

| Caso | Qué se espera |
|---|---|
| D-01 | `python:3.12-alpine` por debajo de 100 MB y `FROM python:3.12-alpine` en el `Dockerfile` |
| D-02 | Contenedor `healthy`; en `docker logs`, las dos migraciones aplicadas al arrancar |
| D-03 | `/health/ready` 200; `/libros/` 200 con los libros del seed; `POST /ventas/` 201 con los precios copiados y total 77000.00 |
| D-04 | Vuelve a `healthy`, `/ventas/` muestra las mismas ventas y Alembic no aplica ninguna migración |
| D-05 | Sin `DATABASE_URL`, `RuntimeError: Falta la variable DATABASE_URL` y código de salida distinto de 0 |
| D-06 | `ls -a /app` sin `.env`; `env` sin `DATABASE_URL` ni contraseñas |
| D-07 | `id` muestra `uid` del usuario `app`, no 0 |
| D-08 | La línea `Comprobante de la venta 2 enviado a tomas@example.com` después de `"POST /ventas/ HTTP/1.1" 201` |

## Pendiente en el VPS

El change se preparó en un entorno que no puede descargar imágenes de Docker Hub, así que la imagen no se
construyó ahí y **todavía no hay salidas `D-0N_*.txt`**. Falta, en este orden:

- [ ] Paso 1 de la tabla de casos en la máquina del grupo.
- [ ] Puesta en marcha en el VPS (secciones 1 a 5) y completar URL, puerto, día y hora arriba.
- [ ] Pasos 2 a 4 de la tabla de casos.
- [ ] Commitear `evidencia/D-0N_*.txt` (revisar antes que ninguna salida muestre la contraseña de la base).
