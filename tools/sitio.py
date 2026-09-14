# -*- coding: utf-8 -*-
"""
Contenido de nivel sitio: SEO, analítica, navegación, home, blog y contacto.

Vive en datos/sitio.json y se edita desde el panel (python tools/admin.py)
o a mano sobre el JSON. Los datos de producto están en productos.py.

Notas:
  · NAV — poner "oculto": true retira una entrada del menú sin borrarla.
  · ANALITICA — si los identificadores están vacíos no se inserta ninguna
    etiqueta de Google, así que en local no se envían datos.
"""
from datos import cargar

_d = cargar('sitio')

SEO       = _d['seo']
ANALITICA = _d['analitica']
NAV       = _d['nav']
HOME      = _d['home']
SERVICIOS = _d['servicios']
CONTACTO  = _d['contacto']
POSTS     = _d['posts']
TIENDA    = _d.get('tienda', {'activa': False})
RHBOTS    = _d.get('rhbots', {
    'kicker': '', 'h1': 'RH·BOTS', 'lede': '',
    'historia_subtitulo': '', 'historia_cuerpo': '',
    'cifras': [], 'equipo': [],
})
