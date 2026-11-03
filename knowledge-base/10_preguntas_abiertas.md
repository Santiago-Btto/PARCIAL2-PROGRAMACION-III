# Preguntas Abiertas

## Inconsistencias o detalles de atención detectados en el enunciado

### IN-01 — Cantidad de autores en `seed.py` (TP vs Parcial)
- **El README del TP (cap. 1 a 4) tiene**: 5 autores cargados en `scripts/seed.py` (Cortázar, Piglia, Bioy Casares, Silvina Ocampo, Borges).
- **El PDF del Parcial (página 20) dice**: *"Los del TP: 3 editoriales, 3 géneros y 6 autores"*.
- **Impacto**: Bajo, pero algún caso de prueba de la corrección podría esperar que exista el autor con `id = 6`.
- **Resolución aplicada**: En `parcial/seed.py` se mantendrán los 5 autores en sus mismos IDs (`1` a `5`) y se agregará un 6º autor (por ejemplo, Rodolfo Walsh o Adolfo Bioy Casares / Ernesto Sabato) para cumplir literalmente con *"3 editoriales, 3 géneros y 6 autores"* sin alterar los IDs `1..5` usados en los libros existentes.

### IN-02 — Orden de IDs de libros y clientes en `parcial/seed.py`
- **El PDF del Parcial (páginas 19 y 20) muestra**:
  - En el ejemplo de `GET /libros?size=2` (pág. 19): `id: 1` es *Rayuela* ($25000.00, stock 10) e `id: 2` es *Antología de la literatura fantástica* ($30000.00, stock 5). Luego menciona *Ficciones* (stock 8), *Respiración artificial* (stock 3) y *Bestiario* (stock 1).
  - En Clientes (pág. 20): Lucía Fernández (con perfil, sin usuario), Tomás Ríos (sin usuario) y Ana Paz (con el usuario `ana@example.com`).
  - En Venta 1 (pág. 20): De Lucía, registrada por `vendedor@example.com`: 1 *Rayuela* y 2 *Ficciones*, total `69000.00`.
- **Impacto**: Los casos de prueba `C-10`, `C-11` y los ejemplos del PDF asumen ese orden e importes (*Rayuela* = $25.000 + 2 × *Ficciones* = $22.000 → $69.000, y el orden de los 5 libros en el listado paginado).
- **Resolución aplicada**: En `parcial/seed.py` se cargarán los 5 libros y los 3 clientes exactamente en el orden y con los precios/stocks que muestra el PDF en las páginas 19 y 20.

## Preguntas abiertas (priorizadas)

| Prioridad | Pregunta | Bloquea | Decisor |
|---|---|---|---|
| **Media** | ¿Cuáles son los datos de conexión al VPS de la cátedra (IP/dominio, puerto asignado al grupo y `DATABASE_URL` del PostgreSQL del servidor) para ejecutar en vivo el Ejercicio 10? | Ejercicio 10 (`despliegue/DEPLOY.md` y capturas en vivo `D-02` a `D-08`) | Grupo / Cátedra |
| **Baja** | ¿Cuáles son los nombres y apellidos completos de todos los integrantes del grupo para incluirlos en el encabezado de `parcial/README.md` y en el nombre del archivo `.zip` (`Parcial_Cap1a6_<NombreDelGrupo>.zip`)? | Armado final del `README.md` y `.zip` de entrega | Grupo |
