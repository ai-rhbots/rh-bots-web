# -*- coding: utf-8 -*-
"""
Sincroniza precios y stock desde Shopify hacia los datos del sitio.

    python tools/sincronizar.py

La web ya consulta Shopify en vivo desde el navegador, así que el visitante
siempre ve el dato correcto. Esto actualiza además el estado que se escribe en
el HTML, que es lo que ve Google y lo que aparece durante el instante previo a
que responda Shopify.

Conviene ejecutarlo antes de publicar. No escribe nada en Shopify: sólo lee.
"""
import io
import json
import os
import sys
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import datos as D  # noqa: E402

TIEMPO = 15


_ULTIMOS_ERRORES = []


def traer(url):
    try:
        with urllib.request.urlopen(url, timeout=TIEMPO) as r:
            return json.load(r)
    except (urllib.error.URLError, ValueError, TimeoutError) as ex:
        print(f'  ! no se pudo leer {url}: {ex}')
        _ULTIMOS_ERRORES.append(str(ex))
        return None


def main():
    sitio = D.cargar('sitio')
    tienda = sitio.get('tienda') or {}
    dominio = (tienda.get('dominio') or '').strip('/')
    if not dominio:
        print('No hay dominio de tienda configurado.')
        return 1

    base = f'https://{dominio}'
    print(f'Leyendo {base} …')

    meta = traer(f'{base}/meta.json')
    moneda = (meta or {}).get('currency') or tienda.get('moneda', '')
    if meta and moneda != tienda.get('moneda'):
        print(f'  moneda: {tienda.get("moneda")} -> {moneda}')
        tienda['moneda'] = moneda
        D.guardar('sitio', sitio)

    prod = D.cargar('productos')
    cambios = 0
    leidos = 0
    fallos = []

    for p in prod['productos']:
        sh = p.get('shopify')
        if not sh or not sh.get('handle'):
            continue

        datos = traer(f'{base}/products/{sh["handle"]}.js')
        if not datos or not datos.get('variants'):
            fallos.append(p['name'])
            continue
        leidos += 1

        v = next((x for x in datos['variants']
                  if str(x['id']) == str(sh.get('variante'))), datos['variants'][0])

        nuevo_precio = f'{v["price"] / 100:.2f}'
        nueva_disp = bool(v['available'])
        antes = (sh.get('precio'), sh.get('disponible'), sh.get('moneda'))

        sh['precio'] = nuevo_precio
        sh['disponible'] = nueva_disp
        sh['moneda'] = moneda

        marca = ' '
        if antes != (nuevo_precio, nueva_disp, moneda):
            cambios += 1
            marca = '*'
        estado = 'disponible' if nueva_disp else 'sin stock'
        print(f'  {marca} {p["name"]:14} {nuevo_precio:>12} {moneda}  {estado}')

    if cambios:
        D.guardar('productos', prod)

    # No decir «todo al día» cuando en realidad no se pudo leer nada: Shopify
    # limita las peticiones (HTTP 429) y sin este aviso la sincronización
    # parecería correcta habiendo fallado entera.
    if fallos:
        print(f'\nNO se pudo leer {len(fallos)} de {len(fallos) + leidos}: '
              f'{", ".join(fallos)}')
        if 'Too Many Requests' in ''.join(_ULTIMOS_ERRORES):
            print('Shopify está limitando las peticiones. Espera un minuto y repite.')
        if cambios:
            print(f'Sí se guardaron {cambios} cambio(s) de los que sí respondieron.')
        print('Los datos NO están completos: vuelve a ejecutarlo antes de publicar.')
        return 1

    if cambios:
        print(f'\n{cambios} cambio(s) guardado(s). Ejecuta ahora:  python tools/build.py')
    else:
        print(f'\nTodo estaba al día ({leidos} producto(s) comprobado(s)).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
