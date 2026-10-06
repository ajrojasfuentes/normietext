# Corrección del wrapper y errata documental — 2026-10-06

A01 y A04 de la auditoría posterior a release quedan corregidos localmente.
La release pública 0.1.0 conserva sus bytes; el cambio se registra como Unreleased.

## Cambio y regresiones

measure_field deja que la API genere INVALID_TYPE y conserva ese código en
Measurement. Solo extrae dimensiones de fuente si recibe FieldInput. Para None,
str o bytes rechazados devuelve result=None, error=INVALID_TYPE y métricas generales,
sin acceder a atributos inexistentes, convertir el input ni exponerlo en trace.

La nueva regresión falló antes del arreglo con AttributeError. Tras el cambio pasan
sus 12 combinaciones: tres tipos inválidos, trace activado/desactivado y contexto
de medición exterior presente/ausente. Verifica rechazo tipado de la API original,
ausencia de contenido privado, dimensiones omitidas y restauración del contexto.
Los tests existentes mantienen comprobaciones de entradas válidas, límites,
concurrencia y bytes canónicos con/sin instrumentación.

El smoke de wheel instalado comprueba también el rechazo de None, fuera del checkout.
Las dos referencias incorrectas de la auditoría integral se corrigieron a clean_text,
con fe de erratas. Se actualizaron la guía operativa y el seguimiento del plan.

## Validación ejecutada

- uv sync --locked: correcto.
- Ruff lint y formato: correctos, 70 archivos.
- mypy con destinos linux, win32 y darwin: correctos, 40 fuentes por destino.
- pytest completo: **470 aprobados**, sin fallos, errores ni skips; 52,89 segundos.
- generate_tables.py --check: correcto; no se regeneraron tablas ni goldens.
- evaluation.quality: 55 casos, passed=true y sin fallos.
- build_distribution.py: wheel y sdist construidos con stamping del árbol modificado.
- Twine estricto sobre ambos artefactos: aprobado.
- check_wheel.py: instalación aislada con dependencias del lock y regresión del
  wrapper aprobadas.
- git diff --check: correcto; ningún cambio en fixtures ni datos de política.

La validación de destinos mypy es estática desde Linux; no se afirma haber ejecutado
CI nativa para estos cambios locales. No se altera la semántica de normalización,
ni esquema/reglas/perfil. La huella de código sí cambia y el manifiesto la identifica.
A02 (granularidad de métricas) y la validación con fuentes reales permanecen fuera
de esta corrección.
