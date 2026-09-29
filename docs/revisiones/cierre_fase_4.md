# Cierre de Fase 4 — Reparación y análisis léxico

Fecha: 2026-09-28. Base: `e012932`. Alcance autorizado: corregir entidades decimales
largas y completar F4. La baseline inició con 130 pruebas aprobadas.

## Resultado

Se corrigió el ValueError no tipado de html_escaped_text ante referencias decimales
de 5.000 dígitos. La conversión queda acotada al rango Unicode, conserva ceros
iniciales semánticamente y aplica las reglas HTML5 sin modificar ajustes globales.
La edición conserva el intervalo original completo y no reinterpreta su resultado.

Se añadieron reparación explicada y análisis léxico en stages/encoding.py y
stages/lexing.py, junto con contratos inmutables y serialización explícita. Las
etapas reparada y léxica son intermedias; todavía no existe JobTextNormalizer.

| Puerta F4 | Evidencia |
|---|---|
| ftfy explícito | Cuatro opciones normativas; fix_encoding_and_explain, sin fix_text |
| Reparación una vez | RepairedDocument con manifiesto; reentrada compatible retorna la misma instancia |
| Unidades lógicas | Líneas, bloques y bordes de anotación; inline transparente no divide palabras |
| Procedencia | Ediciones compuestas a raw; segment sin mapa demostrado, field conservado en HTML |
| Explicación real | EncodingRepair enlaza edición, explicación y spans convertido/reparado |
| NEL/C0/C1 | NEL antes de ftfy, C0 y C1 no reescrito intactos; sin ediciones para no-ops |
| Reemplazo perdido | U+FFFD conservado con REPLACEMENT_CHARACTER_PRESENT |
| Protecciones | Código DOM y delimitadores léxicos; URL/correo conservadores, sin navegación |
| Secuencias | Emoji ZWJ, hints exactos, keycaps, regiones/subdivisiones y candidatos pictográficos |
| Solapamientos | Selección estable; pares regionales anclados, secuencias maximales y símbolos protegidos |
| Contexto para F5 | Tokens particionan texto y conservan sangrías, bloques y protecciones |
| Recursos | Presupuestos previos y timeout regex tipado, sin publicación parcial |
| Replay | Igualdad serializada entre cuatro procesos con semillas distintas y red bloqueada |

Las decisiones completas están en [ADR-0004](../decisions/0004-reparacion-lexico.md).
La especificación incorpora explícitamente las concreciones en §§10.2, 11.1 y 18.1.

## Validación local

- uv sync --locked correcto; pins y lock sin cambios.
- Ruff lint/formato y mypy estricto aprobados.
- **190 pruebas pytest aprobadas**, sin skips; 60 más que la baseline F3.
- 23 fixtures nuevos de etapa léxica, escritos independientemente; propiedades de
  partición, fuente y reentrada, regresiones numéricas y replay de composición HTML.
- Tablas verificadas byte a byte con generate_tables.py --check.
- Corpus previo y sus hashes conservados; el catálogo solo añade los dos archivos
  lexical. T01–T40 y el integral conservan awaiting_normalizer.
- Build stamped, sdist/wheel y Twine estricto aprobados.
- Wheel instalado fuera del checkout: contratos, tablas, manifiesto, adaptación,
  reparación y análisis léxico con reentrada compatible comprobados.

Durante autoría se corrigió explícitamente una expectativa nueva de ftfy: con la
configuración normativa, `Ã and café C++ B2+` se convierte en `à and café C++ B2+`.
Ese comportamiento queda en un fixture de limitación; `Ã` aislado es el
contraejemplo de preservación. No se reescribió un golden anterior ni se cambió la
configuración para acomodar la prueba. La reparación no garantiza ausencia de
falsos positivos sobre toda entrada posible.

## Límites y siguiente fase

F4 no elimina emoji/invisibles, no convierte listas, no aplica solidus, no compacta
espacios ni genera NFC/spans finales. Las acciones de tokens son candidatos que
F5 resolverá con contexto. LexedDocument.issues ya incluye adaptación/reparación;
el consumidor no debe volver a concatenar esas incidencias al integrar etapas.

Los reconocedores de código/contactos son conservadores y su gramática está en el
ADR; no representan un parser Markdown o una validación universal de correos/URL.
Las decisiones pendientes sobre fronteras técnicas, ordinales conflictivos,
asociaciones y párrafos siguen abiertas para F5. F6/F7 deben evaluar corpus real,
calidad y coste; no se midió SLO ni se afirma aceptación del producto final.

La matriz remota de GitHub Actions y la publicación no se ejecutaron. No se hizo
commit, push ni implementación de F5. El siguiente incremento es F5 según el plan.
