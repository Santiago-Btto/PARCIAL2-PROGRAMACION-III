# clientes-y-ventas Specification

## Purpose

Define la atención de clientes, el registro transaccional de ventas con stock trazable, la consulta de compras propias y el estado inicial de la base.

## Requirements

### Requirement: Clientes protegidos y paginados
El sistema SHALL exponer el alta, el detalle con perfil, el PATCH parcial, el alta de perfil y las ventas de un cliente sólo a usuarios con rol vigente `VENDEDOR` o `ADMIN`, con contratos de entrada que rechazan campos no declarados y listados `Pagina[T]`. La unicidad del email y del perfil SHALL garantizarla la base.

#### Scenario: Alta y email repetido
- **WHEN** el personal da de alta un cliente y después otro con el mismo email en otra combinación de mayúsculas
- **THEN** la primera responde `201` con `perfil` nulo y la segunda `409` con mensaje propio

#### Scenario: Perfil uno a uno
- **WHEN** se crea un perfil para un cliente que ya tiene uno, o para un cliente inexistente
- **THEN** responde `409` en el primer caso y `404` en el segundo

#### Scenario: Una cliente en el mostrador
- **WHEN** un usuario con sólo el rol `CLIENTE` pide `GET /clientes/{id}`
- **THEN** responde `403`

### Requirement: Registro transaccional de una venta
`POST /ventas` SHALL aceptar sólo `cliente_id` y renglones (al menos uno, sin libros repetidos, sin precio ni total) de usuarios `VENDEDOR` o `ADMIN`. En un único Unit of Work SHALL verificar el cliente, bloquear y validar cada libro en orden de id, crear la venta con el precio copiado de cada libro y el total calculado por el servidor, y descontar cada renglón por el punto único de stock dejando un movimiento negativo con la venta y el usuario. Ningún rechazo SHALL dejar venta, renglones, descuentos ni movimientos.

#### Scenario: Venta válida
- **WHEN** el vendedor registra 2 Rayuela ($25000) y 1 Ficciones ($22000) para un cliente existente
- **THEN** responde `201` con los precios copiados y total `72000.00`, Rayuela baja 2, Ficciones baja 1 y hay dos movimientos `-2` y `-1` con la venta y el vendedor

#### Scenario: Un libro no alcanza
- **WHEN** la venta pide 1 Rayuela (alcanza) y 2 Bestiario (hay 1)
- **THEN** responde `409` nombrando a Bestiario y el stock y los movimientos de Rayuela no cambian

#### Scenario: Cliente o libro inexistente, o libro dado de baja
- **WHEN** la venta usa un cliente inexistente, un libro inexistente o un libro dado de baja
- **THEN** responde `409` en los tres casos sin dejar escrituras

#### Scenario: Stock igual a la suma de movimientos
- **WHEN** termina cualquier caso de venta, aceptado o rechazado
- **THEN** en todo libro `stock` es igual a la suma de la `cantidad` de sus movimientos

### Requirement: Aviso del comprobante en segundo plano
Al confirmarse una venta el sistema SHALL agendar con `BackgroundTasks` un aviso simulado (`await asyncio.sleep(0.5)` y un mensaje en el registro) que corre después de enviar la respuesta y se ve con el arranque normal de uvicorn. Una venta rechazada SHALL NOT agendar el aviso.

#### Scenario: Aviso después de la respuesta
- **WHEN** se registra una venta válida
- **THEN** la consola muestra la línea de la respuesta `201` y, después, el mensaje del comprobante con el id y el email del cliente

### Requirement: Lo propio y el detalle de una venta
`GET /mis-ventas` SHALL devolver, a cualquier usuario autenticado sin cambio de contraseña pendiente, las ventas de la ficha de cliente vinculada a su usuario, o una página vacía si no tiene ficha. `GET /ventas/{id}` SHALL NOT exigir un rol fijo: SHALL responder `404` si la venta no existe, el detalle si el usuario tiene `VENDEDOR` o `ADMIN` vigente o es el dueño, y `403` en otro caso.

#### Scenario: La cliente y su venta
- **WHEN** Ana pide su propia venta y después la venta de Lucía
- **THEN** recibe `200` y luego `403`

#### Scenario: Sin ficha de cliente
- **WHEN** el vendedor pide `/mis-ventas`
- **THEN** recibe `200` con `items` vacío, `total` 0 y `pages` 1

### Requirement: Detalle de venta sin N+1
El detalle de una venta SHALL resolverse con un número fijo de consultas, con su cliente, sus renglones y el libro de cada renglón, incluido un libro dado de baja.

#### Scenario: Dos contra cuatro renglones
- **WHEN** se piden el detalle de una venta con 2 renglones y el de una con 4
- **THEN** ambos emiten la misma cantidad de consultas

#### Scenario: Venta vieja de un libro dado de baja
- **WHEN** se da de baja Rayuela y se pide la venta 1
- **THEN** el renglón sigue mostrando el título «Rayuela»

### Requirement: Estado inicial conocido
`seed.py` SHALL vaciar todas las tablas, reiniciar los ids y cargar los usuarios, el catálogo, los clientes, la venta 1 y el evento `SISTEMA` de la consigna, sin escribir `libro.stock` fuera del punto único de stock.

#### Scenario: Seed recién cargado
- **WHEN** se ejecuta `python seed.py` sobre una base migrada
- **THEN** los stocks son Rayuela 10, Antología 5, Ficciones 8, Respiración artificial 3 y Bestiario 1, hay siete movimientos y la suma de movimientos coincide con el stock en los cinco libros
