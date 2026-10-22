# IRAM Titleblock Generator

Genera láminas IRAM A0 a A4 en SVG y DXF con rótulo personalizado (empresa, cliente, proyectado / verificado / validado, códigos, hoja, estado y revisión) y con los logos del proveedor y del cliente, a partir de un Excel.

## Qué genera

Por cada fila del Excel:

- `sheet-IRAM-<formato>.svg`: lámina vectorial editable.
- `sheet-IRAM-<formato>.dxf`: lámina para CAD, con textos en Arial, logos como relleno de color y contorno.

Opcionalmente, un bloque de rótulo y uno de lista de modificaciones (`title-block-IRAM4508.svg`, `modifications-block-IRAM4508.svg`).

## Uso como plugin

1. Copiar `plugin/iram-titleblock-plugin.plugin` a tu proyecto y reinstalarlo desde Claude.
2. Copiar a la carpeta del proyecto `input-titleblocks.xlsx` y los logos (`provider-logo-*.svg`, `client-logo-*.svg`). Si no hay Excel, el plugin trae una plantilla en `templates/`.
3. Completar el Excel: una fila por lámina.
4. Pedir: "generá las láminas" o "usá el plugin de rótulos IRAM".

Las láminas quedan en `svg/` dentro de la carpeta del proyecto.

## Requisitos

- Python 3.10 o superior.
- `openpyxl`, `ezdxf`, `svgelements` y `shapely`:

```bash
pip install openpyxl ezdxf svgelements shapely
```

## Uso desde el repositorio

```bash
python src/titleblocks-generator.py
```

Sin `input-titleblocks.xlsx` en la carpeta actual, el script lee `src/input-titleblocks.xlsx`, toma los logos de `assets/` y escribe en `test/`.

## Estructura

```
.
├── assets/                       Logos de cliente y proveedor
├── backups/                      Copias de trabajo (no versionadas)
├── plugin/
│   ├── iram-titleblock-plugin/   Plugin: manifiesto, scripts, skill, plantilla y README
│   └── iram-titleblock-plugin.plugin   Paquete instalable
├── src/                          Scripts y Excel de trabajo
├── test/                         Salida de prueba (no versionada)
└── vendor/                       Plugins o skills de terceros
```

## Documentación

- [CHANGELOG.md](CHANGELOG.md): historial de versiones.
- [CONTRIBUTING.md](CONTRIBUTING.md): cómo colaborar y convenciones de commits.

## Licencia

MIT. Ver [LICENSE](LICENSE).
