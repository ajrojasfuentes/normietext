# Fase 7 — Implementación local y puerta operativa

Fecha: 2026-10-02. Base de trabajo: `c8c1a2b`, checkout `main`, sin commit ni
publicación de estos cambios. Paquete 0.1.0, especificación 2.0, esquema 1.0.0,
reglas 1.0.1, perfil `linkedin_jobs_aggressive_v1`.

**Estado:** implementación local de F7. La puerta de aceptación de producción
permanece abierta: no se han proporcionado entorno objetivo, volumen/distribución
de ingesta ni un SLO aprobado. F8 sigue pendiente. No se presenta una muestra
sintética como prueba de capacidad o calidad universal.

## Correcciones previas a la carga

1. Celdas vacías consecutivas: cada límite DOM contribuye un separador aunque
   varias inserciones compartan posición. `A/vacía/vacía/B` produce `A | | | B`;
   tres vacías, `| |`. Expectativas manuales para cuatro variantes, más pruebas
   de spans de contenido, coordenadas, fuente original y reentrada canónica.
2. Contención padre/hijo: la validación canónica rechaza spans de padres que no
   contienen los hijos, con `OUTPUT_INVARIANT_FAILED`. Tres expectativas manuales
   cubren padre vacío, comienzo incorrecto y final incorrecto. Se mantiene
   separación de representaciones F3/F4 y F5.

ADR-0007 registra el incremento explícito de reglas y la actualización del
apéndice A. Los raw/expected anteriores y los bytes del integral no cambian.
El catálogo cambia solo los hashes de los cuatro fixtures añadidos al archivo
canónico y de la política predeterminada versionada. No se regeneraron goldens
ni tablas a partir de la salida del normalizador. F1–F6 conservan sus informes
históricos; README, API, análisis de inicialización, plan, AGENTS, docstring de
stages y clasificación Alpha reflejan el estado vigente.

## Trazabilidad de F7

| Puerta | Implementación y evidencia |
|---|---|
| Bordes por campo | límite−1/límite/límite+1 de los seis campos; rechazo antes de proyección |
| Agregado | 327.679/327.680/327.681, ampliando solo el presupuesto validado de descripción; conserva 319.488 predeterminado |
| HTML | nodos 19.999/20.000/20.001 (incluye wrappers), profundidad 127/128/129 |
| Expansión | floor y factor 32 en ambos bordes; 2.000 hints y desbordamiento del pipeline tipado sin publicación parcial |
| Regex | timeout inyectado con presupuestos 49/50/51 ms en léxico/renderer, errores tipados, registro partial y strict |
| Seguridad | sockets/subprocesos/navegación bloqueados; entidades externas y código/script no ejecutados; raw preservado |
| Observabilidad | metrics inmutables sin contenido, contadores segmentados y tiempos por etapa; trace optativo separado |
| Concurrencia | normalizadores con políticas independientes, orden y bytes iguales en llamadas secuenciales/concurrentes |
| Carga | 12 escenarios, cohortes separados, campo y registro, entorno efectivo, tamaños y variabilidad |
| Aislamiento | procesos separados, timeout y límite virtual Linux explícito; no se altera el núcleo |
| Regresión de rendimiento | comparador con protocolo/entorno/entradas verificables y umbral explícito; sin tests temporales en CI compartida |
| SLO/capacidad | mediciones locales y procedimiento de aprobación; falta acuerdo del entorno/carga de producción |

La profundidad/nodos se prueban con contratos reales del backend. El timeout
inyectado acredita conversión y propagación del fallo, no una duración exacta
bajo carga. El máximo de entrada no promete normalización exitosa si otro límite
operativo se alcanza: el informe distingue éxitos, errores tipados y fallos externos.

## Protocolo de carga local

CPU AMD Ryzen 5 5600X, 12 CPU lógicas, Linux x86_64 y CPython 3.14.7 con GIL.
El JSON conserva versiones completas, fingerprints y hash del lock. Dos warmups
además de la llamada fría y cinco muestras medidas por escenario. Percentiles
nearest-rank: con cinco muestras, p95/p99 coinciden con el máximo; son descriptivos.
Procesos secuenciales separados, timeout 300 s por escenario y RLIMIT_AS 512 MiB.
Esos límites contienen este experimento y **no son un SLO aprobado por registro**.

```bash
uv run --locked python -m benchmarks.load --output /tmp/normietext-f7-load.json \
  --warmup 2 --repetitions 5 --worker-timeout 300 --worker-memory-mib 512
```

Una exploración previa con warmup 1/repeticiones 3, tracemalloc y cProfile agotó
120s en el escenario de nodos. Por eso estas herramientas son optativas y sus
pasadas no forman parte de la baseline de latencia. El perfil reducido de 1.000
`br` mostró gasto en validación de modelos, renderizado y composición de
procedencia. No se cambiaron backend, GIL ni políticas para ocultar ese coste.

Baseline: [fase_7_carga.json](fase_7_carga.json), con entorno/manifiesto y costes
por etapa. Los 12 workers terminaron; 10 escenarios tuvieron éxito y dos
registraron rechazos operativos tipados. No se produjo salida parcial.

| Escenario | Unidad | p50 ms | p95/p99 ms | Éxitos/s | Pico RSS MiB | Resultado (5 muestras) |
|---|---|---:|---:|---:|---:|---|
| six_fields | record | 60.09 | 66.75 | 16.118 | 48.95 | {'success': 5} |
| integral | field | 263.59 | 305.29 | 3.681 | 49.59 | {'success': 5} |
| compact | field | 13.54 | 14.08 | 76.702 | 48.57 | {'success': 5} |
| escaped | field | 11.02 | 11.19 | 90.959 | 48.56 | {'success': 5} |
| html | field | 18.72 | 19.69 | 53.040 | 48.94 | {'success': 5} |
| max_plain | field | 412.60 | 417.37 | 0.000 | 48.56 | {'REGEX_TIMEOUT': 5} |
| combining | field | 891.86 | 903.46 | 1.160 | 53.99 | {'success': 5} |
| hints_2000 | field | 2010.99 | 2043.30 | 0.501 | 58.30 | {'success': 5} |
| url_near_miss | field | 69.78 | 70.04 | 14.356 | 49.06 | {'success': 5} |
| html_depth | field | 312.67 | 319.14 | 3.223 | 49.23 | {'success': 5} |
| html_nodes | field | 19502.64 | 20355.44 | 0.052 | 111.56 | {'success': 5} |
| html_depth_rejected | field | 0.81 | 0.96 | 0.000 | 42.79 | {'RESOURCE_LIMIT_EXCEEDED': 5} |

El escenario max_plain es una secuencia de 262.144 letras sin separación: acepta
el presupuesto de entrada, pero agota un timeout regex. Su latencia es de rechazo,
no de normalización exitosa. html_depth_rejected excede deliberadamente 128 niveles.
El caso de nodos incluye 19.998 br y los dos wrappers del parser; su coste es
relevante incluso cuando produce texto final vacío. El máximo admitido por tamaño
no es una promesa de latencia baja.

Los costes y contadores completos permiten distinguir escenarios, no solo medias.
No se ocultan los errores en el throughput: el JSON separa llamadas/s de éxitos/s.
El RSS incluye Python, librerías, calentamiento y objetos de medición; no es
memoria marginal que pueda multiplicarse por número de registros.

Perfil separado: [fase_7_perfil.json](fase_7_perfil.json), mismo manifiesto que
la baseline, warmup 0 y una muestra más las pasadas de tracemalloc/cProfile para
integral e hints. Picos Python trazados: 1.203.484 y 5.881.934 bytes respectivamente.
En el perfil de hints, render_document acumula aproximadamente 5,17 s de 6,35 s
perfilados; reemplazos, validación de modelos y transporte de procedencia dominan.
Estos tiempos incluyen instrumentación y no sustituyen la baseline sin perfilado.
No se aplicaron optimizaciones especulativas a esas rutas.

```bash
uv run --locked python -m benchmarks.load --case integral --case hints_2000 \
  --profile --python-memory --warmup 0 --repetitions 1 --worker-timeout 120 \
  --worker-memory-mib 512 --output /tmp/normietext-f7-profile.json
```

## Propuesta para el próximo ensayo, sin aprobación de producción

El máximo exitoso observado por campo fue 20,36 s y 111,56 MiB RSS. Como **margen
experimental a validar**, duplicar esas observaciones sugiere ensayar un watchdog
de 45 s por campo y un techo RSS de 256 MiB por worker. Son propuestas redondeadas,
no garantías, valores implantados ni equivalentes al RLIMIT_AS 512 MiB del banco.
No fijar todavía watchdog de registro desde el registro pequeño de seis campos:
falta medir registros grandes de la mezcla objetivo y la contención concurrente.

El registro sintético medido permite unas 16 llamadas/s secuenciales en esta máquina,
mientras el campo HTML extremo permite unas 0,05/s. Esa diferencia impide proponer
número de workers sin distribución y volumen. Un umbral relativo inicial de 25 %
para un segundo ensayo controlado puede servir para investigar ruido/regresiones,
pero necesita repeticiones suficientes y aprobación; el CLI no lo asume por defecto.


## Verificación final

- `uv sync --locked`: entorno sincronizado, lock sin cambios.
- Ruff lint/formato aprobados (63 archivos); mypy estricto aprobado (35 fuentes).
- `uv run --locked pytest`: **426 pruebas aprobadas, sin skips**, en 41,72 s.
- `generate_tables.py --check`: tablas verificadas, sin regeneración.
- [Calidad F7](fase_7_calidad.json): passed=true; 55 casos de calidad, 30/30 decisiones
  positivas, cero FP en 39 negativos normativos, 58 fragmentos integrales preservados.
  Frente al informe F6 solo cambian `manifest` y `corpus_sha256` (el catálogo incluye
  la política versionada y nuevas regresiones canónicas); métricas, observaciones,
  ablaciones y evidencia permanecen iguales.
- sdist/wheel stamped, Twine estricto e instalación aislada aprobados. El smoke
  verifica la API funcional, reglas 1.0.1, métricas y ausencia de evaluation/benchmarks.
- `git diff --check`: aprobado. No se modificaron goldens normativos anteriores.

El primer intento de suite mientras se editaban fuentes tuvo un POLICY_MISMATCH
por cambio de huella durante la ejecución; se descartó y se repitieron las pruebas
sobre fuentes estables. La suite final anterior es la evidencia de aceptación local.

Artefactos locales verificados, no publicados:

| Artefacto | SHA-256 |
|---|---|
| normietext-0.1.0-py3-none-any.whl | `40c22cf30d0f6c611c2ab5c4bdc8375bc6d09099a6ca7fda94eeae09468d35c5` |
| normietext-0.1.0.tar.gz | `3c4f58a4c1e0faae5139bb3c8fbc299f6b6424b088f8f738ad84946e4ddc61b6` |

Huella del código: `02bc81b357ed201b0ba9a42b62baa1a4bc8a6021e66a677997c157df0e723dee`.
El stamping combina el commit base y esta huella porque hay cambios sin commit.
El manifiesto de checkout usa source-tree y el de wheel usa git+tree; el código
coincide, pero no se afirma igualdad literal entre esos dos manifiestos.

## Aprobación pendiente

Para cerrar la puerta F7 del plan se necesita definir y medir la distribución real,
volumen medio/pico, entorno y concurrencia, latencia objetivo, tasa de fallos,
memoria/timeout por worker y umbrales aceptados de regresión. La guía operativa
incluye la fórmula de capacidad por mezcla y el comando de comparación. No se
asume que el usuario haya aprobado valores por no haberlos proporcionado.

No se ejecutó CI remota, push, tag, publicación o adopción en tráfico real.
