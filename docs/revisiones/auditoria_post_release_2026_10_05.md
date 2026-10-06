# Auditoría posterior a la publicación — 2026-10-05

> Actualización 2026-10-06: A01 y A04 corregidos en el árbol de trabajo. El wrapper
> conserva INVALID_TYPE sin extraer atributos de fuentes rechazadas, y el informe
> original usa clean_text. El cuerpo y JSON siguientes conservan los hallazgos de
> la revisión original; A02 y la limitación de evidencia real continúan vigentes.

## Dictamen

**normietext está disponible y es utilizable como biblioteca Alpha 0.1.0 para
integración controlada. No está completamente terminado frente a cada detalle de
la especificación, ni acreditado para cualquier carga o distribución de ofertas.**

El núcleo de normalización, los seis campos, la trazabilidad, las reglas del perfil
y la distribución están implementados. La suite vuelve a pasar. Quedan una
inconsistencia reproducible en el wrapper de medición, granularidad pendiente de
observabilidad y validación externa al corpus sintético. Son categorías distintas:
corrección de código, implementación de métricas y ampliación de evidencia.

La publicación de F8 se mantiene válida para el alcance aprobado. Su cierre no
implica haber implementado toda mejora futura ni una certificación de uso universal.
No se identificó en esta revisión un defecto de severidad P0/P1 ni un fallo nuevo
de normalización con FieldInput válido en las sondas ejecutadas.

## Identidad, método y evidencia

- Árbol inicial limpio: `e7be574a0604415e94e9b23696e7dfcc593f8503`.
- Release: `v0.1.0`, commit `717903d7e5764596a4d7c400dbf032ab7d4b195d`.
- Sin diferencias entre tag y HEAD en `src/`, `pyproject.toml` y `uv.lock`.
- Software 0.1.0; esquema 1.0.0; reglas 1.0.1; especificación 2.0.
- Perfil único: linkedin_jobs_aggressive_v1; CPython 3.14.7 en la prueba local.

Se contrastó la especificación y la trazabilidad del plan con la implementación,
las ocho ADR, los tests y los cierres de fases. Se reutiliza la lectura y matriz
completa de la [auditoría integral anterior](auditoria_integral_2026_10_04.md),
revalidando las conclusiones que cambiaron tras la publicación. Se inspeccionaron
de nuevo las fronteras de API, errores, renderizado, léxico, estructura, conversión,
instrumentación, evaluación, manifiestos y distribución. Los resultados recientes
no se deducen únicamente de los estados escritos en el plan.

Se ejecutó la suite completa, checks de tres destinos, tablas, evaluación y build
aislado. Se añadieron sondas temporales de formatos y tipos inválidos, sin escribir
goldens desde salidas del normalizador. La
[evidencia de esta ejecución](auditoria_post_release_2026_10_05.json) archiva
resultados, protocolo y código de las sondas. Este trabajo no cambia reglas ni
publica una versión nueva.

## Hallazgos accionables

### A01 — P2: measure_field oculta INVALID_TYPE con AttributeError

Ubicación: `src/normietext/operations.py:104`, llamada a `_field_metrics`;
el acceso incondicional a `source.field` comienza en la línea 33.

```python
from normietext import JobTextNormalizer
from normietext.operations import measure_field

n = JobTextNormalizer()
n.normalize_field(None)       # InputValidationError, código INVALID_TYPE
measure_field(n, None)        # AttributeError: ... has no attribute 'field'
```

También se reprodujo con str y bytes. Son entradas que infringen el tipo de la API;
el defecto se limita a su rechazo y no demuestra pérdida de texto válido.
`_measure` captura correctamente NormalizationError y obtiene INVALID_TYPE, pero
`measure_field` intenta después extraer atributos de la entrada rechazada.
El error secundario impide devolver Measurement y oculta el código original.
Contrasta con la promesa del docstring y ADR-0007 de representar errores tipados
mediante Measurement con result=None.

Impacto: un integrador que usa medición como frontera de ingesta no puede manejar
uniformemente ese rechazo. El wrapper puede fallar por instrumentación donde la
API base rechaza con su código estable. Los tests actuales cubren exceso de tamaño
con FieldInput válido, pero no esta frontera de tipos.

Cierre propuesto: construir métricas de fuente únicamente cuando la entrada sea
válida para ello, preservando INVALID_TYPE en Measurement; alternativamente definir
y documentar explícitamente un rechazo tipado previo. Añadir expectativas manuales
para None, str y bytes, y comprobar restauración de ContextVar. Mantener inalterado
el comportamiento de la API base. Este hallazgo se documenta, no se corrige en esta
auditoría.

### A02 — P2: observabilidad de §25.1 todavía parcial

`operations._field_metrics` publica operaciones por regla, anotaciones, incidencias,
precisión, hints, reparaciones, vacíos y longitud. No publica:

- Invisibles eliminados separados por clase Unicode.
- Porcentaje de emoji eliminados con un denominador definido sobre secuencias.

`removals` cuenta ediciones de emoji.remove y unicode.invisible. No es un número
de codepoints, grafemas, todos los símbolos eliminados ni un porcentaje. No debe
usarse como si tuviera cualquiera de esos significados.

**Precisión respecto de la auditoría anterior:** los candidatos no clasificados sí
son observables indirectamente en `issues_by_code[UNCLASSIFIED_SYMBOL_SEQUENCE]`.
Los caracteres de reemplazo también tienen incidencias propias. No corresponde
presentarlos como totalmente ausentes por no existir un contador de primer nivel.

Cierre propuesto: definir unidad y denominador de las nuevas métricas antes de
implementarlas; incluir emoji consumidos como marcadores, secuencias completas,
protecciones y categorías Unicode superpuestas. No contar dos veces Cf y
Default_Ignorable cuando coinciden. Una muestra sin candidatos debe tener una
convención explícita para el porcentaje. Probar que medir no modifica resultado,
IDs, fuente ni serialización, y que solo se exportan agregados sin texto privado.
La alternativa es aprobar una concreción normativa explícita; no declarar el
requisito cumplido mediante un cambio silencioso de documentación.

### A03 — Brecha de evidencia, no funcionalidad ausente

§§24.1, 25.2 y 27.4 contemplan muestras reales, distribución de carga representativa
y adopción en sombra. El plan F6 y ADR-0008 permiten avanzar con evidencia sintética
si su límite se declara. El proyecto cumplió esa aceptación acotada, no la validación
general con fuentes reales.

Los 20 jobs aportados son sintéticos y 18 comparten plantilla. Los 55 fixtures de
calidad son públicos y no ciegos. La precisión 30/30 observada no demuestra una
precisión poblacional de 99,5 %. El consumidor de F8 conserva señales y offsets;
no sustituye a un parser robusto de un proyecto real. El rollback usa un snapshot
de desarrollo con la misma versión de paquete, no una release pública anterior.

Cierre para adopción real: corpus autorizado del consumidor, diversidad por
familias/campos/formatos, expectativas manuales y medición en su equipo junto con
su parser. Esto corresponde a una integración concreta, no exige convertir la
biblioteca en SaaS ni añadir extracción semántica al núcleo.

### A04 — P3: errata en el informe anterior

La matriz RF-14 y una explicación de la auditoría anterior usaron `normalize_text`.
El nombre real y normativo es **`clean_text`**, como indican api.py, docs/api.md y
§19.2. No falta implementar una API llamada normalize_text. El 2026-10-06 se
corrigieron ambas referencias en el informe original, con una fe de erratas que
conserva la fecha y alcance de sus resultados históricos.

## Matriz funcional actual

Estado “implementado/verificado” se limita a la inspección, corpus y propiedades
ejecutadas. No significa demostración formal de todos los inputs posibles.

| Requisito | Estado | Implementación y prueba distintiva |
|---|---|---|
| RF-01 tipos/campos | Implementado/verificado en API base | Modelos estrictos, T35 y tests de API; A01 afecta al wrapper opcional |
| RF-02 formatos | Implementado/verificado | plain_text, html_fragment, html_escaped_text; unknown literal con incidencia; sin autodetección |
| RF-03 fuente/procedencia | Implementado/verificado | Raw, hash y referencias; SourceStore en ingesta, tests de recuperación y alineación |
| RF-04 HTML | Implementado/verificado | Límites, inline, listas, tablas, dl y anotaciones; 30 fixtures de adaptación y casos canónicos |
| RF-05 reparación | Implementado/verificado | ftfy explícito una vez, unidades estructurales y explicación; falsos positivos posibles documentados |
| RF-06 NFC/UTF-8 | Implementado/verificado | NFC final antes de spans; surrogate rechazado; propiedades Unicode |
| RF-07 invisibles | Implementado/verificado | Captura previa de secuencias y estructura; eliminación por tablas, fuente conservada |
| RF-08 emoji | Implementado/verificado | Secuencias, prioridad, ZWJ, keycaps y política de desconocidos |
| RF-09 señales | Implementado/verificado | Hints, regiones/subdivisiones, tokens y anotaciones; literales no falsifican metadata |
| RF-10 listas | Implementado/verificado | Ordinales, continuidad, relaciones y abstención; 39 negativos obligatorios aprobados |
| RF-11 espacios | Implementado/verificado | SPACE/LF, campos compactos, máximo una línea vacía; corpus y propiedades |
| RF-12 evidencia | Implementado/verificado en corpus | Signos técnicos, negación, importes y fragmentos del integral; no resolución semántica |
| RF-13 estados/ediciones | Implementado/verificado en núcleo | Ediciones atribuidas, issues, empty/partial/failure; A01 y A02 limitan instrumentación |
| RF-14 API | Implementado/verificado | normalize_field, normalize_record, canonicalize y clean_text; strict por registro |
| RF-15 replay/reentrada | Implementado/verificado | Reentrada tipada e igualdad canónica en entorno compatible, tests entre procesos |

## Cobertura de capítulos, plan y decisiones

| Referencia | Conclusión |
|---|---|
| Spec §§1–5 | Alcance local, determinismo, pérdidas aceptadas y separación de parsing respetados |
| §§6–8 | Contratos y metadatos implementados; no hay concatenación irreversible de los seis campos |
| §§9–10 | Conversión única y estructura; precisión HTML field aceptada cuando no existen offsets demostrados |
| §§11–13 | Reparación, Unicode y símbolos implementados; catálogos y decisiones finitos, versionados |
| §§14–18 | Listas, espacios, protecciones y pipeline cubiertos por regresiones y propiedades |
| §19 | API y JSON canónico presentes; reentrada no vuelve a limpiar un string |
| §20 | Consumidores mínimos de evaluación; parser de producción deliberadamente externo |
| §§21–22 | Lock, metadata, runtime y módulos reales coherentes; árbol de §22 ilustrativo |
| §23 | Límites y errores probados en el núcleo; timeout regex no es deadline completo del worker |
| §§24–26 | Tests/quality presentes; evidencia real pendiente y métricas de §25.1 parciales |
| §27 | Release y rollback verificados; mantenimiento futuro requiere repetir las puertas relevantes |
| §28 | Referencias de diseño, no funcionalidades por implementar ni versiones latest prometidas |
| §29 | Política empaquetada y validada; no permite inventar perfiles sin implementar sus reglas |
| §§30–32 | T01–T40, integral y evidencia obligatoria ejecutados con expectativas independientes |
| ADR-0001 | Modelos inmutables, seis sobres, corpus y rechazo de coerciones presentes |
| ADR-0002 | Recuperación, alineación, IDs, manifiesto y stamping presentes; durabilidad externa no simulada |
| ADR-0003 | Adaptación y recuperación HTML, ordinales/tablas/dl presentes; precisión conservadora |
| ADR-0004 | Reparación/léxico y protecciones previos a aplicación destructiva presentes |
| ADR-0005 | Renderer, relaciones, marcadores y API presentes; clean_text es el nombre correcto |
| ADR-0006 | Consumidores, Decimal, abstenciones y 13 ablaciones presentes; reconocimiento fijo en ablaciones |
| ADR-0007 | Operación y límites presentes; A01 revela una frontera incompleta del contrato de medición |
| ADR-0008 | Biblioteca por lotes, MIT/GitHub, adaptación de los 20 casos y publicación efectiva respetados |

F0–F5 tienen entrega funcional. F6 cumple la puerta sintética del plan. F7 tiene
mediciones y límites aprobados para el equipo/corpus, con A01/A02 pendientes.
F8 está publicada y verificada. Los estados de fases son hitos de aceptación;
no sustituyen el seguimiento de defectos descubiertos posteriormente.

No se deben convertir las propuestas rechazadas/diferidas T54–T55 en faltantes de
la política vigente. Tampoco crear wrappers vacíos solo para replicar el árbol de
archivos ilustrativo de la especificación.

## Pruebas y comprobaciones recientes

| Comprobación | Resultado de esta auditoría |
|---|---|
| uv sync --locked | Correcto |
| Ruff lint/formato | Correctos; 70 archivos formateados |
| mypy linux/win32/darwin | Correcto; 40 fuentes por destino |
| pytest completo | 458 aprobados, 0 errores/fallos/skips; JUnit 49,352 s |
| Tablas offline | Verificadas sin regeneración |
| Calidad | 55 casos, passed=true, sin fallos |
| Metamórficas nuevas | 288 pares plain_text/HTML inline transparente, sin diferencias ni errores de reentrada |
| Frontera de medición | None, str y bytes reproducen A01 |
| Build y distribución aislada | sdist/wheel, Twine e instalación comprobados |

Las metamórficas combinan doce fragmentos, incluidos emoji, banderas, mojibake,
combinantes, invisibles y saltos, en dos campos. La equivalencia de texto bajo
b/span es la propiedad comprobada; no son 288 nuevos goldens aprobados ni una
auditoría estadística de HTML arbitrario.

Calidad reciente: 104 etiquetas, 30 TP, 69 TN, 5 abstenciones, 0 FP/FN; precisión
observada 100 %, cobertura 28,846 %, abstención 4,808 %. El integral conserva sus
58 fragmentos y 23 grupos; 15 pérdidas son autorizadas. No se calculó cobertura
de líneas/ramas ni se atribuye un porcentaje de cobertura a esos resultados.

El [CI de HEAD](https://github.com/ajrojasfuentes/normietext/actions/runs/37262558837)
está aprobado. La [Release](https://github.com/ajrojasfuentes/normietext/releases/tag/v0.1.0)
mantiene sus tres assets. La verificación remota de instalación y hashes quedó
archivada en [cierre F8](cierre_fase_8.md); no se sustituye esa evidencia por el
build de HEAD, que identifica otra revisión Git.

No se repitió el benchmark costoso: el núcleo, política y lock no cambiaron desde
la medición comparable. Su evidencia se conserva, sin presentarla como una nueva
ejecución: cuatro procesos, 9,417 ofertas/s y 2,95 horas extrapoladas por 100.000,
con cero fallos en la muestra repetida. La referencia es 6 horas en ese equipo,
no 2 horas garantizadas ni rendimiento universal. HTML cerca del límite de nodos
puede costar aproximadamente 18 segundos por campo en la medición anterior.

## Límites aceptados y responsabilidades del consumidor

- Python >=3.14,<3.15 y perfil único. No se promete PyPy ni soporte universal de
  arquitecturas; lxml/regex requieren distribuciones nativas compatibles.
- Hints y catálogos finitos. No se implementa un reconocimiento semántico ilimitado
  ni se resuelven salario, modalidad, geografía o seniority desde señales.
- Fuente recuperable y procedencia no equivalen a revertir una cadena limpia.
  HTML usa field; los spans canónicos son codepoints, no bytes ni UTF-16.
- Unicode agresivo puede perder distinciones lingüísticas; ftfy admite falsos
  positivos. Raw y ediciones permiten auditarlo. No se promete texto de código
  ejecutable tras compactar sangrías.
- No hay API de deserialización general ni executor público de lotes. No son
  requisitos funcionales omitidos del alcance aprobado.
- Almacenamiento durable, colas, memoria total, deadlines de workers, caché e
  integración del parser pertenecen al host. El límite regex de 50 ms es por
  operación y no limita la llamada completa.
- El instalador resuelve dependencias transitivas; el integrador fija su cierre
  para replay. Un hash de entorno instalado no es un recibo de wheel.
- Publicar los resultados como texto requiere escape en la interfaz del consumidor;
  la biblioteca normaliza texto y no certifica HTML seguro para insertar.

No hay razón para añadir servidor HTTP, base de datos, LLM, scraping, clasificación,
CLI de producto o publicación PyPI para cerrar las brechas detectadas.

## Criterio práctico de preparación

| Uso previsto | Evaluación |
|---|---|
| Descargar e instalar la biblioteca publicada | Listo y verificado |
| Integrar la API principal con FieldInput válido, conservar raw y ejecutar corpus propio | Listo para piloto controlado |
| Exportar mediciones como frontera para entradas dinámicas inválidas | Corregir A01 primero |
| Declarar implementado íntegramente §25.1 | Pendiente A02 |
| Declarar calidad probada en tráfico real o capacidad idéntica en cualquier equipo | No acreditado |
| Declarar que ya existe un parser semántico robusto | Fuera del alcance; no existe como producto del núcleo |

Orden recomendado: corregir A01 con regresiones manuales; completar/precisar A02;
revalidar corpus y distribución para una entrega correctiva; después ampliar adopción
con muestras reales autorizadas y el parser del consumidor. Cambios exclusivos de
instrumentación no deben alterar reglas/texto/anotaciones; cualquier diferencia
conductual exige revisar la versión de reglas según §27.2.

No es necesario reabrir todas las fases. Sí conviene mantener un backlog concreto
de A01/A02 y no usar “F8 cerrada” como sinónimo de “no quedan tareas”.
