# Cierre de Fase 8 — normietext 0.1.0

Verificado el 2026-10-04 en America/Costa_Rica. Publicación: 2026-10-05 02:15:56 UTC.
El mantenedor aprobó expresamente las notas y la publicación de v0.1.0.

## Resultado

La distribución GitHub/MIT está publicada y verificada desde sus assets descargados:
[normietext 0.1.0](https://github.com/ajrojasfuentes/normietext/releases/tag/v0.1.0).
El tag anotado `v0.1.0` apunta al commit
`717903d7e5764596a4d7c400dbf032ab7d4b195d`.
F8 queda cerrada para el alcance aprobado de biblioteca y consumidor sintético.
Esto no convierte en validación real la evidencia sintética ni cierra las mejoras
de observabilidad identificadas en la auditoría.

## Integración y CI

Los cambios recientes se guardaron antes de publicar:

- `87fad6d`: corrección de APIs Unix en benchmarks, pruebas Windows e informes de auditoría.
- `bbd49cb`: restricciones de runtime desde uv.lock para instalaciones aisladas.
- `a8f39eb`: notas de release aprobadas.
- `717903d`: integración del [PR #1](https://github.com/ajrojasfuentes/normietext/pull/1).

La corrección de Windows superó mypy y pytest nativos. Las matrices Linux, Windows
y macOS, y la construcción/instalación de distribución, pasaron en:

- [CI del PR definitivo](https://github.com/ajrojasfuentes/normietext/actions/runs/37254231987).
- [CI del merge en main](https://github.com/ajrojasfuentes/normietext/actions/runs/37254509838).
- [Workflow de Release](https://github.com/ajrojasfuentes/normietext/actions/runs/37254717023).

El workflow de release validó el tag, reutilizó la matriz CI, construyó wheel desde
sdist y adjuntó los artefactos verificados sin reconstruirlos en el job de subida.
El job opcional PyPI quedó omitido. No se habilitó publicación en PyPI.

## Integridad y consumo

Se descargaron wheel, sdist y SHA256SUMS desde la Release. Los hashes calculados
coinciden con el archivo de checksums y con los artefactos construidos localmente
desde el mismo commit limpio. Twine aprobó ambos archivos descargados.

| Asset | SHA-256 |
|---|---|
| normietext-0.1.0-py3-none-any.whl | `7c058ce6729ddbb0915998bca7c4362a4b56f779bca7d665125aa7a6c78a5c48` |
| normietext-0.1.0.tar.gz | `af76ead9f8df88ee8a9ce3d6b15c2c0051ea4e8594dd0488327fb2e00b36694c` |

El wheel identifica `git:717903d7e5764596a4d7c400dbf032ab7d4b195d`, sin sufijo dirty.
La huella del núcleo es
`9f7a4c5c3a1a802214d869d1a068fe2c45b5efc8bcdbd2d3a3022689b909e371`.
No se cambió el comportamiento del normalizador: software 0.1.0, esquema 1.0.0,
reglas 1.0.1, perfil linkedin_jobs_aggressive_v1.

La instalación aislada inicial reveló que una resolución libre podía seleccionar
wcwidth 0.9.2 en vez del 0.9.1 fijado. Se corrigieron check_wheel.py y check_adoption.py
para exportar restricciones de runtime desde uv.lock, sin instalar el checkout
editable ni dependencias de desarrollo. La metadata pública de dependencias no
cambió; cada consumidor sigue manteniendo su propio entorno bloqueado.

La prueba final instaló **el wheel descargado**, el snapshot anterior y otra vez el
wheel descargado. En cada instalación procesó los 20 originales sintéticos con
fuente, spans y reentrada comprobados. `shadow_equal=true` y `replay_equal=true`.
Son 60 procesamientos, no 60 ofertas distintas. El rollback anterior es un snapshot
de desarrollo, no otra versión pública. Se conserva el alcance limitado de esa prueba.

La [evidencia JSON](cierre_fase_8.json) incluye jobs remotos, URLs de assets, hashes,
stamping y las tres observaciones del consumidor. Los informes previos identifican
otras construcciones y no deben usarse como checksums de esta Release.

## Mantenimiento y límites

El responsable sigue siendo Anthony Josue Rojas Fuentes. La compatibilidad publicada
es CPython >=3.14,<3.15, con baseline 3.14.7. El consumidor conserva raw, manifiesto,
wheel y configuración para replay y rollback; no usa texto normalizado como raw.

Quedan como seguimiento explícito la validación en proyectos consumidores reales,
la ampliación de muestras independientes y las métricas detalladas de §25.1.
Se publicaron como limitaciones, sin presentar F8 como una garantía universal.
Las mediciones de 100.000 ofertas siguen siendo extrapolaciones por equipo/corpus.

Esta documentación de cierre se incorpora después del tag; no mueve el tag ni
reemplaza los assets publicados. La descripción empaquetada conserva el estado de
preparación del README en el momento del commit; el README de main y este informe
registran la publicación ya comprobada.
