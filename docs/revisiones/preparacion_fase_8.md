# Fase 8: distribución desde un commit identificado

Verificación local: 2026-10-04. Publicación remota pendiente.
El mantenedor autorizó continuar F8 después de aprobar el commit
`98c47785b6955b8136d2096e71cd711fa46f0508`.

## Artefactos verificados

Se ejecutaron `uv sync --locked`, la construcción con stamping, Twine estricto,
la instalación aislada mediante `check_wheel.py` y la generación de SHA256SUMS.
El árbol estaba limpio al construir. El manifiesto empaquetado identifica
`git:98c47785b6955b8136d2096e71cd711fa46f0508`, sin sufijo de cambios locales.
La huella del código coincide con la evidencia de F7:
`9f7a4c5c3a1a802214d869d1a068fe2c45b5efc8bcdbd2d3a3022689b909e371`.

| Artefacto | SHA-256 |
|---|---|
| normietext-0.1.0-py3-none-any.whl | `7ea043c481429f5afb0e105a85a176c2b0e1e977f8e9dad808e3564da83e0db4` |
| normietext-0.1.0.tar.gz | `a47b721b9ec336d329f9f0b0117b8f37e1e143639fb13f0a38a2a4f6b9f97c5d` |

Dos construcciones consecutivas produjeron los mismos hashes de ambos archivos.
Esto acredita reproducibilidad en este entorno; no demuestra igualdad entre
herramientas o sistemas operativos distintos. Los artefactos permanecen en `dist/`,
excluido de Git. Las modificaciones documentales de este informe son posteriores
a la construcción y no forman parte del commit identificado arriba.

El hash del wheel difiere del candidato anterior porque ahora incorpora la revisión
Git aprobada. El informe histórico no se sustituye ni se presenta como evidencia de
estos nuevos bytes. La versión del paquete sigue siendo 0.1.0; esquema 1.0.0,
reglas 1.0.1 y perfil linkedin_jobs_aggressive_v1.

## Consumidor y rollback

La [prueba archivada](fase_8_adopcion.json) instala candidata, snapshot anterior y
candidata en un entorno externo al checkout. Procesa los 20 originales sintéticos
en cada instalación. `shadow_equal` y `replay_equal` son verdaderos; los hashes de
las dos instalaciones candidatas coinciden con el wheel de la tabla.
El snapshot anterior conserva su condición de artefacto de desarrollo, no de release
pública previa. No se acredita adopción en tráfico real.

La validación funcional de 455 tests y la revisión de corpus permanecen documentadas
en [aceptación de biblioteca](aceptacion_biblioteca.md). En este paso no se modifica
comportamiento ni se vuelven a generar expectativas.

## Puertas remotas pendientes

No hay tags locales. El remoto configurado es
`https://github.com/ajrojasfuentes/normietext.git`. GitHub CLI (`gh`) no está instalado;
no se ha podido comprobar autenticación ni ejecutar el flujo remoto de release.

Para completar F8 quedan: comprobar el estado del remoto, integrar la revisión que
se publicará, aprobar su matriz de CI, crear el tag coherente con 0.1.0, publicar la
Release y verificar hashes e instalación de los assets descargados. Si cambia el
commit elegido, se deben construir y verificar sus artefactos, sin atribuirle los
hashes de este informe. PyPI continúa siendo opcional.

No se ha realizado push, creado un tag ni publicado una Release durante esta
verificación. F8 continúa abierta hasta obtener evidencia de las puertas remotas.

Actualización de auditoría (2026-10-04): se pudo consultar GitHub mediante el conector,
sin depender de `gh` local. El [CI de 98c4778](https://github.com/ajrojasfuentes/normietext/actions/runs/37236852002)
pasó en Ubuntu/macOS, falló en mypy de Windows y omitió distribución. No hay Releases
en la consulta. Véase la [auditoría integral](auditoria_integral_2026_10_04.md);
esta evidencia sustituye la falta de comprobación remota indicada arriba, no los
hashes históricos ni la necesidad de verificar el commit corregido.

## Incidencia de CI comunicada después de esta verificación

El mantenedor realizó el push y proporcionó el fallo de mypy en Windows: seis
errores `attr-defined` por APIs de `resource` en `benchmarks/load.py` y
`benchmarks/batch.py`. Se reprodujeron localmente con `mypy --platform win32`.
La captura de `ImportError` cubría ejecución, pero no delimitaba para mypy las
APIs que los stubs solo declaran fuera de Windows.

La corrección añade condiciones explícitas de plataforma para RSS y para el
límite Linux de memoria. Mypy acepta los 40 archivos con destinos win32, darwin
y linux. La matriz remota debe repetirse sobre el commit que incluya la corrección;
el fallo informado no acredita un resultado posterior exitoso. Los hashes de la
tabla anterior identifican exclusivamente la construcción limpia de `98c4778`;
las reconstrucciones posteriores con cambios locales no son esos artefactos.

Validación local de la corrección: 458 pruebas aprobadas, Ruff lint/formato,
tablas offline, construcción de sdist/wheel, Twine estricto e instalación aislada
aprobados. Las nuevas pruebas cubren RSS no disponible en Windows y rechazo de
contención de memoria en Windows/macOS. No se modificó el núcleo normalizador.
