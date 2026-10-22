"""Convierte una lámina SVG (en mm) a DXF (AutoCAD).

Uso: python svg_to_dxf.py lamina.svg

- Líneas, rectángulos y círculos -> LINE / LWPOLYLINE (capa LINEAS).
- Textos del rótulo -> TEXT en Arial (capa TEXTO): 1,7 mm; aviso legal 1 mm; títulos con su tamaño.
- Cada logo -> relleno de color embebido (HATCH) y contorno (capa LOGOS).
- Unidades: mm. El origen queda abajo-izquierda (el DXF tiene Y hacia arriba).
"""
import math
import os
import sys
import xml.etree.ElementTree as ET

import ezdxf
from ezdxf.colors import rgb2int
from ezdxf.enums import TextEntityAlignment
from svgelements import SVG, Circle, Ellipse, Path, Polygon, Rect, Shape, SimpleLine, Text

PX_POR_MM = 3.779530  # svgelements convierte las medidas a px (96 dpi)
SEGMENTOS_CURVA = 16  # puntos por segmento curvo al aproximar las formas
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


def _polilineas(elemento):
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
                for k in range(1, SEGMENTOS_CURVA + 1):
                    actual.append(_mm(seg.point(k / SEGMENTOS_CURVA)))
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
        x0, y0, x1, y1 = e.bbox(transformed=True)
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
    doc.layers.add("LINEAS")
    doc.layers.add("TEXTO")
    doc.layers.add("LOGOS")
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
            texto = msp.add_text(e.text, dxfattribs={"height": alto, "layer": "TEXTO",
                                                     "rotation": -angulo, "style": ESTILO_TEXTO})
            alineacion = ALINEACION.get(str(e.values.get("text-anchor", "start")), TextEntityAlignment.BOTTOM_LEFT)
            if abs(fs - FS_LEGAL) < 0.01:
                alineacion = TextEntityAlignment.MIDDLE_CENTER
            desplazamiento = AJUSTES_TEXTO_MM.get(e.text.strip(), 0.0)
            if e.text.strip().startswith("CODIGO"):
                x += DESPLAZAMIENTO_CODIGO_X_MM
            texto.set_placement((x, y_dxf(y) + desplazamiento), align=alineacion)
        elif isinstance(e, (SimpleLine, Rect, Polygon, Circle, Ellipse, Path)):
            if getattr(e, "id", None) == "papel":
                continue
            if id(e) in omitir:
                color = _relleno(e)
                bucles = [pts for pts, _ in _polilineas(e) if len(pts) > 2]
                if color and bucles:
                    for exterior, interiores in _area_relleno(bucles):
                        relleno = msp.add_hatch(color=7, dxfattribs={"layer": "LOGOS"})
                        relleno.dxf.true_color = rgb2int(color)
                        relleno.paths.add_polyline_path([(px, y_dxf(py)) for px, py in exterior], is_closed=True)
                        for hueco in interiores:
                            relleno.paths.add_polyline_path([(px, y_dxf(py)) for px, py in hueco], is_closed=True)
                # contorno siempre, para que las letras blancas (p. ej. "ORD") se vean sobre el papel
                for pts, cerrada in _polilineas(e):
                    msp.add_lwpolyline([(px, y_dxf(py)) for px, py in pts],
                                       close=cerrada, dxfattribs={"layer": "LOGOS"})
                continue
            for puntos, cerrada in _polilineas(e):
                if len(puntos) == 2 and not cerrada:
                    (x1, y1), (x2, y2) = puntos
                    msp.add_line((x1, y_dxf(y1)), (x2, y_dxf(y2)), dxfattribs={"layer": "LINEAS"})
                else:
                    msp.add_lwpolyline([(x, y_dxf(y)) for x, y in puntos],
                                       close=cerrada, dxfattribs={"layer": "LINEAS"})

    doc.saveas(dxf_path)
    return dxf_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("uso: python svg_to_dxf.py lamina.svg")
    print(convertir(sys.argv[1]))
