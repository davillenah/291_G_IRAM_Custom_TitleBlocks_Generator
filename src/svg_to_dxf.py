"""Convierte una lámina SVG (en mm) a DXF (AutoCAD).

Uso: python svg_to_dxf.py lamina.svg

- Líneas, rectángulos y círculos -> LINE / LWPOLYLINE (capa 0, color y tipo de línea ByLayer).
- Textos del rótulo -> TEXT en Arial (capa 0): 1,7 mm; aviso legal 1 mm; títulos con su tamaño.
- Cada logo vectorial -> relleno de color embebido (HATCH) y contorno (capa 0).
- Cada logo PNG (imagen incrustada en el SVG) -> se vectoriza a color con vtracer y se rellena (HATCH, capa 0),
  con el mismo ajuste que en el SVG. Sin vtracer el logo PNG no se incluye en el DXF.
- Unidades: mm. El origen queda abajo-izquierda (el DXF tiene Y hacia arriba).
"""
import hashlib
import io
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

import ezdxf
from ezdxf.colors import rgb2int
from ezdxf.enums import TextEntityAlignment
from svgelements import SVG, Circle, Ellipse, Image, Path, Polygon, Rect, Shape, SimpleLine, Text

try:
    import vtracer
except ImportError:  # opcional: solo hace falta para vectorizar logos PNG
    vtracer = None

PX_POR_MM = 3.779530  # svgelements convierte las medidas a px (96 dpi)
SEGMENTOS_CURVA = 16  # puntos por segmento curvo al aproximar las formas
SEGMENTOS_CURVA_LOGO = 3  # ídem en logos vectorizados: sus curvas son tramos de pocos píxeles
# vectorizado de logos PNG (vtracer): color, capas apiladas, curvas suaves
PARAMETROS_VECTORIZADO = dict(colormode="color", hierarchical="stacked", mode="spline", filter_speckle=4,
                              color_precision=6, layer_difference=16, corner_threshold=60, length_threshold=4.0,
                              max_iterations=10, splice_threshold=45, path_precision=3)
FORMATOS_IMAGEN = {"image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg"}
ALTURA_TEXTO_MM = 1.7  # altura de los textos del rótulo
FS_ROTULO = 2.778  # font-size que genera el SVG para 2 mm
ALTURA_LEGAL_MM = 1.0  # aviso de propiedad intelectual
FS_LEGAL = 1.528
ESTILO_TEXTO = "ARIAL"
FUENTE = "arial.ttf"
MARGEN_ESQUINA_MM = 1.4
SEPARACION_TITULOS_MM = 1.4  # separación extra entre las dos líneas del título  # distancia de los textos al borde superior de su celda
DESPLAZAMIENTO_CODIGO_X_MM = 1.0  # separa CODIGO DEL CLIENTE / CODIGO INTERNO del borde
# separación extra en el cuadro de dimensiones (mm, positivo = hacia arriba)
AJUSTES_TEXTO_MM = {"DIMENSIONES:": 0.6, "MILIMÉTRICAS": -0.6}
LOGOS = ("provider-logo", "client-logo")
FORMAS_XML = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}
ALINEACION = {
    "start": TextEntityAlignment.BOTTOM_LEFT,
    "middle": TextEntityAlignment.BOTTOM_CENTER,
    "end": TextEntityAlignment.BOTTOM_RIGHT,
}


def _mm(p):
    return (p.x / PX_POR_MM, p.y / PX_POR_MM)


def _pos_mm(e):
    x, y = e.transform.point_in_matrix_space((e.x, e.y))
    return x / PX_POR_MM, y / PX_POR_MM


def _polilineas(elemento, segmentos=SEGMENTOS_CURVA):
    """Devuelve [(puntos_mm, cerrada), ...] para una forma (trazos y contornos)."""
    salida = []
    actual = []
    cerrada = False

    def cerrar():
        nonlocal actual, cerrada
        if len(actual) > 1:
            cierra = cerrada or math.dist(actual[0], actual[-1]) < 1e-6
            if math.dist(actual[0], actual[-1]) < 1e-6:
                actual = actual[:-1]
            if len(actual) > 1:
                salida.append((actual, cierra))
        actual = []
        cerrada = False

    for seg in Path(elemento):
        tipo = type(seg).__name__
        if tipo == "Move":
            cerrar()
            actual = [_mm(seg.end)]
        elif tipo == "Close":
            cerrada = True
        elif seg.start is None or seg.end is None:
            continue
        else:
            if not actual:
                actual = [_mm(seg.start)]
            if tipo == "Line":
                actual.append(_mm(seg.end))
            else:
                for k in range(1, segmentos + 1):
                    actual.append(_mm(seg.point(k / segmentos)))
    cerrar()
    return salida


def _nombres_logos(svg_path):
    """Nombre del logo (o None) de cada forma, en el mismo orden que el SVG parseado."""
    nombres = []

    def recorrer(el, dentro):
        etiqueta = el.tag.split("}")[-1]
        nombre = dentro
        if etiqueta == "g" and el.get("id") in LOGOS:
            nombre = el.get("id")
        if etiqueta in FORMAS_XML:
            nombres.append(nombre)
        for hijo in el:
            recorrer(hijo, nombre)

    recorrer(ET.parse(svg_path).getroot(), None)
    return nombres


def _centrar_en_celda(lineas, textos):
    """Textos del rótulo: se ubican en la esquina superior de su celda.

    Devuelve {(texto, x_mm, y_mm): nueva_y_mm} (y en mm, hacia abajo)."""
    cap = ALTURA_TEXTO_MM * 0.716  # altura de mayúscula de Arial
    nuevas = {}
    tratados = set()
    for e, x, y in textos:
        if abs(float(e.font_size) - FS_ROTULO) > 0.01:
            continue
        arriba = [l for l in lineas if l[0] < y - 0.2 and l[1] - 0.5 <= x <= l[2] + 0.5]
        abajo = [l for l in lineas if l[0] > y + 0.2 and l[1] - 0.5 <= x <= l[2] + 0.5]
        if not arriba or not abajo:
            continue
        a = max(arriba)[0]
        b = min(abajo)[0]
        if not (3.0 <= b - a <= 12.0):
            continue
        grupo = [t for t in textos if a < t[2] < b and abs(t[1] - x) < 40
                 and abs(float(t[0].font_size) - FS_ROTULO) < 0.01]
        claves = [(t[0].text.strip(), round(t[1], 2), round(t[2], 2)) for t in grupo]
        if any(c in tratados for c in claves):
            continue
        desplazamiento = (a + MARGEN_ESQUINA_MM + cap) - min(t[2] for t in grupo)
        for c, t in zip(claves, grupo):
            nuevas[c] = t[2] + desplazamiento
            tratados.add(c)
    return nuevas


def _logos(svg_path, formas):
    """Caja de cada logo (mm) y conjunto de formas que forman parte de un logo."""
    nombres = _nombres_logos(svg_path)
    cajas, omitir = {}, set()
    if len(nombres) != len(formas):
        return cajas, omitir
    for nombre, e in zip(nombres, formas):
        if not nombre:
            continue
        omitir.add(id(e))
        caja_forma = e.bbox(transformed=True)
        if caja_forma is None:  # forma sin área (p. ej. path vacío de un trazado): no aporta a la caja
            continue
        x0, y0, x1, y1 = caja_forma
        caja = cajas.get(nombre, [x0, y0, x1, y1])
        cajas[nombre] = [min(caja[0], x0), min(caja[1], y0), max(caja[2], x1), max(caja[3], y1)]
    return {k: [v / PX_POR_MM for v in caja] for k, caja in cajas.items()}, omitir


def _relleno(e):
    """Color de relleno (r, g, b) de una forma, o None si no tiene relleno."""
    f = getattr(e, "fill", None)
    if f is None or f.value is None or str(f.value).lower() == "none":
        return None
    return (int(f.red), int(f.green), int(f.blue))


def _area_relleno(bucles):
    """Regla de relleno no cero (como SVG por defecto): contornos positivos menos negativos.

    Devuelve [(contorno_exterior, [huecos]), ...] en mm."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    def firmado(pts):
        return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) / 2

    # sentido principal: el del contorno de mayor área; los de sentido contrario son huecos
    principal = max(bucles, key=lambda p: abs(firmado(p)))
    sentido = firmado(principal) > 0
    pos, neg = [], []
    for pts in bucles:
        pol = Polygon(pts).buffer(0)
        if pol.is_empty:
            continue
        (pos if (firmado(pts) > 0) == sentido else neg).append(pol)
    area = unary_union(pos) if pos else Polygon()
    if neg:
        area = area.difference(unary_union(neg))
    geometrias = list(area.geoms) if hasattr(area, "geoms") else [area]
    salida = []
    for g in geometrias:
        if g.is_empty or g.geom_type != "Polygon":
            continue
        salida.append((list(g.exterior.coords)[:-1], [list(h.coords)[:-1] for h in g.interiors]))
    return salida


def _separar_titulos(textos):
    """Separa verticalmente las dos líneas del título (denominación y tipo de plano)."""
    titulos = [t for t in textos if float(t[0].font_size) > 2.9 and len(t[0].text.strip()) > 2]
    nuevas = {}
    for i, (e1, x1, y1) in enumerate(titulos):
        for e2, x2, y2 in titulos[i + 1:]:
            if abs(x1 - x2) < 3 and 0 < abs(y1 - y2) < 6:
                arriba, abajo = ((e1, x1, y1), (e2, x2, y2)) if y1 < y2 else ((e2, x2, y2), (e1, x1, y1))
                mitad = SEPARACION_TITULOS_MM / 2
                nuevas[(arriba[0].text.strip(), round(arriba[1], 2), round(arriba[2], 2))] = arriba[2] - mitad
                nuevas[(abajo[0].text.strip(), round(abajo[1], 2), round(abajo[2], 2))] = abajo[2] + mitad
    return nuevas


_CACHE_VECTORIZADO = {}
_AVISOS = set()


def _aviso(clave, texto):
    if clave not in _AVISOS:
        _AVISOS.add(clave)
        print(f"aviso: {texto}", file=sys.stderr)


def _rellenar(msp, bucles, color, y_dxf):
    """HATCH de color (capa 0) para los contornos de una forma."""
    for exterior, interiores in _area_relleno(bucles):
        relleno = msp.add_hatch(dxfattribs={"layer": "0"})
        relleno.dxf.true_color = rgb2int(color)
        relleno.paths.add_polyline_path([(px, y_dxf(py)) for px, py in exterior], is_closed=True)
        for hueco in interiores:
            relleno.paths.add_polyline_path([(px, y_dxf(py)) for px, py in hueco], is_closed=True)


def _trazar(datos, formato):
    """Cuerpo SVG (texto) de la imagen vectorizada a color, o None si no se puede. Se guarda en caché por contenido."""
    clave = hashlib.sha1(datos).hexdigest()
    if clave not in _CACHE_VECTORIZADO:
        cuerpo = None
        if vtracer is None:
            _aviso("vtracer", "falta vtracer (pip install vtracer): los logos PNG no se incluyen en el DXF")
        else:
            try:
                svg = vtracer.convert_raw_image_to_svg(datos, img_format=formato, **PARAMETROS_VECTORIZADO)
                cuerpo = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
            except Exception as error:  # imagen dañada o formato no soportado por vtracer
                _aviso(clave, f"no se pudo vectorizar un logo ({error})")
        _CACHE_VECTORIZADO[clave] = cuerpo
    return _CACHE_VECTORIZADO[clave]


def _formas_imagen(imagen):
    """[(forma, color)] de una imagen incrustada vectorizada, ya colocada en el documento (px).

    Usa la transformación acumulada de la imagen, la misma que la ajusta a su recuadro en el SVG."""
    datos = getattr(imagen, "data", None)
    tipo = (getattr(imagen, "media_type", None) or [""])[0].lower()
    if not datos:
        return []
    if tipo not in FORMATOS_IMAGEN:
        _aviso(tipo, f"imagen {tipo or 'sin tipo'} no soportada para vectorizar; no se incluye en el DXF")
        return []
    cuerpo = _trazar(datos, FORMATOS_IMAGEN[tipo])
    if not cuerpo:
        return []
    m = imagen.transform
    envoltorio = (f'<svg xmlns="http://www.w3.org/2000/svg"><g transform="matrix('
                  f'{m.a:.10g} {m.b:.10g} {m.c:.10g} {m.d:.10g} {m.e:.10g} {m.f:.10g})">{cuerpo}</g></svg>')
    area_imagen = abs(float(imagen.width) * m.a) * abs(float(imagen.height) * m.d)
    salida = []
    for forma in SVG.parse(io.StringIO(envoltorio), reify=True).elements():
        if not isinstance(forma, Shape) or isinstance(forma, Text):
            continue
        color = _relleno(forma)
        caja = forma.bbox(transformed=True)
        if not color or caja is None:
            continue
        # el fondo blanco que cubre toda la imagen no es parte del logo
        if color == (255, 255, 255) and area_imagen and (caja[2] - caja[0]) * (caja[3] - caja[1]) >= 0.98 * area_imagen:
            continue
        salida.append((forma, color))
    return salida


def convertir(svg_path, dxf_path=None):
    dxf_path = dxf_path or os.path.splitext(svg_path)[0] + ".dxf"
    svg = SVG.parse(svg_path, reify=True)
    alto_mm = 0.0
    if svg.height is not None:
        alto_mm = float(svg.height.in_px() if hasattr(svg.height, "in_px") else svg.height) / PX_POR_MM

    elementos = list(svg.elements())
    formas = [e for e in elementos if isinstance(e, Shape) and not isinstance(e, Text)]
    cajas_logos, omitir = _logos(svg_path, formas)

    textos = []
    for e in elementos:
        if isinstance(e, Text) and e.text and e.text.strip():
            x, y = _pos_mm(e)
            textos.append((e, x, y))
    lineas = []
    for e in formas:
        if id(e) in omitir or getattr(e, "id", None) == "papel":
            continue
        try:
            for pts, cerr in _polilineas(e):
                for (x1, y1), (x2, y2) in zip(pts, pts[1:] + ([pts[0]] if cerr else [])):
                    if abs(y1 - y2) < 0.05 and abs(x1 - x2) > 0.5:
                        lineas.append(((y1 + y2) / 2, min(x1, x2), max(x1, x2)))
        except Exception:
            pass
    centrados = _centrar_en_celda(lineas, textos)
    centrados.update(_separar_titulos(textos))

    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4  # milímetros
    doc.styles.add(ESTILO_TEXTO, font=FUENTE)
    msp = doc.modelspace()

    def y_dxf(y):
        return alto_mm - y

    for e in elementos:
        if isinstance(e, Text):
            if not e.text or not e.text.strip():
                continue
            x, y = _pos_mm(e)
            clave = (e.text.strip(), round(x, 2), round(y, 2))
            if clave in centrados:
                y = centrados[clave]
            fs = float(e.font_size) if e.font_size else 2.0
            if abs(fs - FS_ROTULO) < 0.01:
                alto = ALTURA_TEXTO_MM
            elif abs(fs - FS_LEGAL) < 0.01:
                alto = ALTURA_LEGAL_MM
            else:
                alto = fs
            angulo = math.degrees(math.atan2(e.transform.b, e.transform.a))
            texto = msp.add_text(e.text, dxfattribs={"height": alto, "layer": "0",
                                                     "rotation": -angulo, "style": ESTILO_TEXTO})
            alineacion = ALINEACION.get(str(e.values.get("text-anchor", "start")), TextEntityAlignment.BOTTOM_LEFT)
            if abs(fs - FS_LEGAL) < 0.01:
                alineacion = TextEntityAlignment.MIDDLE_CENTER
            desplazamiento = AJUSTES_TEXTO_MM.get(e.text.strip(), 0.0)
            if e.text.strip().startswith("CODIGO"):
                x += DESPLAZAMIENTO_CODIGO_X_MM
            texto.set_placement((x, y_dxf(y) + desplazamiento), align=alineacion)
        elif isinstance(e, Image):
            # logo PNG: se vectoriza y se rellena, sin contorno (solo relleno de color)
            for forma, color in _formas_imagen(e):
                bucles = [pts for pts, _ in _polilineas(forma, SEGMENTOS_CURVA_LOGO) if len(pts) > 2]
                if bucles:
                    _rellenar(msp, bucles, color, y_dxf)
        elif isinstance(e, (SimpleLine, Rect, Polygon, Circle, Ellipse, Path)):
            if getattr(e, "id", None) == "papel":
                continue
            if id(e) in omitir:
                color = _relleno(e)
                bucles = [pts for pts, _ in _polilineas(e) if len(pts) > 2]
                if color and bucles:
                    _rellenar(msp, bucles, color, y_dxf)
                # contorno siempre, para que las letras blancas (p. ej. "ORD") se vean sobre el papel
                for pts, cerrada in _polilineas(e):
                    msp.add_lwpolyline([(px, y_dxf(py)) for px, py in pts],
                                       close=cerrada, dxfattribs={"layer": "0"})
                continue
            for puntos, cerrada in _polilineas(e):
                if len(puntos) == 2 and not cerrada:
                    (x1, y1), (x2, y2) = puntos
                    msp.add_line((x1, y_dxf(y1)), (x2, y_dxf(y2)), dxfattribs={"layer": "0"})
                else:
                    msp.add_lwpolyline([(x, y_dxf(y)) for x, y in puntos],
                                       close=cerrada, dxfattribs={"layer": "0"})

    doc.saveas(dxf_path)
    return dxf_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("uso: python svg_to_dxf.py lamina.svg")
    print(convertir(sys.argv[1]))
