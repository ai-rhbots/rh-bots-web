# -*- coding: utf-8 -*-
"""
Optimizador de vídeo.

    python tools/optimizar_video.py

Lee los originales de web/assets/ (hasta 4K y casi 1 GB) y escribe versiones
web en web/assets/video/: H.264 a 1080p como mucho, con `faststart` para que
empiecen a reproducirse sin descargar el archivo entero, más un fotograma de
portada en JPEG para el `poster`.

Los originales NO deben subirse al servidor.
"""
import os
import subprocess
import sys

import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'web', 'assets')
DST = os.path.join(SRC, 'video')

FF = imageio_ffmpeg.get_ffmpeg_exe()

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


# (destino, origen, alto máximo, crf, segundo del que sacar la portada)
TRABAJOS = [
    ('a3-ultra-1',   '2026.03.3001.mp4',          1080, 24, 1.0),
    ('a3-ultra-2',   '2026.03.3002.mp4',           720, 24, 2.0),
    # Los dos largos van a 720p y con más compresión: son de 3 y 6 minutos, y
    # a 1080p se iban a 56 y 113 MB. Nadie debería gastar eso en datos móviles.
    ('x2',           'AGIBOT X2.MP4',              720, 31, 6.0),
    ('gama',         'AgiBot All Products.mp4',    720, 31, 8.0),
]


# ── bucles de fondo ───────────────────────────────────────────────────────
# (destino, origen, segundo inicial, duración, ancho)
#
# El desenfoque se aplica AQUÍ, no con CSS. Dos motivos:
#   · un `filter: blur()` sobre un vídeo en marcha se recalcula en cada
#     fotograma y funde la batería del móvil;
#   · desenfocado el vídeo pierde casi todo el detalle, así que comprime
#     muchísimo mejor: pasan de decenas de MB a unos cientos de KB.
# Los segundos de inicio no están elegidos a ojo: se muestreó cada vídeo cada
# 15 s midiendo el color medio, y se quedaron los tramos neutros y azulados.
# Los que salían verdes (exteriores con césped) chocaban con la paleta.
FONDOS = [
    ('fondo-gama', 'AgiBot All Products.mp4', 145, 12, 720),
    ('fondo-x2',   'AGIBOT X2.MP4',           100, 12, 720),
    ('fondo-a3',   '2026.03.3002.mp4',          2, 11, 720),
]


def procesar_fondo(destino, origen, desde, dur, ancho):
    ruta = os.path.join(SRC, origen)
    if not os.path.exists(ruta):
        print(f'  FALTA  {origen}')
        return 0, 0

    os.makedirs(DST, exist_ok=True)
    salida = os.path.join(DST, destino + '.mp4')
    portada = os.path.join(DST, destino + '.jpg')

    antes = os.path.getsize(ruta)
    ok = ejecutar([
        '-ss', str(desde), '-t', str(dur), '-i', ruta,
        '-vf', f'scale={ancho}:-2,boxblur=luma_radius=18:luma_power=2,'
               f'eq=brightness=-0.04:saturation=1.05',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '34',
        '-profile:v', 'main', '-pix_fmt', 'yuv420p',
        '-an',                       # sin audio: es decoración, no contenido
        '-movflags', '+faststart',
        salida,
    ])
    if not ok:
        return antes, 0

    ejecutar(['-ss', '1', '-i', salida, '-frames:v', '1', '-q:v', '6', portada])

    ahora = os.path.getsize(salida)
    pj = os.path.getsize(portada) if os.path.exists(portada) else 0
    print(f'  {destino:14} {dur}s desenfocado  →  {ahora/1024:>5,.0f} KB'
          f'   portada {pj/1024:>3,.0f} KB')
    return antes, ahora + pj


def ejecutar(args):
    r = subprocess.run([FF, '-y', '-hide_banner', '-loglevel', 'error'] + args,
                       capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if r.returncode != 0:
        print('    ffmpeg:', (r.stderr or '').strip()[:300])
    return r.returncode == 0


def procesar(destino, origen, alto, crf, seg_portada):
    ruta = os.path.join(SRC, origen)
    if not os.path.exists(ruta):
        print(f'  FALTA  {origen}')
        return 0, 0

    os.makedirs(DST, exist_ok=True)
    salida = os.path.join(DST, destino + '.mp4')
    portada = os.path.join(DST, destino + '.jpg')

    antes = os.path.getsize(ruta)
    print(f'  {destino:14} comprimiendo… ({antes/1e6:,.0f} MB)')

    ok = ejecutar([
        '-i', ruta,
        # escala a la altura pedida sólo si el original es mayor; ancho par
        '-vf', f'scale=-2:{alto}:force_original_aspect_ratio=decrease:'
               f'force_divisible_by=2',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', str(crf),
        '-profile:v', 'high', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '128k', '-ac', '2',
        '-movflags', '+faststart',
        salida,
    ])
    if not ok:
        return antes, 0

    ejecutar(['-ss', str(seg_portada), '-i', salida, '-frames:v', '1',
              '-q:v', '4', portada])

    ahora = os.path.getsize(salida)
    pj = os.path.getsize(portada) if os.path.exists(portada) else 0
    print(f'  {destino:14} {antes/1e6:>7,.0f} MB → {ahora/1e6:>6,.1f} MB'
          f'   portada {pj/1024:>4,.0f} KB')
    return antes, ahora + pj


def main():
    filtro = sys.argv[1] if len(sys.argv) > 1 else ''
    print('Optimizando vídeo…' + (f'  (sólo «{filtro}»)' if filtro else ''))
    ta = tb = 0
    for destino, origen, alto, crf, seg in TRABAJOS:
        if filtro and filtro not in destino:
            continue
        a, b = procesar(destino, origen, alto, crf, seg)
        ta += a
        tb += b

    for destino, origen, desde, dur, ancho in FONDOS:
        if filtro and filtro not in destino:
            continue
        a, b = procesar_fondo(destino, origen, desde, dur, ancho)
        tb += b
    if tb:
        print(f'\nTotal: {ta/1e6:,.0f} MB → {tb/1e6:,.1f} MB '
              f'({ta/max(tb,1):.0f}× más ligero)')
    print('Publicar sólo web/assets/video/ — los originales se quedan fuera.')


if __name__ == '__main__':
    main()
