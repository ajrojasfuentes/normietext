# ADR-0003 — Conversión única y estructura de origen

Fecha: 2026-09-27. Estado: adoptado para Fase 3, autorizada por el usuario.
Base: `753bb96`; [especificación §10](../normietext_v2.0_especificacion.md#10-conversión-de-formatos-y-tratamiento-de-html)
y [plan F3](../plan_implementacion.md#7-fase-3--adaptadores-de-formato-y-estructura-de-origen).

## Alcance y contrato

`normietext.adapters.convert_source(FieldInput, limits=...)` despacha exclusivamente
por SourceFormat. Devuelve ParsedDocument, fase `converted`; no publica resultados
canónicos. Rechaza recibir un documento ya convertido. La siguiente etapa usa
`tracked_document` para recuperar texto y alineación sin ejecutar otra conversión.
No se implementa todavía JobTextNormalizer ni canonicalize del pipeline completo.

El presupuesto de entrada se comprueba antes del parser. Se conserva SourceEvidence
con raw exacto, digest y metadatos de ingesta; no se llama a SourceStore ni a la red.
Los adaptadores comprueban el formato incluso si se invocan directamente.

ParsedDocument incorpora `alignment`, una tupla de AlignmentSegment que cubre su
texto. El modelo del segmento se ubica en models para evitar una dependencia
circular y conserva su importación anterior desde provenance. `tracked_document`
exige cobertura completa; un ParsedDocument construido manualmente sin alineación
no obtiene una correspondencia ficticia. La serialización explícita incluye este
campo y los metadatos nuevos de Block.

## Literal y entidades

Plain y unknown conservan etiquetas, entidades, Markdown, marcadores, espacios,
sangrías, emoji y controles ajenos a los separadores de línea. Unknown añade una
incidencia SOURCE_FORMAT_UNKNOWN. No hay autodetección.

Los separadores CRLF (una unidad), CR, NEL, LS, PS, VT y FF se convierten a LF antes
de reparar codificación. Se generan bloques line con spans, incluidos vacíos y
líneas finales. Se conserva alineación exacta de copias e intervalos consumidos;
no se infieren encabezados o listas. Tampoco se compactan campos de una línea aún.

Html_escaped_text reconoce referencias en el original, aplica html.unescape una
vez a cada unidad y registra su edición/alineación. No vuelve a recorrer el texto
decodificado para buscar otras referencias o HTML. La gramática corresponde a la
implementación de CPython fijada y se prueba con referencias numéricas, ambiguas,
sin punto y coma y entidades dobles.

La decodificación HTML5 de `&#x85;` es `…`; un NEL **literal** es un separador LF.
El fixture nuevo F3-entities-numeric se corrigió explícitamente durante autoría
para respetar esa distinción. No se cambió una expectativa del corpus original ni
se generaron goldens a partir de la implementación. Las referencias inválidas siguen
la semántica HTML5 de html.unescape; no son una llamada a ftfy.

## Parser HTML y límites

Beautiful Soup usa directamente LXMLTreeBuilder, con un parser por conversión:
HTMLParser, recover=True, no_network=True, huge_tree=False, decompress=False,
remove_blank_text=False, remove_comments=False, remove_pis=False y collect_ids=False.
Se consulta [la referencia de lxml](https://lxml.de/apidoc/lxml.etree.html) y se
verifica la integración instalada de Beautiful Soup 4.15.0 con lxml 6.1.3.
No se selecciona otro backend ante un fallo. La integración tipada importa el
builder desde bs4.builder._lxml, un detalle de la versión fijada que debe revisarse
al actualizar dependencias.

El builder limita tags y profundidad durante los callbacks. Después del parseo se
cuentan también nodos de texto, comentarios y contenido excluido. Las envolturas
html/head/body cuentan en el total de nodos, pero no en profundidad estructural.
Se conservan restricciones nativas del parser; ampliar un presupuesto no habilita
huge_tree. Un agotamiento de recursión del host es un RESOURCE_LIMIT_EXCEEDED tipado.
Los límites posparseo no prometen sustituir el aislamiento del worker de F7.

El builder impide que Beautiful Soup compacte nodos formados solo por espacios.
Eso conserva espaciado entre elementos inline y dentro de pre/code. No promete
reconstruir caracteres que libxml2 ya haya recuperado, normalizado u omitido.

Los errores disponibles en feed_error_log se registran con dominio/tipo/nivel y
línea/columna del diagnóstico, sin atribuirles precisión de procedencia textual.
Un error FATAL impide publicar el documento. Excepciones de parsing son
HTML_PARSE_FAILED, sin fallback. La advertencia de XML tratado como HTML se conserva;
la advertencia heurística de que el fragmento parece un nombre de archivo o URL se
omite porque el formato ya fue declarado. No se abre ese archivo ni esa URL.
No se genera un diagnóstico heurístico por ratio de longitud.

## Estructura y proyección convertida

Los bloques mantienen IDs, parent_id, origin_tag y metadatos inmutables. Se añade
BlockKind.CONTAINER para listas, tablas, filas, grupos, div y otros contextos de
bloque explícitos. No se consideran encabezados semánticos por sus palabras.

- b/strong/em/span y otros inline conservan texto contiguo, sin espacios añadidos.
- p, encabezados y contenedores aportan límites LF provisionales, deduplicados.
- br aporta LF explícito; hr es un bloque vacío que solicita un límite.
- html/head/body no crean límites ni bloques artificiales.
- pre/code tienen tipo code; inline code no añade límites alrededor.
- blockquote, caption, figcaption y grupos de tabla conservan contexto y parentesco.
- a conserva texto y href ya interpretado por el parser, sin navegar.
- img aporta alt no vacío y una anotación diferenciada, con src como metadata.
- s/strike/del conservan texto y anotación de tachado; sup/sub anotan representación.
- script/style/template y comentarios/declaraciones se excluyen con edición y raw
  recuperable. Button/select/noscript y texto fallback permanecen.

No se ejecuta CSS ni se pretende reproducir visibilidad de un navegador. Espacios,
sangrías y líneas del texto DOM sobreviven a esta etapa, salvo conversión de
separadores. Las secuencias de emoji y sus componentes se conservan.

F3 no introduce `- ` ni `N. `, no consume marcadores de texto y no añade ` | ` entre
celdas. El LF provisional permite representar el documento convertido; la estructura
capturada es autoritativa, incluidos bloques vacíos que comparten un offset. La
compactación de celdas y la proyección final corresponden a F5, según la puerta del
plan. Puede quedar un LF final al abrir un último bloque vacío: no es salida canónica.

## Listas y asociaciones

Ol computa start/value/reversed; el inicio reversed sin start usa el número de li
hijos directos. El salto de ordinal no se corrige. Listas anidadas conservan list_id,
parent_id y profundidad relativa de listas; los bloques de contexto aportan el árbol
completo. Se registran type y value declarados; estilos 1/a/A/i/I de ol/li se conservan.
No se interpretan estilos CSS como numeración.

Los enteros admiten espacio ASCII periférico, signo y hasta 64 dígitos ASCII. Un
atributo inválido genera INVALID_HTML_ATTRIBUTE y usa el fallback especificado:
inicio 1 o cantidad reversed, value secuencial, tipo heredado/decimal. Límites a la
longitud del atributo evitan conversiones enteras arbitrariamente costosas.

Dl agrupa dt consecutivos con dd consecutivos, incluyendo multiplicidad y miembros
faltantes. Cada div hijo directo de dl delimita un grupo; no se completa con el
miembro de un grupo vecino. Se conservan asociaciones bajo html.dl/1.0.0. Un dl
anidado tiene contexto propio. Fuera de dl, dt/dd conservan bloques sin inventar
asociaciones; h3/b/strong dentro de li no crea pares. Modelos permiten a adaptadores
externos declarar otras asociaciones con su propio contrato versionado.

## Tablas

Table, fila y agrupación conservan IDs y parentesco; celdas tienen fila/columna,
header y spans declarados/efectivos. Las columnas saltan posiciones ocupadas por
rowspan/colspan anteriores; las tablas anidadas tienen su propio estado. Se conservan
celdas vacías sin repetir valores para rellenar la cuadrícula.

Colspan válido es 1–1000; rowspan válido es 0–65534. Inválidos usan 1 con incidencia.
Rowspan=0 se concreta en las filas restantes del grupo conocido, conservando el
atributo original. Los grupos explícitos reinician ocupación de columnas; no se
arrastra una celda de thead a tbody. Las filas siguen índices documentales del table.
La suma de anchuras procesadas y la anchura alcanzada no pueden superar html_nodes:
un exceso causa fallo operativo, no truncamiento ni una matriz desmesurada.
Celdas huérfanas conservan sus bloques; no se inventa un table de negocio.

## Procedencia, IDs y aceptación

El backend HTML no aporta offsets raw demostrados. Se usa precisión field y se
registra ORIGIN_PRECISION_REDUCED; no se busca texto repetido con find para fingir
alineación exacta. Los IDs de origen identifican nodos del recorrido determinista
del DOM recuperado, no offsets ni IDs del futuro documento canónico. El raw y el
entorno fijado permiten reconstruir ese recorrido.

La alineación cubre el texto proyectado; conversiones posteriores de líneas se
componen con el origen HTML. Los spans de bloques/anotaciones se actualizan mediante
un mapa local de proyección, sin convertir su procedencia field en exacta. No se
aplica NFC en esta etapa. Los spans canónicos se recalculan después de NFC en F5.

La suite separa fixtures de adaptación (phase=converted) del corpus pendiente del
normalizador. Cubre T03–T08 por conversión, T31/T32 por estructura y R06/R07/R10 por
contextos y representación. Pruebas de propiedades y replay verifican composición
y determinismo; la instalación aislada verifica que los adaptadores viajan en el
wheel. No se da por aprobada la proyección final ni T38/T39 del pipeline completo.

No cambia la versión documental 2.0 ni la del paquete 0.1.0. Los contratos iniciales
1.0.0 siguen sin publicar; hashes de código/manifestación identifican estos cambios.
