# Cierre de Fase 2 — Baseline, fuentes, procedencia y manifiesto

Fecha: 2026-09-25. Base: `c3111e4`. Alcance autorizado: Fase 2 del plan revisado.
La base de F1 pasó sus 28 pruebas antes de comenzar. La implementación se realizó
sobre el checkout actual; no se inició F3 ni se hizo commit, push o publicación.

## Entregables y evidencia

| Puerta del plan | Implementación y comprobación |
|---|---|
| Límites antes de procesamiento | prepare_input, validate_input y validate_record; bordes exactos y presupuesto agregado independiente |
| Entrada inválida recuperable | Sobre local RejectedInput; conserva bytes/None/sustitutos y rechaza su serialización canónica |
| Fuente local y externa | Raw exacto, digest, protocolo SourceStore, persistencia con read-back y rechazo de cambios de contenido/metadatos |
| Alineación compuesta | Segmentos a fuente inicial, copias lineales, sustituciones, inserciones, eliminaciones y degradación explícita |
| IDs estables | SHA-256 con dominio/campo/fuente/regla/origen/aparición; vector independiente fijo y texto repetido |
| Serialización | Mapping explícito de modelos, estados/fases, colecciones ordenadas, Unicode estricto y sin no finitos |
| Manifiesto | Política/tablas, código, runtime, dependencias, backend/libxml2 y artefactos instalados; recibos de wheels opcionales y exigibles |
| Build sin Git en consumidor | Stamping en árbol temporal; wheel desde sdist; instalación/manifiesto fuera del checkout |
| Renderer base | Separadores, espacios, NFC final, alineación y spans después de composición; sin borrar componentes léxicos pendientes |
| Reutilización canónica | Revalidación de límites/invariantes/referencias y rechazo POLICY_MISMATCH; misma instancia compatible |
| Determinismo | Replay byte a byte en cuatro procesos con PYTHONHASHSEED 0, 1, 42 y random, conexiones de red bloqueadas en el test |

Las decisiones completas, incluido el alcance del validador base y la distinción
entre fingerprints instalados y hashes de wheels, están en
[ADR-0002](../decisions/0002-baseline-fuentes-procedencia.md).

## Validación local

- 75 pruebas pytest aprobadas, incluidas propiedades Hypothesis y replay entre procesos.
- Ruff lint/formato y mypy estricto aprobados.
- Lock y tablas de F1 conservados; regeneración de tablas en modo --check aprobada.
- Goldens y hashes del corpus original intactos; no se generaron expectativas desde
  un normalizador ni se añadieron skips para las fases pendientes.
- sdist/wheel construidos; metadatos aprobados por Twine estricto.
- Wheel instalado en entorno temporal externo; contratos, tablas, hashes,
  código empaquetado y manifiesto sin acceso a Git verificados.
- Diff sin errores de espacios.

Casos relevantes: `a + invisible + acento` tras eliminación explícita produce `á`
con origen de segmento a la fuente completa; un hint expandido conserva su origen;
recortes dentro de la expansión no fingen alineación por carácter. Cambios de igual
longitud no adquieren precisión exacta. Se cubren vacíos, bordes, texto repetido,
solapamientos, fuentes alteradas sin cambio de longitud, límites y timeout tipado.

## Qué no acredita este cierre

Las 75 pruebas acreditan la infraestructura implementada. No son ejecución de
T01–T40/T41–T64 contra JobTextNormalizer. El corpus conserva awaiting_normalizer.
La baseline de espacios/NFC no interpreta HTML, repara mojibake ni elimina emoji.
La validación canónica base no sustituye las comprobaciones conductuales de F4/F5.

No se midieron SLO ni calidad de listas, ni se ejecutó la matriz remota de GitHub
Actions. La durabilidad de almacenes reales y el inventario de wheels del despliegue
son responsabilidades del integrador que el protocolo permite verificar/configurar;
no se afirma haber validado una infraestructura externa inexistente.

F2 queda completada localmente. El siguiente incremento es F3: adaptadores de
formato y estructura de origen, reutilizando estos contratos sin cambiar de fuente.
