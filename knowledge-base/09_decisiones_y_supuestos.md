# Decisiones y Supuestos

## Decisiones documentadas

### DD-01 — Separación del repositorio en dos carpetas raíz (`parcial/` y `despliegue/`)
- **Decisión**: Estructurar la raíz del proyecto con las dos carpetas exactas que exige el formato de entrega de la página 24 (`parcial/` para los ejercicios 1 a 8 y `despliegue/` para los ejercicios 9 y 10).
- **Contexto**: El enunciado establece que la entrega final es un único `.zip` con dos proyectos independientes porque el despliegue en el VPS se realiza sobre el TP de los capítulos 1 a 4 sin las modificaciones de los capítulos 5 y 6.
- **Alternativas consideradas**: Usar dos ramas de Git distintas para `parcial` y `despliegue`.
- **Justificación**: Tener ambas carpetas en la misma rama `main` permite que distintos integrantes del grupo trabajen y hagan push en paralelo sobre `parcial/` y `despliegue/` sin conflictos, y que el `.zip` de entrega se arme directamente desde el árbol de trabajo.
- **Trade-offs aceptados**: Se duplica el código base de los capítulos 1 a 4 entre ambas carpetas, lo cual es intencional porque `despliegue/` debe permanecer congelado en la versión del TP.

### DD-02 — Unificación de la `AsyncSession` entre dependencias de Auth y `UnitOfWork`
- **Decisión**: Tanto `get_usuario_actual` / `requiere_rol` como la fábrica del `UnitOfWork` de cada módulo reciben `SessionDep` (`Depends(get_session)`), que FastAPI cachea por petición.
- **Contexto**: En cada ruta protegida se consulta primero el usuario y sus roles vigentes en la base y luego el servicio ejecuta la operación de negocio dentro del `UnitOfWork`.
- **Alternativas consideradas**: Que el `UnitOfWork` cree su propia sesión internamente al entrar al `async with`.
- **Justificación**: Si el `UnitOfWork` abriera otra sesión, cada petición autenticada tomaría **dos conexiones del pool** al mismo tiempo y el `UnitOfWork` tendría que cerrar su sesión. Compartiendo `SessionDep`, toda la petición usa una sola conexión y `get_session` es el único responsable de cerrarla al finalizar (Ejercicio 6, sección 6.7).
- **Trade-offs aceptados**: La única excepción explícita es el registro de `IntentoAcceso` en el login, que abre su propia sesión desde `request.app.state.session_factory` para confirmar el intento aunque la petición principal haga rollback (Ejercicio 7).

### DD-03 — Disparador `BEFORE UPDATE OR DELETE FOR EACH ROW` para `movimiento_stock`
- **Decisión**: Implementar la invariante de sólo agregado (RN-12) mediante una función PL/pgSQL `impedir_modificacion_movimiento_stock()` y un trigger `BEFORE UPDATE OR DELETE ON movimiento_stock FOR EACH ROW` en la 4ª migración manual (`c8e31f5a9021`).
- **Contexto**: La tabla `movimiento_stock` no debe permitir modificaciones ni borrados de filas ni desde la aplicación ni desde `psql` (Caso `C-14`), pero `seed.py` necesita poder vaciar las tablas al reiniciar las pruebas.
- **Alternativas consideradas**: Bloquear también `TRUNCATE` con un trigger a nivel de sentencia.
- **Justificación**: En PostgreSQL un trigger `FOR EACH ROW BEFORE UPDATE OR DELETE` rechaza cualquier `UPDATE` o `DELETE` individual o masivo (cumpliendo estrictamente RN-12 y `C-14`), mientras permite que `seed.py` use `TRUNCATE TABLE ... RESTART IDENTITY CASCADE` para limpiar la base rápidamente antes de cada archivo `.http`.
- **Trade-offs aceptados**: Ninguno para el alcance del parcial.

### DD-04 — Compatibilidad doble de punto de entrada (`main.py` y `app/main.py`)
- **Decisión**: Ubicar la aplicación principal en `parcial/main.py` (como pide la tabla de estructura obligatoria de la página 8) y mantener `parcial/app/main.py` como un re-export ligero (`from main import app, lifespan`).
- **Contexto**: La página 8 indica la ruta `main.py` en la raíz de `parcial/`, mientras que algunos comandos habituales o configuraciones de uvicorn usan `uvicorn app.main:app` o `uvicorn main:app`.
- **Justificación**: Con el re-export ambos comandos (`uvicorn main:app` y `uvicorn app.main:app`) funcionan sin duplicar lógica.

## Supuestos inferidos

### SU-01 — Contraseñas de prueba en `seed.py`
- **Supuesto**: Las contraseñas de los 5 usuarios iniciales en `seed.py` (página 19: *"Las contraseñas son de mentira y viven sólo en ese archivo"*) serán definidas de forma clara y documentadas en `parcial/README.md` y usadas de manera consistente en todos los archivos `test/*.http`.
- **Origen**: Página 19 del PDF del parcial.
- **Riesgo si es falso**: Ninguno, siempre que los casos `.http` de `test/` utilicen exactamente las contraseñas cargadas por `seed.py`.
- **Cómo validar**: Ejecutar `python seed.py` antes de correr la suite `test/*.http`.

### SU-02 — Asociaciones de `LibroAutor` para los 5 libros del seed
- **Supuesto**: En `seed.py` se mantienen los mismos 5 libros del TP (*Rayuela*, *Antología de la literatura fantástica*, *Ficciones*, *Respiración artificial*, *Bestiario*) con los stocks y ventas actualizados según la tabla de la página 20 (*Rayuela* 10, *Antología* 5, *Ficciones* 8, *Respiración artificial* 3, *Bestiario* 1, y los 6autores / 3 editoriales / 3 géneros).
- **Origen**: Página 20 del PDF del parcial.
- **Cómo validar**: Verificar que los casos `C-10`, `C-11`, `C-13`, `C-15` y `C-16` coincidan con los IDs y stocks de esos 5 libros.
