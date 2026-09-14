# -*- coding: utf-8 -*-
"""
Saneado del HTML que escribe el editor de artículos.

El cuerpo de un artículo llega como HTML desde el navegador y acaba escrito
tal cual en una página publicada. Sin filtrar, cualquier cosa pegada desde
otra web —un <script>, un onclick, un iframe— quedaría incrustada en el sitio.

Aquí se aplica una lista blanca: sólo pasan las etiquetas y atributos que el
editor puede generar. Todo lo demás se descarta.
"""
import html
import re
from html.parser import HTMLParser

# lo único que el editor produce
ETIQUETAS = {
    'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's',
    'h2', 'h3', 'h4', 'ul', 'ol', 'li',
    'blockquote', 'a', 'img', 'figure', 'figcaption', 'hr', 'code', 'pre',
}
VACIAS = {'br', 'img', 'hr'}

ATRIBUTOS = {
    'a': {'href', 'title', 'target', 'rel'},
    'img': {'src', 'alt', 'width', 'height', 'loading'},
}

# nada de javascript: ni data: en enlaces e imágenes
ESQUEMA_MALO = re.compile(r'^\s*(javascript|vbscript|data)\s*:', re.I)


class Limpiador(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes = []
        self.pila = []

    # --- atributos ---
    def _filtrar(self, etiqueta, attrs):
        permitidos = ATRIBUTOS.get(etiqueta, set())
        out = []
        for k, v in attrs:
            k = (k or '').lower()
            if k not in permitidos:
                continue                       # fuera on*, style, class, id…
            v = v or ''
            if k in ('href', 'src') and ESQUEMA_MALO.match(v):
                continue                       # javascript:… y compañía
            out.append((k, v))

        if etiqueta == 'a':
            claves = dict(out)
            # los enlaces que abren en pestaña nueva necesitan noopener
            if claves.get('target') == '_blank':
                out = [(k, v) for k, v in out if k != 'rel']
                out.append(('rel', 'noopener noreferrer'))
        if etiqueta == 'img':
            claves = dict(out)
            if 'loading' not in claves:
                out.append(('loading', 'lazy'))
            if 'alt' not in claves:
                out.append(('alt', ''))
        return out

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag not in ETIQUETAS:
            return
        pares = self._filtrar(tag, attrs)
        texto = ''.join(f' {k}="{html.escape(v, quote=True)}"' for k, v in pares)
        if tag in VACIAS:
            self.partes.append(f'<{tag}{texto}>')
        else:
            self.partes.append(f'<{tag}{texto}>')
            self.pila.append(tag)

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if tag not in ETIQUETAS:
            return
        pares = self._filtrar(tag, attrs)
        texto = ''.join(f' {k}="{html.escape(v, quote=True)}"' for k, v in pares)
        self.partes.append(f'<{tag}{texto}>')

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag not in ETIQUETAS or tag in VACIAS:
            return
        # cierra sólo lo que esté realmente abierto
        if tag in self.pila:
            while self.pila:
                abierta = self.pila.pop()
                self.partes.append(f'</{abierta}>')
                if abierta == tag:
                    break

    def handle_data(self, data):
        self.partes.append(html.escape(data, quote=False))

    def resultado(self):
        while self.pila:                        # cierra lo que quedara abierto
            self.partes.append(f'</{self.pila.pop()}>')
        return ''.join(self.partes)


def limpiar(bruto):
    """HTML del editor → HTML seguro para publicar."""
    if not bruto:
        return ''
    # los bloques peligrosos se quitan enteros, con su contenido
    bruto = re.sub(r'<(script|style|iframe|object|embed|form|svg)[^>]*>.*?</\1\s*>',
                   '', bruto, flags=re.I | re.S)
    bruto = re.sub(r'<!--.*?-->', '', bruto, flags=re.S)

    p = Limpiador()
    p.feed(bruto)
    p.close()
    salida = p.resultado()

    salida = re.sub(r'(<p>(\s|&nbsp;|<br>)*</p>)+', '', salida)   # párrafos vacíos
    return salida.strip()


def resumir(html_limpio, limite=200):
    """Saca un resumen en texto plano del cuerpo, para las tarjetas del blog."""
    texto = re.sub(r'<[^>]+>', ' ', html_limpio or '')
    texto = html.unescape(texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    if len(texto) <= limite:
        return texto
    corte = texto[:limite].rsplit(' ', 1)[0]
    return corte + '…'
