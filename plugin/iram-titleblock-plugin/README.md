# iram-titleblock-plugin

Genera láminas IRAM A0 a A4 en SVG con rótulo personalizado y logos del proveedor y del cliente, a partir de `input-titleblocks.xlsx`.

## Uso

1. Copiar `input-titleblocks.xlsx` y los logos (`provider-logo-*.svg`, `client-logo-*.svg`) a la carpeta del proyecto. Si no hay Excel, el plugin trae una plantilla en `templates/`.
2. Completar el Excel (una fila por lámina).
3. Pedir: "generá las láminas" o "usá el plugin de rótulos IRAM". Las láminas quedan en `svg/` como SVG y DXF (`sheet-IRAM-A0.svg` y `sheet-IRAM-A0.dxf`, etc.).

## Requisitos

- Python 3 con `openpyxl`, `ezdxf`, `svgelements` y `shapely` (`pip install openpyxl ezdxf svgelements shapely`).

## Estructura

- `scripts/titleblocks-generator.py`: lee el Excel de la carpeta actual y genera una lámina por fila.
- `scripts/sheet-generator.py`: dibuja la lámina, el rótulo y los logos.
- `skills/iram-titleblock-custom-generator/SKILL.md`: instrucciones para Claude.
- `templates/input-titleblocks.xlsx`: plantilla del Excel.
