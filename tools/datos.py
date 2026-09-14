# -*- coding: utf-8 -*-
"""
Acceso a los datos del sitio.

El contenido vive en JSON (datos/productos.json y datos/sitio.json) y no en
código: así el panel de administración puede leerlo y escribirlo sin tocar
ningún archivo .py.

    from datos import cargar, guardar
"""
import io
import json
import os
import shutil
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATOS = os.path.join(ROOT, 'datos')
COPIAS = os.path.join(DATOS, 'copias')

ARCHIVOS = {'productos': 'productos.json', 'sitio': 'sitio.json'}


def ruta(nombre):
    return os.path.join(DATOS, ARCHIVOS[nombre])


def cargar(nombre):
    with io.open(ruta(nombre), encoding='utf-8') as f:
        return json.load(f)


def guardar(nombre, dato):
    """Guarda con copia de seguridad previa y escritura atómica."""
    destino = ruta(nombre)

    if os.path.exists(destino):
        os.makedirs(COPIAS, exist_ok=True)
        marca = time.strftime('%Y%m%d-%H%M%S')
        shutil.copy2(destino, os.path.join(COPIAS, f'{nombre}-{marca}.json'))
        _podar_copias(nombre, conservar=30)

    tmp = destino + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(dato, f, ensure_ascii=False, indent=2)
    os.replace(tmp, destino)     # atómico: nunca deja el archivo a medias


def _podar_copias(nombre, conservar=30):
    if not os.path.isdir(COPIAS):
        return
    copias = sorted(x for x in os.listdir(COPIAS) if x.startswith(nombre + '-'))
    for vieja in copias[:-conservar]:
        try:
            os.remove(os.path.join(COPIAS, vieja))
        except OSError:
            pass
