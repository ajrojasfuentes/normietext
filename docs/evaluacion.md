# Evaluación de evidencia

La evaluación F6 vive en `evaluation/`, fuera del wheel y del cleaner. Requiere el
checkout y su entorno `uv sync --locked`. Consume resultados tipados de
`JobTextNormalizer`; no altera la política ni añade inferencias al texto canónico.

```bash
uv run --locked python -m evaluation.quality --output /tmp/calidad.json
uv run --locked pytest
```

El comando termina con código 1 si falla la puerta. Antes de normalizar verifica
los hashes del catálogo. Registra el manifiesto efectivo, hashes del evaluador,
lockfile y catálogo, resultados por caso y segmentos. Dos ejecuciones sobre el
mismo árbol y entorno producen los mismos bytes. Cambiar revisión Git, código o
entorno cambia el manifiesto: el informe archivado es evidencia de su ejecución,
no un golden que deba reemplazarse automáticamente para aprobar tests.

## Muestra y decisiones de lista

`tests/fixtures/quality/cases.json` contiene entradas y expectativas redactadas
manualmente, familias, idioma, formato, campo, split y etiquetas de líneas en el
texto convertido/reparado. Nunca se derivan textos esperados de la implementación.
El índice de línea es cero-based; una línea vacía no entra en el denominador.
`explicit` comprueba listas DOM y se excluye de la métrica de inferencia contextual.
Los elementos DOM vacíos se comprueban mediante su golden y las relaciones de spans.

Para `item`, reconocer un elemento es TP y omitirlo FN. Para `negative`, reconocer
uno es FP y omitirlo TN. `abstain` identifica un contexto deliberadamente ambiguo:
no reconocerlo cuenta como abstención y reconocerlo como FP. No es una estimación
de incertidumbre del modelo ni una clasificación secreta obtenida del cleaner.

- Precisión: TP / (TP + FP); puerta observada ≥99,5 % y cero FP conocidos.
- Recall: TP / (TP + FN).
- Cobertura: decisiones positivas / líneas etiquetadas no DOM.
- Abstención: etiquetas ambiguas respetadas / líneas etiquetadas no DOM.
- Denominador vacío: `null`, nunca 100 % por ausencia de decisiones.

El JSON separa desarrollo/validación e idioma/formato/campo. Comprueba familias,
duplicados exactos tras casefold/espacios y similitud `SequenceMatcher >= 0.85`
entre splits del corpus nuevo. Es un detector de similitud literal, no una prueba
de independencia semántica. Las regresiones históricas, integral y seis campos
son contratos públicos separados y no inflan ese denominador. La puerta añade
cero FP sobre negativos normativos T01–T40 y pytest ejecuta los casos de error.

La muestra es sintética, pública y pequeña, sin validación ciega. La precisión
observada no demuestra un límite estadístico de 99,5 % ni calidad de tráfico real.
No hay ofertas reales autorizadas incorporadas a esta fase.

## Consumidores mínimos

`collect(result)` devuelve candidatos ordenados de tecnologías del catálogo
mínimo, importes, porcentajes y banderas anotadas. Cada candidato conserva campo,
fragmento, span Python, origen, línea de contexto, bloques/elementos, cues literales,
regla y estado. Los encabezados cortos terminados en `:` pueden aportar el rol,
con span/texto del encabezado; el más próximo desconocido corta la herencia.
Se distinguen requerido, deseable, negado, mencionado y responsabilidad con reglas
limitadas en español, inglés y portugués. No es un parser universal de habilidades.

`collect_record(record)` conserva los seis estados y códigos de extracción o
normalización, candidatos parciales y alternativas. Diferencia salario base, bono,
presupuesto y coste técnico. `salary` solo proyecta un único candidato base con
moneda, periodo, cantidad interpretable y sin cues de condición/negación. Ante
alternativas, ambigüedad o información insuficiente devuelve `null`. `type`,
`seniority` y `modality` permanecen `null`: estos consumidores no los resuelven.

Importes internos: `Decimal`. `evidence_bytes` serializa decimales como cadenas
exactas, sin float, redondeo implícito ni notación científica; rechaza floats y
valores no finitos. Un separador único seguido de tres cifras, como `4,500`, se
considera ambiguo; `0.004` conserva el coste decimal. No se adivina moneda para `$`.
No se convierten periodos ni se reconcilian salarios contradictorios.

Las regiones proceden exclusivamente de anotaciones generadas; escribir
`[flag:CR]` en raw no crea evidencia regional. Los offsets exactos se mantienen
cuando están demostrados; HTML conserva `field`. Un span exacto de bandera vincula
la secuencia raw con el token generado, no implica identidad textual.

`DerivedView.casefold` mantiene un mapa por punto de código para expansiones como
`ß` e `İ`. Solo sirve para matching; sus coincidencias vuelven al texto canónico.
No se entrega una vista derivada a la API como nueva fuente raw. Los nombres de
integración usan `role_responsibilities_list`; no existe un consumidor que requiera
el alias externo `rol_responsabilities_list`, por lo que no se implementa un alias
innecesario ni una API semántica pública.

## Ablaciones y pérdidas

`without_rule` suprime una regla de ediciones planificadas cada vez. Conserva el
reconocimiento inicial; al retirar marcadores recalcula el fallback de símbolos.
Transporta spans y elimina metadatos generados por la regla suprimida. Devuelve
`EvidenceView(experiment="without:...")`, nunca un documento canónico válido ni
un manifiesto de una supuesta política alternativa.

Se ejercitan 13 reglas de listas, emoji, kaomoji, invisibles, solidus y huecos.
El reporte muestra casos afectados, cambios textuales, fragmentos obligatorios,
pérdidas autorizadas, tecnología, regiones y pertenencia a listas, con desglose
por idioma, campo, formato y split. Los experimentos son contribuciones locales
con dependencias de reconocimiento fijas; no miden todas las interacciones causales
ni equivalen a reentrenar o diseñar otro perfil. Un texto puede quedar igual por
una transformación posterior. Las pérdidas autorizadas se contabilizan separadas
de los fragmentos obligatorios. El inventario integral revisa 58 fragmentos de
23 grupos de §32 y 15 pérdidas autorizadas, además del golden completo existente.
