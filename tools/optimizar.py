# -*- coding: utf-8 -*-
"""
Optimizador de imágenes de producto.

    python tools/optimizar.py

Lee los originales de web/assets/productos/<MODELO>/ (PNG de 4–20 MB) y escribe
versiones web en web/assets/robots/<slug>/ (WebP con transparencia, ~40–150 KB).

Los originales NO deben subirse al servidor: sólo se publica web/assets/robots/.
"""
import io, os, sys

from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None

# la consola de Windows usa cp1252 por defecto y rompe con «→» / «×»
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC  = os.path.join(ROOT, 'web', 'assets')
DST  = os.path.join(ROOT, 'web', 'assets', 'robots')

ANCHO_VISTA   = 900    # fotogramas del visualizador
ANCHO_HERO    = 1300   # imagen principal de ficha
ANCHO_GALERIA = 900
CALIDAD       = 82


# ── secuencias de giro ────────────────────────────────────────────────────
# Todos los fotogramas de una secuencia comparten encuadre: se recortan con el
# mismo rectángulo (unión de sus siluetas) para que el objeto no cambie de
# tamaño ni salte de sitio al girar.
SECUENCIAS = [
    ('rhc5/vista', [
        'productos/C5/C5_Frontal.png',               # 0 · frontal
        'productos/C5/C5_Perpendicular.png',         # 1 · 3/4 delantera
        'productos/C5/C5_Perfil_Izq.png',            # 2 · perfil
        'productos/C5/C5_Perpendicular_Trasera.png',  # 3 · 3/4 trasera
        'productos/C5/C5_Trasera.png',               # 4 · trasera
        'productos/C5/C5_Perfil_Der.png',            # 5 · perfil opuesto
    ], ANCHO_VISTA),
]


# ── trabajos sueltos ──────────────────────────────────────────────────────
# (destino, origen, ancho)
TRABAJOS = [
    # galería RHC5
    ('rhc5/robot-estacion',   'productos/C5/C5_Robot_Estación.png',      ANCHO_GALERIA),
    ('rhc5/estacion-frontal', 'productos/C5/Estación_Frontal.png',       ANCHO_GALERIA),
    ('rhc5/estacion-perfil',  'productos/C5/Estación_Perfil_Der.png',    ANCHO_GALERIA),
    ('rhc5/estacion-perp',    'productos/C5/Estación_Perpendicular.png', ANCHO_GALERIA),

    # ─── RHG2 ───
    ('rhg2/hero',             'productos/G2/G2_Frontal.png',         ANCHO_HERO),
    ('rhg2/perfil',           'productos/G2/G2_Perfil.png',          ANCHO_GALERIA),
    ('rhg2/saludando',        'productos/G2/G2_Saludando.png',       ANCHO_GALERIA),
    ('rhg2/display-frontal',  'productos/G2/G2_Display_Frontal.png', ANCHO_GALERIA),
    ('rhg2/display',          'productos/G2/G2_Display.png',         ANCHO_GALERIA),

    # ─── familia X2: una imagen distinta por modelo ───
    # (rhx2 y rhx2-ultra ya usan robot-sentado.png y robot-frontal.png)
    ('rhx2-edu/hero',         'bcdaf302f10439090f551e9906ef7285.png', 460),

    # ─── accesorios / varios ───
    ('accesorios/mano',       'ea340bb6b53603126a1bc9f845073742.png', 700),
    ('accesorios/vr',         'VR.png',                               800),

    # ─── gama completa, para la home ───
    ('gama',                  'Gama RH.png',                         1600),
]

# A3: hay un único render, así que cada modelo usa un encuadre distinto.
A3 = ('rha3/hero', 'A3-fondo.png', ANCHO_HERO)
A3_ULTRA = ('rha3-ultra/hero', 'A3-fondo.png', ANCHO_HERO)



def caja_util(im, umbral=30):
    """Recuadro del contenido con cuerpo, ignorando halos y humo casi invisibles.

    getbbox() cuenta cualquier píxel con alfa > 0, así que un resto de humo a
    dos pantallas de distancia mantiene el lienzo enorme y deja el producto
    diminuto. Aquí sólo cuenta lo que se ve de verdad.
    """
    mascara = im.getchannel('A').point(lambda a: 255 if a > umbral else 0)
    return mascara.getbbox() or im.getbbox()


def recortar_alpha(im, margen=0.015):
    """Elimina el margen transparente sobrante y deja un pequeño aire."""
    if im.mode != 'RGBA':
        return im
    bb = caja_util(im)
    if not bb:
        return im
    im = im.crop(bb)
    m = int(max(im.size) * margen)
    if m:
        lienzo = Image.new('RGBA', (im.width + 2 * m, im.height + 2 * m), (0, 0, 0, 0))
        lienzo.paste(im, (m, m))
        im = lienzo
    return im


def limpiar_caligrafia(im):
    """Borra el texto decorativo del render del A3.

    El fondo del original ya es transparente y la caligrafía es opaca, así que
    basta con vaciar esa esquina: no queda costura. La zona está a la derecha
    del robot, no lo toca.
    """
    w, h = im.size
    im.paste((0, 0, 0, 0), (int(w * .33), 0, w, int(h * .22)))   # caligrafía
    # el resto del lienzo son volutas de humo decorativas: se recorta al robot
    return im.crop((0, 0, int(w * .72), h))


def preparar_a3_ultra(im):
    """Mismo render del A3 con un encuadre más cerrado, para diferenciar la
    ficha del Ultra de la del modelo base."""
    im = limpiar_caligrafia(im)
    w, h = im.size
    return im.crop((int(w * .04), 0, w, int(h * .62)))


def procesar(destino, origen, ancho, pre=None):
    ruta = os.path.join(SRC, origen)
    if not os.path.exists(ruta):
        print(f'  FALTA  {origen}')
        return None

    im = Image.open(ruta).convert('RGBA')
    if pre:
        im = pre(im)
    im = recortar_alpha(im)

    if im.width > ancho:
        alto = round(im.height * ancho / im.width)
        im = im.resize((ancho, alto), Image.LANCZOS)

    salida = os.path.join(DST, destino + '.webp')
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    im.save(salida, 'WEBP', quality=CALIDAD, method=6)

    antes = os.path.getsize(ruta)
    ahora = os.path.getsize(salida)
    print(f'  {destino:34} {im.size[0]:>5}×{im.size[1]:<5} '
          f'{antes/1e6:>6.1f} MB → {ahora/1024:>6.0f} KB')
    return antes, ahora


def procesar_secuencia(prefijo, origenes, ancho):
    """Recorta todos los fotogramas con el mismo rectángulo (unión de siluetas)."""
    rutas = [os.path.join(SRC, o) for o in origenes]
    faltan = [o for o, r in zip(origenes, rutas) if not os.path.exists(r)]
    if faltan:
        for o in faltan:
            print(f'  FALTA  {o}')
        return 0, 0

    imgs = [Image.open(r).convert('RGBA') for r in rutas]

    # unión de las siluetas → encuadre común
    cajas = [im.getbbox() for im in imgs]
    x0 = min(c[0] for c in cajas); y0 = min(c[1] for c in cajas)
    x1 = max(c[2] for c in cajas); y1 = max(c[3] for c in cajas)
    m = int(max(x1 - x0, y1 - y0) * .02)
    caja = (max(0, x0 - m), max(0, y0 - m),
            min(imgs[0].width, x1 + m), min(imgs[0].height, y1 + m))

    antes = ahora = 0
    for i, (im, ruta) in enumerate(zip(imgs, rutas)):
        im = im.crop(caja)
        if im.width > ancho:
            im = im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)
        salida = os.path.join(DST, f'{prefijo}-{i}.webp')
        os.makedirs(os.path.dirname(salida), exist_ok=True)
        im.save(salida, 'WEBP', quality=CALIDAD, method=6)
        antes += os.path.getsize(ruta)
        ahora += os.path.getsize(salida)
        print(f'  {prefijo}-{i:<28} {im.size[0]:>5}×{im.size[1]:<5} '
              f'{os.path.getsize(ruta)/1e6:>6.1f} MB → {os.path.getsize(salida)/1024:>6.0f} KB')
    print(f'  └─ encuadre común {caja[2]-caja[0]}×{caja[3]-caja[1]} px para {len(imgs)} vistas')
    return antes, ahora


def main():
    filtro = sys.argv[1] if len(sys.argv) > 1 else ''
    def toca(nombre):
        return not filtro or filtro in nombre

    print('Optimizando imágenes de producto…' + (f'  (sólo «{filtro}»)' if filtro else ''))
    total_antes = total_ahora = 0

    for prefijo, origenes, ancho in SECUENCIAS:
        if not toca(prefijo):
            continue
        a, b = procesar_secuencia(prefijo, origenes, ancho)
        total_antes += a
        total_ahora += b

    for destino, origen, ancho in TRABAJOS:
        if not toca(destino):
            continue
        r = procesar(destino, origen, ancho)
        if r:
            total_antes += r[0]
            total_ahora += r[1]

    for trabajo, prep in ((A3, limpiar_caligrafia), (A3_ULTRA, preparar_a3_ultra)):
        if not toca(trabajo[0]):
            continue
        r = procesar(trabajo[0], trabajo[1], trabajo[2], pre=prep)
        if r:
            total_antes += r[0]
            total_ahora += r[1]

    print(f'\nTotal: {total_antes/1e6:.1f} MB → {total_ahora/1024:.0f} KB '
          f'({total_antes/max(total_ahora,1):.0f}× más ligero)')
    print('Publicar sólo web/assets/robots/ — los originales se quedan fuera.')


if __name__ == '__main__':
    main()
