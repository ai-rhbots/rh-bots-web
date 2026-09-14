# -*- coding: utf-8 -*-
"""
Comprueba si una contraseña coincide con la guardada, sin arriesgar nada:
la escribes aquí, en tu propia terminal, y no se muestra ni se envía a
ningún sitio. Sólo compara localmente contra datos/admin.json.

    python tools/verificar_clave.py
"""
import getpass
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ARCHIVO = os.path.join(ROOT, 'datos', 'admin.json')
sys.path.insert(0, HERE)

from werkzeug.security import check_password_hash  # noqa: E402

if not os.path.exists(ARCHIVO):
    print('No hay ninguna contraseña guardada todavía (datos/admin.json no existe).')
    sys.exit(1)

with io.open(ARCHIVO, encoding='utf-8') as f:
    h = json.load(f).get('hash')

print(f'Hash guardado el: {__import__("time").strftime("%d/%m/%Y %H:%M", __import__("time").localtime(os.path.getmtime(ARCHIVO)))}')
clave = getpass.getpass('Escribe la contraseña a comprobar (no se mostrará): ')

if check_password_hash(h, clave):
    print('\nCOINCIDE. El usuario es «admin» y esa es la contraseña correcta.')
else:
    print('\nNO COINCIDE con lo guardado.')
    print('Prueba con cuidado: revisa mayúsculas/minúsculas, el teclado, y que')
    print('el navegador no esté autorrellenando una contraseña antigua guardada.')
