# Corpus de contratos y regresión

Este corpus es sintético. F1 valida su forma y fidelidad; **ningún fixture declara
aprobada una ejecución del normalizador**. `execution_status=awaiting_normalizer`
es estado de cobertura, no un marcador pytest.skip ni un resultado de producto.

`catalog.json` vincula los archivos exactos con SHA-256 y una configuración de
perfil versionada. Los hashes se actualizan solo tras revisar una modificación
intencional del corpus. Nunca se regeneran expected desde la implementación.

- `regression/cases.json`: T01–T40, expandidos en 49 escenarios. `input_type=text`
  usa raw sin coerción; bytes_hex se materializa con bytes.fromhex; JSON null se
  entrega como None; los escapes de sustitutos se materializan como tales.
- `integral/`: raw y expected exactos, campos/formatos/estados, hashes y secciones.
  Se excluye el LF que delimita el cierre de cada fence, no contenido interno.
- `supplemental/`: criterios, HTML, límites y fronteras. Las expectativas pendientes
  de renderer tienen texto null y decision_status explícito; no son goldens exactos.
- `records/`: un contrato distinto con los seis campos presentes.
- `review_inventory.json`: destino selectivo de T41–T64, incluidas propuestas
  rechazadas o diferidas. No impone la revisión externa como nueva especificación.

Las colecciones `annotations` y `structure` son **restricciones**, no listados
exhaustivos de objetos; una lista vacía no afirma ausencia. Para exigir ausencia
se usa una propiedad explícita como `no_generated_annotations`. Los conteos de
hints del integral son exactos. `properties` identifica obligaciones de aceptación
que la futura suite ejecutará; no se validan llamando funciones inexistentes.

Spans/IDs no se fijan a mano. F2–F5 producirán mapas y pruebas contra fragmentos
reales. Los loaders leen bytes y decodifican UTF-8 sin conversión universal de LF.
Los esquemas rechazan claves desconocidas. El split por familia evita mezclar
copias entre development y validation; el integral público no es una validación
ciega ni reemplaza la futura muestra real autorizada.
