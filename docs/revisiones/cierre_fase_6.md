# Cierre local de Fase 6

Fecha: 2026-09-29. Base: `ae1fff5` (F5 integrada por fast-forward en `main`).
Trabajo en rama `codex/fase-6`, worktree aislado de F5. F6 completada localmente;
F7 y F8 pendientes. Software 0.1.0, especificación 2.0, esquema/reglas 1.0.0.

## Entrega y resultado

- 55 casos nuevos escritos manualmente: español, inglés, portugués y mixtos;
  seis campos, cuatro formatos, listas, negativos, abstenciones y adversariales.
- Consumidores de dinero/porcentajes, tecnología, banderas y pertenencia a bloques,
  con contexto, procedencia, estados, alternativas y Decimal exacto. No se incluyen
  en el wheel ni convierten el cleaner en un parser semántico.
- Ablación de 13 reglas, con métricas de evidencia obligatoria, pérdidas autorizadas
  y candidatos, desglosadas por idioma, formato, campo y split.
- 52 fragmentos obligatorios preservados en el corpus nuevo; 10 pérdidas autorizadas.
  Inventario integral: 58 fragmentos en 23 grupos de §32, cero ausentes y 15 pérdidas
  autorizadas. Los goldens integrales completos siguen pasando sin modificar sus bytes.
- Dos correcciones de spans descubiertas por la evaluación: los contenedores DOM
  incluyen marcadores de hijos y las anotaciones generadas conservan spans propios
  junto a marcadores insertados. Véase [ADR-0006](../decisions/0006-evaluacion-evidencia.md).

El [informe JSON](fase_6_calidad.json) contiene manifiesto, hashes, resultados,
segmentos y ablaciones. La [guía de evaluación](../evaluacion.md) explica contratos,
fórmulas y cómo reproducirlo.

## Precisión contextual observada

| Muestra | Líneas etiquetadas | TP | FP | FN | TN | Abstenciones |
|---|---:|---:|---:|---:|---:|---:|
| Desarrollo | 58 | 14 | 0 | 0 | 41 | 3 |
| Validación | 46 | 16 | 0 | 0 | 28 | 2 |
| Total | 104 | 30 | 0 | 0 | 69 | 5 |

Precisión observada: **30/30 = 100 %**; supera la puerta de 99,5 % en esta muestra.
Cobertura: **30/104 = 28,846 %**. Abstención: **5/104 = 4,808 %**.
DOM explícito se verifica por separado y no entra en el denominador contextual.
Además, 39 escenarios negativos normativos tienen cero elementos inferidos falsos.
Los 49 escenarios T01–T40 completos, incluidos errores, permanecen en pytest.

Corpus sintético, público y pequeño; no es validación ciega ni tráfico real.
Este resultado no demuestra un límite inferior estadístico de 99,5 %, independencia
semántica universal de los splits ni rendimiento. Las familias y similitud literal
se comprueban como se documenta; no se duplican ejemplos para inflar el denominador.

## Verificación

- `uv sync --locked`: entorno instalado con pins intactos.
- Ruff lint y formato: aprobados; mypy estricto: 31 fuentes sin errores.
- `uv run --locked pytest`: **369 tests aprobados, sin skips**.
- Propiedades de composición Unicode/HTML, astrales, NFC, tokens repetidos, padres
  e hijos, reentrada tipada y procedencia conservadora.
- Metamórficas entre texto, CRLF, texto escapado y HTML inline.
- Replay de consumidores e informe en cuatro procesos (`PYTHONHASHSEED`
  0, 1, 42 y random), con sockets bloqueados y orden invertido de procesamiento.
- `generate_tables.py --check`: aprobado, sin regenerar tablas.
- Build stamped de sdist/wheel, Twine estricto e instalación aislada aprobados.
  El smoke confirma API funcional y ausencia de `evaluation` en el wheel.

## Revisión de diffs del corpus

Todos los raw/expected y hashes preexistentes se conservan. El catálogo incorpora
únicamente los cuatro archivos nuevos de calidad y sus hashes. Sus expectativas
se redactaron manualmente. Durante la revisión se corrigió el índice convertido
del caso `<hr>` (el adaptador produce dos líneas, no tres), y la grafía de subdivisión
se fijó conforme a §13 (`[flag-subdivision:gbsct]`). No se sustituyeron goldens por
salidas del normalizador. Los casos DOM vacíos y bandera junto a marcador fijan
regresiones descubiertas durante esta fase.

La calidad está limitada a los contratos y corpus aceptados. HTML continúa con
precisión field cuando no hay offsets demostrables; las ablaciones mantienen
reconocimiento fijo y no son perfiles alternativos válidos. F7 medirá límites,
observabilidad y coste de las proyecciones; F8 conserva release/adopción.
No se ejecutó CI remota, push ni publicación.
