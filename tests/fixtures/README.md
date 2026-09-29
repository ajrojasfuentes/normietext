# Corpus de contratos y regresión

Este corpus es sintético. F1 validó su forma y fidelidad; F5 ejecuta sus expectativas
con `JobTextNormalizer`. `verified_f5` registra esa cobertura local, sin declarar
aceptación de tráfico real. `awaiting_normalizer`, si aparece en futuros fixtures,
no cuenta como aprobado ni se oculta con skips.

`catalog.json` vincula los archivos exactos con SHA-256 y una configuración de
perfil versionada. Los hashes se actualizan solo tras revisar una modificación
intencional del corpus. Nunca se regeneran expected desde la implementación.

- `regression/cases.json`: T01–T40, expandidos en 49 escenarios. `input_type=text`
  usa raw sin coerción; bytes_hex se materializa con bytes.fromhex; JSON null se
  entrega como None; los escapes de sustitutos se materializan como tales.
- `integral/`: raw y expected exactos, campos/formatos/estados, hashes y secciones.
  Se excluye el LF que delimita el cierre de cada fence, no contenido interno.
- `supplemental/`: criterios, HTML, límites y fronteras. Las expectativas anteriormente null se fijan manualmente conforme a ADR-0005;
  las demás expectativas originales no cambian.
- `records/`: un contrato distinto con los seis campos presentes.
- `review_inventory.json`: destino selectivo de T41–T64, incluidas propuestas
  rechazadas o diferidas. No impone la revisión externa como nueva especificación.

Las colecciones `annotations` y `structure` son **restricciones**, no listados
exhaustivos de objetos; una lista vacía no afirma ausencia. Para exigir ausencia
se usa una propiedad explícita como `no_generated_annotations`. Los conteos de
hints del integral son exactos. `properties` identifica obligaciones de aceptación
ejecutadas por la suite de regresión.

Spans/IDs no se fijan a mano. F2–F5 incluyen mapas y pruebas contra fragmentos
reales. Los loaders leen bytes y decodifican UTF-8 sin conversión universal de LF.
Los esquemas rechazan claves desconocidas. El split por familia evita mezclar
copias entre development y validation; el integral público no es una validación
ciega ni reemplaza la futura muestra real autorizada.

## Adaptación F3

`adaptation/cases.json` y su schema verifican `phase=converted`. Son expectativas
manuales independientes para formato/estructura, no sustituyen los goldens del
normalizador ni su estado awaiting_normalizer. El catálogo agrega sus hashes sin
modificar los del corpus anterior. Un LF final en un bloque/celda vacío es una
proyección intermedia; delimitadores finales y compactación se validan en F5.

## Reparación y léxico F4

`lexical/cases.json` contiene 23 expectativas intermedias escritas independientemente:
texto reparado, número de reparaciones, tokens especiales, protecciones e incidencias.
El schema exige phase=lexed. No sustituye la salida final del normalizador.

Se incluye una limitación explícita del ftfy configurado: `Ã and café C++ B2+`
se repara a `à and café C++ B2+`. La expectativa inicial de preservación de ese
fixture nuevo fue corregida explícitamente durante autoría, tras inspeccionar la
configuración fijada; el contraejemplo de preservación usa `Ã` aislado. No se
modificaron los goldens previos ni se generaron expectativas desde el pipeline.

## Canonicalización F5

`canonical/cases.json` contiene 56 casos de decisiones de renderer, escritos
independientemente de la salida del programa. La suite cubre T41–T64 según su
**decisión adoptada**: T47/T49 no infieren asociaciones por encabezados; T54/T55
son negativos de listas; T56 conserva hints sin viñeta; T61 usa dos LF entre p.
Las propiedades y tests unitarios amplían combinaciones, límites y spans.

La migración a `verified_f5` cambia metadatos y schemas de ejecución. No cambia
los raw/expected de T01–T40 ni los cuatro archivos de texto del integral. Las siete
expectativas suplementarias antes null se resuelven mediante la tabla manual de
ADR-0005, no por generación desde el pipeline. El catálogo se actualiza solo para
estos cambios revisados y los dos archivos nuevos.
