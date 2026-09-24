# Análisis del proyecto y decisiones de inicialización

Fecha: 24 de septiembre de 2026 (UTC; 23 de septiembre en Costa Rica).
Referencia normativa: [especificación 2.0](normietext_v2.0_especificacion.md), leída
completa, incluidos sus 32 capítulos y los apéndices A–D.
Audiencia: responsables del núcleo, integradores y mantenedores.

## 1. Estado encontrado

El repositorio estaba en `main`, con remoto
`https://github.com/ajrojasfuentes/normietext.git` y un commit inicial `3246889`.
Los archivos existentes eran un README de una línea, licencia MIT de Anthony Josue
Rojas Fuentes y la especificación de 1.720 líneas en `docs/`, todavía sin seguimiento
por Git. No había código de producto, dependencias, build, pruebas, workflows ni
instrucciones locales `AGENTS.md` aplicables encontradas en el proyecto o ancestros.

Por tanto, no existe una implementación anterior que migrar ni comportamiento que
preservar por compatibilidad. La especificación es el contrato de diseño, no una
evidencia de funcionamiento. No hay benchmarks, corpus ejecutable ni API pública
que permitan afirmar aceptación funcional.

Esta inicialización añade un paquete importable con layout `src`, metadatos,
`py.typed`, lockfile real, herramientas y workflows. El módulo no expone todavía
`JobTextNormalizer`; implementarlo parcialmente con sustituciones globales crearía
un contrato engañoso frente a las garantías de procedencia requeridas.

## 2. Producto y frontera arquitectónica

La unidad de producto es una biblioteca síncrona y local, con seis campos tratados
independientemente: `job_title`, `job_description`, `job_criteria_list`, `job_type`,
`seniority` y `raw_location`. El perfil inicial es
`linkedin_jobs_aggressive_v1`. Prioriza español, inglés, portugués y mezclas.

Su valor consiste en reducir variación de representación manteniendo evidencia:
contenido técnico, cifras, negaciones, condiciones, bloques, relaciones y acceso
a la fuente. No pretende garantizar fidelidad lingüística universal: borrar
caracteres de unión y dirección puede perjudicar otras escrituras.

Un servicio consumidor podrá importar el paquete y envolverlo con sus límites de
worker, almacenamiento o transporte. HTTP, autenticación, scraping, bases de datos,
colas, Docker y orquestación no son requisitos de este núcleo. La capa de parsing
reconoce entidades y resuelve significado después; no se añade una dependencia NLP.

## 3. Contratos que condicionan todo el diseño

### Entrada y estados

`FieldInput` exige un `str`, un campo válido, formato declarado y datos de origen.
`None`, bytes y sustitutos Unicode aislados son errores, no texto vacío. Un registro
contiene exactamente seis claves y estados `present`, `missing` o `extraction_error`.
Una fuente vacía presente se distingue de una fuente ausente o fallida.

La fuente debe recuperarse: localmente mediante `raw`, o mediante una referencia
a un almacén bajo contrato explícito. Un hash identifica contenido, pero no lo
recupera. La escritura o validación de esa referencia precede a las transformaciones.

### Conversión y canonicalización

Los formatos `plain_text`, `html_fragment`, `html_escaped_text` y `unknown` son
explícitos. No hay autodetección. HTML se interpreta una vez; las entidades escapadas
se decodifican una capa. `unknown` conserva semántica literal y emite incidencia.

La idempotencia se aplica a un documento tipado e inmutable, con fase, perfil y
versiones compatibles. Recanonicalizarlo valida invariantes y devuelve el mismo
valor. No ejecuta de nuevo reparación de origen, parseo, anotaciones ni ediciones.
`clean_text` devuelve una proyección con pérdida de metadatos; no tiene la garantía
general de idempotencia `str -> str`.

### Resultado y trazabilidad

El resultado debe contener texto, estado, fuente, formato, bloques, anotaciones,
ediciones, incidencias y manifiesto. Los estados de éxito son `ok`,
`ok_with_issues` y `empty`; los fallos no son resultados canónicos parciales.

Los spans son índices Python de puntos de código, semiabiertos. Se calculan tras
el renderizado y NFC final. Hace falta alineación muchos-a-uno y uno-a-muchos,
con precisión `exact`, `segment` o `field`. Beautiful Soup no garantiza posiciones
exactas de cada carácter original: degradar precisión es correcto; inventarlas no.

La coincidencia textual entre un token escrito por el autor y un token generado
es intencional. Solo las anotaciones distinguen `[flag:CR]` literal de una bandera
convertida. Una bandera indica región observada, nunca ubicación laboral resuelta.

### Determinismo

Se fija entrada, formato, configuración, tablas, reglas y entorno efectivo. La
serialización canónica tiene orden explícito y hashes SHA-256. Tiempos, métricas de
latencia y timestamps quedan fuera. Los timeouts son errores operativos y no una
segunda salida válida. Las colecciones anidadas también deben ser inmutables;
`frozen=True` con diccionarios mutables internos no basta.

## 4. Dependencias y autoridades

| Mecanismo | Autoridad y límite |
|---|---|
| HTML | Beautiful Soup con lxml explícito, local; sin fallback ni red |
| Mojibake | `ftfy.fix_encoding`, cuatro opciones explícitas; nunca `fix_text` global |
| NFC | `unicodedata` del runtime efectivo |
| Propiedades Unicode | Tablas del perfil versionadas y verificables |
| Emoji catalogado | `emoji` y tablas propias con versión, hash y licencia |
| Candidatos pictográficos | Gramática restringida y propiedades fijadas; no borrado global por `Emoji` |
| Contexto, reglas y renderer | Código propio; las bibliotecas no gobiernan el pipeline |

La diferencia entre UCD 16 de Python 3.14 y Unicode 17 declarado por regex no es
por sí sola un error. El riesgo es mezclarlos sin especificar quién clasifica cada
propiedad. Las tablas deben documentar autoridad, generación y hash. El runtime
registra también versiones efectivas de libxml2 y artefactos nativos; el lockfile
por sí solo no implementa ese manifiesto ni garantiza equivalencia entre sistemas.

## 5. Orden de transformaciones y consecuencias

1. Validar tipos, Unicode y límites; asegurar fuente recuperable.
2. Convertir el formato una vez y tokenizar límites reales de línea, manteniendo
   sangría y relaciones de origen. NEL se resuelve antes de ftfy.
3. Reparar unidades textuales, con explicación y alineación hacia la fuente inicial.
4. Reconocer protección, emoji, kaomoji y estructura antes de borrar componentes.
5. Resolver listas con vista virtual sin ruido; los hints no desaparecen de esa vista.
6. Aplicar ediciones no solapadas con precedencia normativa.
7. Renderizar según campo; NFC final; calcular spans y validar resultado completo.

Este orden impide que ZWJ o tag characters destruyan una bandera antes de detectarla,
que compactar espacios elimine relaciones de continuación o que `🚀• Python`
necesite una segunda pasada. Las reglas deben decidir primero y editar después.

La protección de URL, correo y código limita reglas de listas/puntuación, pero no
exime de eliminación global de invisibles, emoji o compactación. Cuando se modifica
su uso potencial se registra `PROTECTED_SPAN_MODIFIED`.

## 6. Comportamientos sutiles que deben conservarse

- `List<T>` y `<br>` en texto literal no son HTML; no hay parser Markdown implícito.
- Inline HTML no introduce separadores artificiales: `C<b>++</b>` produce `C++`.
- Las tablas proyectan ` | `, preservando celdas vacías y relaciones autoritativas
  mediante metadatos; el carácter `|` no determina los límites.
- Listas HTML respetan `start`, `value`, `reversed` y registran estilos de origen.
- Las heurísticas de listas planas solo operan en descripción y criterios. Las
  listas explícitas del DOM pueden conservarse en todos los campos.
- `6 - Offer` requiere continuidad; `1 - 2 years` no es una lista. No se rellenan
  ordinales ausentes ni se convierten viñetas inline en ítems.
- TAB equivale a tab stops de cuatro columnas solo para analizar estructura.
- Eliminaciones entre letras, marcas o cifras pueden introducir un espacio:
  `foo🚀bar` produce `foo bar`; un invisible se elimina sin separador.
- El ajuste ante puntuación se limita al hueco de emoji/kaomoji eliminado;
  `81,4 %` mantiene su espacio y la puntuación repetida permanece.
- No se borra toda categoría M o C. Se preservan acentos, privados y no asignados.
- Keycaps preservan su base; `©`, `®`, `™`, cifras, `#` y `*` no son ruido genérico.
- `U+FF0F` solo se convierte a `/` en texto ordinario, no en URL/correo/código.
- La salida de código pierde sangría y no promete ejecutabilidad; el raw permanece.
- Las entradas ya dañadas con `�` se conservan con incidencia, sin reconstrucción ficticia.

## 7. Caso integral y prueba de producto

El caso `complex_multilingual_ai_role_001` declara dos campos presentes y cuatro
`missing`. El título conserva ambas líneas originales dentro del mismo campo al
compactarlas. La descripción debe coincidir exactamente con §31.5 y tener cinco
anotaciones generadas: dos regiones CR y tres hints (warning, money_bag,
round_pushpin). Las seis listas contienen 11, 8, 11, 7, 6 y 10 elementos.

El inventario de §32 exige preservar evidencia económica de varias clases,
negaciones, restricciones geográficas, experiencia, tecnologías, contactos y la
instrucción de aplicación. No basta comparar una cadena larga: hay que verificar
asociaciones de continuación, origen, evidencia y ausencia de conclusiones semánticas.
Los offsets concretos se calculan y validan al materializar el fixture.

## 8. Decisiones de inicialización

| Decisión | Motivo y alcance |
|---|---|
| Python 3.14.7 con GIL | Última estable verificada y baseline normativo; no CPython 3.15 RC |
| uv 0.12.18 y `uv_build` 0.12.18 | Gestión y build fijados, sin añadir otro backend |
| Ruff 0.16.8 | Última estable verificada; lint y formato de código, sin reformatear la especificación |
| mypy estricto | Verificador de tipos solicitado por §21; versiones efectivas en lock |
| pytest e Hypothesis | Base para pruebas unitarias, regresión y propiedades |
| `>=3.14,<3.15` | Contrato de instalación de §21; reproducibilidad normativa usa 3.14.7 exacto |
| Cinco dependencias de runtime exactas | Adoptar la política validada, sin actualizar comportamiento incidentalmente |
| Layout `src` y wheel probado fuera del checkout | Evitar que imports locales oculten un paquete incompleto |
| Publicación de biblioteca | CD entrega artefactos Python; despliegue de un servicio corresponde al consumidor |
| Versiones separadas | Paquete 0.1.0 no significa especificación ni normalización 2.0 |
| Documentos y `AGENTS.md` | Memoria persistente revisable; no depender de memoria de una conversación |

La política funcional y sus tablas aún no se crean: requerirían decisiones exactas
y pruebas de corpus. Tampoco se crean módulos vacíos para aparentar implementación.

## 9. Decisiones pendientes antes de implementar contratos

La especificación es suficientemente precisa para iniciar, pero deja detalles de
representación a resolver mediante ADR y pruebas, sin modificar sus obligaciones:

| Tema | Resolución propuesta / puerta |
|---|---|
| Esquema de documento interno | Dataclasses congeladas, tuplas y payloads tipados; definir fases y unidades antes de reglas |
| JSON canónico | UTF-8, orden de claves definido, sin NaN/Infinity, orden estable de colecciones; fijar vectores de hash |
| IDs y repetición de texto | Incluir campo, referencia/hash de fuente, regla y posición de origen; evitar colisiones por texto idéntico |
| Fuente externa | Protocolo inyectado fuera de funciones puras; documentar quién garantiza persistencia y retención |
| `empty` con incidencias | Mantener incidencias aunque el estado de texto sea empty; formalizar precedencia en modelos |
| Atributos HTML inválidos | Incidencia y regla determinista documentada; no fabricar valores de negocio |
| Tablas Unicode y variantes exactas | Generación offline reproducible, versiones, licencias y revisión del diff antes de fijar perfil |
| Texto/código ambiguos | Reconocimiento léxico acotado y abstención; no clasificación semántica |
| Despliegue externo | Plataforma, volumen y SLO se acuerdan con datos; no inventar latencias objetivo |
| Publicación | Verificar disponibilidad/propiedad del nombre normietext y configurar Trusted Publisher |

## 10. Riesgos y controles de aceptación

| Riesgo | Control |
|---|---|
| Spans obsoletos después de reparación/NFC | Alineación compuesta y validación final; fixtures muchos-a-uno |
| Borrado de números o símbolos técnicos | Protecciones y T01–T40; gramática pictográfica restringida |
| Falsos positivos de listas | Contexto, abstención, regresiones negativas y precisión observada ≥99,5 % |
| HTML malformado/nativo | Backend fijo, límites previos, límites estructurales y aislamiento de worker |
| Pérdida sin auditoría | Fuente recuperable y registro por regla para cada transformación destructiva |
| Deriva por actualización | Lock, manifiesto, perfil versionado, revisión de corpus y benchmarks |
| Fuga de contenido en logs | IDs/códigos/contadores; raw y trace solo mediante acceso explícito |
| Sobreajuste al ejemplo largo | Corpus multilingüe autorizado separado por familias de duplicados |
| Confundir bootstrap con producto listo | Estado explícito, fases pendientes y puerta final de §26 |

## 11. Fuentes verificadas para herramientas

Consultadas durante la inicialización, además del documento del proyecto:

- [Python 3.14.7](https://www.python.org/downloads/release/python-3147/).
- [uv 0.12.18](https://github.com/astral-sh/uv/releases/tag/0.12.18).
- [Ruff 0.16.8](https://github.com/astral-sh/ruff/releases/tag/0.16.8).
- [uv en GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/).
- [checkout 7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1),
  [setup-uv 10.2.0](https://github.com/astral-sh/setup-uv/releases/tag/v10.2.0),
  [upload-artifact 7.0.1](https://github.com/actions/upload-artifact/releases/tag/v7.0.1),
  [download-artifact 8.0.1](https://github.com/actions/download-artifact/releases/tag/v8.0.1).

Los hashes de las acciones y versiones en los archivos son referencias fijas. Las
releases posteriores requieren actualización deliberada, no seguimiento de `latest`.
