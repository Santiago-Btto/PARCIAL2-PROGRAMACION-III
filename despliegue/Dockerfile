# Imagen del TP de la librería (capítulos 1 a 4) · Ejercicio 9 del parcial.
#
# Construir:  docker build -t libreria .
# Correr:     docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped \
#               --env-file <archivo-de-variables> libreria
# Detalle en DEPLOY.md.

# Imagen base Alpine: 74,7 MB contra 180 MB de python:3.12-slim. Cada megabyte se
# descarga y se guarda en el VPS en cada despliegue, y cada paquete del sistema que
# no se usa es superficie de ataque. No hace falta compilador: todas las
# dependencias del TP (asyncpg, pydantic-core, uvloop...) tienen ruedas musllinux.
FROM python:3.12-alpine

# PYTHONUNBUFFERED: sin terminal, Python acumula la salida en un búfer y el aviso del
#   comprobante podría tardar en aparecer en `docker logs`.
# PYTHONDONTWRITEBYTECODE: el proceso no puede escribir en /app (es de root), así
#   que no tiene sentido que intente guardar __pycache__.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Las dependencias van antes que el código: mientras requirements.txt no cambie,
# esta capa sale de la caché y un cambio en el código no reinstala todo.
# --no-cache-dir: la caché de pip no queda guardada dentro de la imagen.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Usuario de sistema sin privilegios (sin contraseña ni carpeta personal). Si alguien
# vulnera la aplicación, no es dueño del contenedor.
RUN addgroup -S app && adduser -S -G app -H app

# El código queda de root: el proceso lo puede leer pero no modificar.
# .dockerignore deja afuera .env, .venv, .git, __pycache__, test/ y evidencia/:
# lo que se copia a una capa queda ahí aunque una capa posterior lo borre.
COPY . .

USER app

EXPOSE 8000

# Sana = la aplicación responde y llega a su base (/health/ready, no /health/live).
# 127.0.0.1 y no localhost: el wget de Alpine resuelve localhost a ::1 (IPv6) y
# uvicorn con --host 0.0.0.0 escucha sólo en IPv4, así que quedaría "unhealthy".
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8000/health/ready > /dev/null || exit 1

# Ninguna dirección de base ni contraseña acá: DATABASE_URL entra con --env-file.
# Primero las migraciones; si la base no responde (o falta DATABASE_URL) Alembic
# falla, el && corta y el contenedor termina con error en lugar de quedar
# atendiendo sin base. Alembic no repite migraciones ya aplicadas.
# exec: uvicorn reemplaza al shell y recibe la señal de `docker stop`, así el
# lifespan cierra el pool de conexiones. 0.0.0.0: con 127.0.0.1 sólo se lo
# alcanzaría desde adentro del contenedor y el puerto publicado no respondería.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
