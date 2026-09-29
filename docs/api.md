# API de normalización

`JobTextNormalizer` es una biblioteca síncrona, local y determinista. No realiza
scraping, navegación ni interpretación semántica. Requiere CPython 3.14 y las
versiones fijadas en el lockfile para reproducir el manifiesto de este proyecto.

## Normalizar un campo

```python
from normietext import FieldInput, JobField, JobTextNormalizer, SourceFormat

normalizer = JobTextNormalizer()
result = normalizer.normalize_field(FieldInput(
    JobField.JOB_DESCRIPTION,
    "<p>• Python</p><p>• AWS 🇨🇷</p>",
    SourceFormat.HTML_FRAGMENT,
))
assert result.text == "- Python\n- AWS [flag:CR]"
assert result.annotations[0].payload["value"] == "CR"
assert normalizer.canonicalize(result) is result
```

Los campos y formatos se pasan como enums, sin autodetección ni coerción de tipos.
Los seis campos son independientes. Título, tipo, seniority y ubicación se compactan
a una línea; descripción y criterios conservan líneas y como máximo una vacía.

`plain_text` es literal, incluido HTML aparente y entidades. `html_escaped_text`
decodifica una sola capa; `html_fragment` interpreta el fragmento una vez. `unknown`
se trata literalmente con incidencia. El resultado conserva `source.raw`,
referencias de origen, bloques, asociaciones, anotaciones, ediciones e incidencias.

`clean_text(text, field, *, source_format=SourceFormat.PLAIN_TEXT)` delega al mismo
flujo y devuelve `result.text`. Esta proyección pierde los metadatos para el
consumidor; no distingue un token escrito literalmente de uno generado.

## Continuar documentos tipados

`canonicalize(document)` acepta `ParsedDocument`, `RepairedDocument`,
`LexedDocument` o `NormalizedField`. Convierte a canónico lo pendiente desde esa
fase; no vuelve al adaptador. Un canónico compatible devuelve el mismo objeto
inmutable, tras validar manifiesto, referencias, texto, listas y anotaciones.
Reparación de origen no se repite. Un manifiesto incompatible causa
`POLICY_MISMATCH`: hay que reprocesar la fuente original.

No se promete idempotencia al volver a ingresar strings como fuente. Por ejemplo,
el texto ya decodificado conserva su literalidad únicamente al transportar su fase.
Ninguna transformación consulta `SourceStore`; recuperación externa pertenece a ingesta.

## Normalizar un registro

```python
from normietext import ExtractionStatus, InputField, JobInputRecord

source = FieldInput(JobField.JOB_TITLE, "Python Engineer")
record = JobInputRecord(tuple(
    InputField(field, ExtractionStatus.PRESENT, source)
    if field is JobField.JOB_TITLE
    else InputField(field, ExtractionStatus.MISSING)
    for field in JobField
))
output = normalizer.normalize_record(record)
assert output.status.value == "partial"
assert output.fields[0].result.text == "Python Engineer"
assert output.fields[1].result is None
```

Los seis sobres se conservan, en orden `JobField`. Un ausente o `extraction_error`
no se transforma en string vacío. Cada fallo de normalización conserva `FieldInput`
en `FieldFailure`; los demás campos pueden completarse. `strict=True` propaga el
primer fallo de normalización. Un error de extracción ya declarado permanece en su
sobre, incluso en modo estricto. El límite total de registro se verifica antes de
normalizar campos y su exceso rechaza la llamada completa.

`JobInputRecord.from_mapping` exige exactamente las seis claves conocidas y sobres
coherentes. `NormalizedJobRecord.status` es `ok`, `partial` o `missing`.
`NormalizedField.status` es `empty` si no queda texto, incluso con incidencias;
con texto distingue `ok` de `ok_with_issues`.

## Consultar evidencia

Offsets son puntos de código Python, semiabiertos `[start, end)`, después de NFC.
Consultar `result.text[annotation.span.start:annotation.span.end]` devuelve el token
generado. Los tokens literales no reciben anotaciones por su apariencia.

Los bloques conservan listas, ordinales, profundidad, continuaciones, celdas y
asociaciones explícitas. El texto no permite reconstruir toda la estructura ni
código ejecutable: la política elimina sangría también dentro de código. URL,
correo y código bloquean equivalencias de puntuación y heurísticas de listas,
pero no la política global de emoji, invisibles y espacios. Cambios en una
protección generan `PROTECTED_SPAN_MODIFIED`.

`origin.precision` declara `exact`, `segment` o `field`. HTML permanece `field`
cuando el backend no demuestra offsets raw. Una reparación del mismo largo no
prueba exactitud. Ningún offset hacia raw se obtiene buscando texto repetido.

`canonical_bytes(result)` en `normietext.serialization` produce JSON determinista.
El manifiesto identifica política, código, dependencias y tablas; no contiene
timestamps ni tiempos operativos. El normalizador inmutable puede compartirse
entre llamadas concurrentes sin modificar su configuración.

## Fallos y límites

Los fallos heredan de `NormalizationError` y exponen `code: ErrorCode`. Incluyen
entradas inválidas, Unicode inválido, límites de entrada/HTML/profundidad/salida,
timeouts regex, invariantes y política incompatible. No hay truncamiento ni
fallback silencioso. Los mensajes de diagnóstico no incorporan el texto privado.

Se configura un presupuesto con `NormalizationPolicy(limits=ResourceLimits(...))`.
Las opciones conductuales de este perfil están fijadas y no se aceptan opciones
arbitrarias. `strict` es una opción de agregación de fallos, no una regla de texto.

El corpus disponible es sintético y público. F5 acredita sus regresiones; calidad
en muestras representativas, precisión de listas ≥99,5 %, SLO y despliegue siguen
en F6–F8. Véanse [ADR-0005](decisions/0005-renderer-api.md) y el
[plan](plan_implementacion.md).
