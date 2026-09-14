# -*- coding: utf-8 -*-
"""
Prepara el paquete que se sube al hosting.

    python tools/empaquetar.py

Genera `publicar/rh-bots-web.zip` con exactamente los archivos que la web
referencia, y nada más. Los originales de imagen y vídeo (1,4 GB) se quedan
fuera automáticamente: no se incluyen por estar en assets/, sino por aparecer
en algún href/src/poster del HTML, el CSS o el JS.
"""
import io
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WEB = os.path.join(ROOT, 'web')
SALIDA = os.path.join(ROOT, 'publicar')

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# se suben siempre, los referencie o no algún archivo
SIEMPRE = ('sitemap.xml', 'robots.txt', 'favicon.ico', '.htaccess')

PATRON = re.compile(r'(?:href|src|poster)\s*=\s*["\']([^"\'#?]+)', re.I)
PATRON_CSS = re.compile(r'url\(\s*["\']?([^"\')]+)', re.I)


def referencias():
    """Todo lo que el sitio pide de verdad, resuelto a rutas relativas a web/."""
    vistos = set()
    for base, _, archivos in os.walk(WEB):
        for a in archivos:
            if not a.endswith(('.html', '.css', '.js')):
                continue
            ruta = os.path.join(base, a)
            vistos.add(os.path.relpath(ruta, WEB).replace('\\', '/'))
            texto = io.open(ruta, encoding='utf-8', errors='ignore').read()

            encontrados = PATRON.findall(texto) + PATRON_CSS.findall(texto)
            for r in encontrados:
                if r.startswith(('http', 'mailto:', 'tel:', 'data:', '//')):
                    continue
                destino = os.path.normpath(os.path.join(base, r))
                if not os.path.isfile(destino):
                    continue
                rel = os.path.relpath(destino, WEB).replace('\\', '/')
                if not rel.startswith('..'):
                    vistos.add(rel)

    for s in SIEMPRE:
        if os.path.isfile(os.path.join(WEB, s)):
            vistos.add(s)
    return sorted(vistos)


def main():
    archivos = referencias()
    os.makedirs(SALIDA, exist_ok=True)

    # El gestor de archivos de cPanel suele atragantarse con subidas grandes,
    # así que además del paquete completo se dejan dos partes: el sitio (unos
    # pocos MB, se sube en segundos) y el vídeo aparte.
    videos = [f for f in archivos if f.lower().endswith('.mp4')]
    sitio = [f for f in archivos if f not in videos]

    def escribir(nombre, lista):
        ruta = os.path.join(SALIDA, nombre)
        with zipfile.ZipFile(ruta, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for rel in lista:
                z.write(os.path.join(WEB, rel), rel)
        return ruta

    escribir('rh-bots-sitio.zip', sitio)
    escribir('rh-bots-video.zip', videos)
    zip_ruta = escribir('rh-bots-web.zip', archivos)
    total = sum(os.path.getsize(os.path.join(WEB, f)) for f in archivos)

    print('Paquetes en publicar/:')
    for n, lista in (('rh-bots-sitio.zip', sitio), ('rh-bots-video.zip', videos),
                     ('rh-bots-web.zip', archivos)):
        p = os.path.join(SALIDA, n)
        print(f'  {n:22} {len(lista):>3} archivos  {os.path.getsize(p)/1e6:>7,.1f} MB')
    print()

    # qué se ha quedado fuera, para que no haya sorpresas
    todos = set()
    for base, _, fs in os.walk(WEB):
        for a in fs:
            todos.add(os.path.relpath(os.path.join(base, a), WEB).replace('\\', '/'))
    fuera = sorted(todos - set(archivos))
    peso_fuera = sum(os.path.getsize(os.path.join(WEB, f)) for f in fuera)


    por_tipo = {}
    for f in archivos:
        ext = os.path.splitext(f)[1].lower() or '(sin extensión)'
        por_tipo[ext] = por_tipo.get(ext, 0) + os.path.getsize(os.path.join(WEB, f))
    for ext, b in sorted(por_tipo.items(), key=lambda x: -x[1]):
        print(f'    {ext:8} {b/1e6:>8,.1f} MB')

    print(f'\n  Fuera del paquete: {len(fuera)} archivos · {peso_fuera/1e6:,.0f} MB '
          f'(originales de imagen y vídeo)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
