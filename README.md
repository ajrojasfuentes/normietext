# normietext

Biblioteca Python local y determinista para normalizar seis campos de ofertas
laborales extraídas de LinkedIn. Conserva evidencia, estructura y procedencia
para consumidores de parsing, sin LLM ni llamadas de red al normalizar.

**Estado: Fase 0 verificada localmente y fases 1–2 completadas.** El paquete incluye
contratos, política/tablas, fuentes verificadas, alineación compuesta, serialización
canónica y manifiesto efectivo;
`JobTextNormalizer` y las reglas de normalización todavía no están implementados.
La especificación 2.0 no es la versión del paquete: la base usa `0.1.0`.

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
uv run --locked twine check --strict dist/*
uv run --locked python scripts/check_wheel.py
```

`uv.lock` fija las dependencias efectivas; no se edita manualmente. El rango de
Python publicado es `>=3.14,<3.15`, con validación inicial sobre 3.14.7. Para
reproducir el comportamiento normativo se usa el runtime exacto y, cuando exista
el normalizador, su manifiesto de política y dependencias.

## Contratos disponibles

```python
from normietext import FieldInput, JobField, NormalizationPolicy

source = FieldInput(JobField.JOB_TITLE, "Python Engineer")
policy = NormalizationPolicy()
assert source.value == "Python Engineer"  # Validación, sin transformar contenido.
assert policy.limits.max_expansion_factor == 32
```

La API de normalización llegará en las fases siguientes. Las pruebas actuales
comprueban contratos, procedencia, baseline de espacios/NFC y replay; los 40 casos normativos están
materializados en 49 escenarios y aún no se han ejecutado contra un normalizador.

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

## Distribución e integración

La entrega principal es un wheel importable con tipos (`py.typed`). Un consumidor
puede instalar `dist/normietext-0.1.0-py3-none-any.whl` con su gestor de paquetes.
Esto instala los contratos, datos y utilidades de baseline, todavía sin API de limpieza. Las cinco dependencias de
runtime son las fijadas por §21 de la especificación. Las herramientas de pruebas,
tipado y publicación no son dependencias de los consumidores.

El núcleo será síncrono e independiente del framework. Un servicio HTTP, workers,
almacenamiento y orquestación pertenecen a adaptadores externos; no se incorporan
FastAPI, Docker ni infraestructura distribuida a esta inicialización.

## Documentación

- [Especificación normativa 2.0](docs/normietext_v2.0_especificacion.md).
- [Análisis del proyecto y decisiones](docs/analisis_proyecto.md).
- [Plan detallado de implementación](docs/plan_implementacion.md).
- [Desarrollo, CI y publicación](docs/desarrollo_y_release.md).
- [ADR de contratos y corpus](docs/decisions/0001-contratos-fase-1.md).
- [ADR de baseline y procedencia](docs/decisions/0002-baseline-fuentes-procedencia.md).
- [Informe de cierre F2](docs/revisiones/cierre_fase_2.md).
- [Informe de revisión F0 y cierre F1](docs/revisiones/cierre_fases_0_1.md).

CI comprueba lint, formato, tipos y pruebas en Linux, Windows y macOS, y construye
y prueba la distribución en Linux. El workflow de release reutiliza esos checks.
La publicación en PyPI necesita la configuración externa descrita en la guía.

Licencia [MIT](LICENSE).
