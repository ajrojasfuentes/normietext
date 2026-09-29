# ADR-0005 — Estructura, símbolos y API funcional

Fecha: 2026-09-29. Estado: decisiones de implementación de F5, conforme al plan §9/18.

## Decisiones normativas previas

- La vista virtual de prefijos oculta emoji eliminables e invisibles, conserva
  hints y marcadores candidatos. Los vecinos son candidatos léxicos, no resultados
  ya convertidos. Dos líneas contiguas de igual marcador (`→`, `–` o `—`) y
  sangría bastan. Una línea vacía, código, celda o contenedor distinto corta el
  contexto. `N - texto` necesita vecino ordinal N±1; el cuerpo no empieza por
  número o signo numérico. No se amplía el catálogo por parecido visual.
- Prefijos encerrados U+2460–U+2473 y U+24EA conservan su valor, sin NFKC global.
  Los ordinales ASCII tienen como máximo 64 dígitos; fuera de ese límite se
  conservan literalmente. La gramática no consume decimales ni versiones.
- Las listas DOM prevalecen. Un prefijo textual equivalente se sustituye bajo
  `list.redundant_marker`. Un ordinal diferente se conserva: `<ol start="3"><li>1.
  X</li></ol>` produce `3. 1. X`, con `LIST_ORDINAL_CONFLICT`.
- Párrafos HTML separados usan dos LF. Div/br y elementos contiguos de una lista
  usan un LF; párrafos contiguos reconocidos como ítems usan un LF. Encabezados
  y contenedores mantienen límites explícitos, sin añadir líneas vacías a cada
  elemento. Las celdas compactan LF interno a SPACE y se separan con ` | `;
  cada fila mantiene LF. Celdas vacías y spans de celdas siguen en metadatos.
- Una asociación explícita con un término y una definición se proyecta como
  `término: definición`; asociaciones múltiples mantienen cada miembro en su
  propia línea, sin duplicar valores ni inferir pares. Los grupos se separan
  por LF. Miembros faltantes permanecen ausentes.
- Tras eliminar emoji/kaomoji, se separan letras/marcas/números adyacentes.
  Se extiende únicamente al vecino izquierdo que termina en sufijo técnico
  `+`/`#` tras alfanumérico, `%` tras número o cierre `)`/`]`/`}` tras contenido,
  y vecino derecho alfanumérico. Ejemplos: `C++🚀Python` → `C++ Python`,
  `C#🔥Java` → `C# Java`, `(Remote)🌎LATAM` → `(Remote) LATAM`,
  `100%🔥bonus` → `100% bonus`. Negativos: `C🚀++` → `C++`,
  `$🚀500` → `$500`, `"piña🍍"` → `"piña"`. No se generaliza a comillas,
  guiones, prefijos monetarios o toda puntuación. Invisibles no insertan SPACE.
- Tokens generados se separan de letras/marcas/números, moneda y otros tokens
  generados; se conservan aperturas/cierres: `(🇨🇷)` → `([flag:CR])`,
  `💰$500` → `[emoji:money_bag] $500`. Tokens literales no generan anotación.
- Cualquier modificación de una protección por reglas globales queda registrada
  con `PROTECTED_SPAN_MODIFIED`, incluidos espacios/NFC de código. Kaomoji en
  protecciones permanecen. Solidus y heurísticas de lista respetan protecciones.

## Contrato de entrega

La API de campo convierte, repara, reconoce, estructura, transforma y renderiza
una vez. `canonicalize` acepta fases convertida/reparada/léxica y resultado
canónico compatible; la reentrada canónica valida sin ejecutar reparación.
La API de registro conserva los seis sobres y fallos por campo; `strict=True`
propaga el primer fallo de normalización. El presupuesto agregado se comprueba
antes de procesar campos. No se llama a SourceStore desde transformaciones.

La alineación temporal del renderer refiere al texto reparado exclusivamente para
transportar spans; la trazabilidad publicada sigue apuntando a raw. IDs de bloques
de origen y asociaciones se conservan. IDs nuevos usan origen y posición estable.
Los spans se finalizan después de NFC; ningún matching de texto repetido establece
precisión raw. No se regenera ningún esperado a partir de la implementación.

Se conserva la primera baseline no publicada de reglas/esquema 1.0.0 y paquete
0.1.0. F6–F8 conservan sus puertas de calidad, rendimiento y release.

## Implementación y comprobaciones

Las reglas se agrupan en `structure.py` (decisiones sobre offsets reparados),
`symbols.py` (emoji/kaomoji/invisibles/solidus) y `stages/rendering.py` (proyección y
spans). No se crean wrappers vacíos para cada regla del árbol ilustrativo de §22.
`api.py` conecta ese flujo con las etapas F3/F4 y validación canónica.

Las continuaciones y listas hijas amplían el span del elemento padre. Los
marcadores DOM vacíos o con solo sublistas tienen proyección propia; una alineación
auxiliar distingue inserciones que comparten offsets, sin inventar precisión raw.
Las celdas vacías conservan spans vacíos con ancla conservadora a la izquierda;
fila/columna, tabla y asociaciones son autoritativas, nunca la posición de `|`.

La validación de reentrada comprueba tokens generados/payload, marcadores y
referencias, además de Unicode/espacios/manifiesto. No vuelve a reconocer contenido
como nueva fuente: una combinación visible surgida por borrar invisibles no
habilita reinterpretación de formato, nuevas anotaciones ni otra reparación.

Las propiedades detectaron dos bordes corregidos: selectores dentro de candidatos
pictográficos ambiguos y variantes de marcadores con selector fuera del catálogo
exacto de emoji. Se preservan las marcas textuales y se retiran los selectores;
el gesto aislado sigue la acción de su base, sin convertirlo en lista.

El renderer evita segmentar grafemas si el texto ya está en NFC. El presupuesto
regex cubre matching, sin incluir la construcción Python de ediciones. Una cadena
que sí requiere NFC sigue recorriendo grafemas con timeout operativo comprobado.
Esto permite los 2.000 hints (51.999 caracteres) sin elevar el límite del perfil.
