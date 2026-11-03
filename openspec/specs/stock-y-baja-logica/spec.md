# stock-y-baja-logica Specification

## Purpose

Define las operaciones de inventario del catálogo y la conservación de libros e historial al darlos de baja, con trazabilidad atómica y un contrato de variaciones reutilizable por ventas.

## Requirements

### Requirement: Alta con stock inicial trazable
El sistema SHALL aceptar `stock_inicial >= 0` en el alta de libro, conservar los límites enteros vigentes y crear el libro y sus autorías atómicamente. Un stock positivo SHALL generar exactamente un movimiento con motivo `Stock inicial`, actor autenticado y sin venta asociada; cero SHALL producir stock cero sin movimiento.

#### Scenario: Alta con stock positivo
- **WHEN** un administrador crea un libro válido con `stock_inicial=7`
- **THEN** devuelve `201`, stock 7 y exactamente un movimiento de cantidad 7 asociado al nuevo libro y al administrador

#### Scenario: Alta sin existencias
- **WHEN** se crea un libro válido con `stock_inicial=0` o sin enviar el campo
- **THEN** devuelve `201`, stock cero y ningún movimiento de cantidad cero

#### Scenario: Alta inválida o fallida
- **WHEN** el stock inicial es negativo, se envía el antiguo campo `stock` o falla una referencia de autoría
- **THEN** devuelve `422` para entrada inválida o `409` para conflicto de referencia y no quedan libro, autorías ni movimiento parciales

### Requirement: Variación de stock atómica y serializada
Las operaciones de inventario del catálogo SHALL registrar una variación no nula y su movimiento en una sola transacción, preservando el actor y stock entre cero y el máximo INTEGER. El contrato compartido SHALL admitir variaciones negativas y referencia de venta para su integración posterior; ningún error SHALL dejar sólo una de las dos escrituras.

#### Scenario: Dos reposiciones simultáneas
- **WHEN** dos reposiciones válidas de 2 y 3 unidades se confirman sobre un libro con stock 4
- **THEN** el stock final es 9 y existen ambos movimientos, sin pérdida de actualizaciones

#### Scenario: Fallo al registrar el movimiento
- **WHEN** falla la inserción del movimiento después de calcular una variación
- **THEN** la operación revierte y conserva el stock y los movimientos previos

#### Scenario: Variación negativa aceptada por el contrato compartido
- **WHEN** se invoca el contrato dentro de una transacción de prueba con stock 5, variación -2, actor y referencia de venta válidos
- **THEN** deja stock 3 y un movimiento -2 con esa referencia, sin confirmar independientemente la transacción del llamador

#### Scenario: Variación negativa insuficiente
- **WHEN** el contrato recibe una variación que dejaría stock negativo
- **THEN** rechaza la operación con conflicto sin modificar stock ni crear movimiento

#### Scenario: Desborde del stock acumulado
- **WHEN** una cantidad de reposición válida sumada al stock supera el máximo INTEGER
- **THEN** devuelve `409` sin modificar stock ni crear movimiento; una cantidad de entrada fuera del límite devuelve `422`

### Requirement: Reposición administrativa validada
El sistema SHALL responder a `POST /libros/{id}/reponer` con `200` y datos del libro actualizado, exigir `cantidad > 0` y `motivo` no vacío de hasta 200 caracteres, y registrar el actor. SHALL devolver `404` para un identificador inexistente y `409` para un libro dado de baja.

#### Scenario: Reposición válida
- **WHEN** se reponen 3 ejemplares con motivo válido sobre un libro vigente
- **THEN** aumenta el stock en 3 y agrega exactamente un movimiento con cantidad, motivo y actor correspondientes

#### Scenario: Entrada inválida
- **WHEN** la cantidad es cero o negativa, el motivo está vacío o sólo tiene espacios, excede 200 caracteres o hay campos desconocidos
- **THEN** devuelve `422` sin escrituras

#### Scenario: Reposición sobre baja o identificador inexistente
- **WHEN** se intenta reponer un libro dado de baja o un identificador inexistente
- **THEN** devuelve `409` o `404` respectivamente sin cambios de stock ni movimientos

### Requirement: Baja lógica y reutilización de ISBN
El sistema SHALL responder a `DELETE /libros/{id}` vigente con `204` sin cuerpo, conservar físicamente el libro y sus relaciones, y ocultarlo del detalle público, listados, totales y libros por editorial, género o autor. Su ISBN SHALL quedar disponible para un nuevo libro vigente sin modificar el historial original.

#### Scenario: Baja visible en todas las lecturas públicas
- **WHEN** se confirma la baja de un libro vigente
- **THEN** el detalle devuelve `404`, las colecciones públicas y sus totales lo excluyen y el registro original conserva una fecha de baja con zona horaria

#### Scenario: Baja repetida o inexistente
- **WHEN** se solicita borrar un libro ya dado de baja o inexistente
- **THEN** devuelve `404` y conserva todos los datos históricos

#### Scenario: ISBN liberado y conflicto vigente
- **WHEN** se da de alta otro libro con el ISBN de un libro dado de baja
- **THEN** la nueva alta devuelve `201` con identificador distinto y una segunda alta con ese ISBN todavía vigente devuelve `409`

### Requirement: Historial paginado conservado
El sistema SHALL devolver los movimientos de un libro en `GET /libros/{id}/movimientos` con el envoltorio y validaciones de `Pagina`, orden estable por identificador y campos `id`, `libro_id`, `venta_id`, `usuario_id`, `cantidad`, `motivo` y `cuando`, incluso si el libro está dado de baja. SHALL devolver `404` si nunca existió el libro.

#### Scenario: Historial después de baja y reutilización de ISBN
- **WHEN** se consulta un libro dado de baja cuyo ISBN fue reutilizado por otro libro
- **THEN** devuelve únicamente los movimientos del identificador original sin mezclarlos con los del nuevo

#### Scenario: Historial vacío o inexistente
- **WHEN** se consulta la página 1 de un libro sin movimientos o la de un identificador inexistente
- **THEN** devuelve una página vacía con `pages=1` o `404` respectivamente
