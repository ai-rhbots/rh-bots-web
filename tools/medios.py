# -*- coding: utf-8 -*-
"""
Biblioteca de imágenes del panel: subida, validación y optimización.

Las imágenes subidas van a web/assets/medios/ y se optimizan al vuelo
(redimensionado + WebP), igual que hace tools/optimizar.py con los originales
de producto. Una foto de móvil de 6 MB acaba pesando unos 100 KB.

── Sobre la validación ──────────────────────────────────────────────────────
No basta con mirar la extensión: cualquiera puede llamar «foto.jpg» a un
script. Aquí se abre el archivo con Pillow y se verifica que sea una imagen
de verdad antes de guardar nada, y el nombre se reescribe desde cero para que
no pueda contener rutas («../../algo») ni caracteres raros.
"""
import io
import os
import re
import time
import unicodedata

from PIL import Image

Image.MAX_IMAGE_PIXELS = 80_000_000        # frena las «bombas de descompresión»

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DESTINO = os.path.join(ROOT, 'web', 'assets', 'medios')
RUTA_WEB = 'assets/medios'

EXTENSIONES = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif'}
FORMATOS_OK = {'JPEG', 'PNG', 'WEBP', 'GIF', 'AVIF', 'MPO'}

ANCHO_MAX = 1600
CALIDAD = 82
TAM_MAX = 25 * 1024 * 1024                 # 25 MB por archivo


class ErrorMedio(Exception):
    """Problema al procesar una imagen; el mensaje se le muestra al usuario."""


def nombre_seguro(nombre):
    """Reescribe el nombre desde cero: sin rutas, sin acentos, sin sorpresas."""
    base = os.path.basename(nombre or '')
    base = os.path.splitext(base)[0]
    base = unicodedata.normalize('NFKD', base).encode('ascii', 'ignore').decode()
    base = re.sub(r'[^a-zA-Z0-9]+', '-', base).strip('-').lower()
    return (base or 'imagen')[:60]


def _ruta_dentro(ruta):
    """Confirma que la ruta final cae dentro de la carpeta de medios."""
    destino = os.path.realpath(DESTINO)
    final = os.path.realpath(ruta)
    return final == destino or final.startswith(destino + os.sep)


def guardar(stream, nombre_original):
    """Valida, optimiza y guarda. Devuelve la ruta relativa para la web."""
    datos = stream.read(TAM_MAX + 1)
    if len(datos) > TAM_MAX:
        raise ErrorMedio(f'La imagen pasa de {TAM_MAX // 1024 // 1024} MB.')
    if not datos:
        raise ErrorMedio('El archivo llegó vacío.')

    ext = os.path.splitext(nombre_original or '')[1].lower()
    if ext not in EXTENSIONES:
        raise ErrorMedio(f'Formato no admitido ({ext or "sin extensión"}). '
                         f'Usa JPG, PNG, WebP, GIF o AVIF.')

    # ¿es de verdad una imagen? verify() sólo lee las cabeceras
    try:
        Image.open(io.BytesIO(datos)).verify()
    except Exception:
        raise ErrorMedio('El archivo no es una imagen válida.')

    # verify() deja el objeto inservible, así que se vuelve a abrir para trabajar
    im = Image.open(io.BytesIO(datos))
    if (im.format or '').upper() not in FORMATOS_OK:
        raise ErrorMedio(f'Formato interno no admitido ({im.format}).')

    animado = getattr(im, 'n_frames', 1) > 1
    os.makedirs(DESTINO, exist_ok=True)

    raiz = nombre_seguro(nombre_original)
    marca = time.strftime('%Y%m%d-%H%M%S')

    if animado:
        # un GIF animado se guarda tal cual: reescribirlo rompería la animación
        salida = os.path.join(DESTINO, f'{raiz}-{marca}{ext}')
        if not _ruta_dentro(salida):
            raise ErrorMedio('Ruta de destino no válida.')
        with io.open(salida, 'wb') as f:
            f.write(datos)
        return f'{RUTA_WEB}/{os.path.basename(salida)}', len(datos)

    # transparencia: se conserva; el resto pasa a RGB
    im = im.convert('RGBA' if im.mode in ('RGBA', 'LA', 'P') else 'RGB')
    if im.width > ANCHO_MAX:
        alto = round(im.height * ANCHO_MAX / im.width)
        im = im.resize((ANCHO_MAX, alto), Image.LANCZOS)

    salida = os.path.join(DESTINO, f'{raiz}-{marca}.webp')
    if not _ruta_dentro(salida):
        raise ErrorMedio('Ruta de destino no válida.')
    im.save(salida, 'WEBP', quality=CALIDAD, method=6)

    return f'{RUTA_WEB}/{os.path.basename(salida)}', os.path.getsize(salida)


def listar():
    """Las imágenes de la biblioteca, de más reciente a más antigua."""
    if not os.path.isdir(DESTINO):
        return []
    out = []
    for n in os.listdir(DESTINO):
        if os.path.splitext(n)[1].lower() not in EXTENSIONES:
            continue
        completo = os.path.join(DESTINO, n)
        try:
            with Image.open(completo) as im:
                medidas = f'{im.width}×{im.height}'
        except Exception:
            medidas = '?'
        out.append({
            'nombre': n,
            'url': f'{RUTA_WEB}/{n}',
            'kb': round(os.path.getsize(completo) / 1024),
            'medidas': medidas,
            'ts': os.path.getmtime(completo),
        })
    return sorted(out, key=lambda x: -x['ts'])


def borrar(nombre):
    """Borra una imagen de la biblioteca. Sólo acepta nombres, no rutas."""
    if not nombre or '/' in nombre or '\\' in nombre or nombre.startswith('.'):
        raise ErrorMedio('Nombre no válido.')
    ruta = os.path.join(DESTINO, nombre)
    if not _ruta_dentro(ruta) or not os.path.isfile(ruta):
        raise ErrorMedio('Esa imagen no existe.')
    os.remove(ruta)
