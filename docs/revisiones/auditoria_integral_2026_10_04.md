# Auditoría integral de normietext — 2026-10-04

> Fe de erratas (2026-10-06): se corrigió el nombre de la proyección solo texto a
> `clean_text` en RF-14 y en la explicación de API. Los resultados de la auditoría
> conservan su fecha y alcance originales.

## Dictamen y alcance

El núcleo funcional de la biblioteca está implementado y supera la suite disponible.
No se encontró un nuevo incumplimiento funcional reproducible en esta revisión.
Esto acredita los contratos, casos y propiedades comprobados; no demuestra ausencia
universal de defectos ni permite declarar F8 terminada. La distribución pública y
la validación nativa de Windows sobre la corrección local siguen pendientes.

Se contrastaron la especificación 2.0 completa, el plan, las decisiones ADR-0001 a
ADR-0008, los informes de cierre y las guías de uso con el pipeline, modelos,
procedencia, validación, serialización, tablas, consumidores de evaluación,
benchmarks, scripts de distribución y workflows. Se ejecutaron nuevamente las
pruebas, calidad, construcción, instalación aislada y adopción. Se añadieron sondas
temporales de composición HTML sin convertir sus salidas en expectativas del corpus.
No se modificaron reglas, fixtures, goldens ni la especificación.

Base Git: `98c47785b6955b8136d2096e71cd711fa46f0508`, con cambios locales previos
en benchmarks, pruebas y documentación. La corrección de mypy para Windows todavía
no forma parte de ese commit. Paquete **0.1.0**, esquema **1.0.0**, reglas **1.0.1**,
perfil **linkedin_jobs_aggressive_v1**. El número 2.0 corresponde a la especificación.
La metadata del paquete declara estado Alpha.

La evidencia compacta de esta revisión se conserva en
[auditoria_integral_2026_10_04.json](auditoria_integral_2026_10_04.json).
Los informes históricos conservan sus cifras y hashes: no se atribuyen sus artefactos
a esta nueva construcción del árbol modificado.

## Hallazgos y pendientes, por prioridad

1. **P1 — Puerta remota de release abierta.** El CI del commit publicado falla en
   Windows durante mypy; Ubuntu y macOS pasan sus comprobaciones. El job de
   distribución quedó omitido. La corrección local pasa mypy para los tres destinos,
   pero esa simulación de tipos no ejecuta Python en Windows. Hace falta integrar
   la corrección y obtener una matriz remota completa aprobada antes de cerrar F8.
   [Ejecución comprobada](https://github.com/ajrojasfuentes/normietext/actions/runs/37236852002).
2. **P1 — Publicación y consumo del artefacto remoto sin acreditar.** La consulta a
   GitHub no devolvió Releases. Construir e instalar localmente no prueba la descarga
   de assets publicados. Faltan el tag/revisión definitivos, Release, checksums e
   instalación desde esos assets. PyPI es opcional según ADR-0008.
3. **P2 — Alcance de la evidencia de calidad.** §§24.1 y 25.2 contemplan muestras
   reales y distribución representativa. La aceptación posterior de biblioteca usa
   explícitamente muestras sintéticas: permite avanzar con una aceptación acotada,
   pero no satisface una afirmación de validación sobre tráfico real. Los consumidores
   F6 son demostraciones conservadoras; no equivalen al parser robusto de un proyecto
   externo. Mantener esta limitación visible en cualquier anuncio de release.
4. **P2 — Observabilidad con menor granularidad que §25.1.** `_field_metrics`
   expone operaciones por regla, hints, reparaciones, longitudes, estados e incidencias.
   No expone directamente invisibles separados por clase Unicode, porcentaje de
   emoji eliminados con su denominador ni candidatos no clasificados. El contador
   `removals` cuenta operaciones de dos reglas, no caracteres. La instrumentación
   operativa existe, pero esa lista de métricas de la especificación no está cubierta
   literalmente en su totalidad; falta acordar denominadores y añadir esos agregados
   si se mantiene ese contrato de observabilidad.
5. **P3 — Comando local de Twine no repetible después de checksums, corregido.**
   `twine check --strict dist/*` falla con `InvalidDistribution` al encontrar
   `dist/SHA256SUMS`. Se reprodujo el fallo y se ajustó la guía para pasar únicamente
   `dist/*.whl dist/*.tar.gz`; esos artefactos superan Twine. El workflow CI construye
   en un checkout limpio y genera checksums después, por lo que este hallazgo no
   explica el fallo remoto de mypy.

No se realizó commit, push, creación de tag ni publicación durante esta auditoría.

## Estado de las fases

| Fase | Estado comprobado | Frontera de aceptación |
|---|---|---|
| F0 | Entorno, lock, tipos, lint y empaquetado operativos | Portabilidad nativa depende de la matriz CI |
| F1 | Contratos inmutables, seis sobres y corpus normativo ejecutable | No confundir esquemas con ejecución de reglas |
| F2 | Fuente, recuperación, alineación, IDs, manifiesto y JSON canónico | Durabilidad de SourceStore pertenece al integrador |
| F3 | Conversión explícita de los tres formatos y estructura HTML | HTML conserva precisión field; no inventa offsets raw |
| F4 | Reparación y reconocimiento léxico implementados | Sus documentos intermedios no son canónicos |
| F5 | Renderer y API funcional aprobados por regresión y propiedades | Reentrada tipada; no idempotencia de strings reenviados como raw |
| F6 | Evaluación sintética, consumidores y ablaciones aprobados | Sin validación ciega ni tráfico real |
| F7 | Límites, métricas básicas, adversariales y lotes medidos | Objetivo ligado al equipo/corpus; granularidad de §25.1 pendiente |
| F8 | Build, instalación, replay y rollback locales aprobados | CI completa, Release y verificación de assets pendientes |

## Contraste de los requisitos funcionales

“Verificado” significa implementación inspeccionada y pruebas aprobadas dentro del
alcance del corpus. Los requisitos no se consideran demostrados para toda entrada
posible por el mero hecho de pasar tests.

| Requisito | Implementación principal | Evidencia y observación |
|---|---|---|
| RF-01: str y campos reconocidos | models.py, validation.py | test_models, test_api; rechaza bytes, None, campos desconocidos y Unicode inválido |
| RF-02: formato declarado | adapters/ | test_adapters, adapter_replay; plain_text, html_escaped_text y html_fragment, sin autodetección |
| RF-03: fuente y procedencia | sources.py, provenance.py, models.py | test_sources, test_provenance, propiedades; raw/hash, recuperación y degradación conservadora |
| RF-04: estructura HTML | adapters/html_fragment.py | 30 fixtures de adaptación, casos canónicos y sondas adicionales; listas, tablas, asociaciones y anotaciones |
| RF-05: mojibake | stages/encoding.py | test_encoding y fixtures léxicos; ftfy configurado y unidades delimitadas |
| RF-06: NFC/UTF-8 | rendering.py, validation.py | propiedades Unicode, regresión T09/T36 y replay; spans sobre texto final |
| RF-07: invisibles | stages/lexing.py, stages/symbols.py, tablas | test_lexing, test_tables, regresiones; captura de secuencias antes de borrar |
| RF-08: emoji no permitidos | stages/lexing.py, stages/symbols.py | secuencias completas, ZWJ, variantes, keycaps y exclusiones técnicas |
| RF-09: tokens y anotaciones | stages/symbols.py, stages/rendering.py | banderas, subdivisiones y hints; distingue tokens generados de texto literal |
| RF-10: listas | stages/structure.py, stages/rendering.py | 39 negativos obligatorios sin falsos positivos; conserva ordinales y relaciones |
| RF-11: espacios/LF | rendering.py y renderer final | corpus, propiedades e invariantes; campos compactos sin LF y multilínea acotado |
| RF-12: evidencia | protecciones léxicas y renderer | C++, C#, importes, negaciones, URLs y anclas integrales; no transforma señales en hechos |
| RF-13: ediciones/estados | models.py, provenance.py, operations.py | reglas/orígenes, issues, empty/partial/failure; errores explícitos sin truncamiento silencioso |
| RF-14: API | api.py | normalize_field, normalize_record y clean_text; strict propaga fallos |
| RF-15: idempotencia/determinismo | api.py, validation.py, serialization.py, manifest.py | propiedades y replay en procesos, registros y wheel aislado; mismo entorno/perfil |

Los nombres de módulos son relativos a `src/normietext/`; las pruebas unitarias
citadas están en `tests/unit/`. La organización ilustrativa de §22 se materializó
con algunas responsabilidades agrupadas, según ADR-0005. La ausencia de un archivo
por cada nombre de esa ilustración no representa una funcionalidad faltante.

## Capacidades efectivas y decisiones de diseño

### Biblioteca y API

Es una biblioteca Python local, síncrona y sin red ni LLM en la normalización.
Los seis campos son job_title, job_description, job_criteria_list, job_type,
seniority y raw_location. Título, tipo, seniority y ubicación son compactos;
descripción y criterios admiten estructura multilínea. Cada campo conserva su
estado de extracción; una ausencia no se convierte en texto vacío exitoso.

El recorrido es conversión → reparación → captura léxica/estructural → aplicación
de reglas/render → validación. Los modelos de cada fase evitan interpretar de nuevo
HTML o reparar dos veces. `canonicalize` acepta documentos tipados y valida su
compatibilidad; no es una función para declarar normalizado cualquier string.
`clean_text` es una proyección conveniente que descarta los metadatos del resultado.
Quien necesite parsing auditable debe consumir `NormalizedField`.

La API de registro captura errores por campo y conserva los seis sobres; `strict`
los propaga. No proporciona un scheduler, servicio HTTP ni executor público de lotes.
El host puede procesar registros independientes con concurrencia acotada. La
infraestructura de `benchmarks/` demuestra esa integración y está fuera del wheel.

### Texto, estructura y precisión

HTML y entidades se convierten una sola vez. Se preservan las relaciones soportadas
de listas, tablas y definiciones, y representaciones de enlaces, tachado, alt y
super/subíndices. No se reconstruye el diseño visual de una página ni se ejecutan
scripts. Markdown/pseudoformatos recibidos como texto no activan otro parser.

Se conserva NFC sin aplicar NFKC global, casefold, traducción o corrección ortográfica.
El perfil agresivo elimina controles e invisibles definidos y puede perder
distinciones lingüísticas asociadas a joiners o dirección de escritura. Es una
decisión explícita, no una garantía de fidelidad multilingüe absoluta.

Los hints pertenecen a una tabla finita; no expresan modalidad, salario, seniority
ni ubicación resueltos. Kaomoji también usa un inventario acotado. Las protecciones
técnicas conservan evidencia pero no equivalen a congelar cada byte: transformaciones
globales aplicables pueden generar `PROTECTED_SPAN_MODIFIED`.

HTML usa precisión `field` porque el backend no demuestra intervalos exactos en el
raw. Texto copiado puede usar `exact`; reparaciones y composiciones conservan o
reducen precisión según la evidencia. La alineación local usada para tokens no
reconstruye offsets raw inexistentes. Los spans finales cuentan codepoints de Python,
no bytes UTF-8 ni posiciones UTF-16 de JavaScript.

### Recuperación, determinismo y versionado

Los resultados retienen fuente, hashes, ediciones, bloques, anotaciones e incidencias.
La persistencia externa ocurre en ingesta mediante SourceStore; el pipeline no llama
a ese almacén. Una referencia o un hash aislados no garantizan recuperación futura.

El manifiesto separa software, esquema, reglas, perfil, tablas, runtime y dependencias.
El replay byte a byte se garantiza dentro del entorno identificado, no entre
manifiestos de sistemas diferentes. Las huellas de archivos instalados no son
hashes de wheel; los recibos de artefactos requieren archivos reales suministrados
por quien instala. La serialización es explícita y canónica; no incluye una API
general de deserialización/reconstrucción de modelos.

Solo se ofrece el perfil implementado. Los límites admiten configuración validada;
no todas las opciones de comportamiento pueden cambiarse libremente. Una política
arbitraria exige diseño, versión de reglas y pruebas nuevas.

### Compatibilidad y distribución open source

`requires-python` es `>=3.14,<3.15`; la baseline probada es CPython 3.14.7.
No se promete Python 3.13, 3.15, PyPy ni cualquier arquitectura. El wheel del proyecto
es puro Python, pero lxml y regex tienen componentes nativos: su disponibilidad
importa al instalar en otros dispositivos. Las cinco dependencias directas están
fijadas exactamente; esto favorece reproducibilidad y puede exigir resolver
conflictos con dependencias de una aplicación anfitriona.

El paquete incorpora MIT, datos y avisos de licencia de tablas, `py.typed` y metadata.
Evaluación, benchmarks y pruebas no forman parte del wheel de consumo. El stamping
permite conocer revisión y huella sin exigir `.git` al consumidor. El proyecto no
instala servicios ni requiere infraestructura SaaS. Actualizar dependencias o tablas
requiere volver a validar comportamiento, no solo cambiar versiones.

## Validación ejecutada

| Comprobación | Resultado |
|---|---|
| uv sync --locked | Correcto |
| Ruff lint y formato | Correctos |
| mypy para win32, darwin y linux | Correcto en los tres destinos; 40 fuentes |
| pytest completo | **458 aprobados, 0 fallos, 0 errores, 0 skips; 47,873 s** |
| generate_tables.py --check | Correcto; no se regeneraron tablas ni goldens |
| evaluation.quality | passed=true, sin fallos |
| build_distribution.py | sdist y wheel construidos con stamping |
| Twine, wheel y sdist explícitos | Ambos aprobados |
| check_wheel.py | Instalación e importación aisladas, datos, fases, API y reentrada aprobados |
| check_adoption.py | candidate → rollback → candidate; shadow_equal y replay_equal verdaderos |
| benchmarks.load | 12 escenarios medidos; 11 correctos y un rechazo de profundidad esperado |
| Sondas adicionales HTML | 111 combinaciones, sin excepciones ni spans inválidos; raw y reentrada conservados |

Distribución de pytest: 308 casos unitarios, 130 de regresión, 14 de propiedades y
6 de integración. Los 14 tests de propiedades generan múltiples ejemplos; no se
equiparan a 14 entradas ni se inventa un total de ejemplos Hypothesis.

Inventario: 49 casos normativos cubren T01–T40; 19 suplementarios, 30 de adaptación,
23 léxicos, 60 canónicos y 55 de calidad, además de los fixtures integral y de
registro. Son capas con solapamiento, no muestras independientes sumables. Los 49
normativos y 19 suplementarios declaran `verified_f5` y se ejecutan; no quedan
ocultos mediante skips como `awaiting_normalizer`.

Calidad: 104 líneas etiquetadas, 30 verdaderos positivos, 69 verdaderos negativos,
5 abstenciones, 0 falsos positivos y 0 falsos negativos. Precisión y recall observados
100 %, cobertura 28,846 % y abstención 4,808 % según los denominadores del evaluador.
Los 39 negativos obligatorios pasan. Se conservan 52 fragmentos requeridos del
corpus de calidad y 58 del integral, que cubren 23 grupos; se contabilizan 10 y 15
pérdidas autorizadas, respectivamente. Hay 13 ablaciones. Estos resultados superan
la puerta de precisión observada 99,5 %, sin demostrar esa precisión poblacional.

Las 20 ofertas adversariales son sintéticas; 18 comparten plantilla. Su adaptación
deja seniority como missing y modality en un sidecar. Por eso los registros partial
son esperados y no equivalen a fallos de normalización. El consumidor de rollback
compara contenido y evidencia excluyendo el manifiesto de esa firma; el snapshot
anterior es de desarrollo, no una release pública anterior.

## Operación, rendimiento y límites

Equipo medido: Linux x86_64, AMD Ryzen 5 5600X, 12 CPU lógicas visibles, CPython
3.14.7. RAM total visible 30,28 GiB; disponible al iniciar carga aproximadamente
5,79 GiB. Estos recursos describen esta medición, no requisitos mínimos del paquete.

La referencia aprobada en [aceptación de biblioteca](aceptacion_biblioteca.md) es
100.000 ofertas en 6 horas con cuatro procesos, o 16 horas con uno. Son objetivos
para esa mezcla y equipo. **No está acreditado un lote de 100.000 ofertas en dos
horas**, ni se ha ejecutado un lote completo de 100.000 entradas distintas.

Se repitió el protocolo comparable de cinco rondas: 100 procesamientos por nivel
de concurrencia, 300 en total y 20 ofertas distintas. Incluye arranque, coordinación,
serialización y comprobaciones; no es tiempo exclusivo del núcleo.

| Procesos | Ofertas/s | Horas extrapoladas /100.000 | Cambio de throughput frente a baseline | Fallos |
|---:|---:|---:|---:|---:|
| 1 | 2,798 | 9,93 | −2,55 % | 0 |
| 2 | 5,354 | 5,19 | −3,62 % | 0 |
| 4 | 9,417 | 2,95 | −3,84 % | 0 |

Replay idéntico dentro de cada configuración y entre configuraciones. RSS máximo
vital observado: 69,05 MiB por proceso reportado. Se cumplen las referencias de
6/16 horas por extrapolación; ninguna diferencia supera el umbral de investigación
de degradación del 25 %. Estas cifras no incluyen un parser externo ni garantizan
escalamiento lineal al aumentar workers.

La carga usa una vuelta de calentamiento y tres repeticiones por escenario; sus
percentiles son descriptivos. Resultados representativos de tiempo medio por unidad:

| Escenario | Segundos | RSS máximo vital MiB | Resultado |
|---|---:|---:|---|
| Registro sintético de seis campos | 0,0544 | 48,9 | Correcto |
| Descripción integral | 0,2334 | 49,6 | Correcto |
| Texto plano máximo | 0,8059 | 57,0 | Correcto |
| 2.000 hints | 1,6634 | 58,5 | Correcto |
| HTML próximo al límite de nodos | 17,9810 | 109,5 | Correcto, coste adversarial considerable |
| HTML con profundidad excesiva | 0,0008 | 42,9 | RESOURCE_LIMIT_EXCEEDED esperado |

El límite de regex de 50 ms es por operación; no es un deadline total por campo. La biblioteca
no impone un límite universal de RAM. El benchmark puede aislar workers con timeout
y, en Linux, RLIMIT_AS. RSS no disponible en Windows se registra como null.
El integrador debe acotar colas y concurrencia y dimensionar también su propio parser.
El RSS reportado no es memoria incremental por oferta ni memoria total del pool.

Los límites por defecto en codepoints son: título/ubicación 8.192 cada uno,
descripción 262.144, criterios 32.768, tipo/seniority 4.096 cada uno; registro 327.680.
HTML admite hasta 20.000 nodos y profundidad 128; la expansión se controla con
factor 32 y suelo 1.024. Las entradas que exceden presupuesto fallan explícitamente;
no se truncan. Una entrada aceptada puede seguir siendo costosa, como muestra HTML.

## Acciones para cerrar lo pendiente

1. Integrar la corrección de portabilidad y obtener CI verde en los tres sistemas.
2. Seleccionar la revisión definitiva, construirla limpia y asociar sus hashes al tag.
3. Publicar los artefactos verificados en GitHub y probar descarga, checksum e
   instalación externa desde la Release. Mantener separado el ensayo local de rollback.
4. En cada proyecto consumidor, medir con su hardware, mezcla de formatos, volúmenes
   y parser. Ampliar expectativas manuales con muestras autorizadas y casos distintos
   de la plantilla sintética antes de formular garantías de calidad más amplias.
5. Completar las métricas específicas de §25.1, con denominadores documentados y
   pruebas, o aprobar explícitamente una concreción normativa de su alcance.

No hace falta convertir la biblioteca en un servicio ni añadir parsing semántico
para completar estas tareas. El trabajo pendiente pertenece principalmente a
distribución, validación de entornos y ampliación de evidencia de adopción.

## Reproducción y artefactos

Desde la raíz del repositorio, con el entorno fijado:

```bash
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy --platform win32
uv run --locked mypy --platform darwin
uv run --locked mypy --platform linux
uv run --locked pytest --junitxml=/tmp/normietext-auditoria-pytest.xml
uv run --locked python scripts/generate_tables.py --check
uv run --locked python -m evaluation.quality --output /tmp/normietext-auditoria-calidad.json
uv run --locked python scripts/build_distribution.py
uv run --locked twine check --strict dist/*.whl dist/*.tar.gz
uv run --locked python scripts/check_wheel.py
uv run --locked python scripts/release_assets.py dist
uv run --locked python -m benchmarks.load --warmup 1 --repetitions 3 \
  --output /tmp/normietext-auditoria-carga.json
uv run --locked python -m benchmarks.batch --workers 1 2 4 --rounds 5 \
  --output /tmp/normietext-auditoria-lotes-comparables.json
```

La adopción se ejecutó con `scripts/check_adoption.py`, pasando `--candidate`
al wheel recién construido y `--rollback` al snapshot local conservado en
`/tmp/normietext-rollback/normietext-0.1.0-py3-none-any.whl`. Para repetirla en otra
máquina se necesitan ambos artefactos; sus hashes están archivados en el JSON.
El código de las 111 sondas también se conserva dentro del JSON, separado de los
fixtures aprobados. No se midió cobertura de líneas/ramas, por lo que no se publica
un porcentaje de cobertura ni se deduce uno de los 458 tests.

| Artefacto construido durante la auditoría | SHA-256 |
|---|---|
| normietext-0.1.0-py3-none-any.whl | `8dcacd1955367ac7b86dd4b8d3c4f05c6877d00ebaa55319abfa75d131c569e7` |
| normietext-0.1.0.tar.gz | `3c6e7abd7c1d675dbee97e5f78953420a7d497c0104052408bec0a71c0b3323b` |

El stamping incluye `+tree:` porque existen cambios locales. La huella del núcleo
es `9f7a4c5c3a1a802214d869d1a068fe2c45b5efc8bcdbd2d3a3022689b909e371`.
Estos bytes no son los artefactos históricos construidos desde el commit limpio,
ni una release pública. Los informes completos temporales tienen sus hashes
registrados en el JSON; el archivo permanente conserva métricas seleccionadas,
manifiestos, protocolo e inventario del wheel, sin depender de su permanencia en /tmp.
