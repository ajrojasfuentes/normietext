# Desarrollo, CI y publicación

Guía operativa para mantenedores. El [plan](plan_implementacion.md) contiene las
puertas funcionales pendientes; esta guía describe las herramientas ya configuradas.

## 1. Entorno reproducible

Instalar uv 0.12.18 usando las instrucciones de su
[release oficial](https://github.com/astral-sh/uv/releases/tag/0.12.18).
Desde el repositorio:

```bash
uv --version
uv python install
uv sync --locked --no-build-package lxml --no-build-package regex
uv run --locked python --version
uv run --locked ruff --version
```

`.python-version` selecciona 3.14.7. No se utiliza el Python de sistema por defecto.
`required-version` rechaza una versión distinta de uv y Ruff. `uv.lock` debe
acompañar a `pyproject.toml` en Git. `uv sync --locked` falla si están desalineados.
Las opciones `--no-build-package` impiden compilaciones incidentales de lxml y regex
contra bibliotecas del host durante CI; una plataforma sin wheel requiere revisión.

## 2. Comprobaciones locales

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv run --locked pytest
uv run --locked python scripts/generate_tables.py --check
uv build
uv run --locked twine check --strict dist/*
uv run --locked python scripts/check_wheel.py
```

En Windows, usar las órdenes de lint, tipos, tests y build normalmente; para Twine
pueden pasarse los dos nombres de artefacto explícitos si el shell no expande `*`.
El script del wheel resuelve rutas de Python para Windows y POSIX.

Ruff revisa código Python y configuración del proyecto; no reescribe los ejemplos
normativos Markdown. El test inicial acredita metadatos y `py.typed`, no reglas del
producto. Hypothesis está listo para la fase de contratos y corpus; no se añaden
propiedades ficticias para un normalizador inexistente.

`uv build` construye sdist y wheel desde ese sdist. El script instala el wheel en
un entorno temporal independiente, importa el paquete y las cinco dependencias,
y comprueba el marcador de tipos desde fuera del checkout. Fallará si hay más de
un wheel en `dist`; separar artefactos anteriores antes de preparar otra versión.

## 3. CI en GitHub Actions

`ci.yml` se ejecuta en pushes a main, pull requests y ejecución manual. También es
reutilizable desde release. La matriz Linux/Windows/macOS usa el runtime exacto.
Cada combinación sincroniza el lock y ejecuta Ruff, mypy y pytest. La construcción,
validación de metadatos e instalación aislada del wheel se hacen en Linux después
de aprobar la matriz. Los dos artefactos quedan disponibles durante 14 días.

Permisos de lectura por defecto; credenciales del checkout no persistentes;
acciones por SHA; caché de uv; timeouts de jobs. Solo se cancelan comprobaciones
obsoletas de pull requests. La cancelación no interrumpe una publicación iniciada.
Dependabot revisa semanalmente acciones. Las dependencias conductuales Python se
actualizan mediante el procedimiento del apartado 5, con revisión de corpus.

Las comprobaciones se han ejecutado localmente en Linux. El resultado de la matriz
remota solo puede confirmarse tras subir estos cambios y ejecutar GitHub Actions.
La configuración del workflow no activa por sí sola reglas de protección de rama.

## 4. Configurar y ejecutar CD de paquetes

El workflow `release.yml` revalida el tag, ejecuta CI sobre el código del evento de
release y publica los mismos archivos ya verificados, sin reconstruirlos en el job
con permiso de identidad. No hay publicación automática por un push a main.

Preparación externa, una sola vez, cuando el producto esté listo para distribuir:

1. Verificar que se controla el nombre `normietext` en PyPI, o registrar un pending
   publisher si procede. La inicialización no verificó propiedad ni disponibilidad.
2. Configurar el Trusted Publisher en PyPI: owner `ajrojasfuentes`, repositorio
   `normietext`, workflow `release.yml`, environment `pypi`.
3. Crear el environment `pypi` en GitHub; elegir sus restricciones de release según
   la política del repositorio y limitar publicación a los responsables adecuados.
4. Definir la variable del repositorio `ENABLE_PYPI_PUBLISH=true`. Mientras falte,
   release valida y construye, pero omite publicación. No necesita un token PyPI.
5. Configurar las comprobaciones de CI como requeridas en el ruleset de main si se
   desea bloquear merges que fallen. Esto es configuración remota, no un YAML.

Preparación de cada release:

1. Completar §26 de la especificación y adjuntar informe de aceptación. Esta base
   aún no cumple las puertas funcionales y no constituye una release del cleaner.
2. Cambiar la versión del paquete y, cuando corresponda, versiones de esquema,
   reglas y perfil; regenerar lock y revisar changelog/diffs de comportamiento.
3. Ejecutar los checks; integrar el commit revisado en main.
4. Crear tag `v<VERSION>` exactamente igual a `project.version` y publicar su
   GitHub Release. El workflow rechaza discrepancias antes de construir/publicar.
5. Revisar el resultado de OIDC y comprobar instalación del artefacto publicado
   desde un proyecto consumidor aislado.

No se publicaron paquetes ni releases ni se cambiaron ajustes remotos durante esta
inicialización. El job usa `uv publish --trusted-publishing always`, que exige OIDC
y falla si no existe la relación de confianza; no recurre a credenciales ocultas.
Véase [publicación con uv en Actions](https://docs.astral.sh/uv/guides/integration/github/#publishing-to-pypi).

Para consumo privado se puede instalar el wheel o usar un índice privado configurado
por el consumidor. El soporte de otro destino debe añadirse como decisión explícita.
No se publica una imagen de servicio porque todavía no existe un servicio de producto.

## 5. Actualizar herramientas y dependencias

Verificar primero releases estables oficiales. Si cambia uv, coordinar
`required-version`, build backend y todos los pasos `setup-uv`; si cambia Python,
coordinar `.python-version`, compatibilidad, CI y manifiesto. Ruff se fija tanto en
el grupo dev como en su `required-version`. Las versiones auxiliares se resuelven y
fijan realmente en `uv.lock`, no se inventan.

Para regenerar deliberadamente tras editar los requisitos:

```bash
uv lock
uv sync --locked
```

Revisar el diff del lock. Cualquier cambio de salida, clasificación Unicode, emoji,
backend o reparación necesita versión de reglas, corpus completo, revisión de texto,
bloques y anotaciones, y pruebas de consumidores. Repetir benchmarks si afecta el
coste. Antes de actualizar un artefacto en producción, comparar en modo sombra.

## 6. Rollback y reproducibilidad

Los consumidores fijan la versión del wheel y el perfil, y conservan el artefacto
anterior. Un rollback cambia esa selección; no reutiliza texto ya normalizado como
raw. El reprocesamiento parte de fuentes recuperables. Si se añade caché, su clave
incluye fuente, campo, formato, política, reglas y entorno conductual.

Un lock de desarrollo no viaja como imposición a los instaladores del wheel. Los
consumidores deben bloquear también transitivas y runtime si necesitan replay
exacto. El manifiesto futuro registrará esas versiones efectivas y el backend nativo.

## 7. Validación de esta inicialización

En Linux, CPython 3.14.7, se verificaron instalación del stack, Ruff, mypy, pytest,
construcción de sdist/wheel, Twine y consumo del wheel en entorno aislado. Los
resultados funcionales, calidad de listas, determinismo del normalizador y SLO siguen
pendientes de implementación; no se extrapolan desde estos checks de infraestructura.


Resultado adicional de revisión: actionlint 1.7.12 validó ambos workflows sin
incidencias; el binario temporal se verificó contra su checksum oficial. El
validador de release aceptó `v0.1.0` y rechazó `v9.9.9`. `uv lock --check`, la
sincronización sin build de lxml/regex y los enlaces locales también pasaron.

El entorno local comprobado reportó GIL activo (`Py_GIL_DISABLED=0`), UCD 16.0.0 y
libxml2 2.14.6. Las herramientas auxiliares resueltas fueron pytest 9.1.1,
Hypothesis 6.168.1 y mypy 2.3.1. Estos datos describen la verificación local;
no sustituyen el manifiesto por resultado que implementará la fase 2.


## 8. Estado después de Fase 1

Se añadieron jsonschema y stubs de desarrollo para schemas/tipos; las cinco
dependencias de runtime siguen fijadas sin cambios. CI verifica también la
regeneración offline de tablas en el job de distribución. El smoke test del wheel
comprueba imports de contratos, configuración y hashes de datos/licencias desde
un entorno externo, usando `uv pip install --only-binary` para lxml y regex.

La evidencia y limitaciones actuales están en [el cierre F0/F1](revisiones/cierre_fases_0_1.md).
La validación original de inicialización en §7 se mantiene como registro histórico.
