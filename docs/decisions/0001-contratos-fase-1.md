# ADR-0001 — Contratos y corpus de la primera baseline

Fecha: 2026-09-24. Estado: adoptado para F1, siguiendo el plan revisado y la
instrucción del usuario de comprobar F0 y continuar con F1.

## Alcance

F0 queda verificada localmente: lock, sincronización, Ruff, mypy, pytest, build,
Twine e importación aislada. Los workflows ya configurados permanecen sujetos a
su ejecución remota; configurar PyPI corresponde a una release funcional, no es
prerrequisito para desarrollar contratos. No se publica ni se promete normalización.

Se trabaja sobre el checkout actual preservando las anotaciones previas sin commit.
No se realiza commit ni push como parte de esta entrega.

## Modelos y validación

Dataclasses congeladas y colecciones tuple; los payloads usan `FrozenMap`, que
copia estructuras JSON recursivamente, rechaza no finitos, claves no textuales,
sustitutos y ciclos/profundidad mayor de 64. No se usa un dict mutable detrás de
un modelo congelado. Los enums son tipos explícitos: los constructores Python no
coercionan strings arbitrarios, bool a int ni bytes a texto.

`FieldInput` valida campo/formato/tipo/Unicode; los límites operativos se configuran
aquí y se ejecutarán en F2. `InputField` es la suma etiquetada present/missing/error;
`JobInputRecord.from_mapping` exige las seis claves exactas y ordena por `JobField`.
El constructor por tupla exige ese mismo orden. Una entrada inválida antes de crear
FieldInput debe permanecer en el sobre del sistema de ingesta; el cleaner no logra
recuperabilidad externa con un hash o con una mera cadena de referencia.

`SourceEvidence` conserva raw local o una referencia con longitud declarada. En F1
se comprueba el contrato; F2 implementa su recuperación y garantías de almacén.
`Origin` usa exact/segment con span o field sin afirmación posicional. Los modelos
comprueban límites, IDs, referencias y ciclos, pero no calculan correspondencias.
Los IDs de bloques fuente viven en el documento de origen, no se confunden con IDs
canónicos. Los ordinales pueden ser cero o negativos si un ol lo declara válidamente.

Las asociaciones explícitas agrupan términos y definiciones sin asumir uno-a-uno;
pueden faltar términos o valores, pero no todos. Los bloques vacíos usan spans
vacíos. Solo dl/dt/dd o un contrato de adaptador explícito aportan la relación.
Los nuevos tipos de anotación conservan representación (tachado, alt, enlaces,
super/subíndice); no resuelven hechos semánticos. Su emisión pertenece a F3–F5.

`ParsedDocument` significa convertido y todavía no reparado. `NormalizedField`
tiene fase canónica de solo lectura; su constructor valida integridad estructural,
no acredita que se hayan ejecutado las reglas. El pipeline de F2–F5 debe comprobar
invariantes, manifiesto y compatibilidad aunque reciba un modelo ya construido.
No se ofrece un método que marque un string como normalizado ni un stub de API.

`empty` prevalece para texto vacío, conservando issues. Un fallo es `FieldFailure`,
no un NormalizedField. Un registro con ausencias o errores es partial; all-missing
es missing; seis campos presentes procesados correctamente es ok. Que un campo
correcto esté vacío no lo convierte en ausente. La opción estricta de publicación
del registro es responsabilidad futura de la fachada, no de estos contenedores.

## Política y cambios normativos

Se integran explícitamente en §§8/23/29/31 R01, R05, R06, R12 y R13: factor 32 y
`OUTPUT_LIMIT_EXCEEDED`, presupuesto agregado independiente, asociaciones,
precedencia empty y fidelidad de fixtures. Las observaciones R02–R04/R07/R09/R10
que requieren renderer siguen anotadas y no se implementan anticipadamente.

El perfil inicial acepta solo su comportamiento normativo; las opciones desconocidas
o cambios de comportamiento sin soporte se rechazan. Los límites positivos pueden
configurarse por separado; factor de expansión mínimo 32. Están agrupados en
`limits`, evitando duplicar la misma autoridad entre input/output. Configuración
JSON y esquema empaquetados documentan todos los campos. La versión del software
sigue siendo 0.1.0; esquema y reglas 1.0.0 identifican la primera baseline, no un
normalizador ya publicado ni una compatibilidad funcional garantizada.

## Serialización prevista (F2)

El serializer no usará `dataclasses.asdict` como contrato público implícito. Se define
un mapping explícito para cada modelo, incluyendo propiedades como field/status/
phase. JSON UTF-8 con claves ordenadas lexicográficamente, sin NaN/Infinity,
separadores compactos y sin timestamps; enums por value. Orden de campos = JobField;
bloques y asociaciones por orden del documento; anotaciones/ediciones por origen,
posición y regla con ID como desempate. Mapas de payload ordenan sus claves al
serializar; su orden de construcción no cambia el hash canónico. SHA-256 usa esos
bytes. El hash de política incluye opciones efectivas, tablas y versiones; no `hash()`.

El manifiesto tiene tipos para versiones, hashes de tablas y artefactos de runtime;
su generación efectiva y los vectores de replay corresponden a F2. No se inventan
hashes de wheels ni revisión de código en resultados de producción durante F1.

## Tablas y licencias

`generate_tables.py` usa emoji 2.16.0 para regiones/subdivisiones y regex 2026.9.10
para propiedades Unicode 17.0.0, de acuerdo con la [documentación de esa versión](https://pypi.org/project/regex/2026.9.10/).
NFC permanece en CPython/UCD 16.0.0. Los rangos
son intervalos de puntos de código semiabiertos, no bytes. El generador no usa red.
Hacer `--check` compara bytes; no actualiza datos durante normalización.

Los hints enumeran base y variantes FE0E/FE0F para los cinco símbolos de la allowlist;
no se añaden sinónimos o nuevas marcas. Catálogo kaomoji exacto de tres entradas.
Se incluyen avisos de las dependencias y Unicode. Cada tabla tiene esquema, versión,
autoridad, licencia y hash en el manifiesto de tablas. El texto de licencia Unicode
es un insumo vendorizado y no una descarga del generador. Es necesario revisar
licencias y diff al cambiar sus fuentes. Los esquemas/configuración se empaquetan;
la generación de manifiesto conductual completo queda en F2.

## Fixtures y aceptación de F1

T01–T40 se materializan en 49 escenarios (T35 incluye None, bytes y campo inválido).
Los bytes negativos usan representación hex explícita; los sustitutos usan escapes
JSON que el loader materializa. El caso integral conserva dos presentes y cuatro
missing, raw/expected independientes y expectativas de cinco hints y seis listas.
Sus offsets se calcularán por la implementación, nunca se estiman a mano.

Los archivos exactos evitan conversión de EOL, trim y adición de newline del editor.
Las pruebas cotejan fences, hashes, espacios múltiples, sangrías, kaomoji y saltos.
Un fixture separado cubre seis campos presentes; otros cubren criterios y casos
adversariales. T41–T64 tienen un inventario de aceptación selectiva y no se convierten
en goldens por copiar el texto de la revisión externa. Los pendientes de renderer
se declaran como tales; no hay tests saltados para simular un producto completo.

Todo el corpus es sintético. Los splits se separan por familia; el integral queda
en validation y los casos de desarrollo no lo duplican. Esta separación no vuelve
ciego un ejemplo público ni sustituye una futura muestra real autorizada.

La aceptación de F1 consiste en integridad de modelos, configuración/tablas y corpus,
no en aprobar T01–T40 contra un normalizador inexistente. F2 inicia procedencia,
serialización y baseline; no está incluida en esta entrega.
