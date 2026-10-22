# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

### Pendiente

- Unificar `src/` y `plugin/iram-titleblock-plugin/scripts/`: hoy hay copias duplicadas de los scripts.
- Corregir las rutas fijas que quedaron en los scripts de ejemplo, si aparecen.

## [0.5.1]

### Corregido

- El conversor a DXF fallaba si un logo tenía paths vacíos (sin área): esas formas se ignoran ahora.

## [0.5.0]

### Añadido

- Logos en PNG: `provider-logo-*.png` y `client-logo-*.png` se ajustan al recuadro del rótulo (escala uniforme, centrados) y se incrustan en el SVG. Se usan cuando no hay un SVG del mismo prefijo; si hay ambos, gana el SVG.
- DXF: los logos PNG se vectorizan a color con `vtracer` (dependencia opcional) y se colocan con el mismo ajuste que en el SVG, solo con relleno de color. Sin `vtracer` el DXF sale sin ese logo y se avisa.

### Cambiado

- Logos DAVH: se agregan `provider-logo-DAVH.png` y `client-logo-DAVH.png`, copias de `logo.png` (que se mantiene porque lo usa el README), y se conservan los SVG vectorizados.
- Documentación y skill: logos SVG o PNG, dependencia `vtracer` y DXF en capa 0.

## [0.4.2]

### Cambiado

- Logos `client-logo-DAVH.svg` y `provider-logo-DAVH.svg` vectorizados a partir de `logo.png` (color, con viewBox). Ahora aparecen también en el DXF.

## [0.4.1]

### Cambiado

- Logos de cliente y proveedor: `client-logo-DAVH.svg` y `provider-logo-DAVH.svg` reemplazan a FORD y EnergySapiens.

### Corregido

- Los logos en PNG incrustados en SVG no se mostraban en el rótulo: al limpiar el logo se perdía el enlace `xlink:href`.
- Logos sin `viewBox` se escalan a partir de `width` y `height`.

## [0.4.0]

### Cambiado

- Eliminadas las señales de centrado de 0,5 mm (IRAM 4504, 2.4.1) de todas las láminas. Se mantiene la flecha de orientación.
- DXF: todas las entidades quedan en la capa `0`, con color y tipo de línea ByLayer. Se eliminan las capas `LINEAS`, `TEXTO` y `LOGOS`. Los logos conservan su color embebido en el relleno.

## [0.3.0]

### Añadido

- Salida DXF por lámina (`sheet-IRAM-A0.dxf` … `sheet-IRAM-A4.dxf`), con textos en Arial, capa `TEXTO` y capa `LOGOS`.
- Logos del proveedor y del cliente embebidos en el DXF como relleno de color (HATCH) con su contorno.
- Lista de modificaciones opcional por lámina (columna "Lista de modificaciones" del Excel).

### Cambiado

- Los textos fijos del rótulo se fuerzan a 2 mm, en mayúscula y negrita, salvo el aviso legal, el título y el tipo de plano.
- Logos escalados y centrados en su celda, sin contorno.
- Nombres de archivo en kebab-case; nombres de salida `sheet-IRAM-<formato>.svg`, sin sufijo `-mod`.
- Estructura del proyecto: `assets/`, `backups/`, `plugin/`, `src/`, `test/`, `vendor/`.

### Eliminado

- Previsualizaciones PNG.
- Línea de centrado inferior que tapaba el rótulo A4.

## [0.1.0]

- Versión inicial sin historial detallado.
