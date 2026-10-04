# ADR-0007 — Correcciones canónicas y operación F7

Fecha: 2026-10-02. Estado: adoptado para implementación local; aprobación de SLO
para el entorno objetivo pendiente. Norma: especificación 2.0 §§10, 18, 23, 25–27.

## Correcciones y versiones

Las inserciones de separadores de tabla no se identifican únicamente por un span:
varias celdas vacías consecutivas comparten la misma posición. Se concatenan sus
separadores en orden DOM. Cuatro celdas A/vacía/vacía/B producen `A | | | B`;
tres vacías producen `| |` después de trim. Las coordenadas de celda y raw se conservan.
Las cuatro expectativas nuevas se escriben a mano, sin sustituir salidas anteriores.

La validación canónica exige que el span de cada padre contenga el de cada hijo.
La existencia de referencias y la ausencia de ciclos no bastan. Se comprueba en
la frontera canónica; no se impone esta representación final a documentos F3/F4.
Se rechaza con `OUTPUT_INVARIANT_FAILED`, sin reparar un documento ya canónico.

La corrección altera texto: reglas 1.0.1, según §27.2. No cambia esquema 1.0.0,
perfil `linkedin_jobs_aggressive_v1`, paquete 0.1.0 ni tablas Unicode/emoji.
Los resultados de reglas anteriores requieren reprocesar raw. La política
predeterminada y su schema se actualizan explícitamente; el catálogo registra
el hash de esos bytes y de los fixtures redactados, nunca de salidas generadas.
Los informes históricos F1–F6 conservan sus versiones y evidencias originales.

## Observabilidad y privacidad

`operations.measure_field` y `measure_record` envuelven la API pública. La captura
se limita al contexto de la llamada mediante ContextVar y se restaura en finally.
Sin captura, las etapas se ejecutan directamente. Los contadores y tiempos quedan
fuera del resultado canónico y no afectan sus IDs ni su serialización.

Los errores tipados se representan como código en Measurement, con result=None;
la API original conserva su contrato de excepciones. En registros no estrictos
se conservan los seis sobres y los fallos por campo. Los errores inesperados se
propagan. No se añaden logs, callbacks de terceros, red ni persistencia.

Solo `metrics` se exporta a observabilidad. No contiene raw, source_ref, mensajes,
URLs ni payloads. La versión del scraper se agrupa por SHA-256 porque es entrada
libre del llamador. `trace=True` permite acceso explícito a documentos intermedios
en memoria: contiene datos privados y no debe exportarse como métricas. La ingesta
controla autorización, retención y acceso. Por defecto no se guardan snapshots.

## Medición y aceptación

El banco de carga de desarrollo ejecuta cada escenario en un proceso separado,
con timeout del proceso y terminación si se excede. Publica cold start, warmup,
repeticiones, percentiles nearest-rank, variabilidad, throughput, costes de etapa,
memoria Python y RSS, entorno/manifiesto/lock y hashes de entradas.

Memoria y cProfile usan pasadas separadas, para no mezclar su sobrecoste con latencia.
El RSS es máximo vital del proceso e incluye inicialización y la pasada de memoria;
no equivale a bytes incrementales por registro. Los escenarios representativos
son sintéticos y se separan de adversariales. No se agregan en una mezcla que
pretenda representar tráfico sin conocer su distribución.

La comparación exige un umbral explícito y entorno/protocolo/entradas comparables.
No se imponen tests temporales en CI compartida. Aprobar SLO/capacidad requiere
entorno, volumen y distribución de ingesta; no se inventa ese acuerdo a partir de
una muestra local. Límites de entrada/regex no sustituyen watchdog y memoria de
un worker de producción. No se introduce un servicio ni paralelismo en el núcleo.
