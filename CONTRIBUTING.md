# Cómo contribuir

Gracias por colaborar con el generador de láminas IRAM.

## Estructura

| Carpeta | Contenido |
|---|---|
| `assets/` | Logos de cliente y proveedor (`client-logo-*.svg` o `.png`, `provider-logo-*.svg` o `.png`) y `logo.png` del README |
| `backups/` | Copias de trabajo (no versionadas) |
| `plugin/` | Plugin empaquetable: manifiesto, scripts, skill, plantilla y paquete `.plugin` |
| `src/` | Copia de trabajo de los scripts y del Excel de ejemplo |
| `test/` | Salida de prueba (no versionada) |
| `vendor/` | Plugins o skills de terceros que el proyecto necesite |

## Flujo de trabajo

1. Crear una rama desde `main`: `git checkout -b feat/nombre-corto`.
2. Hacer los cambios y generar las láminas A0 a A4 para comprobarlas.
3. Regenerar los DXF de las láminas modificadas.
4. Actualizar `CHANGELOG.md` con la nueva versión.
5. Abrir un Pull Request usando la plantilla de `.github/pull_request_template.md`.

## Scripts

Los cambios en `plugin/iram-titleblock-plugin/scripts/` deben reflejarse en `src/` en el mismo PR, mientras existan las dos copias.

## Mensajes de commit

Usar [Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/):

- `feat(lamina): ...` nueva funcionalidad
- `fix(lamina): ...` corrección de geometría o texto
- `fix(dxf): ...` corrección del conversor DXF
- `docs: ...` documentación
- `chore(release): x.y.z` cambio de versión

## Versionado

Se usa Versionado Semántico:

- **MAJOR**: cambio que rompe el formato del Excel o los nombres de salida.
- **MINOR**: funcionalidad nueva (por ejemplo, un formato o una columna nueva).
- **PATCH**: corrección de geometría, de texto o de un error.

## Reportar problemas

Abrí un issue con el nombre de la lámina, la versión del plugin y una captura del resultado esperado y del obtenido.
