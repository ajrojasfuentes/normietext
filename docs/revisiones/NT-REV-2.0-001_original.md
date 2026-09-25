### Documento formal: Revisión, correcciones y mejoras propuestas de `normietext` 2.0

**Identificador:** NT‑REV‑2.0‑001
**Título:** Propuesta de corrección y mejora de la especificación `normietext_v2.0_especificacion.md` y del `plan_implementacion.md`
**Fecha:** 2026‑09‑24
**Estado:** Propuesta aprobada en redacción, pendiente de integración
**Ámbito:** Fases 1–8 del plan de implementación; ninguna corrección altera los entregables de Fase 0
**Convenciones:** Las palabras DEBE, NO DEBE, PUEDE y SE RECOMIENDA se usan con el sentido de RFC 2119. Los identificadores de sección (§) refieren a la especificación 2.0; los identificadores F0–F8 refieren a las fases del plan. Los casos de prueba nuevos se numeran T41–T64 en continuidad con la matriz existente (T01–T40).

---

#### 1. Objeto y alcance

1.1. Este documento consolida las correcciones, cambios y mejoras identificados en la revisión completa de la especificación 2.0 y del plan de implementación de `normietext`, biblioteca local y determinista para normalizar texto de ofertas de empleo de LinkedIn sin uso de modelos de lenguaje.

1.2. Se distinguen tres categorías de hallazgo:

- **Error normativo:** regla cuya aplicación literal produce salida incorrecta o imposible.
- **Vacío de especificación:** caso real de entrada sin regla que determine su salida.
- **Mejora:** aclaración, redundancia, riesgo operativo o ajuste documental.

1.3. Prioridades:

| Prioridad | Significado |
|---|---|
| P1 | Bloquea la apertura de Fase 1. Error normativo o vacío que cambia el texto de salida. |
| P2 | DEBE resolverse antes de la fase que implementa la regla afectada. |
| P3 | Mejora documental u operativa; no bloquea ninguna fase. |

1.4. Toda modificación de los puntos 1 a 11 altera texto o anotaciones de salida y, conforme a §27.2, exige incremento de `normalization_version` y revisión de diferencias sobre el golden corpus cuando este exista.

---

#### 2. Resumen de hallazgos

| Nº | Sección | Categoría | Prioridad | Resumen |
|---|---|---|---|---|
| 1 | §23.1 | Error | P1 | Factor de expansión `16×` inferior a la expansión real de los hints (hasta 26×). |
| 2 | §13.6 | Error | P1 | La regla de separación concatena `C++Python`, `(Remote)LATAM`, `100%bonus`. |
| 3 | §14.2 | Error | P1 | Regla `N - texto` circular: una lista pura `1 - A / 2 - B` nunca se reconoce. |
| 4 | §14.2 | Ambigüedad | P1 | "Dos líneas vecinas compatibles" admite dos lecturas incompatibles. |
| 5 | §23.1 | Regla muerta | P3 | El límite total por registro (327.680) nunca es vinculante. |
| 6 | §7.1, §8.2, §10.4, §17 | Vacío | P1 | `job_criteria_list` carece de proyección para pares etiqueta–valor. |
| 7 | §10.4, §14.2, §17 | Vacío | P1 | Viñetas textuales dentro de HTML sin regla. |
| 8 | §13.3, §14.2 | Inconsistencia | P2 | `✅`, `✔`, `✓` producen tres resultados para la misma intención. |
| 9 | §13.6 | Vacío | P2 | Adyacencia token–token y token–símbolo sin regla. |
| 10 | §10.3, §10.4 | Vacío | P2 | Elementos HTML sin tratamiento; detalles del adaptador BS4/lxml. |
| 11 | §11, §12.2 | Inconsistencia | P2 | `fix_c1_controls=true` contradice la lectura natural de §12.2. |
| 12 | §31, F1, F6 | Riesgo | P2 | Fixture integral copiado desde Markdown; corrupción silenciosa de espacios y `\_`. |
| 13 | §8.1, §8.5, §23.2 | Ambigüedad | P2 | Precedencia de `status=empty`; incidencias de diagnóstico ausentes; alineación tras ftfy. |
| 14 | F1, F3, F4, F5, F7 | Trazabilidad | P2 | T31–T32 declarados cubiertos en F3 cuando dependen del renderer de F5; tareas faltantes. |
| 15 | §20.2, §21.1, §29, F0 | Documental | P3 | Referencia a documento no adjunto; versiones no auditables; nuevas claves de configuración. |

---

#### 3. Correcciones normativas (P1)

##### 3.1. §23.1 — Límite de expansión de salida

**Hallazgo.** El límite `max(1.024, 16 × longitud_entrada)` se mide en puntos de código de entrada. Un hint de un solo punto de código produce la siguiente expansión (token más SPACE separador):

| Entrada | Punto de código | Salida | Expansión |
|---|---|---|---|
| `✅` | U+2705 | `[emoji:check_mark_button] ` | 26× |
| `📍` | U+1F4CD | `[emoji:round_pushpin] ` | 22× |
| `❌` | U+274C | `[emoji:cross_mark] ` | 19× |
| `💰` | U+1F4B0 | `[emoji:money_bag] ` | 18× |
| `⚠` | U+26A0 | `[emoji:warning] ` | 16× |

Una descripción compuesta mayoritariamente por `✅` (patrón real: listas de requisitos) supera el límite de forma legítima y dispara `OUTPUT_INVARIANT_FAILED`, que §23.2 clasifica como error de implementación o política y bloquea la publicación.

**Texto normativo propuesto** (sustituye la fila correspondiente de la tabla de §23.1):

> | Longitud de salida por campo | Máximo `max(1.024, 32 × longitud_entrada)` |

**Párrafo adicional** (se añade tras la tabla):

> El factor 32 es un techo de seguridad, no una expectativa de salida. DEBE ser mayor o igual a la expansión máxima de cualquier token generado por el perfil, calculada como la longitud del token más largo más un separador, dividida por la longitud mínima de su secuencia de origen. El factor DEBE recalcularse al modificar la allowlist de §13.3. Superar el límite se registra como `OUTPUT_LIMIT_EXCEEDED` (fallo operativo sin salida parcial), distinto de `OUTPUT_INVARIANT_FAILED`, que se reserva para violaciones de las invariantes de §12 y §15.

**Cambios derivados.**
- §23.2: añadir `OUTPUT_LIMIT_EXCEEDED` en la fila `RESOURCE_LIMIT_EXCEEDED`.
- §29 (Apéndice A): añadir `output.max_expansion_factor: 32`.
- F7: prueba adversarial con ≥ 2.000 `✅` consecutivos; resultado esperado: salida válida, sin incidencia.

##### 3.2. §13.6 — Separadores alrededor de eliminaciones

**Hallazgo.** El texto vigente ("se inserta un espacio si ambos vecinos sobrevivientes inmediatos son letras, marcas o números; si uno es puntuación, espacio, salto de línea o límite de campo, no se inserta") trata toda puntuación como separador. En texto técnico la puntuación forma parte del token:

| Entrada | Regla vigente | Resultado correcto |
|---|---|---|
| `C++🚀Python` | `C++Python` | `C++ Python` |
| `C#🔥Java` | `C#Java` | `C# Java` |
| `(Remote)🌎LATAM` | `(Remote)LATAM` | `(Remote) LATAM` |
| `100%🔥bonus` | `100%bonus` | `100% bonus` |
| `Node.js🚀AWS` | `Node.jsAWS` | `Node.js AWS` |

**Texto normativo propuesto** (sustituye el primer párrafo de §13.6):

> La eliminación de un emoji o kaomoji DEBE evitar concatenar dos tramos que estaban separados exclusivamente por él. Se inserta un SPACE SALVO que se cumpla alguna de las siguientes condiciones sobre los vecinos sobrevivientes inmediatos:
>
> 1. Alguno de los dos vecinos es SPACE, LF o límite de campo.
> 2. El vecino siguiente es puntuación de cierre: `,` `.` `;` `:` `!` `?` `)` `]` `}` `"` `”` `»` `’` `…`.
> 3. El vecino anterior es puntuación de apertura: `(` `[` `{` `"` `“` `«` `‘` `¿` `¡`.
>
> En cualquier otro caso, incluidos vecinos como `+`, `#`, `%`, `/`, `$`, dígitos, o `)` seguido de letra, se inserta SPACE. El SPACE insertado queda sujeto a la reparación de hueco ante puntuación y al colapso de espacios del renderer (§15).

**Ejemplos que se añaden al bloque de §13.6:**

```text
C++🚀Python          -> C++ Python
(Remote)🌎LATAM      -> (Remote) LATAM
100%🔥bonus          -> 100% bonus
texto🍕, siguiente   -> texto, siguiente
```

Los ejemplos vigentes (`foo🚀bar`, `piña🍍`, `"piña🍍"`, `Benefits ✨`) se conservan y siguen cumpliéndose.

**Cambios derivados.** Ampliar T15–T17 con las tres primeras entradas del bloque anterior.

##### 3.3. §14.2 — Regla `N - texto`

**Hallazgo.** La condición "ordinal previo `N-1` o siguiente `N+1`" no define si el vecino debe ser un ítem ya reconocido o basta un prefijo léxico consecutivo. Bajo la primera lectura, `1 - Recruiter / 2 - Technical / 3 - Offer` es circular y nunca se reconoce. Bajo la segunda, sin restricción sobre el cuerpo, `1 - 2 years / 2 - 3 years` (rangos, T02) se activaría indebidamente.

**Texto normativo propuesto** (sustituye el ítem correspondiente de §14.2):

> - `N - texto` (guion ASCII o tipográfico rodeado de SPACE) se reconoce como ítem ordenado si se cumplen ambas condiciones:
>   - (a) el cuerpo no comienza con cifra, signo numérico, símbolo de moneda ni forma de rango;
>   - (b) dentro del mismo bloque, la línea inmediatamente anterior tiene prefijo ordinal `N-1` o la inmediatamente siguiente tiene prefijo ordinal `N+1`, donde el prefijo del vecino PUEDE ser cualquiera de los patrones admitidos en esta sección (`N.`, `N)`, `N.)`, keycap, número encerrado, o `N - texto` que cumpla a su vez la condición (a)).
>
>   La evaluación se realiza sobre prefijos léxicos, no sobre ítems ya reconocidos, de modo que una secuencia `1 - A / 2 - B / 3 - C` se reconoce completa en una sola pasada.

##### 3.4. §14.2 — Contexto de lista para `→` y guiones tipográficos

**Hallazgo.** "Al menos dos líneas vecinas compatibles dentro del mismo bloque" admite (i) el bloque contiene ≥ 2 líneas con el marcador, o (ii) cada línea requiere dos vecinas con el marcador. Bajo (ii), una lista de dos elementos nunca se reconoce y la primera y última línea de toda lista quedan excluidas. El caso integral (§31.5, bloque Benefits, once flechas) solo es consistente con (i).

**Texto normativo propuesto:**

> - `→`, `➜`, `–` y `—` seguidos de SPACE y contenido al inicio de línea se reconocen como viñetas únicamente si, dentro del mismo bloque (sin línea vacía intermedia), existen al menos dos líneas consecutivas que comienzan con el mismo marcador. Todas las líneas de esa secuencia se convierten. Una línea aislada se conserva literal.

##### 3.5. `job_criteria_list` — Proyección de pares etiqueta–valor

**Hallazgo.** §7.1 exige "conservar etiquetas, valores y asociaciones" y §17 "mantener asociaciones etiqueta–valor", pero no existe tipo de bloque ni proyección textual para pares. La estructura habitual de LinkedIn es:

```html
<ul>
  <li><h3>Seniority level</h3><span>Mid-Senior level</span></li>
  <li><h3>Employment type</h3><span>Full-time</span></li>
</ul>
```

Con §10.4 vigente, `<li>` produce `- ` y `<h3>` un encabezado dentro del ítem: la salida es indefinida. La tabla de §10.4 no contempla `<dl>/<dt>/<dd>` y ningún fixture ejercita el campo (§31.1 lo marca `missing`).

**Cambios normativos propuestos.**

- **§8.2** — añadir tipos de bloque `term` y `definition`, con atributo `pair_id` compartido y `parent_id` al contenedor.
- **§10.4** — añadir filas:

  > | `<dl>`, `<dt>`, `<dd>` | Par etiqueta–valor: bloques `term`/`definition` con `pair_id` compartido. |
  > | `<li>` cuyo primer hijo elemento es `<h1>`–`<h6>`, `<b>`, `<strong>` o `<dt>` y va seguido de texto o `<span>` | Par etiqueta–valor, no viñeta; se asigna `pair_id`. |

- **§17**, fila `job_criteria_list` — añadir:

  > Cada par se proyecta como una línea `Etiqueta: Valor` (dos puntos seguidos de SPACE). Si la etiqueta ya termina en `:`, el carácter no se duplica. Las listas sin estructura de par se proyectan como en `job_description`. Los metadatos `pair_id`, no el carácter `:`, son la fuente autoritativa de la asociación.

- **§31.1** — sustituir `missing` por un `job_criteria_list` HTML mínimo de cuatro pares (Seniority level, Employment type, Job function, Industries) y actualizar §31.5 en consecuencia, de modo que el caso integral ejercite los seis campos.

##### 3.6. Viñetas textuales dentro de HTML

**Hallazgo.** Patrón dominante en descripciones pegadas desde procesadores de texto: `<p>• Item</p><p>• Item</p>` y `<li>• Item</li>`. §17 habilita la heurística de listas de texto plano solo para descripción y criterios, sin indicar si aplica al texto de origen HTML; un `list_item` DOM cuyo contenido comienza por `•` produciría `- • Item`.

**Texto normativo propuesto** (se añade a §14.2):

> Los marcadores textuales de esta sección se evalúan también sobre el texto de bloques `paragraph` y `line` procedentes de HTML, con las mismas condiciones de contexto. Dentro de un `list_item` de origen DOM, un marcador textual redundante al inicio del contenido (`•`, `-`, `▪`, `◦`, `‣`, `→` seguidos de SPACE, o un ordinal del mismo valor que el asignado por el DOM) se consume y se registra como edición `list.redundant_marker`. NUNCA se emite doble marcador. Si el ordinal textual difiere del ordinal DOM, el texto se conserva literal, el ordinal DOM se registra en metadatos y se emite la incidencia `LIST_ORDINAL_CONFLICT`.

**Nota que se añade bajo la tabla de §10.4:**

> Una secuencia de `<p>` o `<div>` consecutivos cuyo texto comienza con un marcador de §14.2 se reconoce como lista según las reglas de texto plano; el DOM no la contradice porque no declara lista alguna.

---

#### 4. Correcciones previas a la fase afectada (P2)

##### 4.1. §13.3 y §14.2 — Marcas de verificación como viñetas

**Hallazgo.** Para la misma intención visual el perfil produce tres resultados:

| Entrada | Punto de código | Resultado vigente |
|---|---|---|
| `✅ Python` | U+2705, allowlist | `[emoji:check_mark_button] Python`, sin `list_item` |
| `✔ Python` | U+2714, emoji fuera de allowlist | `Python` (viñeta perdida) |
| `✓ Python` | U+2713, no emoji | `✓ Python` literal |

Lo mismo aplica a `●`, `■`, `➢`, `➤`, `»`, `*` y `✔️`.

**Decisión recomendada.**

- **§14.2** — ampliar los marcadores textuales con `●`, `■`, `➢`, `➤`, `✓`, `✔`, `✔️`, `»` y `* ` (asterisco + SPACE), todos sujetos a la condición de ≥ 2 líneas consecutivas del §3.4 para no capturar énfasis Markdown aislado.
- **§13.3** — un hint de la allowlist (`✅`, `❌`, `⚠️`) al inicio de línea, seguido de SPACE y contenido, en una secuencia de ≥ 2 líneas consecutivas con hint inicial, genera además un `list_item` con `marker_style: hint`; la proyección es `- [emoji:check_mark_button] Python`. Se conserva la polaridad y se recupera la estructura.
- Alternativa admisible: mantener la proyección vigente y declarar en §13.3 que los hints iniciales NO son viñetas y que la pérdida de estructura es una pérdida autorizada. La especificación DEBE elegir explícitamente una de las dos opciones.
- Verificar §31.5: las líneas `⚠️ NOTE`, `💰 Compensation` y `📍 …` no forman secuencias de dos líneas consecutivas con hint inicial; su salida no cambia bajo ninguna de las dos opciones.

##### 4.2. §13.6 — Adyacencia token–token y token–símbolo

**Hallazgo.** "Los tokens conservados se separan de palabras adyacentes mediante espacios cuando sea necesario" no define "palabra" ni "necesario". Casos abiertos: `🇨🇷🇲🇽`, `💰$5.000`, `Costa Rica🇨🇷,`.

**Texto normativo propuesto:**

> Todo token generado se emite rodeado de SPACE por ambos lados. El renderer colapsa SPACE duplicados y aplica la reparación de hueco ante puntuación de cierre. Resultados de referencia: `🇨🇷🇲🇽` → `[flag:CR] [flag:MX]`; `💰$5.000` → `[emoji:money_bag] $5.000`; `Costa Rica🇨🇷,` → `Costa Rica [flag:CR],`.

##### 4.3. §10.3 y §10.4 — Elementos HTML sin regla y adaptador

**Filas que se añaden a la tabla de §10.4:**

| Elemento | Tratamiento |
|---|---|
| `<hr>` | Límite de bloque; sin texto. |
| `<blockquote>` | Bloque `paragraph` con `origin_tag: blockquote`; sin prefijo textual. |
| `<s>`, `<del>`, `<strike>` | Conservar texto; anotación `struck_text` con span. Evidencia (p. ej. `<s>$50k</s> $60k`) que el consumidor debe poder descartar. |
| `<ins>`, `<u>`, `<mark>`, `<small>` | Inline; conservar texto. |
| `<sup>`, `<sub>` | Inline; conservar texto sin insertar SPACE (`m<sup>2</sup>` → `m2`). |
| `<caption>` | Línea previa a la tabla con `parent_id` de la tabla. |
| `<thead>`, `<tbody>`, `<tfoot>` | Transparentes; `<th>` marca `header: true` en la celda. |
| `<img alt="…">` | Proyectar `alt` como texto inline con anotación `alt_text`; `alt` vacío o ausente no produce texto. |
| `<input>`, `<button>`, `<select>`, `<iframe>`, `<noscript>` | Excluir del texto; conservar en fuente. |

**Notas que se añaden a §10.3:**

> - Beautiful Soup con `lxml` envuelve los fragmentos en `<html><body>`. El adaptador DEBE operar sobre el contenido de `body` y NO DEBE emitir límites de bloque por esa envoltura.
> - lxml/libxml2 no trata `<template>` como contenido inerte. La exclusión de `<template>` de §10.4 DEBE implementarse explícitamente en el adaptador.
> - `<p>Hola</p><p>mundo</p>` produce LF; `<span>Hola</span><span>mundo</span>` produce `Holamundo` por la regla de inline. Este comportamiento es intencional.

##### 4.4. §11 y §12.2 — Controles C1 y `fix_c1_controls`

**Hallazgo.** §12.2 establece que los controles `Cc` (salvo LF) se eliminan, pero ftfy se ejecuta antes con `fix_c1_controls=true`, que reinterpreta U+0080–U+009F como cp1252 (U+0092 → `’`, U+0080 → `€`, U+0093/U+0094 → `“ ”`). En la práctica los C1 casi nunca llegan a §12.2 y ningún T‑case fija el comportamiento.

**Texto normativo propuesto** (se añade a §11 tras el párrafo sobre NEL):

> `fix_c1_controls=true` convierte los controles C1 (U+0080–U+009F, excepto NEL, ya tokenizado en la etapa previa) a su interpretación cp1252 antes de la etapa de invisibles. Es una decisión deliberada: esos controles proceden casi siempre de texto Windows‑1252 mal decodificado y su valor tipográfico (`’`, `“`, `”`, `€`, `…`) constituye evidencia útil. En consecuencia, la eliminación de `Cc` de §12.2 alcanza solo a C0 y a los C1 que ftfy no haya reescrito. La conversión se registra como edición `encoding.c1_reinterpreted`.

##### 4.5. §31, F1 y F6 — Fidelidad del fixture integral

**Hallazgo.** El texto raw de §31 contiene espacios internos múltiples (`Flask   y`, `pipelines  +`), sangrías significativas (continuaciones, fragmento Python), el kaomoji `¯\_(ツ)_/¯` y tres LF consecutivos. Un editor con *trim trailing whitespace*, un formateador Markdown o un renderizador que interprete `\_` corrompen el fixture silenciosamente. El plan indica "copiar con fidelidad" desde el `.md`.

**Cambios propuestos.**

- F1: crear `tests/fixtures/integral/complex_multilingual_ai_role_001/job_title.raw.txt` y `job_description.raw.txt` (y `job_criteria_list.raw.html` conforme a §3.5), tratados como binarios (`-text` en `.gitattributes`), con SHA‑256 registrado en `fixture.json`.
- §31: declarar que los bloques de §31.2–31.5 son copia ilustrativa y que la fuente autoritativa es el archivo con hash.
- F1: test que verifique el hash y la presencia de señales frágiles: al menos una secuencia de ≥ 3 SPACE, una línea con sangría ≥ 6 columnas, el kaomoji exacto y tres LF consecutivos.
- Repositorio: `.editorconfig` con `trim_trailing_whitespace = false` para `tests/fixtures/**`.

##### 4.6. §8.1, §8.5 y §23.2 — Estados, incidencias y alineación

- **§8.1**, añadir:

  > `empty` prevalece cuando el texto final es la cadena vacía, aunque existan incidencias; estas se conservan en `issues[]`. `ok_with_issues` requiere texto no vacío y al menos una incidencia.

- **§23.2**, añadir como incidencias no fatales:

  | Código | Condición | Efecto |
  |---|---|---|
  | `POSSIBLE_HTML_IN_PLAIN_TEXT` | ≥ 2 etiquetas bien formadas de la tabla §10.4 en un campo declarado `plain_text` | Ninguno sobre el procesamiento; diagnóstico de adaptadores. Compatible con la prohibición de autodetección. |
  | `GENERATED_TOKEN_COLLISION` | El raw ya contenía una cadena con forma de token generado (`[flag:XX]`, `[emoji:…]`) | Ninguno; complementa §8.4. |
  | `LIST_ORDINAL_CONFLICT` | Ordinal textual distinto del ordinal DOM (§3.6) | Texto conservado literal. |

- **§8.5**, añadir:

  > Cuando `fix_encoding` altera una unidad, la procedencia de esa unidad se degrada a `segment` salvo que la reparación conserve longitud carácter a carácter. F4 NO DEBE intentar construir un mapa exacto a través de ftfy.

---

#### 5. Mejoras documentales y de plan (P3 y trazabilidad)

##### 5.1. §23.1 — Límite total por registro

Suma de límites por campo: 8.192 + 262.144 + 32.768 + 4.096 + 4.096 + 8.192 = **319.488** < 327.680. El límite de registro nunca es vinculante. Opciones: (a) eliminar la fila; (b) fijarlo en un valor vinculante (p. ej. 294.912 = 262.144 + 32.768) documentado como presupuesto de memoria por registro; (c) conservarlo con nota explícita de que no es alcanzable con los límites por campo vigentes. SE RECOMIENDA (b) o (c). La prueba de F7 DEBE reflejar la opción elegida.

##### 5.2. Plan de implementación — Correcciones de trazabilidad

| Fase | Cambio |
|---|---|
| F1 | Añadir tareas: fixtures de `job_criteria_list` (T47–T49); patrón `<p>•` (T50–T53); archivos raw con hash del caso integral (§4.5). |
| F3 | Cambiar T31 y T32 de "cubiertos" a "cubiertos estructuralmente"; en F3 se verifican únicamente `blocks` (tipo `code`; `table_cell` con `row`/`column`). Las aserciones textuales (ausencia de sangría, ` \| ` entre celdas) pasan a F5. |
| F4 | Añadir T62–T64 y la expectativa de alineación `segment` tras reparación (§4.6). |
| F5 | Añadir T41–T46 y T54–T61 a la matriz de salida de fase. |
| F7 | Añadir la prueba adversarial de expansión (§3.1); ajustar la prueba del límite por registro (§5.1). |
| Matriz RF ↔ fases | RF‑04 enlaza con `term`/`definition`; RF‑10 con `list.redundant_marker`. |

##### 5.3. Observaciones documentales

- El plan referencia `desarrollo_y_release.md`, no incluido en el conjunto revisado. DEBE adjuntarse al repositorio o eliminarse la referencia.
- §21.1 afirma versiones concretas (Python 3.14.7, lxml 6.1.3, regex 2026.9.10, emoji 2.16.0, uv 0.12.18, Ruff 0.16.8). En esta revisión solo se confirmó externamente beautifulsoup4 4.15.0. F0 DEBE dejar un artefacto auditable (`uv.lock` con hash o salida de `uv pip freeze`) citado desde §21.1.
- §20.2: indicar que la corrección ortográfica del alias `rol_responsabilities_list` es responsabilidad del consumidor, no del serializador.
- §29 (Apéndice A): incorporar las claves `output.max_expansion_factor`, `structure.hint_as_list_marker`, `structure.extra_text_markers`, `html.struck_text_annotation`.

---

#### 6. Matriz de casos de prueba nuevos (T41–T64)

| ID | Área | Entrada | Resultado obligatorio |
|---|---|---|---|
| T41 | Listas | `1 - Recruiter\n2 - Technical\n3 - Offer` | `1. Recruiter\n2. Technical\n3. Offer` |
| T42 | Listas | `1 - 2 years\n2 - 3 years` | Conservar (condición a) |
| T43 | Listas | `1 - Intro\n\n2 - Detalle` | Conservar (sin continuidad en el mismo bloque) |
| T44 | Listas | `→ Health insurance\n→ Remote budget` | `- Health insurance\n- Remote budget` |
| T45 | Listas | `→ Health insurance` aislada en párrafo | Conservar |
| T46 | Listas | `– 3 años exp.\n– B2 English` | `- 3 años exp.\n- B2 English` |
| T47 | Criterios | `<li><h3>Seniority level</h3><span>Mid-Senior level</span></li>` en `job_criteria_list` | `Seniority level: Mid-Senior level`; `term`/`definition` con `pair_id`; sin `list_item` |
| T48 | Criterios | `<dl><dt>Industries</dt><dd>Software, Fintech</dd></dl>` | `Industries: Software, Fintech` |
| T49 | Criterios | HTML de T47 en `job_description` | Misma proyección (regla estructural, no por campo) |
| T50 | HTML + listas | `<p>• Python</p><p>• AWS</p>` | `- Python\n- AWS`; dos `list_item` con mismo `list_id` |
| T51 | HTML + listas | `<ul><li>• Python</li></ul>` | `- Python`; edición `list.redundant_marker` |
| T52 | HTML + listas | `<ol><li>1. Recruiter</li><li>2. Technical</li></ol>` | `1. Recruiter\n2. Technical` |
| T53 | HTML + listas | `<ol start="3"><li>1. X</li></ol>` | Conservar texto; `LIST_ORDINAL_CONFLICT`; ordinal DOM en metadatos |
| T54 | Marcadores | `✔ Python\n✔ AWS` | `- Python\n- AWS` |
| T55 | Marcadores | `✓ Python\n✓ AWS` | `- Python\n- AWS` |
| T56 | Marcadores | `✅ Python\n❌ Visa` | `- [emoji:check_mark_button] Python\n- [emoji:cross_mark] Visa` (o alternativa declarada en §4.1) |
| T57 | Marcadores | `* Python` aislado en párrafo | Conservar |
| T58 | Separación | `🇨🇷🇲🇽` | `[flag:CR] [flag:MX]` |
| T59 | Separación | `💰$5.000` | `[emoji:money_bag] $5.000` |
| T60 | Separación | `Costa Rica🇨🇷, pero` | `Costa Rica [flag:CR], pero` |
| T61 | HTML | `<span>Hola</span><span>mundo</span>` / `<p>Hola</p><p>mundo</p>` | `Holamundo` / `Hola\nmundo` |
| T62 | Encoding | `don\u0092t` | `don’t`; edición `encoding.c1_reinterpreted` |
| T63 | Encoding | `a\u0085b` | `a\nb` |
| T64 | Encoding | `a\u0001b` | `ab` |

Adicionalmente: ampliar T15–T17 con `C++🚀Python`, `(Remote)🌎LATAM` y `100%🔥bonus`; añadir la prueba adversarial de expansión (§3.1) a la capa 9 de §24.2.

---

#### 7. Plan de aplicación

| Orden | Puntos | Hito |
|---|---|---|
| 1 | §3.1–§3.4 (errores normativos) | Nueva revisión de la especificación antes de abrir F1. |
| 2 | §3.5, §3.6, §4.5 | Tareas de F1 (fixtures y contratos). |
| 3 | §4.1, §4.2, §4.3, §4.4, §4.6 | Cierre antes de F3–F5 según la etapa afectada. |
| 4 | §5.1, §5.2, §5.3 | Limpieza documental y del plan; no bloqueante. |

---

#### 8. Registro de decisiones pendientes

| Nº | Decisión | Opciones | Responsable |
|---|---|---|---|
| D1 | Proyección de hints iniciales (§4.1) | Viñeta con hint / hint sin estructura | Propietario de la especificación |
| D2 | Límite total por registro (§5.1) | Eliminar / valor vinculante / nota explícita | Propietario de la especificación |
| D3 | Contenido definitivo del `job_criteria_list` del caso integral (§3.5) | Cuatro pares propuestos u otro conjunto | Propietario de fixtures |

---

*Fin del documento NT‑REV‑2.0‑001.*

Si querés, el siguiente paso puede ser producir el texto final integrado de §13.6, §14.2 y §23.1 completos (versión sustitutiva, no diff) o el `fixture.json` y estructura de archivos del caso integral para F1.
