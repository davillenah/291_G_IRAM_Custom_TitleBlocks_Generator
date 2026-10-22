<div align="center">

<img src="assets/logo.png" alt="IRAM Titleblock Generator" width="420"/>

# 📐 IRAM Titleblock Generator

**Láminas IRAM A0 a A4 en SVG y DXF, con rótulo personalizado y logos embebidos.**
Rótulo IRAM 4508 y lista de modificaciones, a partir de un Excel.

[![Version](https://img.shields.io/badge/version-0.3.0-1f6feb?style=for-the-badge)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f?style=for-the-badge)](LICENSE)
[![IRAM](https://img.shields.io/badge/IRAM-4504%20%7C%204508-64748b?style=for-the-badge)](assets/)
[![SVG](https://img.shields.io/badge/format-SVG-f97316?style=for-the-badge)](#-qué-genera)
[![DXF](https://img.shields.io/badge/CAD-DXF-8b5cf6?style=for-the-badge)](#-qué-genera)

[Contribuir](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [Reportar un problema](.github/ISSUE_TEMPLATE.md)

</div>

---

Genera láminas IRAM A0 a A4 en SVG y DXF con rótulo personalizado (empresa, cliente, proyectado / verificado / validado, códigos, hoja, estado y revisión) y con los logos del proveedor y del cliente, a partir de un Excel.

## ✨ Qué genera

Por cada fila del Excel:

- `sheet-IRAM-<formato>.svg`: lámina vectorial editable.
- `sheet-IRAM-<formato>.dxf`: lámina para CAD, con textos en Arial y todo en la capa 0 (color y tipo de línea ByLayer). Los logos van como relleno de color; los logos PNG se vectorizan.

Opcionalmente, un bloque de rótulo y uno de lista de modificaciones (`title-block-IRAM4508.svg`, `modifications-block-IRAM4508.svg`).

## 🚀 Uso como plugin

1. Copiar `plugin/iram-titleblock-plugin.plugin` a tu proyecto y reinstalarlo desde Claude.
2. Copiar a la carpeta del proyecto `input-titleblocks.xlsx` y los logos (`provider-logo-*.svg` o `.png`, `client-logo-*.svg` o `.png`). Si no hay Excel, el plugin trae una plantilla en `templates/`.
3. Completar el Excel: una fila por lámina.
4. Pedir: "generá las láminas" o "usá el plugin de rótulos IRAM".

Las láminas quedan en `svg/` dentro de la carpeta del proyecto.

## 🖼️ Logos

El generador busca un `provider-logo-*` (recuadro de la empresa) y un `client-logo-*` (recuadro del cliente) en la carpeta de logos (`assets/`, o la del proyecto si se usa como plugin):

- **SVG** (`provider-logo-*.svg`, `client-logo-*.svg`): se ajusta al recuadro del rótulo (escala uniforme, centrado) en el SVG y en el DXF.
- **PNG** (`provider-logo-*.png`, `client-logo-*.png`): se ajusta igual y se incrusta en el SVG. Para el DXF se vectoriza a color (requiere `vtracer`).
- Si hay SVG y PNG del mismo prefijo, se usa el SVG. Si no hay ninguno, el recuadro muestra la leyenda LOGO EMPRESA o LOGO CLIENTE.
- `assets/logo.png` es solo la imagen del README: el generador no la usa.

## 🧰 Requisitos

- Python 3.10 o superior.
- `openpyxl`, `ezdxf`, `svgelements` y `shapely`.
- `vtracer`, solo si usás logos PNG: sin él el logo sale en el SVG pero no en el DXF.

```bash
pip install openpyxl ezdxf svgelements shapely vtracer
```

## 🛠️ Uso desde el repositorio

```bash
python src/titleblocks-generator.py
```

Sin `input-titleblocks.xlsx` en la carpeta actual, el script lee `src/input-titleblocks.xlsx`, toma los logos de `assets/` y escribe en `test/`.

## 🗂️ Estructura

```
.
├── assets/                       Logos de cliente y proveedor (y logo.png del README)
├── backups/                      Copias de trabajo (no versionadas)
├── plugin/
│   ├── iram-titleblock-plugin/   Plugin: manifiesto, scripts, skill, plantilla y README
│   └── iram-titleblock-plugin.plugin   Paquete instalable
├── src/                          Scripts y Excel de trabajo
├── test/                         Salida de prueba (no versionada)
└── vendor/                       Plugins o skills de terceros
```

## 📚 Documentación

- [CHANGELOG.md](CHANGELOG.md): historial de versiones.
- [CONTRIBUTING.md](CONTRIBUTING.md): cómo colaborar y convenciones de commits.

## 📜 Licencia

MIT. Ver [LICENSE](LICENSE).
