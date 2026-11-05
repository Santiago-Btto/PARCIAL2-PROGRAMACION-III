# despliegue-contenedor Specification

## Purpose
Define cómo se empaqueta el TP de los capítulos 1 a 4 en una imagen de Docker, cómo se corre contra la base del servidor y qué documentación y evidencia deja su despliegue en el VPS.

## Requirements

### Requirement: Imagen basada en Alpine y sin secretos
La imagen del TP SHALL construirse desde `python:3.12-alpine` con un `Dockerfile` en `despliegue/` que instala `requirements.txt` con `--no-cache-dir` antes de copiar el código. La imagen SHALL NOT contener `.env`, `.venv`, `.git`, `__pycache__`, la dirección de la base ni ninguna contraseña.

#### Scenario: Imagen base por debajo del límite
- **WHEN** se lista `docker images`
- **THEN** `python:3.12-alpine` ocupa menos de 100 MB y el `Dockerfile` del TP parte de ella

#### Scenario: Ningún secreto horneado
- **WHEN** se corre `docker run --rm --entrypoint ls libreria -a /app` y `docker run --rm --entrypoint env libreria`
- **THEN** no aparece `.env` en `/app` y el entorno no muestra `DATABASE_URL` ni contraseñas

### Requirement: Proceso sin privilegios
El contenedor SHALL ejecutar la aplicación con un usuario de sistema sin privilegios activado con `USER`.

#### Scenario: Usuario del proceso
- **WHEN** se corre `docker exec libreria id`
- **THEN** el usuario no es `root` (uid distinto de 0)

### Requirement: Migraciones al arrancar y salud declarada
Al arrancar, el contenedor SHALL aplicar `alembic upgrade head` y sólo si funciona levantar uvicorn con `app.main:app` en `0.0.0.0:8000`. La imagen SHALL declarar un `HEALTHCHECK` sobre `GET http://127.0.0.1:8000/health/ready`.

#### Scenario: Servidor limpio
- **WHEN** se construye la imagen y se corre con `docker run` y el archivo de variables del servidor
- **THEN** `docker ps` muestra el contenedor `healthy` y `docker logs` muestra las migraciones del TP aplicadas

#### Scenario: Reemplazo del contenedor
- **WHEN** se ejecuta `docker rm -f libreria` y el mismo `docker run`
- **THEN** el contenedor vuelve a `healthy`, los datos siguen y Alembic no aplica migraciones nuevas

#### Scenario: Sin dirección de base
- **WHEN** se corre la imagen sin `DATABASE_URL`
- **THEN** el contenedor termina con error y no queda sirviendo

### Requirement: Despliegue accesible y documentado
El TP SHALL quedar accesible desde fuera del VPS en la URL declarada en `despliegue/DEPLOY.md` hasta la publicación de las notas. `DEPLOY.md` SHALL incluir la URL pública, el día y la hora del despliegue, los comandos `docker build` y `docker run` completos (con el nombre del archivo de variables y sin su contenido), los cambios hechos al TP para correr en el contenedor y cómo se actualiza la aplicación.

#### Scenario: Uso desde afuera
- **WHEN** desde fuera del VPS se pide `GET /health/ready`, `GET /libros/` con los datos iniciales cargados y `POST /ventas/` con el cuerpo de ejemplo del TP
- **THEN** responden `200`, `200` con la lista de libros y `201` con los precios copiados y el total calculado

#### Scenario: Aviso visible en el registro del contenedor
- **WHEN** se registra la venta del escenario anterior
- **THEN** `docker logs libreria` muestra el aviso del comprobante después de la línea de la respuesta
