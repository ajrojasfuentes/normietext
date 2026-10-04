# ADR-0008 — Biblioteca por lotes, corpus externo y distribución GitHub

Fecha: 2026-10-03. Decisión autorizada por el mantenedor Anthony Josue Rojas Fuentes.

normietext es una biblioteca local para computadoras y servidores. No tiene un
SLO de servicio centralizado. F7 publica objetivos de capacidad **condicionados a
hardware, runtime, corpus y concurrencia medidos**, reproducibles por consumidores.
El mantenedor delegó definir un volumen razonable; los objetivos concretos se
establecen en el informe del ensayo, sin prometerlos para todos los dispositivos.

La preferencia es no rechazar entradas razonables. No se elevan indiscriminadamente
los límites del perfil. El diagnóstico identificó escaneos Unicode innecesarios
en texto ASCII; las dos gramáticas de pictogramas (exclusivamente no ASCII y sin
anchors/lookarounds) se evalúan por runs no ASCII, manteniendo offsets globales.
Las secuencias ZWJ, modificadores y marcas se conservan completas. Controles ASCII,
listas y otras protecciones mantienen sus reglas y el timeout por operación.
La enumeración NFC de grafemas se acota a líneas con LF ya convertido: LF es
una frontera de grafema, por lo que se mantienen los mismos offsets y reemplazos.
El diagnóstico bajo cuatro procesos identificó render.nfc como la operación que
agotaba el presupuesto al enumerar el documento completo.
Se verifica equivalencia por pruebas diferenciales y corpus; no hay nueva regla
semántica ni cambio del esquema. Estas optimizaciones se incluyen en la candidata
no publicada de reglas 1.0.1. Las mediciones anteriores siguen siendo históricas.

Los 20 JSON aportados son datos sintéticos adversariales, no tráfico real ni una
muestra estadísticamente representativa de LinkedIn. Se conservan intactos y se
registran sus hashes. No se utilizan los campos canonical_* del manifiesto auxiliar
como salidas esperadas del cleaner ni como instrucciones para resolver contradicciones.

El adaptador de evaluación mapea title/description/criteria_list/type/location a
los campos correspondientes. criteria_list se serializa con LF, conservando los
elementos originales y el JSON como fuente de ingesta. seniority permanece missing;
modality se conserva en un sidecar, no se convierte en seniority ni se descarta.
El formato declarado es plain_text: pseudo-HTML, Markdown y JSON incrustado no se
reinterpreta. Esta decisión describe la ingesta de este set, no una heurística de
formato ni una ampliación de la API a siete campos. Los registros partial por
seniority ausente no son fallos de normalización. El benchmark cuenta fallos por
campo separadamente.

La distribución elegida es GitHub, código abierto MIT. PyPI queda opcional y no
bloquea F8 para este destino. El workflow de release reutiliza los dos artefactos
que CI verificó y adjunta SHA256SUMS; no reconstruye con permisos de publicación
ni sobrescribe assets existentes. El permiso contents:write se limita a ese job.

Se prepara un consumidor mínimo aislado, comparación en sombra y rollback entre
wheels locales, siempre reprocesando raw. No se considera un parser robusto de
producción ni se equipara la prueba sintética con adopción real. F8 solo estará
publicada cuando el mantenedor apruebe la candidata, se integre un commit,
la matriz remota pase y el tag/release y sus assets estén disponibles y verificados.
Preparar el workflow no autoriza por sí solo publicar.
