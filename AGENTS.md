# Contexto de normietext

Leer `docs/normietext_v2.0_especificacion.md` antes de implementar comportamiento.
Es la fuente normativa completa; `docs/analisis_proyecto.md` conserva las decisiones
de inicialización y `docs/plan_implementacion.md` el trabajo pendiente y sus puertas.
No confundir la especificación 2.0 con la versión del paquete 0.1.0.

- Biblioteca Python local, determinista, sin LLM, sin red durante normalización.
- Seis campos independientes; preservar fuente recuperable, estados y procedencia.
- Convertir formato una vez; idempotencia sobre documentos tipados, no sobre strings.
- Capturar secuencias emoji y estructura antes de borrar invisibles o sangrías.
- NFC final antes de calcular spans; no NFKC global ni interpretación semántica.
- Mantener separados versiones del software, esquema, reglas y perfil.
- F1–F5 implementan contratos, corpus, procedencia, adaptación, reparación, léxico,
  símbolos, listas y renderer. F6 añade consumidores y evaluación sintética.
  `JobTextNormalizer` es la API funcional; F7 implementa operación local y F8 conserva release. El smoke de wheel no sustituye corpus.
- Usar `uv sync --locked`, Ruff, mypy y pytest; construir y comprobar el wheel.
- Cambios de comportamiento requieren fixtures y revisión de diffs del corpus.
- Nunca sustituir los textos esperados del corpus automáticamente por la salida
  de la implementación. No corregir la especificación silenciosamente.

Estado actual y evidencia: `docs/revisiones/aceptacion_biblioteca.md`; F7 valida
capacidad por equipo/corpus. F8 queda preparada, pendiente de aprobación/publicación. Las decisiones de
contratos se fijan en `docs/decisions/0001-contratos-fase-1.md` y
`docs/decisions/0002-baseline-fuentes-procedencia.md` y
`docs/decisions/0003-adaptadores-formato.md` y
`docs/decisions/0004-reparacion-lexico.md` y
`docs/decisions/0005-renderer-api.md`. Los fixtures con
`awaiting_normalizer` no son pruebas funcionales aprobadas ni deben ocultarse con
skips. Ejecutar `uv run --locked python scripts/generate_tables.py --check`; no
regenerar goldens o hashes de corpus a partir de la salida de la implementación.

- Construir con `uv run --locked python scripts/build_distribution.py` para incorporar
  revisión Git/huella sin requerir `.git` en consumidores. El smoke test exige ese stamping.
- `render_baseline` es infraestructura posterior a captura léxica/estructural, no API
  de limpieza. `validate_canonical` comprueba texto, manifiesto, referencias y representación F5.
- Persistencia/recuperación externa pertenecen a ingesta; no llamar SourceStore desde
  las transformaciones. Un fingerprint instalado no equivale al hash de un wheel.

- `convert_source` solo recibe FieldInput nuevo. Su resultado es converted, con
  alineación; usar `tracked_document` para continuar sin reinterpretar formato.
- HTML conserva precisión field si el backend no demuestra offsets raw. Nunca
  usar búsquedas de texto repetido para declarar exactitud.
- Los fixtures adaptation verifican F3; sus LF son provisionales. La salida final
  de tablas/listas y NFC/spans se verifica en F5. Preservar esas puertas separadas.

- F4 usa `repair_document` una vez y `lex_document` sobre su resultado tipado.
  RepairedDocument/LexedDocument no son resultados canónicos. No reinterpretar
  formatos ni aplicar todavía los candidatos destructivos de tokens.
- Mantener las unidades de reparación separadas por líneas, bloques y anotaciones;
  conservar explicación de cambios reales y precisión segment/field sin inventar mapas.
- El léxico conserva secuencias completas y contextos; F5 aplica marcadores,
  separadores y PROTECTED_SPAN_MODIFIED al aplicar cambios. No duplicar issues
  al integrar LexedDocument: su colección ya incluye los de reparación/adaptación.

- `canonicalize` continúa documentos tipados; no recibe strings ni reinterpreta raw.
  La API de registro conserva los seis sobres y captura fallos por campo; strict
  propaga fallos. No repetir reparaciones ni concatenar colecciones de issues.
- Las expectativas F1 existentes mantienen raw/text intactos. `verified_f5` es
  estado respaldado por tests ejecutables, no aceptación de tráfico real ni F6.

- F6: `evaluation/` es infraestructura de desarrollo, excluida del wheel. Usar
  `uv run --locked python -m evaluation.quality --output /tmp/calidad.json`.
  El informe fija denominadores, abstenciones y pérdidas autorizadas; no acredita
  tráfico real. No convertir vistas derivadas o ablaciones en fuente raw.
- Mantener `quality` como corpus de expectativas manuales, separado de regresiones
  normativas. La nueva alineación local de tokens distingue marcadores insertados;
  no altera procedencia raw. Los spans padres incluyen sus hijos renderizados.

- F7: `normietext.operations` mide llamadas de forma explícita sin registrar texto.
  Exportar solo `Measurement.metrics`; resultado y trace contienen fuentes privadas.
  `benchmarks/` es desarrollo, excluido del wheel. Usar `python -m benchmarks.load`.
  No confundir percentiles sintéticos locales con SLO aprobado de producción.
- Reglas 1.0.1 corrigen separadores de celdas vacías y validación canónica padre/hijo;
  esquema 1.0.0, paquete 0.1.0. Mantener versionado y regresiones manuales.

- ADR-0008: biblioteca por lotes, GitHub/MIT; PyPI opcional. Mantenedor: Anthony
  Josue Rojas Fuentes. Los 20 casos de benchmarks/cases son sintéticos; preservar bytes.
- Su adaptador conserva modality aparte y seniority missing; no reinterpretar
  pseudo-HTML ni usar canonical_* como verdad del cleaner. Partial no implica fallo.
- `benchmarks.batch` mide procesos y replay; los tiempos de 100.000 son extrapolados.
  Pictogramas se buscan por runs no ASCII; NFC por líneas conserva offsets y límites.
