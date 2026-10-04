# Aceptación de biblioteca por lotes y preparación de distribución

Decisiones del mantenedor: 2026-10-03. Verificación: 2026-10-04.
Responsable: Anthony Josue Rojas Fuentes. Destino: GitHub, licencia MIT.
Paquete candidato 0.1.0, esquema 1.0.0, reglas 1.0.1.

## Alcance y criterios adoptados

F7 mide una biblioteca local que se incorpora antes del parsing en otros proyectos.
No establece un SLO universal para computadoras de capacidades distintas. El coste
del parser robusto que cada proyecto añada queda fuera de estos objetivos. Por
encargo del mantenedor, se adopta esta referencia por lotes:

- **100.000 ofertas en 6 horas con cuatro procesos** en el equipo de referencia,
  usando la mezcla uniforme de los 20 casos aportados. Equivale a 4,63 registros/s.
- Referencia alternativa de un proceso: **100.000 ofertas en 16 horas**, para no
  exigir paralelismo en el núcleo. Cada consumidor mide de nuevo en su dispositivo.
- Cero fallos de normalización y cero pérdidas de los fragmentos manuales comprobados
  en este corpus; misma salida por oferta y orden determinista entre 1/2/4 procesos.
- Umbral de investigación: degradación >25 % respecto de una baseline comparable,
  sin tolerar nuevos fallos o pérdida de evidencia. Repetir mediciones para separar
  regresión de ruido antes de aceptar cambios. No imponer tiempos en CI compartida.
- Presupuesto inicial recomendado para ensayos del consumidor: 256 MiB por proceso,
  más memoria del coordinador y de su propio parser. No es un límite implantado por
  la biblioteca ni se deduce de sumar el tamaño de strings. Controlar cola y fuentes.

Se mantiene el perfil y sus límites documentados; una oferta de 45.428 caracteres
con pseudoformatos no se rechaza por ser compleja. Entradas que excedan presupuestos
siguen fallando explícitamente. Los casos estructurales máximos patológicos se
reportan aparte; no se promete procesar 100.000 HTML de 20.000 nodos en ese plazo.

## Corpus y adaptación

Los 20 JSON se conservan sin modificación. Cada reporte registra hashes de bytes.
Las variantes 18/20 comparten plantilla: son diversidad sintética de dominios, no
observaciones independientes de tráfico ni validación ciega. El manifiesto con
canonical_title/salary/modality se mantiene fuera de la normalización/evaluación
de texto; resolver esas etiquetas pertenece al parsing posterior.

Se declaran strings plain_text; title/description/type/location se mapean sin
reinterpretación. criteria_list se une con LF en un campo y conserva sus diez
elementos originales en el sobre de ingesta. modality permanece en el sidecar;
seniority es missing. Por ello los 20 registros son partial esperados, aunque
sus 100 campos presentes se normalicen correctamente. No equiparar ese estado
con errores o rechazos.

Expectativas de evidencia escritas a mano: negaciones, importes y contexto de
salarios/decoys seleccionados; además fuente intacta, spans válidos y reentrada.
No se fabrican textos esperados copiando salida, ni se afirma que estas anclas
constituyan un parser semántico completo o demuestren preservación universal.

## Correcciones de coste

El primer diagnóstico aisló búsquedas de pictogramas sobre ASCII; ahora se acotan
a runs no ASCII con offsets globales. El texto plano máximo de 262.144 caracteres
ASCII se normaliza sin agotar ese presupuesto. Controles y listas ASCII siguen
procesándose. Pruebas diferenciales comparan matches completos con segmentados.

La primera carga con cuatro procesos detectó además timeouts en render.nfc sobre
la muestra 01. El renderer ahora enumera grafemas por líneas, donde LF ya convertido
es una frontera segura. Se conserva la misma composición NFC y procedencia, sin
subir 50 ms ni ocultar errores con reintentos. La prueba posterior sustituye las
mediciones preliminares que contenían fallos; estas no cuentan como aceptación.

## Reproducir

```bash
uv sync --locked
uv run --locked pytest
uv run --locked python -m benchmarks.batch --workers 1 2 4 --rounds 5 \
  --output /tmp/normietext-batch-20-final.json
uv run --locked python scripts/build_distribution.py
uv run --locked twine check --strict dist/*.whl dist/*.tar.gz
uv run --locked python scripts/check_wheel.py
```

Cinco vueltas por configuración: 100 registros medidos por nivel de concurrencia,
300 procesamientos en total, pero solo 20 ofertas distintas. Los tiempos para 100.000
son extrapolaciones explícitas, no una ejecución de ese lote completo. El tiempo
total incluye arranque, coordinación, verificaciones de evidencia y serialización
de firmas; el corpus pequeño se conserva en una caché local de ingesta por proceso.

## Resultados verificados

Equipo visible: AMD Ryzen 5 5600X, seis núcleos físicos y 12 CPU lógicas; afinidad 12,
Linux x86_64, CPython 3.14.7 con GIL. RAM total visible 30,28 GiB; disponible en el
snapshot 6,12 GiB; swap 8 GiB. No se detectaron límites cgroup en las rutas consultadas;
esto no demuestra ausencia de otras restricciones del host. El JSON conserva
los bytes exactos, SO, runtime, dependencias, huella de código y hash de lock.

| Procesos | Registros/s | p50 s | p95 s | p99 s | RSS máximo MiB | Horas estimadas /100.000 | Fallos |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2.871 | 0.225 | 0.373 | 2.399 | 69.32 | 9.68 | 0 |
| 2 | 5.556 | 0.222 | 0.375 | 2.233 | 69.32 | 5.00 | 0 |
| 4 | 9.793 | 0.241 | 0.391 | 2.440 | 69.32 | 2.84 | 0 |

[Informe de lotes](lotes_20_resultados.json): cero fallos de campo, spans o anclas
manuales; replay idéntico dentro y entre configuraciones. El archivo archivado
conserva 20 observaciones por configuración; los agregados usan las 100. Incluye el
hash del informe completo reproducible de 300 observaciones. Los percentiles son
descriptivos sobre esta muestra repetida, no estimadores garantizados de tráfico.

El objetivo de referencia de 6 h con cuatro procesos tiene margen frente a la
extrapolación 2,84 h; el de 16 h con un proceso frente a 9,68 h. No se declara una ejecución
real de 100.000 ofertas. El RSS es máximo vital del proceso, no memoria incremental
por registro, y puede incluir inicialización previa del proceso/exec.

Validación: **455 tests aprobados**, sin skips; Ruff lint/formato (70 archivos),
mypy (40 fuentes), tablas offline, [calidad](calidad_biblioteca.json), build stamped,
Twine y wheel instalado aprobados. Calidad conserva los mismos resultados que F7;
solo cambia el manifiesto por la optimización. No se modifican goldens anteriores.

[Adopción local](adopcion_local.json): shadow_equal=true y replay_equal=true en
la secuencia candidata→anterior→candidata, con los 20 originales. El snapshot
anterior no es una release pública. La prueba confirma contenido y evidencia
iguales en el consumidor de demostración, no exactitud semántica universal.

Wheel candidato verificado SHA-256:
`c935df7cb184abb0a0c83760aef0d02660831d903328bbb3f46609d7edae802a`.

## Distribución F8 y aprobación

La candidata incluye guía de instalación desde GitHub, changelog, matriz de CI,
checksums, prueba de consumidor aislado y rollback desde fuentes originales.
GitHub Releases recibe los artefactos que CI verificó; PyPI es opcional y no bloquea
el destino seleccionado. MIT ya identifica al mantenedor en LICENSE.

La prueba de adopción usa un consumidor mínimo y los 20 originales, con instalación
candidata→snapshot anterior→candidata en un entorno externo al checkout. Compara
texto, estructura, fuentes y señales con offsets, excluyendo solo el manifiesto
de la firma de contenido. Es una integración sintética, no un proyecto consumidor
real ni una release anterior pública. El resultado se adjunta como evidencia local.

**Pendiente externo para completar F8:** aprobación final del mantenedor, commit/tag
identificados, matriz GitHub Actions aprobada, publicación de Release y comprobación
de descarga/instalación de sus assets. La preparación local no acredita esos pasos.
No se realizó push ni publicación. No hay CLI gh ni actionlint disponible localmente;
el workflow se revisó y sus scripts se probaron, pero no se declara validación remota.
