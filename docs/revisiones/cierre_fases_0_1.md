# Revisión de Fase 0 y cierre de Fase 1

Fecha: 2026-09-24. Base de trabajo: `dc154ce` más las anotaciones de revisión ya
presentes en el checkout. Alcance autorizado: comprobar F0 y, si estaba correcta,
completar F1. No se hizo commit, push, publicación ni implementación de F2.

## Fase 0

La base pasó `uv lock --check`, sincronización bloqueada sin builds incidentales de
lxml/regex, Ruff, formato, mypy y el test de empaquetado inicial. Se construyeron
sdist y wheel, Twine aceptó ambos y el wheel se instaló/importó desde un entorno
temporal externo. Las versiones Python 3.14.7, uv 0.12.18 y Ruff 0.16.8 permanecen
fijadas. No se encontró un bloqueo local para desarrollar F1.

La matriz de GitHub Actions no se ejecutó desde esta tarea y no se afirma que haya
pasado remotamente. Trusted Publisher y ajustes remotos de release siguen pendientes
para F8; no son necesarios para los contratos locales de F1. El diseño de CI/CD se
conserva, añadiendo comprobación de regeneración de tablas en el job de distribución.

## Entregables de Fase 1

| Área | Resultado |
|---|---|
| Entrada | Enums, FieldInput, estados de extracción y registro estricto de seis campos |
| Inmutabilidad | Dataclasses frozen con slots, tuplas y payload JSON profundamente inmutable |
| Salida | Modelos de documentos, bloques, asociaciones, anotaciones, ediciones e incidencias |
| Errores | Jerarquía tipada y códigos; fallos separados de resultados vacíos |
| Procedencia | Contratos de fuente/origen, spans y validación de referencias; generación en F2 |
| Manifiesto | Modelo tipado de versiones/hashes/artefactos; generación efectiva en F2 |
| Política | Perfil normativo y límites positivos; opciones desconocidas o no soportadas rechazadas |
| Tablas | Hints exactos, regiones/subdivisiones, kaomoji y propiedades Unicode versionadas |
| Schemas | Configuración, tablas y variantes de fixtures con claves desconocidas rechazadas |
| Corpus | T01–T40 en 49 escenarios; integral fiel; suplementarios; registro de seis presentes |
| Revisión | Inventario selectivo T41–T64; expectativas pendientes identificadas |
| Decisiones | ADR-0001 y revisión explícita de §§8/23/29/31 de la especificación |

R01 se resuelve con factor 32 y error de límite diferenciado, sin afirmar que ya se
midió expansión de todo el pipeline. R05 conserva 327.680 y explicita la redundancia
predeterminada. R06 permite asociaciones múltiples explícitas y no deduce pares por
formato visual. R12 preserva bytes de raw/expected con hash y cotejo de la fuente.
R13 resuelve empty con incidencias y prohíbe inferir exactitud por longitud igual.

Los hints iniciales no se convierten por sí solos en listas planas. Las decisiones
de separación, HTML/rendering y métricas pendientes no se implementaron parcialmente
ni se asumieron cerradas. Las variantes FE0E/FE0F de los cinco hints están enumeradas
en tablas, sin ampliar a símbolos visualmente similares.

## Validación final

- 28 pruebas pytest aprobadas, incluyendo cinco propiedades Hypothesis.
- Ruff y formato aprobados; mypy estricto aprobado en código y scripts.
- JSON Schemas y hashes validados; todos los casos T01–T40 inventariados.
- Integral cotejado contra los cuatro fences de la especificación, sin reinterpretar
  Markdown; cuatro missing, cinco hints previstos y 53 elementos en seis listas.
- Tablas regeneradas en modo `--check` con igualdad byte a byte, sin red.
- Wheel construido desde sdist; Twine aprobó ambos artefactos.
- Wheel instalado en entorno aislado: imports de contratos, configuración, tablas,
  hashes y avisos de licencia verificados fuera del checkout.

Estas pruebas verifican **contratos e integridad de datos**, no ejecución de las
reglas de normalización. El catálogo conserva `awaiting_normalizer`; no hay skips
que disimulen una implementación faltante. Todo el corpus inicial es sintético.

## Límites y siguiente fase

No existe aún `JobTextNormalizer`. Tampoco hay adaptadores, alineación generada,
serializer canónico, hashes conductuales efectivos, comparación de corpus contra
el pipeline ni SLO medido. Un `NormalizedField` construido directamente valida su
estructura, pero no acredita que un pipeline haya normalizado el texto; F2–F5
validarán invariantes/compatibilidad antes de publicar cualquier resultado.

F2 podrá empezar con los contratos aquí fijados: recuperabilidad, procedencia,
serialización, manifiesto y baseline. La publicación y la validación remota se
mantienen registradas como pendientes; no se iniciaron al cerrar F1.
