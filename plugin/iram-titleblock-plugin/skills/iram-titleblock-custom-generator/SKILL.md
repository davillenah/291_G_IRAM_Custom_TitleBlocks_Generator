---
name: iram-titleblock-custom-generator
description: Genera láminas IRAM A0 a A4 en SVG con rótulo personalizado (empresa, cliente, proyectado/verificado/validado, códigos y hoja/estado/revisión) e incrusta los logos provider-logo-*.svg y client-logo-*.svg, a partir de input-titleblocks.xlsx. Usar cuando el usuario pida generar láminas, rótulos IRAM, planos A0-A4 o actualizar los logos del rótulo.
---

# Láminas IRAM con rótulo personalizado

Trabajar en la carpeta del proyecto del usuario (la que contiene `input-titleblocks.xlsx`). Los scripts viven en el plugin, en `${CLAUDE_PLUGIN_ROOT}/scripts/`; no copiarlos al proyecto.

## Archivos del proyecto

- `input-titleblocks.xlsx`: única fuente de datos. Una fila por lámina, hoja "Láminas".
- `provider-logo-*.svg`: logo de la empresa responsable. Va en el recuadro LOGO EMPRESA.
- `client-logo-*.svg`: logo del cliente. Va en el recuadro LOGO CLIENTE.
- `svg/`: salida. Por cada lámina se genera `sheet-IRAM-<formato>.svg` y `sheet-IRAM-<formato>.dxf` (para CAD). Se borra y se regenera en cada corrida.

Si no existe `input-titleblocks.xlsx`, copiar la plantilla `${CLAUDE_PLUGIN_ROOT}/templates/input-titleblocks.xlsx` al proyecto.

## Flujo

1. Completar `input-titleblocks.xlsx`. Columnas: formato (HOJA), proyectado / verificado / validado (fecha y nombre), empresa y cliente (razón social, CUIT, email, web), proyecto, descripción, ubicación, tipo de plano, denominación (dos renglones), escala, código cliente (reemplaza a y reemplazado por), código interno (plano N°), página (n / m), estado, revisión, lista de modificaciones (SI/NO) y plano propio.
2. Verificar que estén los logos. Si falta uno, su recuadro muestra la leyenda LOGO EMPRESA o LOGO CLIENTE.
3. Desde la carpeta del proyecto, ejecutar: `python "${CLAUDE_PLUGIN_ROOT}/scripts/titleblocks-generator.py"`. Si el sistema pide permiso para borrar, pedirlo: la regeneración borra `svg/` antes de crear los archivos nuevos.
4. Verificar cada SVG: XML válido y sin `{clave}` sin reemplazar. Los archivos `block-rotulo_IRAM4508.svg` sí conservan llaves de plantilla; es normal.
5. Para revisar el rótulo, recortar el viewBox a la zona del rótulo (A0: x 985 a 1170, y 760 a 821) y renderizar. Renderizar con ImageMagick solo para vistas previas.

## Reglas

- No inventar datos. Si faltan, dejar la casilla vacía y decirlo.
- Logos: se incrustan centrados en su celda, sin recuadro. El generador ajusta cada logo a su celda, así que no hace falta editar los SVG para cambiar el tamaño. En el DXF, cada logo va como relleno de color (HATCH) con su contorno, en la capa LOGOS.
- Escapar `&`, `<` y `>` como `&amp;`, `&lt;` y `&gt;` en los valores.
- La denominación se dibuja en rojo, como en la referencia del cliente.
- Si la lista de modificaciones es SI, la lámina se genera con `--mod` (agrega la lista encima del rótulo). El nombre del archivo no cambia.
- El generador no ajusta el texto al ancho de la casilla: acortar nombres y correos largos y revisar el render, sobre todo la empresa y el cliente.
