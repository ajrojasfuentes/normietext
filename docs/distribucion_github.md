# Distribución y mantenimiento desde GitHub

Responsable de aprobación y mantenimiento: **Anthony Josue Rojas Fuentes**.
Licencia del proyecto: MIT. Destino elegido: repositorio y Releases de GitHub.
PyPI/Trusted Publisher son opcionales; no forman parte de la puerta de esta entrega.

## Preparar la candidata

Conservar la biblioteca como paso previo al parsing: no convertir el normalizador
en un servicio ni incorporar extracción semántica. Revisar API, changelog, corpus,
licencias de tablas, informe de carga y limitaciones. La compatibilidad declarada
es Python>=3.14,<3.15; baseline verificada 3.14.7. La matriz Linux/Windows/macOS de CI
confirma su ejecución cuando se ejecute remotamente; no afirmar verificación de
plataformas que solo estén configuradas en YAML.

1. Ejecutar todos los checks de desarrollo y quality, incluidos fixtures manuales.
2. Revisar las diferencias de texto/estructura/procedencia y la prueba de consumidor.
3. Integrar el commit aprobado. Construir con build_distribution.py, comprobar
   Twine y check_wheel.py. No publicar un árbol de desarrollo sin commit identificado.
4. Aprobar versión, notas y resultados; crear tag v0.1.0 coincidente con pyproject.
5. Publicar GitHub Release. El workflow valida tag, ejecuta CI y adjunta los mismos
   wheel/sdist verificados y SHA256SUMS. No reconstruye en el job de subida.
6. Verificar que los assets existen y sus hashes coinciden; instalar el wheel
   descargado en un entorno limpio y ejecutar el consumidor. Una ejecución local
   no sustituye esta comprobación posterior a publicación.

El workflow no reemplaza assets existentes. Un reintento con nombres duplicados
falla de forma visible; revisar el estado de la release antes de actuar. Mantener
ENABLE_PYPI_PUBLISH sin activar salvo decisión futura explícita de publicar en PyPI.
El mantenedor controla permisos, revisión y protección de ramas en GitHub.

Las verificaciones aisladas de wheel y adopción exportan restricciones de runtime
desde `uv.lock` con `uv export --locked`, sin instalar el checkout ni las dependencias
de desarrollo. Así la resolución de una dependencia transitiva nueva no cambia el
entorno de aceptación. El consumidor final sigue siendo responsable de su propio
lock y de conservar el manifiesto efectivo.

## Consumo reproducible

Descargar el wheel y SHA256SUMS de la release elegida y comprobar su digest antes
de instalarlo. Con uv, usar `uv pip install /ruta/al/normietext-0.1.0-py3-none-any.whl`
en el entorno consumidor. El sdist y el código fuente quedan disponibles también.
Un clone no exige poner credenciales ni red dentro de la normalización.

La biblioteca fija dependencias directas; el consumidor bloquea runtime y cierre
transitivo si necesita replay byte a byte. Conservar manifiesto, wheel, configuración,
versión del scraper y raw verificable. El fingerprint instalado no sustituye el
hash del archivo wheel descargado.

## Prueba en sombra y rollback

`scripts/check_adoption.py` instala una candidata y un wheel anterior en un entorno
ajeno al checkout y ejecuta la secuencia candidata→anterior→candidata. El consumidor
mínimo recorre los 20 JSON originales, conserva señales con spans y verifica fuentes,
reentrada y firmas de contenido/estructura sin confundir cambios de manifiesto con
pérdida de evidencia. Es una prueba de integración sintética, no un parser semántico.

```bash
uv run --locked python scripts/check_adoption.py \
  --candidate dist/normietext-0.1.0-py3-none-any.whl \
  --rollback /ruta/artefacto-anterior/normietext-0.1.0-py3-none-any.whl \
  --output /tmp/adopcion.json
```

En esta primera entrega el anterior es un snapshot de desarrollo, no una versión
pública estable. Después de publicar, conservar versiones distintas e inmutables.
Ante una regresión, fijar el wheel/configuración anterior en el consumidor y
reprocesar las fuentes originales. Nunca usar texto normalizado como raw ni mezclar
cachés entre perfiles/versiones. Los cambios de evidencia requieren revisión;
una mejora de throughput no permite ignorarlos.

Para adoptar en un proyecto real, el mantenedor conecta su consumidor, compara
candidata/anterior sobre sus fuentes y promueve tras revisar errores y evidencia.
No se afirma que una integración real haya ocurrido porque el smoke sintético pase.
