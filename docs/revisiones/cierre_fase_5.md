# Cierre local de Fase 5

Fecha: 2026-09-29. Base: commit `3da0b7b` (F4); rama de trabajo `codex/fase-5`.
F5 implementada y verificada localmente. No acredita las puertas de F6–F8 ni una
publicación del paquete. Especificación 2.0; software 0.1.0; reglas/esquema 1.0.0.

## Entrega

- `JobTextNormalizer.normalize_field`, `normalize_record`, `canonicalize` y
  `clean_text` conectan adaptación, reparación, léxico, estructura, símbolos y
  renderer. La API no exporta stubs ni reinterpreta documentos tipados como raw.
- Listas en descripción/criterios, vista virtual sin ruido, vecinos léxicos,
  ordinales sin renumerar, continuaciones/anidamiento con tab stops de cuatro.
  DOM prevalece; conflictos ordinales conservan ambas cifras y emiten incidencia.
- Hints/banderas con anotaciones de ocurrencia, keycaps, símbolos textuales,
  eliminación atribuida de emoji/invisibles/kaomoji y solidus fuera de protecciones.
  Fronteras técnicas y huecos se ajustan localmente según ADR-0005.
- Campos compactos/multilineales, párrafos/listas/celdas/asociaciones explícitas,
  NFC final, spans y procedencia. Marcadores vacíos con el mismo offset tienen
  spans propios. Las continuaciones amplían el span de sus elementos.
- Reentrada compatible devuelve el mismo objeto, valida referencias, manifiesto,
  texto, marcadores y payloads de anotaciones. Incompatibilidad exige reprocesar raw.
- Registro conserva seis sobres, ausencia, errores de extracción y fallos por campo;
  modo estricto propaga el primer fallo de normalización. Límites agregado, por
  campo, profundidad y expansión impiden resultados truncados.

Las decisiones previas y límites están en [ADR-0005](../decisions/0005-renderer-api.md),
integrado explícitamente en §18.2 de la especificación. La [guía de API](../api.md)
contiene ejemplos ejecutables y el contrato de errores.

## Evidencia

- `uv sync --locked`: entorno del worktree instalado con pins intactos.
- Ruff lint y formato: aprobados; mypy estricto: 27 archivos fuente sin errores.
- `uv run --locked pytest`: **337 tests aprobados**, sin skips, frente a 190 en F4.
- T01–T40: 49 escenarios ejecutados, incluyendo errores, estructura y procedencia.
- Integral: ambos textos exactos; cinco hints, seis listas con 11/8/11/7/6/10
  elementos y relaciones de continuación. Los cuatro archivos UTF-8 raw/expected
  mantienen sus bytes y hashes originales.
- 19 suplementos y 56 casos nuevos de renderer; T41–T64 según las decisiones
  adoptadas. Las propuestas rechazadas/diferidas se prueban como negativos, sin
  convertirlas en obligaciones del perfil.
- Registro de seis campos presentes aprobado; registros parciales, vacíos y
  extracción fallida conservan sus sobres y fuentes.
- Propiedades de Unicode arbitrario y combinaciones léxicas, reentrada completa,
  anotaciones repetidas, spans NFC, límites y errores operativos.
- Replay canónico idéntico en cuatro procesos (`PYTHONHASHSEED` 0, 1, 42, random),
  con sockets bloqueados. Procesamiento concurrente en orden inverso coincide.
- Caso de 2.000 hints: 51.999 caracteres y 2.000 anotaciones, sin elevar presupuestos.
- Tablas: `generate_tables.py --check` aprobado, sin regenerarlas ni cambiar pins.
- `build_distribution.py`: sdist y wheel stamped construidos correctamente.
  Twine estricto aprueba ambos. `check_wheel.py` instala fuera del checkout y prueba
  API funcional, hints y reentrada sin depender de `.git` del consumidor.
- Revisión de diff, integridad del corpus y enlaces documentales locales.

## Revisión del corpus

Se actualiza `execution_status` a `verified_f5` únicamente donde hay tests
funcionales. Los schemas permiten distinguirlo de `awaiting_normalizer`. El
inventario externo mantiene sus decisiones históricas, interpretadas según §18
del plan y los tests de esta fase, incluyendo alternativas y contraejemplos.

No cambia ningún raw ni esperado existente de T01–T40/integral. Siete expectativas
suplementarias que eran null se fijan manualmente: conflicto `3. 1. X`, cuatro
fronteras técnicas separadas y negativos `C++`/`$500`. Los hashes se actualizan
por estas modificaciones deliberadas, schemas, estados y los dos archivos nuevos;
no se obtienen goldens de la salida del programa.

El test de timeout de NFC usa ahora una entrada descompuesta que requiere NFC;
el fast path de texto ya normalizado evita trabajo inútil. El timeout conserva
su resultado operativo y la fuente intacta. Las propiedades detectaron selectores
en pictogramas ambiguos y variantes de marcadores; ambas regresiones quedan fijadas.

## Límites y siguiente fase

Corpus sintético y público, sin evaluación ciega ni muestra representativa de
tráfico real. No se afirma precisión ≥99,5 %, SLO, throughput ni fidelidad lingüística
universal. La reparación ftfy conserva su limitación documentada de falsos positivos.
HTML mantiene precisión field cuando no hay offsets raw demostrables. Los spans de
celdas vacías usan anclas conservadoras, conservando coordenadas y pertenencia.

La validación canónica no reinterpreta nuevas adyacencias como otra fuente: no
crea anotaciones para tokens literales ni repite reparación/decodificación. La
proyección no preserva código ejecutable ni todas las señales de formato.

Sigue F6: consumidores mínimos de evidencia, corpus multilingüe ampliado, análisis
de pérdidas y muestra etiquetada de decisiones contextuales. F7 conserva operación,
benchmarks y SLO; F8, release y adopción. La matriz CI remota y publicación no se
han ejecutado en este cierre local.
