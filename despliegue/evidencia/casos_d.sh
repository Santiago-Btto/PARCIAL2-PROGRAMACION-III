#!/usr/bin/env bash
# Casos D-01 a D-08 del parcial: corre cada comando y guarda comando + salida en
# evidencia/D-0N_<caso>.txt. Se ejecuta desde despliegue/ con la imagen ya construida.
#
#   bash evidencia/casos_d.sh local                 # máquina del grupo: D-01, D-05, D-06, D-07
#   bash evidencia/casos_d.sh vps                   # en el VPS: D-01, D-02, D-04 a D-08
#   bash evidencia/casos_d.sh afuera <url-pública>  # desde OTRA máquina: D-03
#
# Variables (con su valor por defecto):
#   ENV_FILE=/opt/libreria/libreria.env  archivo de variables del servidor (no se muestra su contenido)
#   PUERTO=8000                          puerto publicado que asigna la cátedra
#   ADD_HOST=1                           1 agrega --add-host=host.docker.internal:host-gateway
#   NO_CACHE=1                           1 construye sin caché en D-02 ("servidor limpio")
set -u
cd "$(dirname "$0")/.."

MODO="${1:-}"
URL="${2:-}"
IMAGEN=libreria
NOMBRE=libreria
ENV_FILE="${ENV_FILE:-/opt/libreria/libreria.env}"
PUERTO="${PUERTO:-8000}"
EXTRA=()
[ "${ADD_HOST:-1}" = "1" ] && EXTRA+=(--add-host=host.docker.internal:host-gateway)
SALIDA=evidencia

# Guarda en el archivo del caso el comando (con $ adelante) y su salida.
correr() {
    local archivo="$1"; shift
    { echo "\$ $*"; "$@" 2>&1; echo "[código de salida: $?]"; echo; } | tee -a "$SALIDA/$archivo"
}

encabezado() {
    : > "$SALIDA/$1"
    { echo "# $2"; echo "# $(date '+%Y-%m-%d %H:%M:%S %Z') · $(hostname)"; echo; } >> "$SALIDA/$1"
}

docker_run() {
    docker run -d --name "$NOMBRE" -p "$PUERTO:8000" --restart unless-stopped \
        "${EXTRA[@]}" --env-file "$ENV_FILE" "$IMAGEN"
}

esperar_healthy() {
    for _ in $(seq 1 30); do
        estado=$(docker inspect -f '{{.State.Health.Status}}' "$NOMBRE" 2>/dev/null)
        [ "$estado" = "healthy" ] && break
        sleep 3
    done
    echo "estado de salud: ${estado:-desconocido}"
}

d01() {
    local f=D-01_imagenes.txt
    encabezado $f "D-01 · imagen base por debajo de 100 MB y el Dockerfile parte de ella"
    correr $f docker images python:3.12-alpine
    correr $f docker images "$IMAGEN"
    correr $f grep -n '^FROM' Dockerfile
}

d02() {
    local f=D-02_build_run_healthy.txt
    encabezado $f "D-02 · servidor limpio: build, run, docker ps healthy y migraciones en docker logs"
    local cache=(); [ "${NO_CACHE:-1}" = "1" ] && cache=(--no-cache)
    correr $f docker build "${cache[@]}" -t "$IMAGEN" .
    docker rm -f "$NOMBRE" > /dev/null 2>&1
    echo "\$ docker run -d --name $NOMBRE -p $PUERTO:8000 --restart unless-stopped ${EXTRA[*]} --env-file $ENV_FILE $IMAGEN" >> "$SALIDA/$f"
    docker_run >> "$SALIDA/$f" 2>&1
    esperar_healthy | tee -a "$SALIDA/$f"
    correr $f docker ps --filter "name=$NOMBRE"
    correr $f docker logs "$NOMBRE"
}

seed() {
    local f=D-02_build_run_healthy.txt
    correr $f docker exec "$NOMBRE" python -m scripts.seed
}

d03() {
    [ -n "$URL" ] || { echo "Falta la URL pública: bash evidencia/casos_d.sh afuera http://<ip>:<puerto>"; exit 1; }
    local f=D-03_desde_afuera.txt
    encabezado $f "D-03 · desde afuera del VPS en $URL"
    correr $f curl -sS -i "$URL/health/ready"
    correr $f curl -sS -i "$URL/libros/"
    correr $f curl -sS -i -X POST "$URL/ventas/" -H 'Content-Type: application/json' \
        -d '{"cliente_id": 2, "renglones": [{"libro_id": 1, "cantidad": 2}, {"libro_id": 4, "cantidad": 1}]}'
}

d04() {
    local f=D-04_reemplazo.txt
    encabezado $f "D-04 · docker rm -f y el mismo docker run: healthy, datos intactos, migraciones no se repiten"
    correr $f curl -sS "http://127.0.0.1:$PUERTO/ventas/"
    correr $f docker rm -f "$NOMBRE"
    echo "\$ docker run -d --name $NOMBRE -p $PUERTO:8000 --restart unless-stopped ${EXTRA[*]} --env-file $ENV_FILE $IMAGEN" >> "$SALIDA/$f"
    docker_run >> "$SALIDA/$f" 2>&1
    esperar_healthy | tee -a "$SALIDA/$f"
    correr $f docker ps --filter "name=$NOMBRE"
    correr $f docker logs "$NOMBRE"
    correr $f curl -sS "http://127.0.0.1:$PUERTO/ventas/"
}

d05() {
    local f=D-05_sin_database_url.txt
    encabezado $f "D-05 · sin DATABASE_URL el contenedor termina con error"
    correr $f docker run --rm --name libreria-sin-url "$IMAGEN"
}

d06() {
    local f=D-06_contenido_imagen.txt
    encabezado $f "D-06 · la imagen no tiene .env ni DATABASE_URL ni contraseñas"
    correr $f docker run --rm --entrypoint ls "$IMAGEN" -a /app
    correr $f docker run --rm --entrypoint env "$IMAGEN"
    correr $f docker history --no-trunc --format '{{.CreatedBy}}' "$IMAGEN"
}

d07() {
    local f=D-07_usuario.txt
    encabezado $f "D-07 · el proceso no corre como root"
    if docker ps --format '{{.Names}}' | grep -qx "$NOMBRE"; then
        correr $f docker exec "$NOMBRE" id
    else
        # En la máquina del grupo, sin base: mismo usuario que usaría el contenedor.
        correr $f docker run --rm --entrypoint id "$IMAGEN"
    fi
}

d08() {
    local f=D-08_aviso_en_logs.txt
    encabezado $f "D-08 · el aviso del comprobante de la venta de D-03 aparece después de la línea de la respuesta"
    echo '$ docker logs libreria 2>&1 | grep -E "POST /ventas/|Comprobante"' >> "$SALIDA/$f"
    docker logs "$NOMBRE" 2>&1 | grep -E "POST /ventas/|Comprobante" | tee -a "$SALIDA/$f"
}

case "$MODO" in
    local)  d01; d05; d06; d07 ;;
    vps)    d01; d02; seed; d05; d06; d07
            echo
            echo "Ahora, desde OTRA máquina: bash evidencia/casos_d.sh afuera http://<ip>:$PUERTO"
            echo "y después, otra vez en el VPS: bash evidencia/casos_d.sh vps-final" ;;
    afuera) d03 ;;
    vps-final) d08; d04 ;;
    *) sed -n '2,15p' "$0"; exit 1 ;;
esac
