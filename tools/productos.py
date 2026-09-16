# -*- coding: utf-8 -*-
"""
Catálogo RH·BOTS — datos de producto.

Fuente: fichas técnicas facilitadas por RH·BOTS (base AGIBOT).
Los nombres comerciales usan el prefijo RH (RHC5, RHX2…), tal y como aparecen
en el dossier RHC5_VF y en la maqueta web aprobada.

El contenido vive ahora en datos/productos.json. Se edita desde el panel
(python tools/admin.py) o a mano sobre el JSON; este módulo sólo lo carga.

Estados:
  disponible  → ficha completa y contrastada
  parcial     → producto anunciado, faltan datos oficiales
  provisional → sin ficha oficial; NO usar en oferta contractual
"""
from datos import cargar

_d = cargar('productos')

FAMILIAS  = _d['familias']
ESTADOS   = _d['estados']
PRODUCTOS = _d['productos']

BY_SLUG = {p['slug']: p for p in PRODUCTOS}
