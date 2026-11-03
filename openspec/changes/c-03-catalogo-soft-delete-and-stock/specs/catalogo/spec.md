# Spec Delta

## Purpose

Define el acceso público al catálogo de la librería, su paginación uniforme y los contratos de administración que conservan las relaciones y validaciones existentes.

## ADDED Requirements

### Requirement: Colecciones de catálogo paginadas
El sistema SHALL devolver `{items, total, page, size, pages}` en las colecciones de editoriales, géneros, autores, libros y libros relacionados, con orden estable por identificador, `page >= 1`, `1 <= size <= 100` y tamaño predeterminado 20.

#### Scenario: Segunda página con total filtrado
- **WHEN** se consulta una colección de 25 resultados con `page=2&size=20`
- **THEN** devuelve 5 elementos, `total=25`, `page=2`, `size=20` y `pages=2`

#### Scenario: Colección vacía
- **WHEN** una consulta no encuentra resultados y solicita la página 1
- **THEN** devuelve `items=[]`, `total=0` y `pages=1`

#### Scenario: Página inexistente o parámetros inválidos
- **WHEN** se solicita `page > pages`, `page=0`, `size=0` o `size=101`
- **THEN** devuelve `422` y nunca una lista vacía que oculte el error de página

### Requirement: Contratos estrictos y actualización parcial
El sistema SHALL rechazar campos desconocidos en entradas de catálogo y modificar sólo campos enviados en PATCH. El PATCH de libro SHALL conservar `isbn`, `titulo`, `precio`, `editorial_id` y `genero_id`, rechazando `stock` y `stock_inicial`; los demás valores y validaciones actuales se conservan.

#### Scenario: Actualización parcial sin pérdida de campos
- **WHEN** un administrador modifica sólo el título de un libro
- **THEN** cambia el título y conserva precio, ISBN, editorial, género y stock

#### Scenario: Género explícitamente nulo
- **WHEN** se envía `genero_id=null` en un PATCH válido de libro
- **THEN** se elimina su asociación opcional al género sin cambiar los demás campos

#### Scenario: Stock y campos desconocidos rechazados
- **WHEN** una entrada contiene un campo no declarado o un PATCH de libro contiene `stock` o `stock_inicial`
- **THEN** devuelve `422` sin modificar entidades ni registrar movimientos

#### Scenario: Validaciones de dominio heredadas
- **WHEN** se envía precio no positivo, ISBN inválido, autorías repetidas o un nulo explícito en un campo obligatorio
- **THEN** devuelve `422` conservando las validaciones existentes

### Requirement: Filtros públicos seguros
El sistema SHALL buscar títulos sin distinguir mayúsculas, tratar `%`, `_` y texto SQL como texto literal y combinar `titulo` con `genero_id`; el total y los elementos de la página SHALL usar los mismos filtros.

#### Scenario: Filtros combinados
- **WHEN** se solicita un título con distinta capitalización y un género específico
- **THEN** sólo aparecen libros vigentes que cumplen ambos filtros y el total corresponde a ese conjunto

#### Scenario: Caracteres especiales y texto SQL
- **WHEN** se busca un título con `%`, `_` o `' OR '1'='1`
- **THEN** se busca ese texto literal sin expandir comodines ni alterar las condiciones de la consulta

### Requirement: Lecturas públicas y administración por rol vigente
El sistema SHALL mantener públicas las lecturas de catálogo, exigir rol vigente `ADMIN` y cambio de contraseña resuelto en sus escrituras, reposición e historial de stock, y conservar la implementación de autenticación y las rutas existentes de cada entidad.

#### Scenario: Visitante consulta catálogo
- **WHEN** un visitante sin cookie consulta una lectura pública de catálogo
- **THEN** recibe los datos paginados o el error de recurso/página aplicable sin requerir sesión

#### Scenario: Escritura administrativa autorizada
- **WHEN** un administrador vigente con contraseña resuelta envía una escritura válida
- **THEN** la operación puede ejecutarse bajo las reglas de catálogo

#### Scenario: Sesión ausente o permisos insuficientes
- **WHEN** se solicita una escritura o historial sin cookie válida, con rol no administrativo o con cambio de contraseña pendiente
- **THEN** responde `401` si no hay sesión válida o `403` si la sesión carece del permiso requerido

### Requirement: Integridad y relaciones sin carga implícita
El sistema SHALL conservar los datos de editorial, género y autorías en las respuestas actuales, resolverlos con cantidad acotada de consultas y rechazar conflictos de unicidad o referencias mediante `409` con mensajes propios, sin exponer SQL ni trazas.

#### Scenario: Detalle con varias autorías
- **WHEN** se consulta un libro con una o varias autorías
- **THEN** devuelve sus relaciones y rol/orden de autoría sin consultas individuales por autor

#### Scenario: Conflicto de unicidad o referencia
- **WHEN** una escritura colisiona con un nombre único, ISBN vigente o una referencia inexistente
- **THEN** devuelve `409` con mensaje de dominio y revierte sus escrituras, sin verificar unicidad mediante consulta previa
