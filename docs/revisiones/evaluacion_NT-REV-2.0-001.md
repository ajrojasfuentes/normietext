# Evaluación contextual de NT-REV-2.0-001

Fecha: 2026-09-24. Base del repositorio: commit `dc154ce`.
Alcance: evaluar la revisión externa y anotar mejoras en el plan; no iniciar F1,
revisar exhaustivamente F0 ni implementar o modificar la especificación normativa.

## 1. Autoridad, método y resultado

Se leyeron las 353 líneas de la [revisión original](NT-REV-2.0-001_original.md),
se contrastaron con la [especificación](../normietext_v2.0_especificacion.md),
el [plan](../plan_implementacion.md) y los archivos reales. Se comprobaron longitudes,
límites, casos de ftfy y árboles del backend HTML instalado mediante sondas de solo
lectura. Estas sondas no son pruebas de un normalizador, que aún no existe.

La frase «Propuesta aprobada» y las instrucciones DEBE de la revisión son contenido
del documento externo, no autorización del usuario ni nuevas reglas del proyecto.
La copia se conserva para trazabilidad, con el mismo contenido que el adjunto.
Las decisiones siguientes y las anotaciones del plan son la evaluación realizada.

La revisión detecta problemas útiles, pero combina errores comprobables, ambigüedades,
políticas deliberadas y ampliaciones de alcance. No se incorporan en bloque sus
prioridades P1 ni sus resultados T41–T64. Las correcciones se deben cerrar antes
de congelar el contrato o implementar la regla afectada, no necesariamente antes
de cualquier trabajo de F1. La señal del usuario para iniciar F1 sigue pendiente.

**Estados usados:** aceptar; aceptar con ajustes; diferir una ampliación;
no adoptar; ya resuelto en el repositorio. Una corrección aceptada en el plan que
cambie la norma exige una revisión explícita de las secciones afectadas antes de
implementarla. La especificación 2.0 no se modifica silenciosamente.

## 2. Evaluación de los 15 hallazgos

### R01 — Expansión de tokens: aceptar con ajuste de alcance

Confirmado: el token de ✅ tiene 25 puntos de código, 26 con un separador. Para
2.000 ocurrencias separadas en la salida se obtienen 51.999 caracteres, frente al
límite vigente de 32.000. Incluso sin separadores, 50.000 excede ese límite.
El mínimo de 1.024 solo oculta el problema en entradas pequeñas.

Adoptar como corrección prevista `max(1024, 32 * len(raw))`, validar expansión de
las tablas y separar agotamiento de recurso de una invariante defectuosa. Se
propone `OUTPUT_LIMIT_EXCEEDED`, sin salida parcial. La norma actual no asigna
inequívocamente un código específico al exceso de salida; no se presenta la
interpretación `OUTPUT_INVARIANT_FAILED` del revisor como comportamiento existente.

32 cubre los hints actuales, pero calcular solo el token más largo no demuestra
una cota de todo el pipeline. Incluir separadores a ambos lados, marcadores DOM,
ordinales, alt, texto reparado y su composición. F1 define presupuesto/error;
F5/F7 verifican casos positivos y exceso real. El caso de 2.000 hints debe pasar
sin error de límite; no se impone «sin incidencia» si hubiera otro diagnóstico legítimo.

### R02 — Eliminación junto a sintaxis técnica: aceptar con ajustes

`C++🚀Python`, `C#🔥Java`, `(Remote)🌎LATAM` y `100%🔥bonus` revelan una limitación
real de la regla puramente alfanumérica. Evitar esas fusiones mejora el objetivo
de conservar evidencia técnica. `Node.js🚀AWS`, en cambio, ya satisface la regla
vigente porque sus vecinos inmediatos son `s` y `A`; no es un nuevo defecto.

No adoptar literalmente «insertar espacio salvo apertura/cierre» para todos los
signos: las comillas rectas tienen dos funciones y secuencias como `C🚀++`,
`C🚀#`, `foo🚀/bar` o `$🚀500` requieren una decisión reproducible. El reemplazo
propuesto podría fragmentar sintaxis que hoy se conserva, y no demuestra que esos
nuevos resultados sean deseables.

Planificar una tabla léxica acotada de fronteras técnicas, con casos positivos y
negativos, sin inferir significado. Separar los cuatro ejemplos confirmados,
mantener los T15–T17 actuales, preservar `81,4 %` y limitar el ajuste al hueco
editado. Cerrar la tabla antes de F5; no generalizar la limpieza de puntuación.

### R03 — Ordinales `N - texto`: aceptar la aclaración, no ampliar signos implícitamente

La circularidad es una lectura posible, no una imposibilidad de la norma: el
pipeline ya distingue tokens y estructura. Hacer explícita la evaluación de
prefijos léxicos vecinos válidos resuelve la ambigüedad en una pasada. Cada
candidato, incluido el vecino usado como evidencia, debe superar los guardas de
cuerpo numérico/rango, contexto protegido, bloque y campo.

Aceptar T41–T43. Conservar el guion ASCII que ya define este patrón; incorporar
guiones tipográficos o nuevos límites monetarios a la gramática requiere enumerar
su alcance y contraejemplos, no aprovechar una aclaración para ampliar las reglas.
No atravesar líneas vacías ni reconocer listas en títulos o código.

### R04 — Vecindad para flechas/guiones: aceptar con alcance explícito

Precisar que dos líneas consecutivas compatibles forman una secuencia y que ambas,
incluidos extremos, se convierten. No exigir dos vecinos por elemento. Definir
compatibilidad por marcador y contenedor; la opción conservadora para casos nuevos
es mismo marcador, mismo nivel, sin línea vacía ni segmento protegido.

El requisito de mismo marcador reduce una ambigüedad; debe hacerse explícito en
una revisión, con casos mixtos conservados hasta tener regla. No añadir `➜` por
analogía: es una ampliación de catálogo independiente. Añadir negativos de rangos,
signos y líneas aisladas. Aceptar T44–T46 con esos guardas y contexto de descripción.

### R05 — Presupuesto total de registro: aceptar la observación, conservar el valor

La suma es 319.488, menor que 327.680. El límite agregado es redundante bajo los
límites predeterminados, no un fallo de corrección. Elegir la opción (c): conservar
327.680 y documentarlo como presupuesto independiente para configuraciones futuras.
No reducirlo arbitrariamente a 294.912 sin datos de memoria o carga.

En F7 probar la configuración predeterminada y el límite agregado usando una
configuración validada con límites individuales ampliados o total menor. Una prueba
que intenta exceder el agregado con todos los límites predeterminados válidos es
imposible. No confundir puntos de código con una cota de memoria de un worker.

### R06 — Etiquetas y valores: aceptar el vacío de cobertura, acotar el reconocimiento

Se necesitan fixtures reales o sintéticos de criterios y proyección de asociaciones
explícitas. `<dl>/<dt>/<dd>` aporta estructura útil; `term`/`definition` y un ID de
asociación son una solución de esquema razonable a revisar en F1. Debe soportar
varios términos o definiciones, entradas vacías, anidamiento y HTML roto, sin
forzar un `pair_id` uno-a-uno ni rellenar valores ausentes.

No aceptar la regla general «li cuyo primer hijo es h3/b/strong implica par».
`<li><h3>What you will do</h3><span>Build APIs</span></li>` puede ser un ítem con
encabezado; convertirlo en `What you will do: Build APIs` altera su estructura.
En LinkedIn, asociaciones adicionales deben provenir de un contrato de adaptador
versionado o metadatos explícitos, no del nombre del campo ni de negrita sola.

La proyección `Etiqueta: Valor` es candidata para asociaciones explícitas simples;
resolver multiplicidades, etiquetas con colon y spans antes de congelar el esquema.
T47/T49 requieren adaptar su expectativa; T48 justifica soporte de la estructura dl.
No reemplazar los cuatro `missing` del caso integral por datos inventados. Crear
otro fixture que ejercite los seis campos. Añadir criterios al original dejaría
tres campos missing, por lo que tampoco cumpliría la promesa de cubrir los seis.

### R07 — Marcadores textuales en HTML: aceptar con precedencia y negativos

Extender el análisis léxico a texto de bloques HTML en descripción/criterios es
útil; el formato de origen no debería ocultar un marcador explícito. Definir qué
párrafos/div consecutivos comparten contexto, sin cruzar tablas, código, contenedores
independientes o listas anidadas. Capturar esas fronteras en F3 y resolver en F5.

Consumir un marcador redundante dentro de un ítem DOM solo si la equivalencia está
probada: tipo de lista compatible, prefijo real, mismo ordinal si es ordenada y
ningún contexto protegido. No borrar cualquier guion/flecha inicial dentro de li:
puede ser un signo, una expresión o contenido intencional.

`list.redundant_marker` y `LIST_ORDINAL_CONFLICT` son adiciones útiles. Ante conflicto
preservar número textual y ordinal DOM, sin hacerlos concordar artificialmente.
Fijar la proyección exacta antes de F5: «conservar texto» del T53 no define por sí
solo si habrá prefijo DOM adicional. No aplicar la prohibición de doble marcador
redundante a dos números que realmente difieren.

### R08 — Nuevas viñetas y hints: no adoptar la ampliación; explicitar la política actual

Resultados distintos para ✅, ✔ y ✓ son coherentes con una allowlist exacta y la
prohibición de equivalencias por parecido. No es una inconsistencia demostrada.
La intención visual no puede darse por idéntica en todos los contextos.

Elegir la alternativa conservadora ofrecida por el revisor: un hint inicial no
crea por sí solo un `list_item` en texto plano. Conservar token y anotación; un li
explícito del DOM sí conserva estructura. El caso integral no cambia.

Diferir `● ■ ➢ ➤ ✓ ✔ ✔️ » *` y `➜` hasta contar con corpus y evaluación de falsos
positivos; en particular `*`, `»` y flechas tienen otros usos. No abrir opciones
configurables para políticas no implementadas. T54/T55 sirven como observaciones
del perfil vigente, no como obligaciones de convertirlos a guion. T56 usará la
alternativa sin lista inferida. T57 es regresión de preservación válida.

### R09 — Adyacencia de tokens: aceptar, ajustando el renderer

Aceptar las expectativas T58–T60 para tokens adyacentes, moneda y región ante coma.
Definir separación como propiedad de tokens generados, no con reemplazos sobre
cualquier cadena que parezca `[flag:...]` ni con espacios insertados irrestrictamente.

El renderer puede emitir separadores blandos que colapsan en bordes y respetan
puntuación de apertura/cierre. La propuesta «rodear de SPACE y reparar cierres»
produciría, por ejemplo, un espacio espurio tras `(` en `(🇨🇷)`. Añadir ese caso,
comillas, corchetes, comienzo/final de campo y tokens literales. Conservar espacios
originales ajenos a la edición y calcular spans después del resultado final.

### R10 — Tabla HTML más completa: aceptar una parte, no exclusiones amplias

Aceptar tratamiento explícito de hr, blockquote, caption, agrupaciones de tabla y
header de th; conservar inline de ins/u/mark/small, sup/sub y alt diferenciado.
En sup/sub conservar también su relación de origen: `m2` no acredita preservar
por sí solo la distinción tipográfica. Usar anotaciones de representación cuando
sean necesarias, sin convertirlas en interpretación numérica.

Aceptar `struck_text` para s/del/strike, conservando el texto y su span. Es evidencia
de marcado, no una orden al parser de descartar una oferta o salario. DOM wrappers
sintéticos no deben añadir límites ni eliminar contenido recuperado. Recorrer body
cuando corresponda, pero no asumir ciegamente que siempre existe o contiene toda
la información del fragmento. La exclusión de template ya existe y debe ser explícita.

No excluir en bloque button/select/noscript: pueden contener instrucciones, opciones
o contactos. Iframe no se carga y no se ejecuta nada; ello no autoriza a borrar
texto fallback sin política. Input no aporta automáticamente texto de atributos.
Definir comportamiento conservador y fixtures antes de ampliar exclusiones; el raw
conservado no justifica pérdidas no autorizadas en la proyección.

`<p>Hola</p><p>mundo</p>` necesita un límite de párrafo, pero §10.4 no fija por sí
sola uno o dos LF. Documentar la decisión del renderer antes de asignar el golden;
no convertir la preferencia por un LF de T61 en una corrección ya obligatoria.
`<span>Hola</span><span>mundo</span>` sí implica `Holamundo` por la regla inline actual.

### R11 — C1 y NEL: aceptar pruebas/aclaración, no cambiar la precedencia

No hay contradicción entre reparar C1 y eliminar los Cc restantes: §18 ya determina
el orden. Las sondas en ftfy 6.3.1 confirman `don\u0092t` → `don’t`, U+0080 → `€`,
y un C1 sin conversión útil como U+0081 permanece. C0 U+0001 también permanece en
ftfy y debe eliminarse posteriormente, no atribuirse al reparador.

La llamada directa con NEL produce elipsis; esto confirma por qué el adaptador debe
tokenizar NEL antes de ftfy. T63 debe ejercitar el pipeline compuesto y declarar
un campo multilineal: un campo compacto termina con SPACE, no LF. No adoptar la
afirmación empírica «casi siempre Windows-1252» sin corpus que la sostenga.

Registrar transformaciones reales; `encoding.c1_reinterpreted` solo cuando el código
propio pueda atribuirla. Una explicación de ftfy puede ser encode/decode y no tener
una operación con ese nombre. No inventar atribuciones ni ediciones sin cambio.
La [configuración oficial](https://ftfy.readthedocs.io/en/latest/config.html) y la
[API de explicaciones](https://ftfy.readthedocs.io/en/latest/explain.html) respaldan
el uso acotado; las salidas concretas anteriores se verificaron localmente.

### R12 — Fidelidad de fixtures: aceptar, sin desplazar la norma automáticamente

Materializar archivos raw y expected UTF-8, hashes de bytes y verificación de señales
frágiles. Extraer bloques desde el Markdown fuente, no desde su renderizado. La
primera copia requiere cotejo independiente: un hash no detecta que se copió mal
antes de calcularlo. Fijar si el LF previo al cierre del fence es contenido o formato.

Planificar excepciones de `.gitattributes` para impedir conversión de EOL en archivos
raw/expected exactos y `.editorconfig` sin trim ni inserción automática de newline.
`-text` basta para evitar conversión; no es necesario deshabilitar diffs textuales.
Leer bytes o desactivar universal newlines en fixtures de CRLF/CR para no normalizar
las entradas al cargarlas. Verificar también expected, no solo raw.

La especificación sigue siendo normativa; no declarar sus bloques meramente
ilustrativos hasta una migración explícita que vincule archivos, hashes y revisión.
El caso original mantiene identidad y missing; la cobertura adicional vive aparte.

### R13 — Estados, diagnósticos y alineación: aceptación selectiva

Aceptar `empty` si text == "", conservando issues; de otro modo `ok_with_issues` si
hay incidencias, y `ok` si no. Un fallo sigue siendo un error separado, no empty.

Aceptar `LIST_ORDINAL_CONFLICT` donde exista conflicto real. No añadir por defecto
`POSSIBLE_HTML_IN_PLAIN_TEXT` por contar etiquetas: penaliza ejemplos técnicos
legítimos y no demuestra un error de adaptador. Diagnóstico optativo en ingesta
puede evaluarse después, sin reinterpretar formato.

No considerar un token literal una incidencia automática: §8.4 ya lo admite y las
anotaciones resuelven procedencia. `GENERATED_TOKEN_COLLISION` sería como mucho una
herramienta optativa de observación, no un nuevo estado de calidad por defecto.

Después de ftfy, usar procedencia `segment` cuando no haya mapa demostrado. Rechazar
la excepción «misma longitud implica exactitud»: igualdad de tamaños no demuestra
correspondencia carácter a carácter. Tampoco prohibir todo mapa exacto futuro;
permitirlo únicamente con evidencia y pruebas, como §8.5 ya exige.

### R14 — Trazabilidad entre fases: aceptar y completar

Corregir F3: T31/T32 están cubiertos estructuralmente en el documento interno, no
como resultados finales. F5 prueba ausencia de sangría, separadores de tabla y spans
finales. T64 es composición reparación→invisibles, no solo una prueba unitaria de
ftfy en F4. La semilla de T62/T63 puede comprobarse en F3/F4 y su resultado final en F5.

Distribuir regresiones nuevas entre modelado F1, estructura F3, léxico F4, renderer
F5 y recursos F7. Añadir referencia de RF-04/RF-10 sin comprometerse a heurísticas
genéricas de pares o a todas las nuevas viñetas rechazadas.

### R15 — Documentación, versiones y configuración: mayormente ya resuelto o no aplicable

`docs/desarrollo_y_release.md` existe y está versionado en `dc154ce`. También existe
`uv.lock`, con versiones y hashes de distribuciones; la guía registra versiones
efectivas y validación local. Que no estuvieran en el conjunto visto por el revisor
no significa que falten. No hace falta regenerarlos o afirmar que son inverificables.
Añadir en una futura revisión de §21 enlaces a esos artefactos es útil.

Mantener el alias externo `rol_responsabilities_list` en el adaptador de serialización
cuando lo exija un consumidor: es compatibilidad de nombres, no corrección semántica
en el cleaner. La propuesta de cambiar el responsable no mejora el contrato actual.

Solo añadir opciones de configuración realmente adoptadas y validadas, incluidas en
hash y pruebas. Presupuesto de salida, variantes estructurales explícitas y marcado
HTML pueden requerir campos; no añadir `hint_as_list_marker` o `extra_text_markers`
como interruptores para comportamiento diferido.

No todas las observaciones cambian salida: enlaces, trazabilidad y hashes pueden
ser documentales. Un cambio conductual respecto de una baseline congelada requiere
versionar reglas, y el esquema si afecta su contrato. Como aún no hay perfil
implementado/publicado, registrar decisiones para la primera baseline sin inventar
incrementos independientes por cada observación editorial. No cambiar versión del
paquete durante esta tarea documental.

## 3. Destino de T41–T64

Se conserva el número del revisor para comparar, pero no se incorporan como casos
normativos ya aprobados por la especificación 2.0. F1 inventariará solo las
expectativas adoptadas y las pendientes claramente etiquetadas.

| IDs | Destino en el plan | Condición |
|---|---|---|
| T41–T43 | Aceptar, F1/F5 | Vecinos léxicos, guardas y ausencia de cruce de bloques |
| T44–T46 | Aceptar con alcance, F1/F5 | Mismo marcador y negativos de rangos/protección |
| T47 | Adaptar, F1/F3/F5 | No inferir par por h3; contrato de origen o conservar lista |
| T48 | Aceptar con diseño, F1/F3/F5 | Asociación dl explícita; multiplicidad y renderer definidos |
| T49 | No adoptar salida exigida | Mantener contraejemplo de falso par en descripción |
| T50–T52 | Aceptar con guardas, F3/F5 | Contexto HTML, equivalencia DOM y renderer no duplicado |
| T53 | Aceptar objetivo, completar golden en F5 | Preservar ambos ordinales y registrar conflicto |
| T54–T55 | No adoptar conversión propuesta | Cubrir política actual; expansión de marcadores diferida |
| T56 | Elegir alternativa conservadora | Tokens/anotaciones, sin lista plana inferida por hints |
| T57 | Aceptar | Asterisco aislado preservado |
| T58–T60 | Aceptar con renderer de tokens, F5 | Agregar apertura/cierre y tokens literales |
| T61 | Separar aserciones, F3/F5 | Inline ya definido; LF de párrafos necesita regla explícita |
| T62 | Aceptar con atribución comprobada, F4/F5 | No exigir etiqueta de edición ficticia de ftfy |
| T63 | Aceptar, F3/F4/F5 | NEL antes de reparar; distinguir compacto/multilineal |
| T64 | Aceptar, F4/F5 | ftfy conserva C0; etapa de invisibles lo elimina |

Añadir regresiones propias: expansión de 2.000 hints y límite excedido; separación
junto a C++/C#/porcentaje/paréntesis; `(🇨🇷)`; listas dentro de código; ordinales
DOM/texto conflictivos; múltiples dt/dd; pérdidas potenciales en button/noscript;
empty con incidencias; hash de raw/expected y carga de CRLF sin conversión.

## 4. Decisiones D1–D3 y puertas

- **D1:** mantener hints sin lista plana inferida; DOM explícito conserva su lista.
- **D2:** mantener límite agregado 327.680 y documentar redundancia predeterminada.
- **D3:** preservar el integral original; añadir fixtures separados de criterios y
  de seis campos presentes con entradas explícitas, sin inferir datos del anuncio.

Antes de congelar F1: contratos de asociaciones explícitas, estados, presupuesto,
fuentes de fixtures y esquema de incidencias. Antes de F3: política de elementos
HTML y metadatos necesarios. Antes de F5: fronteras léxicas, proyección de pares,
ordinales conflictivos, párrafos y tokens. F7 mide recursos y cierra aceptación.
Las reglas que cambien la norma deben quedar integradas explícitamente antes de
codificarse; esto no es autorización para ejecutar ninguna fase en esta tarea.

## 5. Evidencia y reproducibilidad de esta evaluación

SHA-256 de bytes de los documentos examinados (antes de anotar el plan):

| Artefacto | SHA-256 |
|---|---|
| Adjunto / copia original | `03866da4eead9866bcbd75abeb0e1111018d5d8883643da0499af9e968d094f2` |
| Especificación 2.0 | `9e8baf2d886f5052058244308db9b58d786ae870fa7b7abe486dcef71364b75e` |
| uv.lock | `e99b4599cf4fc924c05830e5c25ed883152c67628b59f64cb36c5ac9fa58b8a2` |

Sondas: `uv run --locked python`, CPython 3.14.7, ftfy 6.3.1, Beautiful Soup 4.15.0,
lxml 6.1.3. Se usaron las cuatro opciones de reparación de §11. Se comprobaron
longitudes con `len`, suma de límites y `fix_encoding_and_explain`; se inspeccionaron
árboles HTML con `BeautifulSoup(raw, "lxml")` sin acceso de red desde el parser.
La configuración del parser de producción sigue siendo una tarea de F3, no una
consecuencia de esta sonda. La [documentación de lxml](https://lxml.de/parsing.html)
sirve de referencia para configurar las opciones y recuperación, no de sustituto
para las pruebas del backend concreto.

No se modificaron fuente, dependencias, lock, workflows, tests ni especificación.
Las comprobaciones documentales finales verifican enlaces, referencias, hashes y
diff; no se presenta una ejecución de producto inexistente como evidencia.
