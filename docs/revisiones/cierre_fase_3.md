# Cierre de Fase 3 — Adaptadores de formato y estructura de origen

Fecha: 2026-09-27. Base: `753bb96`, incluida la corrección de rutas de catálogo para
Windows. Alcance autorizado: F3. La base inició con 75 pruebas aprobadas.

## Resultado

Se implementaron adaptadores plain_text/unknown, html_escaped_text y html_fragment,
con un dispatcher explícito. Devuelven ParsedDocument convertido, conservan raw y
alineación, y no reingresan documentos convertidos como fuente. JobTextNormalizer
sigue pendiente; no se inició F4.

| Puerta de F3 | Evidencia implementada |
|---|---|
| Literal / unknown | Sin HTML, unescape ni Markdown implícitos; incidencia para unknown |
| Entidades | Una capa; origen de cada referencia; entidades dobles y escapes inválidos |
| Separadores | CRLF como unidad; CR/NEL/LS/PS/VT/FF a LF; sangrías/componentes conservados |
| Backend | Beautiful Soup/lxml explícito, parser local por llamada, sin fallback |
| Seguridad | Opciones de parser probadas, sin red, DTD externo sin lectura de contenido |
| Bloques | Inline técnico contiguo, párrafos, encabezados, código y contextos parentales |
| Listas | start/value/reversed, estilos, anidamiento y atributos inválidos; prefijos intactos |
| Tablas | Celdas vacías, coordenadas, spans, grupos, caption/th y tablas anidadas |
| Asociaciones | dl/dt/dd múltiples, grupos div y miembros faltantes; sin inferencia por tipografía |
| Representación | href/alt, tachado, sup/sub; exclusiones explícitas y fallback conservado |
| Errores / recursos | Entrada antes del parser, nodos/profundidad, coordenadas, fallos tipados y diagnóstico disponible |
| Procedencia | Exacta para copias/referencias demostrables; field explícito para DOM sin offsets raw |
| Replay | Documento HTML serializado idéntico en procesos con cuatro PYTHONHASHSEED |

Las decisiones y límites se detallan en [ADR-0003](../decisions/0003-adaptadores-formato.md).
La especificación §10.4.1 hace explícitas las concreciones de esta fase.

## Validación local

- 130 pruebas pytest aprobadas, incluidas 30 fixtures nuevos de adaptación,
  propiedades y replay HTML entre procesos.
- Ruff lint/formato y mypy estricto aprobados.
- Tablas verificadas con generate_tables.py --check; no se cambiaron dependencias.
- Corpus previo intacto. Solo se añaden adaptation/cases.json y su esquema al
  catálogo de hashes; no se reescriben sus goldens para ajustarlos al código.
- Build con revisión incorporada, wheel desde sdist, Twine estricto e instalación
  aislada comprobados; el smoke test ejecuta adaptación HTML desde el wheel.
- Diff y enlaces locales de documentación comprobados.

El fixture nuevo de entidad numérica se corrigió durante autoría: HTML5 convierte
`&#x85;` en elipsis, a diferencia del NEL literal que es LF. Fue una corrección
explícita de expectativa conforme al contrato HTML5, no una regeneración de goldens.

## Límites y siguiente fase

La matriz remota de GitHub Actions no se ejecutó desde esta tarea; no se afirma
haber validado estos cambios en un runner Windows real. El CI conserva la prueba
del catálogo corregida con as_posix y la matriz multiplataforma existente.

Los adaptadores no garantizan layout CSS ni recuperación exacta del marcado roto.
La procedencia HTML es deliberadamente field cuando el parser no proporciona un
mapa probado. Se preserva raw para auditoría/reprocesamiento.

Celdas a una línea, separadores ` | `, prefijos de lista, compactación por campo,
NFC final y spans canónicos quedan en F5. F4 implementará reparación y análisis
léxico sobre el texto ya convertido. El corpus del normalizador conserva
awaiting_normalizer; la aprobación de esta fase no acredita esas reglas futuras.

No se realizó commit, push, publicación ni implementación de F4 en esta entrega.
