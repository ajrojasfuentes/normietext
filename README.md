# normietext

Biblioteca Python local y determinista para normalizar seis campos de ofertas
laborales extraídas de LinkedIn. Conserva evidencia, estructura y procedencia
para consumidores de parsing, sin LLM ni llamadas de red al normalizar.

**Estado: v0.1.0 publicada y verificada en GitHub; F8 cerrada para el alcance sintético aprobado.**
`JobTextNormalizer` ofrece normalización por campo/registro, reentrada canónica
idempotente y proyección solo texto. Incluye listas, emoji, invisibles, espacios,
NFC final, estructura y procedencia. F6 añade evaluación de evidencia y corpus
sintético; no acredita calidad de tráfico real. F7 añade métricas y pruebas de carga;
La capacidad se documenta por hardware y corpus, sin un SLO universal de servicio.
La distribución está disponible en [GitHub Releases](https://github.com/ajrojasfuentes/normietext/releases/tag/v0.1.0)
bajo MIT; véanse [distribución](docs/distribucion_github.md) y [cierre F8](docs/revisiones/cierre_fase_8.md).
La especificación 2.0 no es
la versión del paquete: la base usa `0.1.0`, esquema `1.0.0` y reglas `1.0.1`.

## Desarrollo

Requiere uv **0.12.18**. El runtime del proyecto es CPython **3.14.7 con GIL**;
Ruff **0.16.8** se instala en el grupo de desarrollo.

```bash
uv python install
uv sync --locked
uv run --locked python -c "import normietext"
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv run --locked pytest
uv run --locked python scripts/generate_tables.py --check
uv run --locked python scripts/build_distribution.py
uv run --locked twine check --strict dist/*.whl dist/*.tar.gz
uv run --locked python scripts/check_wheel.py
```

`uv.lock` fija las dependencias efectivas; no se edita manualmente. El rango de
Python publicado es `>=3.14,<3.15`, con validación inicial sobre 3.14.7. Para
reproducir el comportamiento normativo se usa el runtime exacto y su manifiesto de política y dependencias.

## Contratos disponibles

```python
from normietext import FieldInput, JobField, NormalizationPolicy

source = FieldInput(JobField.JOB_TITLE, "Python Engineer")
policy = NormalizationPolicy()
assert source.value == "Python Engineer"  # Validación, sin transformar contenido.
assert policy.limits.max_expansion_factor == 32
```

## Normalización disponible

```python
from normietext import FieldInput, JobField, JobTextNormalizer

normalizer = JobTextNormalizer()
result = normalizer.normalize_field(
    FieldInput(JobField.JOB_DESCRIPTION, "🚀• Python\n🇨🇷")
)
assert result.text == "- Python\n[flag:CR]"
assert normalizer.canonicalize(result) is result
assert result.source.raw == "🚀• Python\n🇨🇷"
assert normalizer.clean_text("C++🚀Python", JobField.JOB_TITLE) == "C++ Python"
```

La [guía de API](docs/api.md) describe formatos explícitos, estados, errores por campo,
modo estricto de registros, anotaciones y reentrada. T01–T40 se ejecutan en 49
escenarios; el integral conserva sus textos esperados originales.

## Fuentes y manifiesto disponibles

```python
from normietext import JobField, SourceEvidence
from normietext.sources import prepare_input, recover_source
from normietext.manifest import create_manifest
from normietext.serialization import canonical_bytes

source = prepare_input("Python Engineer", JobField.JOB_TITLE)
evidence = SourceEvidence.from_input(source)
assert recover_source(evidence) == source
manifest_bytes = canonical_bytes(create_manifest())
```

Estas operaciones no limpian el texto. La recuperación externa se configura en
ingesta mediante `SourceStore`; no introduce I/O en las transformaciones. El
[ADR de Fase 2](docs/decisions/0002-baseline-fuentes-procedencia.md) explica alineación,
validación canónica base, identidad del entorno y requisitos de artefactos de producción.

## Conversión de formato disponible

```python
from normietext import FieldInput, JobField, SourceFormat
from normietext.adapters import convert_source, tracked_document

source = FieldInput(JobField.JOB_DESCRIPTION, "C<b>++</b><br>Python",
                    SourceFormat.HTML_FRAGMENT)
document = convert_source(source)
assert document.text == "C++\nPython"
assert document.phase.value == "converted"
tracked = tracked_document(document)  # Mantiene alineación; no reinterpreta HTML.
```

La conversión conserva estructura, sangrías y componentes de emoji para las etapas
siguientes. No es una API de limpieza completa. El [ADR de Fase 3](docs/decisions/0003-adaptadores-formato.md)
documenta formatos, entidades, límites, listas, tablas, asociaciones y precisión HTML.

## Reparación y análisis léxico disponibles

```python
from normietext import FieldInput, JobField
from normietext.adapters import convert_source
from normietext.stages.encoding import repair_document
from normietext.stages.lexing import lex_document

converted = convert_source(FieldInput(JobField.JOB_DESCRIPTION, "JosÃ© 🇨🇷"))
repaired = repair_document(converted)
assert repaired.text == "José 🇨🇷"
assert repair_document(repaired) is repaired
lexed = lex_document(repaired)
assert lexed.phase.value == "lexed"
assert lex_document(lexed) is lexed
```

Estas etapas conservan estructura y procedencia hacia raw. Los tokens describen
candidatos y protecciones de URL/correo/código; todavía no eliminan emoji, invisibles
ni sangrías ni producen texto canónico. El [ADR de F4](docs/decisions/0004-reparacion-lexico.md)
detalla unidades de reparación, precedencias y limitaciones del reconocimiento.
La reparación configurada puede tener falsos positivos: conserva raw y explicación,
pero no demuestra la intención del autor. El renderer de F5 consume esos candidatos una sola vez.

## Distribución e integración

La entrega principal es un wheel importable con tipos (`py.typed`). Un consumidor
puede instalar `dist/normietext-0.1.0-py3-none-any.whl` con su gestor de paquetes.
Esto instala la API funcional, contratos, datos y etapas tipadas. Las cinco dependencias de
runtime son las fijadas por §21 de la especificación. Las herramientas de pruebas,
tipado y publicación no son dependencias de los consumidores.

El núcleo es síncrono e independiente del framework. Un servicio HTTP, workers,
almacenamiento y orquestación pertenecen a adaptadores externos; no se incorporan
FastAPI, Docker ni infraestructura distribuida a esta inicialización.

## Documentación

- [Especificación normativa 2.0](docs/normietext_v2.0_especificacion.md).
- [Análisis del proyecto y decisiones](docs/analisis_proyecto.md).
- [Plan detallado de implementación](docs/plan_implementacion.md).
- [Desarrollo, CI y publicación](docs/desarrollo_y_release.md).
- [ADR de contratos y corpus](docs/decisions/0001-contratos-fase-1.md).
- [ADR de baseline y procedencia](docs/decisions/0002-baseline-fuentes-procedencia.md).
- [ADR de adaptación](docs/decisions/0003-adaptadores-formato.md).
- [ADR de reparación y léxico](docs/decisions/0004-reparacion-lexico.md).
- [Guía de API](docs/api.md).
- [ADR de renderer y API](docs/decisions/0005-renderer-api.md).
- [Guía de evaluación](docs/evaluacion.md).
- [ADR de evaluación](docs/decisions/0006-evaluacion-evidencia.md).
- [Informe de cierre F6](docs/revisiones/cierre_fase_6.md).
- [Informe F7 y aceptación pendiente](docs/revisiones/cierre_fase_7.md).
- [Operación y benchmarks](docs/operacion.md).
- [Informe de cierre F5](docs/revisiones/cierre_fase_5.md).
- [Informe de cierre F4](docs/revisiones/cierre_fase_4.md).
- [Informe de cierre F3](docs/revisiones/cierre_fase_3.md).
- [Informe de cierre F2](docs/revisiones/cierre_fase_2.md).
- [Informe de revisión F0 y cierre F1](docs/revisiones/cierre_fases_0_1.md).

CI comprueba lint, formato, tipos y pruebas en Linux, Windows y macOS, y construye
y prueba la distribución en Linux. El workflow de release reutiliza esos checks.
La publicación en PyPI necesita la configuración externa descrita en la guía.

Licencia [MIT](LICENSE).

## Capacidad de referencia y distribución

Las 20 muestras sintéticas del mantenedor se procesaron sin fallos con 1/2/4 procesos,
con salida idéntica entre configuraciones. En Ryzen 5 5600X, cuatro procesos midieron
9,79 registros/s. Se adopta 100.000 ofertas en 6 h como objetivo condicionado a esa
mezcla y recursos; es una proyección con margen, no una prueba de 100.000 ofertas ni
una garantía para cualquier equipo. Véase la [aceptación](docs/revisiones/aceptacion_biblioteca.md).

Distribución elegida: GitHub Releases, licencia MIT, mantenida por Anthony Josue
Rojas Fuentes. La candidata aún no está publicada. Instalación, checksums, adopción
y rollback: [guía de distribución](docs/distribucion_github.md).
