# ADR-0004 — Reparación única y análisis léxico con procedencia

Fecha: 2026-09-28. Estado: adoptado para F4, autorizada por el usuario junto con
la corrección de entidades decimales largas. Base: `e012932`, cierre de F3.

## Alcance y fases

Se añaden stages/encoding.py y stages/lexing.py. El flujo disponible es
convert_source → repair_document → lex_document. Sus fases son converted,
repaired y lexed; ninguna equivale a canonical. JobTextNormalizer y la aplicación
de reglas de listas/símbolos permanecen en F5. Se trabaja en el checkout actual;
no se realiza commit, push ni publicación.

RepairedDocument amplía el contrato convertido con manifiesto efectivo,
converted_length y registros EncodingRepair. Mantiene IDs, asociaciones,
anotaciones y alineación. EncodingRepair identifica intervalo convertido, intervalo
reparado, origen inicial, edición y explicación inmutable de ftfy. Los intervalos
de reparación se validan contra ambas longitudes y su texto contra la edición.

LexedDocument contiene ese documento, tokens, protecciones e issues acumulados.
Cada LexicalToken tiene ID, clase, span reparado, origen inicial, candidato de acción,
payload inmutable y referencias a bloques/protecciones. Los tokens cubren exactamente
el texto, ordenados y sin solapamientos. Una colección vacía cubre únicamente texto
vacío. Las protecciones pueden superponerse a tokens; no sustituyen la partición.

La serialización enumera estos miembros explícitamente. Los tipos nuevos se
exportan; las funciones viven en normietext.stages.encoding y .lexing. La reentrada
compatible devuelve la misma instancia y no repite ftfy ni acumula ediciones/issues.
El manifiesto efectivo completo debe coincidir; un cambio requiere fuente original.
Un consumidor no debe convertir el texto intermedio en FieldInput para continuar.

## Entidades numéricas largas

El adaptador escapado antes delegaba números decimales arbitrariamente largos a
html.unescape, cuyo int podía exceder el límite global de Python y filtrar ValueError.
Ahora retira ceros iniciales, compara longitud/valor con el máximo Unicode y solo
entrega una referencia numérica acotada a html.unescape. Valores superiores producen
U+FFFD. HTML5 sigue gobernando C1, sustitutos, nulos y no caracteres. No se cambia
sys.set_int_max_str_digits ni se convierte un entero enorme (decimal o hexadecimal).

La operación registra el intervalo original completo, incluidos ceros y semicolon
cuando exista. El resultado no se vuelve a decodificar. Se prueban valores fuera
de rango y referencias válidas con 5.000 ceros, ausencia de semicolon y propiedades
contra HTML5 para valores numéricos equivalentes acotados. La corrección concreta
§10.2 sin cambiar sus proyecciones ni sus formatos.

## Reparación y límites

Se valida presupuesto de fuente y proyección antes de invocar ftfy. Un documento
convertido debe tener alineación completa y sus separadores ya tokenizados a LF.
Se divide por LF y bordes de bloques/anotaciones, sin compactar texto. Los bordes
anotados evitan que una reparación amplíe un enlace sobre texto ajeno. b/span no
crean por sí solos una frontera, por lo que un mojibake repartido entre inline
transparentes puede repararse. Celdas, asociaciones y código mantienen sus límites.

Cada unidad se entrega una vez a fix_encoding_and_explain con restore_byte_a0=False,
replace_lossy_sequences=False, decode_inconsistent_utf8=True y fix_c1_controls=True.
La convergencia interna de ftfy pertenece a su algoritmo fijado; no se itera el
pipeline ni se vuelve a interpretar el origen. No se usa fix_text ni se repara
marcado o atributos HTML globalmente. No se aplica NFC final todavía.

Solo los cambios reales generan encoding.fix_encoding y explicación. U+0081 puede
recibir una explicación de ftfy sin cambiar; no genera una edición ficticia. NEL
literal ya es LF; C0 y C1 sin reparación útil sobreviven para F5. U+FFFD permanece
con REPLACEMENT_CHARACTER_PRESENT. No se afirma haber recuperado información perdida.

TrackedText compone ediciones a raw. Una reparación sin mapa carácter a carácter
usa segment, incluso con longitud igual; HTML conserva field. Un mapa local
convertido→reparado reproyecta los spans intermedios, pero su fuente auxiliar nunca
se publica como raw. Los cambios segment generan ORIGIN_PRECISION_REDUCED; las
incidencias HTML previas también permanecen.

Limitación comprobada: con estas opciones, ftfy transforma `Ã and café C++ B2+`
en `à and café C++ B2+`; `Ã` aislado permanece. La configuración normativa no
promete ausencia universal de falsos positivos. Se registra esta limitación en
un fixture propio y se preserva la explicación. No se añade una heurística ad hoc
ni se cambia silenciosamente decode_inconsistent_utf8. La evaluación sobre tráfico
real y cualquier revisión de política corresponden a sus puertas posteriores.

## Contextos protegidos

Código DOM/metadatos BlockKind.CODE tiene precedencia. Se reconocen además fences
con al menos tres backticks o tildes al inicio de una línea tras espacio/TAB; su
cierre usa el mismo carácter, longitud suficiente y solo espacio después. Un fence
sin cierre protege hasta el final del documento. Los spans incluyen delimitadores.
Los backticks inline requieren runs de igual longitud y no cruzan LF. No se infiere
un lenguaje por palabras, sangría o apariencia de Python, ni se interpreta Markdown
completo. Bloques code DOM anidados se agrupan por superposición.

URL: http/https/ftp o www., sin distinguir mayúsculas del esquema, hasta espacios,
ángulos, comillas dobles o backticks. Se excluye puntuación periférica final y
cierres no balanceados, conservando parámetros y paréntesis balanceados. No se
navega ni valida el destino. Correo: local-part ASCII conservador con + y signos
permitidos, dominio con puntos y sufijo alfabético. No se convierten formas [at],
no se certifica validez RFC completa y puede haber abstención en direcciones
internacionales o inusuales. Código precede a URL, y URL a correo.

Los huecos de texto se dividen también en los bordes de contexto: una protección no
se propaga al texto ordinario vecino. Emoji e invisibles dentro de código/contactos
siguen reconocidos. La incidencia PROTECTED_SPAN_MODIFIED se decidirá en F5 cuando
se aplique una modificación, no durante reconocimiento sin edición.

## Secuencias y precedencias

Los patrones se compilan una vez con regex.VERSION1 | regex.UNICODE. Propiedades
pictográficas, modificadores e invisibles provienen de tablas del perfil verificadas;
los reconocimientos léxicos de letras/marcas usan regex fijado y manifestado. Cada
operación regex tiene el timeout del perfil y traduce TimeoutError a REGEX_TIMEOUT.
emoji.analyze aporta spans catalogados; se ignoran explícitamente valores no emoji
que la versión instalada puede emitir con join_emoji=False.

La selección de intervalos usa prioridad explícita, longitud descendente, posición
y clase como desempate, sin depender del orden de descubrimiento. Orden de captura:

1. Símbolos ©/®/™ protegidos, con sus selectores.
2. Pares regionales anclados al inicio de cada corrida; el sobrante es incompleto.
3. Keycaps completos, sin borrar dígitos/#/* aislados.
4. Candidatos pictográficos con marcas no clasificadas: conservar e informar.
5. Catálogo emoji y gramática pictográfica maximal, sin letras/cifras consumidas.
6. Marcadores textuales, kaomoji delimitados, invisibles residuales y LF.

Después de capturar una unidad completa se consulta la tabla exacta de regiones,
subdivisiones y hints. Así ⚠ + ZWJ + fuego no se fragmenta para convertir únicamente
su prefijo en hint. Las subdivisiones conservan toda su secuencia de etiquetas.
🇦🇦🇨🇷 produce pareja inválida AA y pareja CR; no se desplaza a una coincidencia AC.
Los símbolos desconocidos fuera de la gramática se mantienen como texto.

Las acciones keep/remove/token/contextual son candidatos, no cambios aplicados.
Los marcadores enumerados y sus selectores de presentación permanecen contextual;
F5 decidirá campo, comienzo de línea, vecindad, redundancia DOM y conflictos. Los
hints no desaparecen de la futura vista virtual. Keycaps y símbolos protegidos
conservan base en payload; F5 puede retirar sus componentes de presentación.
Kaomoji dentro de contexto protegido se conserva como candidato keep; cualquier
ampliación destructiva allí requiere una decisión explícita posterior.

No se añaden marcadores por parecido ni se infieren listas a partir de hints.
Se conservan sangrías y relaciones previas, suficientes para el análisis estructural
posterior. No se aplican las decisiones pendientes de fronteras técnicas, párrafos,
asociaciones múltiples o ordinales conflictivos de F5.

## Evidencia y versiones

Los 23 fixtures lexical declaran resultados intermedios independientes; no sustituyen
T01–T40 ni el integral. Se añade propiedad de partición/reentrada/procedencia y replay
con cuatro PYTHONHASHSEED, además de regresiones de entidades y contextos. El smoke
test instalado ejercita ambas etapas y fases desde el wheel stamped.

Se preservan pins, lock, tablas, goldens previos y sus hashes. Paquete 0.1.0 y
contratos iniciales 1.0.0 siguen siendo la primera baseline sin release funcional;
los hashes de código/manifiesto reflejan el cambio. Las concreciones normativas
quedan explícitas en §§10.2, 11.1 y 18.1, sin anticipar la aceptación de F5–F8.
