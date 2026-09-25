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
- F1 implementa contratos/política/tablas y corpus; aún no existe `JobTextNormalizer`; no documentar APIs inexistentes
  como utilizables ni considerar los tests de empaquetado aceptación del producto.
- Usar `uv sync --locked`, Ruff, mypy y pytest; construir y comprobar el wheel.
- Cambios de comportamiento requieren fixtures y revisión de diffs del corpus.
- Nunca sustituir los textos esperados del corpus automáticamente por la salida
  de la implementación. No corregir la especificación silenciosamente.

Estado actual y evidencia: `docs/revisiones/cierre_fases_0_1.md`. Las decisiones de
contratos se fijan en `docs/decisions/0001-contratos-fase-1.md`. Los fixtures con
`awaiting_normalizer` no son pruebas funcionales aprobadas ni deben ocultarse con
skips. Ejecutar `uv run --locked python scripts/generate_tables.py --check`; no
regenerar goldens o hashes de corpus a partir de la salida de la implementación.
