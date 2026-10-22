"""Láminas A0 a A4 según IRAM 4504 (formatos, elementos gráficos y plegado)
e IRAM 4508 (rótulo), tal como las dibuja el Manual IRAM Ed. XXVII.

- Formato A0 841 x 1189 usado apaisado: 1189 de ancho x 841 de alto
  (hoja tipo "A", 4504 2.1.2 y fig. 1; la fig. 6 muestra el A0 vertical).
- Margen a = 20 en los cuatro lados: en A0 el archivado no lleva margen de
  25 sino una banda adhesiva aparte (4504 2.3.1 y fig. 16, detalle A).
  El valor 20 es el de la fig. 7 (margen izquierdo hasta el recuadro) y el
  de ISO 5457:1980 para A0, norma en la que se basa la revisión.
- Franja de coordenadas de 5 mm (fig. 6/7). Módulo "aproximadamente 105 en
  abscisas y 148,5 en ordenadas" (2.3.3), medido desde los bordes de la hoja y con
  cantidad par de campos para que las señales de centrado caigan en una división:
  12 columnas de 99,08 y 6 filas de 140,17. Letras M..A de izquierda a derecha
  (A del lado del rótulo, sin la I para no confundirla con 1), números 1..6 de
  abajo hacia arriba. Abajo y a la derecha van girados, como en la fig. 6.
- Escala de comparación de 200 mm sin cifras, a 10 mm del borde izquierdo,
  arriba (2.3.4, fig. 7).
- Flecha de orientación en el borde inferior, hacia el dibujante (2.5, fig. 6).
- Rótulo IRAM 4508 fig. 2 (175 x 51) como bloque propio. La lista de modificaciones
  fig. 3 (175 x 21,5) es otro bloque, aparte, que se coloca encima sólo si hace falta
  (posición en data-modificaciones del <svg>).

Unidades mm, origen arriba-izquierda. Uso: python3 sheet-generator.py A0|A1|A2|A3|A4 [salida.svg] [--mod]
Genera también title-block-IRAM4508.svg y modifications-block-IRAM4508.svg junto a la salida.
"""
import base64
import glob
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET

# formato: (ancho, alto, margen izq., margen sup./der./inf., columnas, filas)
# A0: margen 20 en los 4 lados (archivado con banda adhesiva, fig. 16).
# A1..A4: margen de archivado 25 a la izquierda y a = 10 (2.3.1, 2.3.2, fig. 5).
# Coordenadas ~105 x 148,5 (2.3.3): A1 8 x 4 y A3 4 x 2 exactos como en la fig. 6;
# A0 12 x 6 y A2 6 x 3 (módulo ~99 x 140). A4 sin coordenadas (nota fig. 6).
FORMATOS = {
    "A0": (1189, 841, 20, 20, 12, 6),
    "A1": (841, 594, 25, 10, 8, 4),
    "A2": (594, 420, 25, 10, 6, 3),
    "A3": (420, 297, 25, 10, 4, 2),
    "A4": (210, 297, 25, 10, 0, 0),
}
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
MOD = "--mod" in sys.argv          # agrega la lista de modificaciones (fig. 3) sobre el rótulo
FMT = ARGS[0].upper() if ARGS else "A0"
W, H, A_IZQ, A, N_COL, N_FIL = FORMATOS[FMT]
CON_COORD = N_COL > 0
FR = 5 if CON_COORD else 0   # franja de coordenadas
FONT = "osifont, ISOCPEUR, 'DejaVu Sans', Arial, sans-serif"

# Logos: se incrustan en los recuadros del rótulo final (LOGO EMPRESA / LOGO CLIENTE).
# provider-logo-*.svg o .png -> recuadro de la empresa responsable del proyecto
# client-logo-*.svg o .png   -> recuadro del cliente
# Se ajustan (escala uniforme, centrados) a su recuadro. Si hay SVG y PNG del mismo prefijo, gana el SVG.
# Un PNG se incrusta como imagen en el SVG y svg_to_dxf.py lo vectoriza para el DXF.
# Logos: carpeta del proyecto (IRAM_PROYECTO, la fija titleblocks-generator.py); si no, la carpeta de este script
BASE = os.environ.get("IRAM_PROYECTO") or os.path.dirname(os.path.abspath(__file__))
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("xlink", XLINK_NS)


def buscar_logo(prefijo):
    """Ruta del logo <prefijo>-logo-*: el primer .svg; si no hay, el primer .png; o None."""
    for ext in ("svg", "png"):
        hallados = sorted(glob.glob(os.path.join(BASE, f"{prefijo}-logo-*.{ext}")))
        if len(hallados) > 1:
            print(f"aviso: hay varios {prefijo}-logo-*.{ext}; se usa {os.path.basename(hallados[0])}", file=sys.stderr)
        if hallados:
            return hallados[0]
    return None


def _tamano_png(path):
    """(ancho, alto) en píxeles de un PNG, leído de su cabecera IHDR."""
    with open(path, "rb") as f:
        cab = f.read(24)
    if cab[:8] != b"\x89PNG\r\n\x1a\n" or cab[12:16] != b"IHDR":
        raise ValueError(f"{os.path.basename(path)} no es un PNG válido")
    return struct.unpack(">II", cab[16:24])


def logo_anidado(path, x, y, w, h, gid):
    """Incrusta el logo (SVG o PNG) ajustado al recuadro (x, y, w, h en mm): escala uniforme y centrado.
    SVG: se anida su contenido, sin los metadatos de Inkscape/Sodipodi (no son SVG estándar).
    PNG: se incrusta como <image> con los datos en base64; el DXF lo vectoriza."""
    if path.lower().endswith(".png"):
        vx = vy = 0.0
        vw, vh = _tamano_png(path)
        with open(path, "rb") as f:
            datos = base64.b64encode(f.read()).decode("ascii")
        contenido = (f'<image xmlns:xlink="{XLINK_NS}" width="{vw}" height="{vh}" '
                     f'xlink:href="data:image/png;base64,{datos}"/>')
    else:
        root = ET.parse(path).getroot()
        vb = root.get("viewBox")
        if vb:
            vx, vy, vw, vh = (float(v) for v in vb.replace(",", " ").split())
        elif root.get("width") and root.get("height"):
            # logo sin viewBox: se toma el tamaño propio
            vx, vy = 0.0, 0.0
            vw, vh = (float(re.sub(r"[^0-9.]", "", root.get(a))) for a in ("width", "height"))
        else:
            raise ValueError(f"{os.path.basename(path)} no tiene viewBox ni width/height")

        def limpiar(el):
            for hijo in list(el):
                if not hijo.tag.startswith("{" + SVG_NS):
                    el.remove(hijo)
                    continue
                limpiar(hijo)
            for k in list(el.attrib):
                # se conserva xlink:href (imágenes incrustadas); se quitan los demás atributos con namespace
                if k.startswith("{") and not k.startswith("{" + XLINK_NS):
                    del el.attrib[k]

        limpiar(root)
        contenido = "".join(ET.tostring(h_, encoding="unicode").replace(f' xmlns="{SVG_NS}"', "") for h_ in root)
    k = min(w / vw, h / vh)                      # escala uniforme, ajustada al recuadro
    ox = x + (w - vw * k) / 2 - vx * k           # centrado dentro del recuadro
    oy = y + (h - vh * k) / 2 - vy * k
    archivo = os.path.basename(path).replace("&", "&amp;").replace('"', "&quot;")
    return (f'<g id="{gid}" data-archivo="{archivo}" transform="translate({ox:.4f} {oy:.4f}) scale({k:.6f})">'
            + contenido + "</g>")

# Espesores
W_REC = 1.0       # recuadro (línea A, grupo d de IRAM 4502)
W_UTIL = 0.5      # límite de la zona útil y divisiones de coordenadas
W_08, W_04, W_02 = 0.8, 0.4, 0.2  # rótulo (4508 fig. 2)

out = []
grupos = {}


def g(name):
    grupos.setdefault(name, [])
    return grupos[name]


def line(grp, x1, y1, x2, y2, sw):
    g(grp).append(f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke-width="{sw}"/>')


def rect(grp, x, y, w, h, sw):
    g(grp).append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="none" stroke-width="{sw}"/>')


# texto del rótulo final a 2 mm; quedan con su tamaño el título, el tipo de plano (círculo rojo) y el aviso legal
TAMANO_LIBRE = ("denominacion", "denominacion_2", "tipo_plano")
H_FIJO = 2.0  # altura de 2 mm para el texto del rótulo final


def text(grp, x, y, s, h, anchor="start", key=None, rot=0, weight=None):
    if H_FIJO and grp.startswith("rotulo") and key not in TAMANO_LIBRE and h != 1.1:
        h = H_FIJO
    """(x, y): línea base; h: altura nominal de mayúscula (IRAM 4503)."""
    fs = h / 0.72
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    k = f' data-key="{key}" data-placeholder="{{{key}}}"' if key else ""
    r = f' transform="rotate({rot} {x:g} {y:g})"' if rot else ""
    wgt = f' font-weight="{weight}"' if weight else ""
    g(grp).append(f'<text stroke="none" x="{x:g}" y="{y:g}" font-size="{fs:.3f}"{a}{k}{r}{wgt}>{s}</text>')


# ---------------- recuadro y zona útil ----------------
x0, y0, x1, y1 = A_IZQ, A, W - A, H - A             # recuadro
u0, v0, u1, v1 = x0 + FR, y0 + FR, x1 - FR, y1 - FR  # zona útil
rect("corte", 0, 0, W, H, 0.1)
rect("recuadro", x0, y0, x1 - x0, y1 - y0, W_REC)
if CON_COORD:
    rect("recuadro", u0, v0, u1 - u0, v1 - v0, W_UTIL)

# ---------------- coordenadas modulares ----------------
mx, my = W / max(N_COL, 1), H / max(N_FIL, 1)
letras = "MLKJHGFEDCBA"[12 - N_COL:]
th = 3.5
for i in range(1, N_COL):
    x = i * mx
    line("coordenadas", x, y0, x, v0, W_UTIL)
    line("coordenadas", x, v1, x, y1, W_UTIL)
for j in range(1, N_FIL):
    y = j * my
    line("coordenadas", x0, y, u0, y, W_UTIL)
    line("coordenadas", u1, y, x1, y, W_UTIL)
for i in range(N_COL):
    xa, xb = max(i * mx, u0), min((i + 1) * mx, u1)
    cx = (xa + xb) / 2
    text("coordenadas", cx, y0 + FR / 2 + th / 2, letras[i], th, "middle")
    # abajo: girada, como en la fig. 6
    text("coordenadas", cx + th / 2, v1 + FR / 2, letras[i], th, "middle", rot=-90)
for j in range(N_FIL):
    ya, yb = max(j * my, v0), min((j + 1) * my, v1)
    cy = (ya + yb) / 2
    num = str(N_FIL - j)
    text("coordenadas", x0 + FR / 2, cy + th / 2, num, th, "middle")
    text("coordenadas", u1 + FR / 2 + th / 2, cy, num, th, "middle", rot=-90)

# ---------------- escala de comparación (fig. 7) ----------------
if CON_COORD:  # el A4 de la fig. 6 no la lleva
    for k in range(0, 201, 10):
        line("escala_comparacion", 10, y0 + k, 15, y0 + k, W_02)
    line("escala_comparacion", 15, y0, 15, y0 + 200, W_02)

# ---------------- flecha de orientación ----------------
cx, cy = W / 2, H / 2
# Flecha de orientación (detalle fig. 6): triángulo de ~6 mm con el vértice
# en el recuadro, parte superior llena sobre el límite de la zona útil.
if CON_COORD:  # el A4 de la fig. 6 no la lleva
    g("orientacion").append(
        f'<polygon points="{cx - 3:g},{v1 - 1:g} {cx + 3:g},{v1 - 1:g} {cx:g},{y1:g}" fill="none" stroke-width="{W_02}"/>')
    g("orientacion").append(
        f'<polygon points="{cx - 3:g},{v1 - 1:g} {cx + 3:g},{v1 - 1:g} {cx + 1:g},{v1 + 3:g} {cx - 1:g},{v1 + 3:g}" '
        f'fill="#000" stroke="none"/>')
    line("orientacion", cx, v1 - 1, cx, v1 - 4, W_04)
    line("orientacion", cx, v1 - 4, cx + 3, v1 - 4, W_04)
    line("orientacion", cx + 3, v1 - 4, cx + 3, v1 - 1, W_04)

# ---------------- rótulo IRAM 4508 fig. 2 y lista de modificaciones fig. 3 ----------------
RW, RH, MH = 175, 51, 21.5
rx, ry = u1 - RW, v1 - RH
cx_ = [0, 26, 46, 56, 75, 120, 175]   # columnas 26/20/10/19/45/55
XV = 64                               # borde izquierdo de la casilla 7
t25 = 2.5
lab = 1.8   # leyendas impresas en la fig. 2


def dibujar_rotulo(G):
    """Fig. 2: 175 x 51. Espesores 0,8 contorno, 0,4 límites de casilla, 0,2 subdivisiones."""
    L, T, V = G, G + "_txt", G + "_var"
    c = cx_
    rect(L, 0, 0, RW, RH, W_08)
    # (1) anotaciones complementarias: columna de 26 a todo lo alto
    line(L, c[1], 0, c[1], RH, W_04)
    text(V, 1.5, 5, "{notas}", t25, key="notas")
    # (5) Fecha / Nombre y Dib. / Rev. / Apr.: 4 renglones en 17 mm, columnas 20/10/19
    r5 = 17 / 4
    for k in (1, 2, 3):
        line(L, c[1], k * r5, c[4], k * r5, W_02)
    line(L, c[2], 0, c[2], 17, W_02)
    line(L, c[3], 0, c[3], 17, W_02)
    text(T, c[2] + 0.5, r5 - 1.1, "Fecha", lab)
    text(T, c[3] + 0.6, r5 - 1.1, "Nombre", lab)
    for k, s in enumerate(("Dibujado por:", "Revisado por:", "Aprobado por:"), start=2):
        text(T, c[1] + 0.8, k * r5 - 1.1, s, lab)
    for k, role in enumerate(("dib", "rev", "apr"), start=2):
        text(V, c[2] + 0.5, k * r5 - 1.1, "{%s_fecha}" % role, 1.2, key=role + "_fecha")
        text(V, c[3] + 0.6, k * r5 - 1.1, "{%s_nombre}" % role, 1.2, key=role + "_nombre")
    # (6) cliente: 45 x 17
    line(L, c[4], 0, c[4], 17, W_04)
    text(V, (c[4] + c[5]) / 2, 10, "{cliente}", 3.5, "middle", key="cliente")
    # límite inferior de 5 y 6
    line(L, c[1], 17, c[5], 17, W_04)
    # (2) Esc. 11, (3) método ISO (E) 9, (4) Toler. / Rug. 14; columna de 20 y casillero de valor hasta 64
    line(L, c[2], 17, c[2], RH, W_02)
    line(L, c[1], 28, c[2], 28, W_02)
    line(L, c[1], 37, c[2], 37, W_02)
    text(T, c[1] + 0.8, 19.6, "Escala:", lab)
    text(V, (c[1] + c[2]) / 2, 25.8, "{escala}", 2.8, "middle", key="escala")
    sy, sx = 32.5, c[1] + 3.5   # tronco de cono y dos circunferencias (IRAM 4501)
    g(L).append(f'<polygon points="{sx:g},{sy - 1.3:g} {sx + 5:g},{sy - 2.6:g} {sx + 5:g},{sy + 2.6:g} {sx:g},{sy + 1.3:g}" '
                f'fill="none" stroke-width="{W_02}"/>')
    g(L).append(f'<circle cx="{sx + 10.5:g}" cy="{sy:g}" r="2.6" fill="none" stroke-width="{W_02}"/>')
    g(L).append(f'<circle cx="{sx + 10.5:g}" cy="{sy:g}" r="1.3" fill="none" stroke-width="{W_02}"/>')
    line(L, sx - 1, sy, sx + 14.5, sy, W_02)
    text(T, c[1] + 0.8, 37 + 3.2, "Toler.", lab)
    text(T, c[1] + 0.8, RH - 1.5, "Rug.", lab)
    text(V, (c[1] + c[2]) / 2, 45.2, "{tolerancia}", 1.6, "middle", key="tolerancia")
    text(V, c[1] + 9, RH - 1.5, "{rugosidad}", 1.4, key="rugosidad")
    # (7) denominación: de 64 a 120, alto 34
    text(V, (c[2] + c[5]) / 2, 17 + 15, "{denominacion}", 5, "middle", key="denominacion")
    text(V, (c[2] + c[5]) / 2, 17 + 24, "{denominacion_2}", 3.5, "middle", key="denominacion_2")
    # columna de 55: (8) 17 / (9) 17 / (10) 8,5 / (11) 8,5
    line(L, c[5], 0, c[5], RH, W_04)
    line(L, c[5], 17, c[6], 17, W_04)
    line(L, c[5], 34, c[6], 34, W_04)
    line(L, c[5], 42.5, c[6], 42.5, W_04)
    text(V, (c[5] + c[6]) / 2, 10.5, "{empresa}", 5, "middle", key="empresa")
    text(V, (c[5] + c[6]) / 2, 17 + 11, "{plano_n}", 5, "middle", key="plano_n")
    text(V, (c[5] + c[6]) / 2, 34 + 5.5, "{emision}", t25, "middle", key="emision")
    text(V, (c[5] + c[6]) / 2, 42.5 + 5.5, "{reemplaza}", t25, "middle", key="reemplaza")


def dibujar_final(G):
    """Rótulo final (referencia del cliente), en la misma caja 175 x 51.
    Coordenadas medidas sobre la referencia (998 x 297 px -> 175 x 51 mm)."""
    L, T, V, R = G, G + "_txt", G + "_var", G + "_rojo"
    def tl(x, y, s, h, anchor="start", rot=0):
        """etiqueta fija del rótulo: en mayúscula y negrita"""
        text(T, x, y, s.upper(), h, anchor, rot=rot, weight="bold")
    # el marco del rótulo (7..994 x 5..293 en la referencia) ocupa exactamente 175 x 51 mm,
    # así su contorno coincide con el recuadro de la lámina (en A4 se funden en un solo borde)
    P = lambda v: (v - 7) * 175 / 987
    Q = lambda v: (v - 5) * 51 / 288
    def hl(y, x1, x2): line(L, P(x1), Q(y), P(x2), Q(y), W_04)
    def vl(x, y1, y2): line(L, P(x), Q(y1), P(x), Q(y2), W_04)
    rect(L, P(7), Q(5), P(994) - P(7), Q(293) - Q(5), W_08)
    hl(29, 7, 373); hl(53, 7, 373); hl(77, 7, 373)
    hl(101, 7, 994)
    hl(149, 7, 148); hl(197, 7, 148); hl(245, 7, 148)
    hl(149, 148, 684); hl(245, 148, 684)
    hl(149, 684, 994); hl(197, 684, 994); hl(245, 684, 994)
    vl(148, 5, 293); vl(233, 5, 101); vl(373, 5, 101); vl(684, 5, 293)
    vl(761, 245, 293); vl(839, 245, 293); vl(916, 245, 293)
    # recuadros para logos: se incrustan provider-logo-*.svg y client-logo-*.svg;
    # sin logo queda la leyenda de referencia
    # cada logo ocupa su celda (de la línea vertical al texto siguiente), centrado en ambos ejes
    cy_top, cy_h = Q(5) + 0.3, Q(101) - Q(5) - 0.6
    xc_p = (P(373) + P(512)) / 2      # celda de la empresa: línea 373 .. texto 512
    xc_c = (P(684) + P(826)) / 2      # celda del cliente: línea 684 .. texto 826
    for prefijo, caja, leyenda, xc in (
            ("provider", (xc_p - 11.2, cy_top, 22.4, cy_h), "LOGO EMPRESA", xc_p),
            ("client", (xc_c - 11.4, cy_top, 22.8, cy_h), "LOGO CLIENTE", xc_c)):
        ruta = buscar_logo(prefijo)
        if ruta:
            g(L + "_logos").append(logo_anidado(ruta, *caja, prefijo + "-logo"))
        else:
            tl(xc, Q(54), leyenda, 1.6, "middle")
    lab, val = 1.7, 1.9
    # tabla superior: fecha / responsable
    tl(P(190), 3.1, "FECHA", lab, "middle")
    tl(P(303), 3.1, "RESPONSABLE", lab, "middle")
    for yb, lbl, kf, kn in ((7.35, "Proyectado por:", "proy_fecha", "proy_nombre"),
                            (11.6, "Verificado por:", "ver_fecha", "ver_nombre"),
                            (15.9, "Validado por:", "val_fecha", "val_nombre")):
        tl(P(15), yb, lbl, 1.3)
        text(V, P(190), yb, "{%s}" % kf, 1.5 if kf.endswith("fecha") else val, "middle", key=kf)
        text(V, P(303), yb, "{%s}" % kn, val, "middle", key=kn)
    # empresa (izquierda de la tabla superior derecha)
    text(V, P(512), 3.6, "<tspan font-weight=\"bold\">CUIT:</tspan> {empresa_cuit}", lab, key="empresa_cuit")
    tl(P(512), 6.5, "Razón Social:", 1.5)
    text(V, (P(512) + P(684)) / 2, 9.5, "{empresa}", val, "middle", key="empresa")
    text(V, P(512), 12.5, "<tspan font-weight=\"bold\">EMAIL:</tspan> {empresa_email}", lab, key="empresa_email")
    text(V, (P(512) + P(684)) / 2, 15.4, "{empresa_web}", lab, "middle", key="empresa_web")
    # cliente
    text(V, P(826), 3.6, "<tspan font-weight=\"bold\">CUIT:</tspan> {cliente_cuit}", lab, key="cliente_cuit")
    tl(P(826), 6.5, "Razón Social:", 1.5)
    text(V, (P(826) + P(994)) / 2, 9.5, "{cliente}", val, "middle", key="cliente")
    text(V, P(826), 12.5, "<tspan font-weight=\"bold\">EMAIL:</tspan> {cliente_email}", lab, key="cliente_email")
    text(V, (P(826) + P(994)) / 2, 15.4, "{cliente_web}", lab, "middle", key="cliente_web")
    # columna izquierda inferior: ISO, escala, aviso legal
    tl(P(77), 20.95, "DIMENSIONES:", lab, "middle")
    tl(P(77), 23.55, "milimétricas", lab, "middle")
    tl(P(15), 28.5, "Escala:", lab)
    # símbolo de método de proyección ISO (E), debajo de Escala (IRAM 4501): tronco de cono y dos circunferencias
    cxs, cys = P(77), (Q(197) + Q(245)) / 2
    sx, sy = cxs - 6.05, cys
    g(L).append(f'<polygon points="{sx:g},{sy - 1.3:g} {sx + 5:g},{sy - 2.6:g} {sx + 5:g},{sy + 2.6:g} {sx:g},{sy + 1.3:g}" '
                f'fill="none" stroke-width="{W_02}"/>')
    g(L).append(f'<circle cx="{sx + 10.5:g}" cy="{sy:g}" r="2.6" fill="none" stroke-width="{W_02}"/>')
    g(L).append(f'<circle cx="{sx + 10.5:g}" cy="{sy:g}" r="1.3" fill="none" stroke-width="{W_02}"/>')
    line(L, sx - 1, sy, sx + 14.5, sy, W_02)
    text(V, P(77), 32.5, "{escala}", 2.8, "middle", key="escala")
    # aviso legal centrado en horizontal y vertical dentro de la celda inferior izquierda
    yc = (Q(245) + Q(293)) / 2
    for k, s in enumerate(("Propiedad Intelectual del", "Proyectista. Prohibida su",
                           "reproducción total o parcial sin", "autorización expresa de",
                           "acuerdo a la Ley 11.723.")):
        text(T, P(77), yc + (k - 2) * 1.24 - 0.05, s, 1.1, "middle")
    # centro: proyecto, denominación, tipo de plano
    tl(P(153), 19.65, "Proyecto:", 1.4)
    text(V, P(262), 19.65, "{proyecto}", val, key="proyecto")
    tl(P(153), 22.25, "Descripcion:", 1.4)
    text(V, P(262), 22.25, "{descripcion}", val, key="descripcion")
    tl(P(153), 24.85, "Ubicacion:", 1.4)
    text(V, P(262), 24.85, "{ubicacion}", val, key="ubicacion")
    text(R, P(416), Q(205), "{denominacion}", 3.6, "middle", key="denominacion")
    text(V, P(416), Q(224), "{denominacion_2}", 2.2, "middle", key="denominacion_2")
    text(V, P(416), Q(275), "{tipo_plano}", 2.6, "middle", key="tipo_plano")
    # derecha: códigos
    tl(P(690), 19.6, "Codigo del Cliente (Reemplaza a):", 1.4)
    text(V, (P(690) + P(994)) / 2, 23.6, "{reemplaza}", val, "middle", key="reemplaza")
    tl(P(690), 28.2, "Codigo del Cliente (Reemplazado por):", 1.4)
    text(V, (P(690) + P(994)) / 2, 32.1, "{reemplazado_por}", val, "middle", key="reemplazado_por")
    tl(P(690), 37.0, "Codigo Interno:", 1.4)
    text(V, (P(690) + P(994)) / 2, 40.8, "{plano_n}", val, "middle", key="plano_n")
    # inferior derecha: hoja / página / estado / revisión
    for xc, lbl, kk in ((722, "HOJA", "formato"), (800, "PAGINA", "pagina"),
                        (877, "ESTADO", "estado"), (955, "REVISION", "revision")):
        tl(P(xc), 45.5, lbl, 1.4, "middle")
        text(V, P(xc), 49.4, "{%s}" % kk, val, "middle", key=kk)

def dibujar_modificaciones(G):
    """Fig. 3: franja de 21,5 x 175 apoyada sobre el rótulo. (12) 120 de ancho
    para la lista de modificaciones "en la forma más conveniente"; (13) 55 para
    la clave o número propio cuando en (9) va el número del cliente."""
    L, V = G, G + "_var"
    line(L, 0, 0, RW, 0, W_04)
    line(L, 0, 0, 0, MH, W_08)
    line(L, RW, 0, RW, MH, W_08)
    line(L, 0, MH, RW, MH, W_08)   # coincide con el contorno superior del rótulo
    line(L, cx_[5], 0, cx_[5], MH, W_04)
    text(V, (cx_[5] + RW) / 2, 13, "{plano_propio}", 3.5, "middle", key="plano_propio")


if "--iram" in sys.argv:
    dibujar_rotulo("rotulo")
else:
    dibujar_final("rotulo")
BLOQUE_ROT = {k: grupos.pop(k, []) for k in ("rotulo", "rotulo_txt", "rotulo_var", "rotulo_rojo", "rotulo_logos")}
dibujar_modificaciones("modif")
BLOQUE_MOD = {k: grupos.pop(k) for k in ("modif", "modif_var")}

# ---------------- salida ----------------
estilos = {
    "corte": 'stroke="#000"',
    "recuadro": 'stroke="#000" stroke-linecap="square"',
    "coordenadas": 'stroke="#000" fill="#000"',
    "escala_comparacion": 'stroke="#000"',
    "orientacion": 'stroke="#000"',
    "rotulo": 'stroke="#000" stroke-linecap="square"',
    "rotulo_txt": 'fill="#000"',
    "rotulo_var": 'fill="#000"',
    "rotulo_rojo": 'fill="#e00000"',
    "rotulo_logos": "",
    "modif": 'stroke="#000" stroke-linecap="square"',
    "modif_var": 'fill="#000"',
}


def bloque(gid, partes, x, y, norma):
    out = [f'<g id="{gid}" transform="translate({x:g} {y:g})" data-norma="{norma}">']
    for name, items in partes.items():
        out.append(f'<g id="{gid}_{name}" {estilos[name]}>')
        out.extend(items)
        out.append('</g>')
    out.append('</g>')
    return out


def guardar_bloque(carpeta, nombre, gid, partes, w, h, norma, titulo):
    doc = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="-1 -1 {w + 2:g} {h + 2:g}" '
           f'data-norma="{norma}" data-insercion="esquina superior izquierda (0, 0)">',
           f'<title>{titulo}</title>', f'<g font-family="{FONT}">']
    doc += bloque(gid, partes, 0, 0, norma) + ['</g>', '</svg>']
    with open(os.path.join(carpeta, nombre), "w", encoding="utf-8") as f:
        f.write("\n".join(doc))


svg = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}" '
    f'data-format="{FMT}" data-norma="IRAM 4504 / IRAM 4508" '
    f'data-zona-util="{u0:g} {v0:g} {u1:g} {v1:g}" data-rotulo="{rx:g} {ry:g} {u1:g} {v1:g}" '
    f'data-modificaciones="{rx:g} {ry - MH:g} {u1:g} {ry:g}">',
    f'<title>Lamina {FMT} {W} x {H} IRAM 4504 / 4508</title>',
    f'<rect id="papel" x="0" y="0" width="{W}" height="{H}" fill="#fff"/>',
    f'<g font-family="{FONT}">',
]
for name, items in grupos.items():
    svg.append(f'<g id="{name}" {estilos[name]}>')
    svg.extend(items)
    svg.append('</g>')
svg += bloque("rotulo_IRAM4508", BLOQUE_ROT, rx, ry, "IRAM 4508 fig. 2")
if MOD:
    svg += bloque("modificaciones_IRAM4508", BLOQUE_MOD, rx, ry - MH, "IRAM 4508 fig. 3")
svg += ['<g id="dibujo"><!-- insertar el diagrama aqui, dentro de la zona util y fuera del rotulo --></g>',
        '</g>', '</svg>']

dst = os.path.abspath(ARGS[1] if len(ARGS) > 1 else f"sheet-IRAM-{FMT}{'-mod' if MOD else ''}.svg")
with open(dst, "w", encoding="utf-8") as f:
    f.write("\n".join(svg))
guardar_bloque(os.path.dirname(dst), "title-block-IRAM4508.svg", "rotulo_IRAM4508", BLOQUE_ROT, RW, RH,
               "IRAM 4508 fig. 2", "Rotulo IRAM 4508 fig. 2 (175 x 51)")
guardar_bloque(os.path.dirname(dst), "modifications-block-IRAM4508.svg", "modificaciones_IRAM4508", BLOQUE_MOD, RW, MH,
               "IRAM 4508 fig. 3", "Lista de modificaciones IRAM 4508 fig. 3 (175 x 21,5)")
print(dst, f"zona util {u0}..{u1} x {v0}..{v1}; rotulo x {rx}..{u1}, y {ry}..{v1}; modificaciones y {ry - MH}..{ry}")
