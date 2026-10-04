> Decisión vigente: biblioteca por lotes en computadoras y servidores, distribuida
> desde GitHub bajo MIT. Los objetivos se condicionan a recursos y carga medidos,
> no a un entorno SaaS. Véase [ADR-0008](decisions/0008-biblioteca-lotes-github.md).

# Operación, observabilidad y carga

F7 implementa instrumentación optativa, pruebas adversariales y mediciones locales.
La [aceptación vigente](revisiones/aceptacion_biblioteca.md) fija objetivos por
equipo/corpus y conserva las limitaciones. La medición inicial queda como evidencia
histórica; ninguna muestra sintética acredita tráfico real ni release publicada.

## Medir sin registrar ofertas

```python
from normietext import FieldInput, JobField, JobTextNormalizer
from normietext.operations import measure_field
from normietext.serialization import canonical_bytes

normalizer = JobTextNormalizer()
measurement = measure_field(normalizer, FieldInput(JobField.JOB_TITLE, "Python Engineer"))
metrics_json = canonical_bytes(measurement.metrics)
if measurement.error is None:
    canonical = measurement.result
else:
    error_code = measurement.error
```

`measure_field`/`measure_record` usan la API pública. Devuelven Measurement con
resultado, código de fallo tipado, métricas inmutables y trace opcional. Un fallo
de campo no publica un resultado canónico parcial. El registro mantiene seis
sobres y captura fallos por campo como la API no estricta. Los fallos inesperados
se propagan; las excepciones de la API original permanecen sin cambios.

Exportar **solo metrics**. Resultados, fuentes y traces contienen datos de ofertas.
No serializar Measurement entero en logging. La biblioteca no envía ni guarda logs.
`trace=True` habilita snapshots de etapas en memoria: ingesta debe autorizar su
acceso, limitar retención y protegerlos; está desactivado por defecto.

Dimensiones: campo, formato, perfil, reglas y SHA-256 de versión del scraper.
El hash evita exportar contenido libre de `source_adapter_version`; guardar la
correspondencia en configuración de ingesta si se necesita una etiqueta legible.
Los manifiestos se comparten externamente por `manifest_id`, sin repetirlos en
cada evento. No se incluyen source_ref, texto, payloads ni mensajes de error.

Métricas: duración total y de convert/repair/lex/render/validate; tamaños en puntos
de código; vacío antes/después; ratio (null si raw vacío); ediciones por regla;
reparaciones; hints; operaciones de eliminación; anotaciones; incidencias;
precisión de procedencia; errores/timeouts y estados parciales. Los contadores
miden operaciones atribuidas, no caracteres que se adivinan eliminados. El tiempo
de lex incluye su validación de fase reparada; render incluye símbolos, estructura,
proyecciones y NFC. El total incluye sobrecostes fuera de esas etapas.

Las capturas son por contexto y se restablecen incluso si falla una llamada.
Procesar registros independientes en paralelo conserva orden si el integrador
usa un map ordenado. No hay executor ni estado mutable de política en el núcleo.

## Reproducir carga

```bash
uv sync --locked
uv run --locked python -m benchmarks.load --output /tmp/carga.json
uv run --locked python -m benchmarks.load --case integral --case hints_2000 --profile --python-memory --output /tmp/perfil.json
```

`benchmarks/` es desarrollo y queda fuera del wheel. Casos habituales sintéticos:
registro de seis campos, integral, compacto, escapado y HTML. Adversariales:
límite máximo de texto, combinaciones Unicode, 2.000 hints, URL/correo casi válido,
profundidad aceptada/rechazada y nodos HTML en el límite. No se mezclan ambos
cohortes para afirmar un throughput representativo sin conocer la distribución.

Cada caso corre en un proceso independiente. El informe registra CPU/SO/runtime,
lock/manifiesto, hash de entrada, tamaños, fracción HTML, unidad campo/registro,
warmup y repeticiones, cold call, p50/p95/p99 nearest-rank, media/desviación,
throughput de llamadas y de éxitos, resultados tipados y coste por etapa.
Una llamada fría incluye inicialización de manifiesto/tablas, no startup de Python.

RSS se mide con getrusage en Unix: máximo vital del proceso, incluido warmup.
En plataformas sin resource se publica null, nunca cero. `--python-memory` añade
una pasada tracemalloc, que afecta mucho al coste y no mide memoria nativa.
`--profile` añade cProfile en otra pasada. Sus tiempos no entran en percentiles;
ambas opciones pueden hacer agotar el timeout total del proceso. Desactivadas por
defecto para mantener medible la carga grande. El RSS se toma antes de cProfile.

`--worker-timeout` limita todo el escenario, incluidas repeticiones y herramientas;
no es un SLO por llamada. Si expira, el padre mata y espera al hijo y publica
worker_error=timeout, sin fingir percentiles. El comando devuelve código 1 ante
fallos de worker. Los errores tipados se contabilizan como tales; contar throughput
de rechazo no demuestra capacidad de normalización exitosa.

En Linux, `--worker-memory-mib N` añade RLIMIT_AS al worker antes de normalizar;
es un límite de espacio virtual, no RSS, y requiere margen para librerías/mapeos.
No se activa silenciosamente en otras plataformas. En producción usar controles
del supervisor/contenedor (tiempo, RSS/memoria, cola y terminación); el núcleo no
puede convertir cada MemoryError o proceso matado en un resultado recuperable.
La ingesta conserva raw y registra fallo externo por campo/registro.

## Baseline, capacidad y aceptación

```bash
uv run --locked python -m benchmarks.load --output /tmp/nueva.json \
  --warmup 2 --repetitions 5 --worker-timeout 300 --worker-memory-mib 512 \
  --baseline docs/revisiones/fase_7_carga.json --max-regression-percent 25
```

El 25 es un ejemplo de uso, **no un umbral acordado**. Usar exactamente el protocolo
de la baseline y aprobar el umbral en el entorno objetivo. La comparación rechaza
cambios de hardware/SO/runtime/lock/protocolo/inventario/entrada/resultados antes de
interpretar regresiones de p50/p95/p99 y RSS. Los cambios de código se esperan.
Una comparación inadecuada no aprueba una release. CI compartida ejecuta tests
funcionales y no aserciones de microsegundos.

Para cerrar F7: definir distribución de campos/formatos/tamaños, registros por
segundo y picos, latencia máxima, tasa admisible de errores/timeouts, entorno y
recursos por worker; repetir suficientes muestras independientes, aprobar p99,
memoria, watchdog y margen de capacidad. Para una mezcla con pesos w_i y tiempos
medios t_i, capacidad secuencial aproximada = 1/sum(w_i*t_i); multiplicar por
workers y utilización objetivo solo después de medir contención. No extrapolar
linealmente desde hilos Python con GIL ni sumar throughput de casos aislados.

Mantener wheels/lock/perfil anteriores y fuente recuperable para rollback.
La salida es texto, no HTML sanitizado: presentar con escape contextual (por
ejemplo html.escape para contenido HTML), nunca insertarla como markup confiable.

## Muestras aportadas y lotes

`benchmarks.adversarial` conserva los 20 JSON originales, `modality` y los elementos
de criterios. No adivina seniority ni interpreta pseudo-HTML. El manifiesto semántico
auxiliar no alimenta el normalizador. Los registros con cinco campos presentes y
seniority missing son partial sin errores de campo; no deben contarse como rechazos.

```bash
uv run --locked python -m benchmarks.batch --workers 1 2 4 --rounds 5 \
  --output /tmp/normietext-batch-20.json
```

El informe mide procesos independientes, orden estable, latencia, rendimiento total,
RSS por proceso, fallos, hashes de entradas y replay entre configuraciones. Incluye
startup y comprobaciones del consumidor. Los 20 documentos se repiten: esto sirve
para medir coste y estabilidad, no aumenta la diversidad ni acredita un lote real
de 100.000 entradas. La estimación de tiempo para 100.000 está etiquetada como
extrapolación. La ingesta de producción debe limitar su cola y consumir resultados
progresivamente; no materializar 100.000 documentos canónicos en RAM.
