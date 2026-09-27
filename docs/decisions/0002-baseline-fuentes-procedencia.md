# ADR-0002 — Baseline, fuentes, procedencia y manifiesto

Fecha: 2026-09-25. Estado: adoptado para Fase 2, autorizada por el usuario.
Base: commit `c3111e4`, [ADR-0001](0001-contratos-fase-1.md) y
[Fase 2 del plan](../plan_implementacion.md#6-fase-2--baseline-fuentes-procedencia-y-manifiesto).

## Alcance y frontera

Se implementan las bases de validación, recuperabilidad, alineación, identidad,
serialización, manifiesto y proyección de espacios/NFC. No se introduce
`JobTextNormalizer`, ni conversión HTML/entidades, reparación ftfy, reconocimiento
estructural o eliminación de emoji. No se ejecuta la baseline como sustituto de
las fases léxicas: `render_baseline` devuelve `TrackedText`, nunca `NormalizedField`.
Debe usarse después de capturar estructura y secuencias; en F2 se ejercita con
entradas controladas. Los goldens del corpus de producto no se modifican.

## Validación y fuente

`prepare_input` verifica campo, formato, tipo y tamaño antes de recorrer Unicode.
Un campo ya construido se valida con `validate_input`; `validate_record` añade
el presupuesto agregado, independiente del presupuesto de cada campo. Los errores
no truncan texto ni lo sustituyen por un resultado vacío.

`RejectedInputError.rejected` conserva el objeto original, incluso bytes, None o
sustitutos aislados. Es un sobre local de ingesta, excluido deliberadamente del
serializer canónico y de su representación de diagnóstico. No se usa surrogatepass.
El host decide cómo retener entradas que no son texto Unicode válido.

Se añade `SourceEvidence.source_sha256`, opcional en construcción por compatibilidad
con los contratos iniciales sin publicar. `from_input` lo calcula sobre los bytes
UTF-8 exactos, sin NFC ni cambio de EOL. La validación canónica exige el digest cuando
solo hay referencia; los resultados de registro lo cotejan contra la entrada.
Este hash verifica identidad; la recuperabilidad sigue requiriendo raw o almacén.

`recover_source` recupera raw local o verifica un `SourceStore` explícito.
`persist_source` es una operación de **ingesta**, anterior al núcleo: el almacén
promete persistencia durable antes de retornar y referencias inmutables; se exige
lectura posterior coincidente antes de retirar raw. Se verifican campo, formato,
referencia, adaptador, longitud y contenido, también cuando cambia sin variar tamaño.
Si el almacén asigna una referencia a un input sin ella, ingesta usa el sobre
recuperado con esa referencia para formar el registro que procesará el núcleo.

No se suministra un backend remoto ni se llama al almacén desde renderer,
procedencia, serialización o validación canónica. Una implementación externa puede
hacer I/O durante ingesta. La lectura posterior prueba identidad en ese momento;
no demuestra durabilidad futura. Esa garantía corresponde al host, no a un booleano
inventado por la biblioteca. Fallos de recuperación usan `SOURCE_UNAVAILABLE` y
`SOURCE_MISMATCH`; no son resultados canónicos alternativos.

## Alineación compuesta

`Alignment` cubre la proyección con segmentos contiguos, no vacíos y sin huecos.
Cada segmento apunta a la fuente inicial. `linear=True` se reserva para tramos
copiados con correspondencia exacta punto a punto; una sustitución de igual longitud
no obtiene ese atributo automáticamente.

`TrackedText.replace` recibe ediciones ordenadas y disjuntas, comprueba límites y
calcula el tamaño proyectado antes de ensamblar la salida. Conserva tramos copiados
y compone los tramos sustituidos con su origen previo. No conserva snapshots de
cada etapa. Las eliminaciones quedan en `Edit`, aunque no produzcan texto.

Una regla puede declarar `exact_source=True` cuando conoce el intervalo completo
que consume, por ejemplo un símbolo exacto convertido en token. Eso admite una
relación uno-a-muchos, pero no una correspondencia por carácter: recortar parte de
esa proyección degrada a `segment`. Una procedencia imprecisa nunca se vuelve exacta
por esa declaración. Unir tramos separados por contenido eliminado también degrada.
Una sustitución sin mapa explícito mantiene `segment`; `field` no inventa offsets.

`origin_for` resuelve la procedencia de un intervalo final. `project` devuelve la
envolvente final conservadora de un intervalo fuente, incluidos bloques vacíos o
eliminados. En correspondencias no lineales puede abarcar más contenido y no acredita
exactitud. Los bloques fuente vacíos mantienen un span vacío; un ancla ambigua
usa el borde izquierdo, sin declarar exactitud. Los adaptadores/renderer posteriores conservarán IDs estructurales para
resolver casos más finos; F2 no pretende reconstruir un DOM a partir de alineación.

`render_baseline` conserva todos los componentes de emoji e invisibles. Convierte
separadores explícitos, compacta espacios/bordes y aplica NFC por unidades de grafema.
La pasada final con unicodedata comprueba el resultado completo; si aparece una
composición entre unidades, se usa un segmento conservador. La autoridad de grafemas
(regex) y la de NFC pueden tener versiones Unicode distintas, siempre manifestadas.
Los spans se proyectan sobre el texto final. Los timeouts son errores operativos.

## Identificadores y JSON canónico

La identidad fuente es SHA-256 de un objeto con dominio `normietext.source.v1`,
campo, formato, SHA-256 del raw, referencia y versión del adaptador. El ID de una
aparición es SHA-256 de un objeto de dominio `normietext.id.v1` con namespace,
identidad fuente, regla, origen completo, ordinal de aparición y discriminador.
Para ediciones, el discriminador contiene intervalo de la etapa y reemplazo, y el
ordinal es su posición en el registro de ediciones. Repeticiones de texto en
posiciones distintas no comparten ID. `tests/vectors/stable_id_v1.json` fija un
vector construido independientemente con hashlib/json, no con el generador probado.

`serialization.py` enumera explícitamente los miembros de cada tipo. Incluye
propiedades derivadas como field, status y phase; no usa asdict como API implícita.
JSON usa UTF-8 estricto, Unicode sin escapes ASCII, claves ordenadas, separadores
compactos y ningún newline final. No acepta NaN, Infinity, sustitutos, conjuntos ni
objetos no registrados. Los mapas ordenan claves; listas de contenido conservan
orden semántico. El orden original de un payload no cambia sus bytes canónicos.

Campos de registro siguen JobField; bloques/asociaciones siguen orden documental.
Anotaciones/ediciones/issues se ordenan por bloque de origen, intervalo de origen,
precisión, intervalo visible si existe, regla, ID/código y bytes como desempate.
El contenedor de campo aporta el campo y la identidad fuente. Dependencias y
artefactos ordenan por nombre. No se incluyen tiempos ni datos operativos del host.
El serializer no es un deserializador de objetos arbitrarios ni interpreta fases.

## Manifiesto y build

El hash de política incorpora toda configuración efectiva, incluidos límites, y
los artefactos verificados del perfil, con versiones y hashes. El manifiesto añade
esquema/reglas/perfil, revisión de código, versión del paquete, CPython/UCD, backend,
libxml2 efectivo y compilado, dependencias directas/transitivas de runtime,
clasificación Unicode/tablas y huellas de distribución instalada. El descriptor de
Python incluye ABI/GIL, plataforma y arquitectura, sin hostname ni rutas locales.
Su digest identifica el descriptor, no pretende ser el hash del ejecutable.

Los fingerprints `installed:*` usan bytes de archivos distribuidos, omitiendo
bytecode y metadatos de instalación variables; **no son hashes de wheels**.
`wheel_artifact` obtiene nombre/versión de METADATA, comprueba la versión instalada
y calcula SHA-256 de un archivo wheel real. Ingesta/despliegue debe suministrar los
archivos efectivamente utilizados; la función no certifica por sí sola su historial
de instalación. `create_manifest(wheels=..., require_wheels=True)` exige el
inventario de las ocho dependencias de runtime. Un manifiesto local sin esos
archivos sigue identificando contenidos instalados, pero no declara disponer de
recibos de wheels. No se escoge arbitrariamente un hash del lock como si fuera el
artefacto usado. La adopción en producción se controla en F7/F8.

Se calculan una vez las huellas de dependencias y tablas por proceso, bajo el
contrato de entorno instalado inmutable; cambiarlo exige reiniciar el consumidor.
La huella de código se comprueba en la construcción del manifiesto.

`scripts/build_distribution.py` construye en un árbol temporal y empaqueta
`data/build_info.json`. La revisión es `git:<commit>`; con cambios locales añade
`+tree:<huella de código>`. No se presenta un checkout modificado como un commit
limpio. El build fija SOURCE_DATE_EPOCH a la fecha del commit, sin contaminar el
resultado semántico con timestamps. CI usa el wrapper y continúa construyendo el
wheel desde el sdist. No se escribe metadata generada en el árbol de trabajo.

Un consumidor verifica la huella de código y lee la revisión empaquetada, sin Git.
Un checkout editable o un `uv build` directo sin stamping queda identificado como
`source-tree:<huella>`: es reproducible, pero no afirma una revisión Git. El smoke
test de distribución exige el stamping del flujo recomendado. No se cambian pins
ni se añaden dependencias de runtime.

## Reutilización canónica y límites de aceptación

`validate_canonical` exige un NormalizedField y el manifiesto efectivo esperado;
una discrepancia produce POLICY_MISMATCH y exige reprocesar desde fuente. Revalida
referencias, spans, tokens visibles, fuente, límites, NFC, SPACE/LF, compactación y
caracteres prohibidos según tablas. Devuelve el mismo objeto inmutable compatible.
El manifiesto esperado explícito debe proceder de inicialización confiable, nunca
del documento recibido. La validación no recupera fuentes mediante I/O.

Esta es la puerta **base**: la aceptación de todas las reglas emoji, estructura,
solidus y reparación se integra en F4/F5. No prueba que un autor haya ejecutado el
pipeline por construir un NormalizedField. T38/T39 del normalizador completo siguen
pendientes; el replay de F2 cubre únicamente la baseline y los contratos presentes.

F2 no modifica las proyecciones normativas ni congela una release funcional nueva.
Paquete 0.1.0, esquema/reglas 1.0.0 y perfil inicial permanecen como baseline inicial
sin publicar. El digest de configuración/código sí refleja la implementación real.
