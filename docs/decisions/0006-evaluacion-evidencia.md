# ADR-0006: evaluación de evidencia y coordenadas finales

Estado: aceptado para F6. Fecha: 2026-09-29. Base: especificación 2.0,
§§20, 24, 26, 30–32; no cambia reglas normativas ni versiones de paquete/esquema.

## Decisión

Los consumidores de evaluación son módulos de desarrollo independientes del wheel.
Mantienen candidatos y contexto, importes Decimal exactos, alternativas y ausencia
explícita de resolución. No añaden clasificación semántica a `JobTextNormalizer`.
La [guía](../evaluacion.md) fija contratos, fórmulas, limitaciones y reproducción.

Las decisiones contextuales de listas usan etiquetas manuales sobre líneas de la
etapa reparada. DOM explícito no infla la precisión inferida. El corpus nuevo se
separa por familias y similitud literal; las regresiones históricas siguen siendo
contratos. La puerta observada no se presenta como una garantía estadística ni
una medición de ofertas reales.

Las ablaciones suprimen una regla planificada, mantienen reconocimiento fijo y
señalan sus resultados como experimentales. No se incorporan flags de evaluación
a la política de producción ni se llama al resultado un documento canónico.

## Defectos descubiertos por F6

1. Los marcadores insertados ampliaban el elemento DOM sin ampliar siempre sus
   contenedores. El renderer extiende cada ancestro con el span final de sus hijos;
   conserva IDs, relaciones y procedencia raw.
2. Una bandera al inicio de `<li>` podía compartir su envolvente proyectada con el
   marcador insertado y producir `Token/span mismatch`. Se captura una alineación
   local de identidad después de expandir símbolos y antes de insertar marcadores.
   Las anotaciones se transportan por esa alineación; el mapa raw no se sustituye.

Las regresiones incluyen elementos vacíos, ordinales, anidamiento, banderas,
caracteres astrales y NFC. Estos cambios corrigen coordenadas/validación; no cambian
los textos esperados del corpus existente. La huella del código identifica la
corrección respecto de F5, que todavía no constituye una release publicada.

## Consecuencias

Se mantiene una proyección local adicional durante rendering. F7 medirá su coste
junto con el pipeline completo; F6 no acredita rendimiento. HTML conserva precisión
field. Los consumidores usan segment cuando la identidad de offsets no se puede
demostrar y no buscan coincidencias repetidas para inventar exactitud.
