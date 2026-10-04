# Changelog

## 0.1.0 — candidata, sin publicar

Primera biblioteca funcional de normalización determinista de seis campos, con
formatos explícitos, reparación, captura léxica, estructura, NFC, fuentes recuperables,
procedencia y reentrada tipada. Especificación 2.0; esquema 1.0.0; reglas 1.0.1;
perfil linkedin_jobs_aggressive_v1; CPython 3.14 con dependencias fijadas.

- Corrección de separadores para celdas HTML vacías consecutivas.
- Rechazo de documentos canónicos cuyos spans padres no contienen sus hijos.
- Observabilidad optativa sin contenido de ofertas y traces explícitos separados.
- Pruebas de límites, seguridad y concurrencia; benchmarks por campo, registro y lote.
- Corpus sintético adversarial aportado por el mantenedor y adaptador explícito.
- Búsquedas de pictogramas acotadas a runs Unicode para evitar timeouts innecesarios.
- Preparación de distribución GitHub Releases con wheel, sdist y SHA256SUMS.

No incluye scraping, clasificación semántica, resolución salarial, servidor HTTP
ni almacenamiento. El corpus sintético no acredita exactitud en tráfico real.
Las dependencias y tablas conservan sus propias licencias, inventariadas en el paquete.
