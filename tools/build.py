# -*- coding: utf-8 -*-
"""
Generador del catálogo RH·BOTS.

    python tools/build.py

Lee tools/productos.py y escribe:
    web/robots.html            índice del catálogo
    web/robots/<slug>.html     una ficha por producto
"""
import io, os, re, sys, html, json, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WEB  = os.path.join(ROOT, 'web')
sys.path.insert(0, HERE)

from PIL import Image  # noqa: E402
from productos import PRODUCTOS, FAMILIAS, ESTADOS, GUIA, BY_SLUG  # noqa: E402
from sitio import (NAV, HOME, CONTACTO, POSTS, SEO, ANALITICA, CTA, PREFOOTER,  # noqa: E402
                   TIENDA, RHBOTS)
from limpiar_html import limpiar as limpiar_cuerpo  # noqa: E402

e = html.escape
FAM_NAME = {k: n for k, n, _ in FAMILIAS}
FECHA_BUILD = time.strftime('%Y-%m-%d')
LINKEDIN_EMPRESA = 'https://www.linkedin.com/company/rh-bots'
INSTAGRAM_EMPRESA = 'https://www.instagram.com/rhbots/'


# ─────────────────────────────────────────────────────────────── imágenes ──
_DIM_CACHE = {}


def dimensiones(ruta_relativa):
    """Ancho/alto reales de una imagen en web/, para evitar saltos de layout
    (CLS) y para que un crawler que no ejecuta CSS (muchos bots de IA) sepa
    la proporción de la imagen a partir del propio HTML."""
    if ruta_relativa in _DIM_CACHE:
        return _DIM_CACHE[ruta_relativa]
    ruta = os.path.join(WEB, ruta_relativa)
    try:
        with Image.open(ruta) as im:
            dims = im.size
    except (OSError, FileNotFoundError):
        dims = None
    _DIM_CACHE[ruta_relativa] = dims
    return dims


def img_dims_attr(ruta_relativa):
    dims = dimensiones(ruta_relativa)
    return f' width="{dims[0]}" height="{dims[1]}"' if dims else ''


# ───────────────────────────────────────────────────── datos estructurados ──
def jsonld(bloques):
    """Uno o varios dicts @type Schema.org → <script type="application/ld+json">."""
    if not bloques:
        return ''
    if isinstance(bloques, dict):
        bloques = [bloques]
    out = ''
    for b in bloques:
        if not b:
            continue
        out += ('<script type="application/ld+json">'
               + json.dumps(b, ensure_ascii=False, separators=(',', ':'))
               + '</script>\n')
    return out


def schema_organization():
    dominio = SEO['dominio'].rstrip('/')
    contacto_principal = CONTACTO['personas'][0] if CONTACTO.get('personas') else {}
    direccion = CONTACTO.get('direccion') or []
    localidad, region = 'Picassent', 'Valencia'
    cp = ''
    if direccion:
        m = re.search(r'(\d{5})\s+([^(]+)\(([^)]+)\)', direccion[-1])
        if m:
            cp, localidad, region = m.group(1), m.group(2).strip(), m.group(3).strip()
    data = {
        '@context': 'https://schema.org',
        '@type': ['Organization', 'LocalBusiness'],
        '@id': f'{dominio}/#organization',
        'name': 'RH·BOTS',
        'legalName': CONTACTO.get('empresa') or 'RH·BOTS',
        'url': dominio + '/',
        'logo': f'{dominio}/assets/logo-rhbots.png',
        'image': f'{dominio}/{SEO["og_imagen"]}',
        'description': ('Distribuidor oficial de AGIBOT en España y Portugal: robots de limpieza '
                        'autónoma, humanoides, cuadrúpedos, AMR de intralogística y accesorios, con asesoramiento, instalación, '
                        'formación y mantenimiento.'),
        'areaServed': ['ES', 'PT'],
        'address': {
            '@type': 'PostalAddress',
            'streetAddress': ', '.join(direccion[:-1]) if len(direccion) > 1 else (direccion[0] if direccion else ''),
            'addressLocality': localidad,
            'addressRegion': region,
            'postalCode': cp,
            'addressCountry': 'ES',
        },
    }
    if contacto_principal.get('tel'):
        data['telephone'] = contacto_principal['tel']
    if contacto_principal.get('email'):
        data['email'] = contacto_principal['email']
    sameas = [LINKEDIN_EMPRESA, INSTAGRAM_EMPRESA]
    data['sameAs'] = sameas
    return data


def schema_person(nombre, cargo, email=None):
    dominio = SEO['dominio'].rstrip('/')
    data = {
        '@context': 'https://schema.org',
        '@type': 'Person',
        'name': nombre,
        'jobTitle': cargo,
        'worksFor': {'@id': f'{dominio}/#organization'},
    }
    if email:
        data['email'] = email
    return data


def schema_faqpage(preguntas):
    if not preguntas:
        return None
    return {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        'mainEntity': [
            {'@type': 'Question', 'name': q,
             'acceptedAnswer': {'@type': 'Answer', 'text': a}}
            for q, a in preguntas
        ],
    }


def schema_breadcrumb(items):
    """items: lista de (nombre, url_absoluta_o_None). El último puede ir sin url."""
    return {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': i + 1, 'name': nombre,
             **({'item': url} if url else {})}
            for i, (nombre, url) in enumerate(items)
        ],
    }


def schema_product(p):
    dominio = SEO['dominio'].rstrip('/')
    url = f'{dominio}/robots/{p["slug"]}.html'
    data = {
        '@context': 'https://schema.org',
        '@type': 'Product',
        '@id': f'{url}#product',
        'name': p['name'],
        'description': p.get('tagline') or p.get('intro') or p['claim'],
        'url': url,
        'brand': {'@type': 'Brand', 'name': 'AGIBOT'},
        'category': FAM_NAME.get(p['family'], ''),
    }
    if p.get('hero'):
        data['image'] = f'{dominio}/{p["hero"]}'
    sh = p.get('shopify')
    if sh and sh.get('variante'):
        try:
            precio = float(sh.get('precio') or 0)
        except (TypeError, ValueError):
            precio = 0
        if sh.get('sku'):
            data['sku'] = sh['sku']
        if precio > 0 and TIENDA.get('activa') and TIENDA.get('mostrar_precio'):
            data['offers'] = {
                '@type': 'Offer',
                'url': url,
                'priceCurrency': sh.get('moneda') or 'EUR',
                'price': f'{precio:.2f}',
                'availability': ('https://schema.org/InStock' if sh.get('disponible')
                                 else 'https://schema.org/OutOfStock'),
                'seller': {'@id': f'{dominio}/#organization'},
            }
    return data


# ───────────────────────────────────────────────────────────── plantilla ──
def analitica():
    """Etiquetas de Google. Si no hay identificadores, no se emite nada."""
    out = ''
    if ANALITICA.get('google_site_verification'):
        out += (f'<meta name="google-site-verification" '
                f'content="{e(ANALITICA["google_site_verification"])}">\n')
    if ANALITICA.get('gtm'):
        g = ANALITICA['gtm']
        out += ("<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':"
                "new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],"
                "j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;"
                "j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;"
                f"f.parentNode.insertBefore(j,f);}})(window,document,'script','dataLayer','{g}');</script>\n")
    if ANALITICA.get('ga4'):
        g = ANALITICA['ga4']
        out += (f'<script async src="https://www.googletagmanager.com/gtag/js?id={g}"></script>\n'
                "<script>window.dataLayer=window.dataLayer||[];"
                "function gtag(){dataLayer.push(arguments);}gtag('js',new Date());"
                f"gtag('config','{g}');</script>\n")
    return out


def head(title, desc, base, ruta='', extra_css=True, og_img=None, extra_jsonld=None):
    dominio = SEO['dominio'].rstrip('/')
    canonical = f'{dominio}/{ruta}' if ruta and ruta != 'index.html' else dominio + '/'
    imagen = f'{dominio}/{og_img or SEO["og_imagen"]}'
    tw = (f'<meta name="twitter:site" content="{e(SEO["twitter"])}">\n'
          if SEO.get('twitter') else '')
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
<meta name="theme-color" content="#009ee3">
<meta name="robots" content="index, follow">

<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(SEO['nombre'])}">
<meta property="og:locale" content="{e(SEO['locale'])}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:image" content="{e(imagen)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{e(imagen)}">
{tw}{analitica()}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Exo:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@700&family=Saira:wght@600;700&display=swap" rel="stylesheet">
<script>document.documentElement.classList.add('js')</script>
<link rel="stylesheet" href="{base}css/styles.css">
{'<link rel="stylesheet" href="%scss/catalogo.css">' % base if extra_css else ''}
{jsonld(extra_jsonld)}</head>
<body>
<a class="skip-link" href="#contenido">Saltar al contenido</a>
'''


def header(base, active='robots'):
    parts = []
    for it in NAV:
        if it.get('oculto'):
            continue
        cls = ' class="is-active"' if it['key'] and it['key'] == active else ''
        parts.append('<a href="%s%s"%s>%s</a>' % (base, it['href'], cls, e(it['label'])))
    links = '\n      '.join(parts)
    return f'''
<header class="site-header" id="header">
  <div class="wrap header-inner">
    <a class="logo" href="{base}index.html" aria-label="RH·BOTS — inicio">
      <img src="{base}assets/logo-rhbots.png" alt="RH·BOTS" width="348" height="72">
    </a>
    <nav class="nav" id="nav" aria-label="Navegación principal">
      {links}
    </nav>
    <button class="nav-toggle" id="navToggle" aria-label="Abrir menú" aria-expanded="false" aria-controls="nav">
      <span></span><span></span><span></span>
    </button>
  </div>
</header>
'''


# iconos de marca en cuadrado índigo con el glifo en blanco (franja «Síguenos»)
ICONO_INSTAGRAM = (
    '<svg viewBox="0 0 48 48" aria-hidden="true">'
    '<rect width="48" height="48" rx="7" fill="#2f2483" stroke="none"/>'
    '<rect x="11" y="11" width="26" height="26" rx="7.5" fill="none" stroke="#fff" stroke-width="3.4"/>'
    '<circle cx="24" cy="24" r="6.3" fill="none" stroke="#fff" stroke-width="3.4"/>'
    '<circle cx="31.4" cy="16.6" r="2" fill="#fff" stroke="none"/></svg>')
ICONO_LINKEDIN = (
    '<svg viewBox="0 0 48 48" aria-hidden="true">'
    '<rect width="48" height="48" rx="7" fill="#2f2483" stroke="none"/>'
    '<circle cx="14.2" cy="13.8" r="3.4" fill="#fff" stroke="none"/>'
    '<rect x="11.3" y="19.4" width="5.8" height="18.1" fill="#fff" stroke="none"/>'
    '<path d="M21.2 19.4h5.5v2.5h.1c.8-1.4 2.7-2.9 5.5-2.9 5.8 0 6.9 3.8 6.9 8.8v9.7h-5.8v-8.6'
    'c0-2.1 0-4.7-2.9-4.7s-3.4 2.2-3.4 4.6v8.7h-5.8z" fill="#fff" stroke="none"/></svg>')


def prefooter(base):
    """Franja clara previa al pie: mensaje de contacto y logotipo vertical."""
    if not PREFOOTER.get('titulo') and not PREFOOTER.get('texto'):
        return ''
    return f'''
<aside class="prefoot" aria-label="{e(PREFOOTER.get('titulo', ''))}">
  <div class="prefoot__diagonal" aria-hidden="true"></div>
  <div class="wrap prefoot__grid">
    <div class="prefoot__texto">
      <p class="prefoot__titulo">{e(PREFOOTER.get('titulo', ''))}</p>
      <p>{e(PREFOOTER.get('texto', ''))}</p>
    </div>
    <a class="prefoot__logo" href="{base}index.html" aria-label="RH·BOTS — inicio">
      <img src="{base}assets/logo-rhbots-vertical.png" alt="RH·BOTS — Recursos Humanoides"
           width="560" height="452" loading="lazy">
    </a>
    <div class="prefoot__redes">
      <p class="prefoot__titulo">{e(PREFOOTER.get('siguenos', 'Síguenos'))}</p>
      <ul>
        <li><a href="{INSTAGRAM_EMPRESA}" target="_blank" rel="noopener" aria-label="Instagram de RH·BOTS">{ICONO_INSTAGRAM}</a></li>
        <li><a href="{LINKEDIN_EMPRESA}" target="_blank" rel="noopener" aria-label="LinkedIn de RH·BOTS">{ICONO_LINKEDIN}</a></li>
      </ul>
    </div>
  </div>
</aside>'''


def footer(base):
    return f'''{prefooter(base)}
<footer class="site-footer" id="contacto">
  <div class="wrap footer-inner">
    <p class="footer-marca">© {time.strftime('%Y')} RH-BOTS<br>Recursos Humanoides.</p>
    <p class="footer-legal">
      <a href="{base}legal.html">Aviso Legal</a> ·
      <a href="{base}legal.html#privacidad">Política de Privacidad</a> ·
      <a href="{base}legal.html#cookies">Política de Cookies</a>
    </p>
  </div>
</footer>
<script src="{base}js/main.js"></script>
</body>
</html>
'''


SILUETAS = {
    'limpieza': '<rect x="16" y="26" width="32" height="26" rx="6"/><path d="M16 46h32"/><circle cx="24" cy="55" r="3"/><circle cx="40" cy="55" r="3"/><path d="M22 20h20l-2 6H24z"/>',
    'humanoides': '<rect x="25" y="9" width="14" height="12" rx="6"/><path d="M32 21v18"/><path d="M32 24l-10 6M32 24l10 6"/><path d="M32 39l-6 16M32 39l6 16"/>',
    'cuadrupedos': '<rect x="16" y="24" width="32" height="14" rx="5"/><path d="M20 38l-4 16M28 38l-2 16M36 38l2 16M44 38l4 16"/><path d="M48 28h6"/>',
    'amr': '<rect x="12" y="22" width="40" height="18" rx="4"/><path d="M18 22v-6h28v6"/><circle cx="20" cy="46" r="4"/><circle cx="44" cy="46" r="4"/>',
    'accesorios': '<path d="M22 54V34l-6-8a3 3 0 015-3l5 6V12a3 3 0 016 0v14-18a3 3 0 016 0v18-14a3 3 0 016 0v16-10a3 3 0 016 0v20c0 10-6 18-16 18h-2c-3 0-6-1-8-4z"/>',
}


# rótulo de cada tarjeta de la home, en singular
ETIQUETA_FAMILIA = {
    'limpieza': 'Limpieza autónoma',
    'humanoides': 'Robot humanoide',
    'cuadrupedos': 'Robot cuadrúpedo',
    'amr': 'AMR intralogística',
    'accesorios': 'Accesorio',
}


def placeholder(fam, name):
    return (f'<div class="ph ph--{fam}" role="img" aria-label="{e(name)}">'
            f'<svg viewBox="0 0 64 64">{SILUETAS[fam]}</svg>'
            f'<span>{e(name)}</span></div>')


def badges(p):
    label, kind = ESTADOS[p['status']]
    out = f'<span class="badge badge--fam">{e(FAM_NAME[p["family"]])}</span>'
    if p['status'] != 'disponible':
        out += f'<span class="badge badge--{kind}">{e(label)}</span>'
    return out


AVISOS_TIENDA = []


SIMBOLOS = {'EUR': '€', 'USD': '$', 'GBP': '£', 'JPY': '¥'}


def formato_precio(valor):
    """100000.0 → «100.000,00» (miles con punto, decimales con coma)."""
    entero, _, dec = f'{valor:,.2f}'.partition('.')
    return entero.replace(',', '.') + ',' + dec


def formato_moneda(codigo):
    """EUR → «€». Las monedas sin símbolo conocido se muestran por su código."""
    return SIMBOLOS.get((codigo or '').upper(), codigo or '')


def boton_compra(p, base):
    """Botón de compra enlazado con la pasarela de Shopify.

    El enlace es un «cart permalink»: añade la variante y cae directamente en
    el checkout de Shopify, sin claves de API ni JavaScript.

    Salvaguarda deliberada: aunque la tienda esté activada, NO se emite el
    botón si el precio es cero o falta. Publicar un botón de compra con precio
    0,00 permitiría a cualquiera pedir un robot gratis, y eso no puede
    depender de acordarse de revisar un ajuste.
    """
    sh = p.get('shopify')
    if not sh or not TIENDA.get('activa'):
        return ''

    dominio = TIENDA['dominio'].strip('/')
    etiqueta = TIENDA.get('texto_boton') or 'Comprar ahora'
    contacto = base + 'contacto.html'

    try:
        precio = float(sh.get('precio') or 0)
    except (TypeError, ValueError):
        precio = 0
    if sh.get('disponible') and precio <= 0:
        AVISOS_TIENDA.append(f'{p["name"]}: precio {sh.get("precio")!r} — sin botón de compra')

    # Estado del último build. Se ve al instante y es lo que indexa Google;
    # el JS lo reemplaza con el estado en vivo de Shopify en cuanto responde.
    interior = estado_compra(
        disponible=bool(sh.get('disponible')), precio=precio,
        moneda=sh.get('moneda', ''), variante=sh['variante'],
        dominio=dominio, etiqueta=etiqueta, contacto=contacto)

    return (f'<div class="compra" data-tienda '
            f'data-dominio="{e(dominio)}" data-handle="{e(sh.get("handle", ""))}" '
            f'data-variante="{e(sh["variante"])}" data-contacto="{e(contacto)}" '
            f'data-texto="{e(etiqueta)}" '
            f'data-precio="{"1" if TIENDA.get("mostrar_precio") else "0"}">'
            f'{interior}</div>')


def estado_compra(disponible, precio, moneda, variante, dominio, etiqueta, contacto):
    """Los tres estados posibles del bloque de compra."""
    if not disponible:
        return ('<p class="sinstock"><span class="sinstock__punto" aria-hidden="true"></span>'
                'Sin stock — consúltanos la disponibilidad</p>'
                f'<a class="pill pill--line" href="{contacto}">'
                f'<span>Avísame cuando esté</span>{CHEVRON}</a>')

    if precio <= 0:
        return ('<p class="sinstock"><span class="sinstock__punto" aria-hidden="true"></span>'
                'Precio bajo consulta</p>'
                f'<a class="pill pill--line" href="{contacto}">'
                f'<span>Pedir presupuesto</span>{CHEVRON}</a>')

    # Sin ?channel=buy_button: ese parámetro exige tener instalado el canal de
    # ventas "Buy Button" en la tienda. Esta tienda no lo tiene, y Shopify
    # rechazaba el checkout con «Parameter Missing or Invalid: channel».
    # El cart permalink funciona igual de bien sin el parámetro.
    url = f'https://{dominio}/cart/{variante}:1'
    precio_html = ''
    if TIENDA.get('mostrar_precio'):
        precio_html = (f'<p class="precio">{e(formato_precio(precio))} '
                       f'<span>{e(formato_moneda(moneda))}</span></p>')
    return (f'{precio_html}<a class="pill pill--comprar" href="{e(url)}" '
            f'rel="nofollow noopener"><span>{e(etiqueta)}</span>{CHEVRON}</a>')


def fondo_video(nombre, base, clase=''):
    """Bucle desenfocado de fondo.

    Va con `autoplay muted loop playsinline` y sin controles: es decoración.
    El `poster` cubre el hueco mientras carga y sirve de fondo fijo si el
    navegador se niega a autoreproducir. `aria-hidden` porque no aporta nada
    a quien usa lector de pantalla.
    """
    if not nombre:
        return ''
    return (f'<div class="fondovid {clase}" aria-hidden="true">'
            f'<video autoplay muted loop playsinline preload="metadata" '
            f'poster="{base}assets/video/{nombre}.jpg">'
            f'<source src="{base}assets/video/{nombre}.mp4" type="video/mp4">'
            f'</video></div>')


# qué bucle de fondo le toca a cada familia de producto
FONDO_POR_MODELO = {
    'rhx2': 'fondo-x2', 'rhx2-ultra': 'fondo-x2',
    'rhx2-edu': 'fondo-x2',
    'rha3': 'fondo-a3', 'rha3-ultra': 'fondo-a3',
}


def video_html(videos, base, titulo='Vídeo'):
    """Sección de vídeo con carátula y reproducción a petición.

    `preload="none"` y el atributo `poster` son deliberados: sin ellos el
    navegador empezaría a descargar decenas de megas antes de que nadie
    pulse Reproducir.
    """
    if not videos:
        return ''
    piezas = ''
    for v in videos:
        pie = f'<figcaption>{e(v["titulo"])}</figcaption>' if v.get('titulo') else ''
        piezas += (
            f'<li class="vid__item reveal"><figure>'
            f'<video controls preload="none" playsinline '
            f'poster="{base}{e(v["poster"])}">'
            f'<source src="{base}{e(v["src"])}" type="video/mp4">'
            f'Tu navegador no puede reproducir este vídeo.'
            f'</video>{pie}</figure></li>\n')
    return f'''  <section class="section section--light" id="video">
    <div class="wrap">
      <header class="section-head reveal"><h2 class="h-section">{e(titulo)}</h2></header>
      <ul class="vid vid--{min(len(videos), 2)}">{piezas}</ul>
    </div>
  </section>
'''


def notes_html(p):
    if not p['notes']:
        return ''
    rows = ''
    for kind, title, body in p['notes']:
        rows += (f'<div class="nota nota--{kind}"><p class="nota__titulo">{e(title)}</p>'
                 f'<p>{e(body)}</p></div>\n')
    return f'<div class="notas">\n{rows}</div>\n'


# ─────────────────────────────────────────────────────────── ficha (x14) ──
def product_page(p):
    base = '../'
    fam = p['family']
    dominio = SEO['dominio'].rstrip('/')
    title = f'{p["name"]} · {p["claim"]} | RH·BOTS'
    breadcrumb = schema_breadcrumb([
        ('Inicio', dominio + '/'),
        ('Robots', dominio + '/robots.html'),
        (p['name'], None),
    ])
    out = [head(title, p['tagline'], base, f'robots/{p["slug"]}.html',
                og_img=p.get('hero'),
                extra_jsonld=[schema_product(p), breadcrumb]),
           header(base), '<main id="contenido">']

    # ---- hero: visualizador giratorio si hay secuencia de vistas
    frames = p.get('frames') or []
    if len(frames) >= 3:
        capas = ''
        for i, f in enumerate(frames):
            capas += (f'<img class="viewer__frame{" is-on" if i == 0 else ""}" '
                      f'src="{base}{f}" alt="" '
                      f'loading="{"eager" if i == 0 else "lazy"}" '
                      f'draggable="false">')
        media = f'''<div class="viewer" id="viewer" tabindex="0" role="img"
             aria-label="{e(p["name"])} — vista giratoria. Usa las flechas para girarlo."
             data-frames="{len(frames)}">
          {capas}
          <span class="viewer__hint" aria-hidden="true">
            <svg viewBox="0 0 24 24"><path d="M9 7L5 12l4 5M15 7l4 5-4 5"/></svg>
            Gíralo
          </span>
        </div>'''
    elif p.get('hero'):
        media = (f'<img src="{base}{p["hero"]}" '
                 f'alt="{e(p.get("hero_alt", p["name"]))}" loading="eager">')
    else:
        media = placeholder(fam, p['name'])
    facts = ''
    if p['keyfacts']:
        facts = '<ul class="keyfacts">' + ''.join(
            f'<li><span>{e(l)}</span><strong>{e(v)}</strong></li>' for l, v in p['keyfacts']
        ) + '</ul>'

    out.append(f'''
  <section class="phero phero--{fam}">
    {fondo_video(FONDO_POR_MODELO.get(p['slug'], 'fondo-gama'), base, 'fondovid--claro')}
    <div class="wrap phero__grid">
      <div class="phero__copy">
        <nav class="crumbs" aria-label="Miga de pan">
          <a href="{base}index.html">Inicio</a> <span>/</span>
          <a href="{base}robots.html">Robots</a> <span>/</span>
          <em>{e(p['name'])}</em>
        </nav>
        <div class="badges">{badges(p)}</div>
        <h1 class="phero__name" data-punto="manual">{con_punto(e(p['name']))} <span class="phero__claim">{e(p['claim'])}</span></h1>
        <p class="phero__tag">{e(p['tagline'])}</p>
        <div class="phero__cta">
          <a class="pill" href="{base}contacto.html"><span>Pide más información</span>
            <i class="pill__ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg></i></a>
          <a class="pill pill--line" href="#especificaciones"><span>Ver especificaciones</span>
            <i class="pill__ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg></i></a>
          {boton_compra(p, base)}
        </div>
        {facts}
      </div>
      <figure class="phero__media">{media}</figure>
    </div>
  </section>
''')

    # ---- avisos
    if p['notes']:
        out.append(f'  <section class="section section--white section--tight">\n'
                   f'    <div class="wrap wrap--narrow">{notes_html(p)}</div>\n  </section>\n')

    # ---- intro + highlights
    out.append('  <section class="section section--white" id="que-hace">\n    <div class="wrap">\n')
    solo = '' if p['highlights'] else ' section-head--solo'
    out.append(f'      <header class="section-head{solo} reveal"><h2 class="h-section h-section--blue">'
               f'¿Qué es el {e(p["name"])}?</h2>'
               f'<p class="sub">{e(p["intro"])}</p></header>\n')
    if p['highlights']:
        out.append('      <ul class="hl">\n')
        for t, d in p['highlights']:
            out.append(f'        <li class="hl__item reveal"><h3>{e(t)}</h3><p>{e(d)}</p></li>\n')
        out.append('      </ul>\n')
    out.append('    </div>\n  </section>\n')

    # ---- vídeo
    out.append(video_html(p.get('videos'), base,
                          f'El {p["name"]} en vídeo' if p.get('videos') else ''))

    # ---- aplicaciones
    if p['applications']:
        con_foto = any(img for _, img in p['applications'])
        if con_foto:
            cards = ''
            for name, img in p['applications']:
                inner = (f'<img src="{base}{img}" alt="{e(name)}" loading="lazy"{img_dims_attr(img)}>' if img
                         else f'<span class="apx__ico" aria-hidden="true">'
                              f'<svg viewBox="0 0 64 64">{SILUETAS[fam]}</svg></span>')
                cards += (f'<li class="apx__item reveal"><figure>{inner}</figure>'
                          f'<h3>{e(name)}</h3></li>\n')
            lista = f'<ul class="apx apx--3">{cards}</ul>'
        else:
            # sin fotografías: lista sobria en vez de repetir el mismo icono
            lista = '<ul class="applist">' + ''.join(
                f'<li class="reveal">{e(n)}</li>' for n, _ in p['applications']) + '</ul>'
        out.append(f'''  <section class="section section--light" id="aplicaciones">
    <div class="wrap">
      <header class="section-head reveal"><h2 class="h-section">Aplicaciones del {e(p['name'])}</h2>
        <p class="sub">Escenarios en los que encaja el {e(p['name'])}.</p></header>
      {lista}
    </div>
  </section>
''')

    # ---- especificaciones
    groups = ''
    for gtitle, rows in p['specs']:
        trs = ''.join(f'<tr><th scope="row">{e(l)}</th><td>{e(v)}</td></tr>' for l, v in rows)
        groups += (f'<div class="specgrp reveal"><h3>{e(gtitle)}</h3>'
                   f'<table class="spectable"><tbody>{trs}</tbody></table></div>\n')
    out.append(f'''  <section class="section section--white" id="especificaciones">
    <div class="wrap">
      <header class="section-head reveal"><h2 class="h-section h-section--blue">Especificaciones técnicas del {e(p['name'])}</h2></header>
      <div class="specgrid">{groups}</div>
    </div>
  </section>
''')

    # ---- galería
    if p.get('gallery'):
        figs = ''.join(
            f'<li class="gal__item reveal"><figure>'
            f'<img src="{base}{img}" alt="{e(t)}" loading="lazy"{img_dims_attr(img)}>'
            f'<figcaption>{e(t)}</figcaption></figure></li>\n'
            for t, img in p['gallery'])
        out.append(f'''  <section class="section section--white" id="galeria">
    <div class="wrap">
      <header class="section-head reveal"><h2 class="h-section">Galería del {e(p['name'])}</h2></header>
      <ul class="gal">{figs}</ul>
    </div>
  </section>
''')

    # ---- checklist de compra (fichas provisionales)
    if p.get('checklist'):
        lis = ''.join(f'<li>{e(x)}</li>' for x in p['checklist'])
        out.append(f'''  <section class="section section--light" id="checklist">
    <div class="wrap wrap--narrow">
      <header class="section-head reveal"><h2 class="h-section">Antes de ofertar este modelo</h2>
        <p class="sub">Documentación a solicitar al fabricante.</p></header>
      <ol class="checklist reveal">{lis}</ol>
    </div>
  </section>
''')

    # ---- otros modelos
    others = [q for q in PRODUCTOS if q['family'] == fam and q['slug'] != p['slug']][:4]
    if others:
        cards = ''
        for q in others:
            if q.get('hero'):
                media = '<img src="%s%s" alt="%s" loading="lazy">' % (base, q['hero'], e(q['name']))
            else:
                media = placeholder(q['family'], q['name'])
            cards += (
                '<li class="pcard reveal"><a href="%s.html">'
                '<div class="pcard__media">%s</div>'
                '<div class="pcard__body"><div class="badges">%s</div>'
                '<h3>%s</h3><p>%s</p></div></a></li>\n'
                % (q['slug'], media, badges(q), e(q['name']), e(q['claim'])))
        out.append(f'''  <section class="section section--white" id="relacionados">
    <div class="wrap">
      <header class="section-head reveal"><h2 class="h-section">Otros modelos de la familia</h2></header>
      <ul class="pgrid">{cards}</ul>
    </div>
  </section>
''')

    out.append(cta_final(base))
    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


def cta_final(base):
    """Cierre de todas las páginas: franja diagonal, texto y robot a la derecha."""
    return f'''  <section class="ctafinal" id="hablamos">
    <div class="ctafinal__diagonal" aria-hidden="true"></div>
    <div class="wrap ctafinal__grid">
      <div class="ctafinal__copy reveal">
        <p class="kicker">{e(CTA['kicker'])}</p>
        <h2 class="ctafinal__titulo">{e(CTA['titulo'])}</h2>
        <p class="ctafinal__texto">{e(CTA['texto'])}</p>
        <a class="pill" href="{base}contacto.html"><span>{e(CTA['boton'])}</span>{CHEVRON}</a>
      </div>
      <img class="ctafinal__robot" src="{base}{e(CTA['imagen'])}" alt="" loading="lazy" aria-hidden="true">
    </div>
  </section>
'''


# ──────────────────────────────────────────────────────────────── índice ──
def index_page():
    base = ''
    out = [head('Robots RH·BOTS — catálogo completo | RH·BOTS',
                'Catálogo RH·BOTS: robots humanoides, cuadrúpedos, de limpieza y AMR de '
                'intralogística, y accesorios, con fichas técnicas completas.', base, 'robots.html'),
           header(base), '<main id="contenido">']

    # accesos directos a cada familia
    chips = ''.join(
        f'<a class="chip" href="#{key}">{e(name)} <em>{len([p for p in PRODUCTOS if p["family"] == key])}</em></a>'
        for key, name, _ in FAMILIAS if any(p['family'] == key for p in PRODUCTOS))

    out.append(f'''
  <section class="chero">
    <div class="wrap">
      <nav class="crumbs" aria-label="Miga de pan"><a href="index.html">Inicio</a> <span>/</span> <em>Robots</em></nav>
      <h1 class="display display--left">Nuestros robots</h1>
      <p class="lede lede--left">Humanoides, cuadrúpedos, limpieza autónoma, AMR de intralogística y accesorios.
        {len(PRODUCTOS)} modelos con ficha técnica completa para elegir el que encaja en tu operación.</p>
      <nav class="chips chips--familias" aria-label="Familias de robots">{chips}</nav>
    </div>
  </section>
''')

    # una sección por familia
    for i, (key, name, desc) in enumerate(FAMILIAS):
        modelos = [p for p in PRODUCTOS if p['family'] == key]
        if not modelos:
            continue
        cards = ''
        for p in modelos:
            media = (f'<img src="{p["hero"]}" alt="{e(p["name"])}" loading="lazy">'
                     if p.get('hero') else placeholder(p['family'], p['name']))
            facts = ''
            if p['keyfacts']:
                facts = '<ul class="pcard__facts">' + ''.join(
                    f'<li><span>{e(l)}</span><strong>{e(v)}</strong></li>' for l, v in p['keyfacts'][:3]
                ) + '</ul>'
            cards += f'''<li class="pcard reveal">
          <a href="robots/{p['slug']}.html">
            <div class="pcard__media">{media}</div>
            <div class="pcard__body">
              <div class="badges">{badges(p)}</div>
              <h3>{e(p['name'])}</h3>
              <p>{e(p['claim'])}</p>
              {facts}
              <span class="pcard__more">Ver ficha técnica</span>
            </div>
          </a></li>\n'''
        fondo = 'section--white' if i % 2 == 0 else 'section--light'
        out.append(f'''  <section class="section {fondo} familia" id="{key}">
    <div class="wrap">
      <header class="familia__head reveal">
        <p class="kicker">{len(modelos)} {'modelo' if len(modelos) == 1 else 'modelos'}</p>
        <h2 class="familia__titulo">{e(name)}</h2>
        <p class="familia__desc">{e(desc)}</p>
      </header>
      <ul class="pgrid pgrid--big">{cards}</ul>
    </div>
  </section>
''')

    # guía rápida
    rows = ''.join(
        f'<tr><th scope="row"><a href="robots/{s}.html">{e(BY_SLUG[s]["name"])}</a></th>'
        f'<td>{e(txt)}</td></tr>' for s, txt in GUIA)
    out.append(f'''  <section class="section section--light" id="guia">
    <div class="wrap">
      <header class="section-head reveal"><h2 class="h-section">Guía rápida de selección</h2>
        <p class="sub">Qué modelo encaja en cada necesidad.</p></header>
      <div class="guia reveal"><table class="spectable"><tbody>{rows}</tbody></table></div>
    </div>
  </section>
''')

    out.append(cta_final(base))
    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


# ─────────────────────────────────────────────────── bloques compartidos ──
MARCA_SVG = ('<svg viewBox="0 0 64 64">'
             '<rect x="14" y="17" width="36" height="31" rx="13" stroke-width="6"/>'
             '<rect x="24.6" y="29" width="6" height="11.5" rx="3" class="fill nostroke"/>'
             '<rect x="33.4" y="29" width="6" height="11.5" rx="3" class="fill nostroke"/></svg>')

FLECHA = ('<svg class="flecha" viewBox="0 0 24 24" aria-hidden="true">'
          '<path d="M5 12h14M13 6l6 6-6 6"/></svg>')

CHEVRON = '<i class="pill__ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg></i>'


def bloque_faq(preguntas, titulo='Preguntas frecuentes'):
    items = ''
    for q, a in preguntas:
        items += f'''<div class="faq__item reveal">
          <h3><button class="faq__q" aria-expanded="false"><span>{e(q)}</span>
            <i class="faq__ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg></i>
          </button></h3>
          <div class="faq__a"><div class="faq__a-in"><p>{e(a)}</p></div></div>
        </div>\n'''
    return f'''  <section class="section section--white section--faq" id="faq">
    <div class="wrap wrap--narrow">
      <header class="section-head reveal"><h2 class="h-section h-section--blue">{e(titulo)}</h2></header>
      <div class="faq" id="faq-list">{items}</div>
    </div>
  </section>
'''


MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def mes_y_ano(fecha):
    """'2026-09-10' pasa a 'septiembre 2026'. Si no es una fecha ISO, se deja igual."""
    m = re.match(r'(\d{4})-(\d{2})', fecha or '')
    return f'{MESES[int(m.group(2)) - 1]} {m.group(1)}' if m else (fecha or '')


# ──────────────────────────────────────────────────────────────────── home ──
def home_page():
    base = ''
    out = [head('RH·BOTS — Recursos humanoides para tu empresa',
                'Robots humanoides, cuadrúpedos, de limpieza y de intralogística. Asesoramiento, instalación, '
                'formación y soporte en Valencia.', base, 'index.html',
                extra_jsonld=[schema_organization(), schema_faqpage(HOME['faq'])]),
           header(base, 'home'), '<main id="contenido">']

    # hero: vídeo a pantalla completa, velo oscuro y franja diagonal
    out.append(f'''
  <section class="hero" id="inicio">
    {fondo_video('fondo-c5', base, 'fondovid--oscuro')}
    <div class="hero__diagonal" aria-hidden="true"></div>
    <div class="wrap hero__copy">
      <p class="kicker hero__kicker">{HOME['kicker']}</p>
      <h1 class="display display--hero">{HOME['h1']}</h1>
      <p class="lede lede--hero">{e(HOME['lede'])}</p>
      <div class="hero__cta">
        <a class="pill" href="robots.html"><span>Ver los robots</span>{CHEVRON}</a>
        <a class="pill pill--line" href="contacto.html"><span>Habla con nosotros</span>{CHEVRON}</a>
      </div>
    </div>
  </section>
''')

    # qué hacemos: titular a la izquierda, tarjeta con la propuesta a la derecha
    q = HOME.get('que_hacemos')
    if q:
        out.append(f'''  <section class="section section--white que" id="que-hacemos">
    <div class="wrap que__grid">
      <div class="que__texto reveal">
        <p class="kicker">{e(q['kicker'])}</p>
        <h2 class="que__titulo">{q['titulo']}</h2>
        <p class="que__lede">{e(q['texto'])}</p>
      </div>
      <div class="que__tarjeta reveal">
        <p class="que__destacado">{e(q['destacado'])}</p>
        <p class="que__detalle">{e(q['detalle'])}</p>
      </div>
    </div>
  </section>
''')

    # nuestros robots: carrusel con todos los modelos disponibles
    g = HOME.get('robots_grid')
    if g:
        tarjetas = ''
        for p in PRODUCTOS:
            if p['status'] != 'disponible':
                continue
            if p.get('hero'):
                media = (f'<img src="{e(p["hero"])}" alt="{e(p["name"])} — {e(p["claim"])}" '
                         f'loading="lazy" draggable="false">')
            else:
                media = placeholder(p['family'], p['name'])
            tarjetas += f'''<li class="lcard">
          <a href="robots/{p['slug']}.html">
            <div class="lcard__media">{media}</div>
            <div class="lcard__body">
              <p class="lcard__cat">{e(ETIQUETA_FAMILIA.get(p['family'], FAM_NAME[p['family']]))}</p>
              <h3 class="lcard__name">{e(p['name'])}</h3>
              <p class="lcard__desc">{e(p['claim'])}</p>
              <span class="lcard__mas">Ver modelo{FLECHA}</span>
            </div>
          </a></li>\n'''
        out.append(f'''  <section class="section section--light loop" id="nuestros-robots">
    <div class="wrap">
      <header class="loop__head reveal">
        <p class="kicker">{e(g['kicker'])}</p>
        <h2 class="loop__titulo">{g['titulo']}</h2>
      </header>
      <div class="carrusel reveal" data-carrusel>
        <ul class="carrusel__pista" tabindex="0" aria-label="Modelos disponibles">{tarjetas}</ul>
        <button type="button" class="carrusel__btn carrusel__btn--prev" aria-label="Modelos anteriores">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6"/></svg></button>
        <button type="button" class="carrusel__btn carrusel__btn--next" aria-label="Modelos siguientes">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button>
      </div>
      <p class="loop__mas reveal"><a class="pill" href="robots.html"><span>Ver todos los modelos</span>{CHEVRON}</a></p>
    </div>
  </section>
''')

    # aplicaciones por sector: bloque azul con tarjetas
    sec = HOME.get('sectores_bloque')
    if sec:
        fichas = ''.join(
            f'<li class="secbloque__ficha reveal"><h3>{e(t)}</h3><p>{e(txt)}</p></li>\n'
            for t, txt in sec['tarjetas'])
        out.append(f'''  <section class="secbloque" id="sectores">
    <div class="secbloque__diagonal" aria-hidden="true"></div>
    <div class="wrap secbloque__grid">
      <div class="secbloque__copy reveal">
        <p class="kicker">{e(sec['kicker'])}</p>
        <h2 class="secbloque__titulo">{e(sec['titulo'])}</h2>
        <p class="secbloque__lede">{e(sec['texto'])}</p>
        <a class="pill" href="contacto.html"><span>{e(sec['boton'])}</span>{CHEVRON}</a>
      </div>
      <ul class="secbloque__fichas">{fichas}</ul>
    </div>
  </section>
''')

    # método: cuatro pasos en una rejilla con separadores
    met = HOME.get('metodo')
    if met:
        pasos = ''.join(
            f'<li class="metodo__paso reveal"><p class="metodo__num">{i:02d}</p>'
            f'<h3 class="metodo__nombre">{e(t)}</h3>'
            f'<p class="metodo__texto">{e(txt)}</p></li>\n'
            for i, (t, txt) in enumerate(met['pasos'], 1))
        out.append(f'''  <section class="section section--white metodo" id="metodo">
    <div class="wrap">
      <header class="metodo__head reveal">
        <p class="kicker">{e(met['kicker'])}</p>
        <h2 class="metodo__titulo">{met['titulo']}</h2>
      </header>
      <ol class="metodo__grid">{pasos}</ol>
      {f'<p class="metodo__mas reveal"><a class="pill" href="contacto.html"><span>{e(met["boton"])}</span>{CHEVRON}</a></p>' if met.get('boton') else ''}
    </div>
  </section>
''')

    # vídeo general
    if HOME.get('video'):
        out.append(video_html([HOME['video']], base, 'Míralos trabajando'))

    # actualidad: últimas entradas del blog
    act = HOME.get('actualidad')
    if act and POSTS:
        fichas = ''
        for post in POSTS[:3]:
            media = (f'<div class="ncard__media"><img src="{e(post["img"])}" alt="" loading="lazy"></div>'
                     if post.get('img') else '')
            fichas += f'''<li class="ncard reveal"><a href="{e(post['url'])}">
          {media}
          <div class="ncard__body">
            <p class="ncard__fecha">{e(mes_y_ano(post.get('fecha', '')))}</p>
            <h3>{e(post['titulo'])}</h3>
            <p class="ncard__resumen">{e(post.get('resumen', ''))}</p>
            <span class="ncard__mas">Leer más{FLECHA}</span>
          </div></a></li>\n'''
        out.append(f'''  <section class="section section--light actualidad" id="actualidad">
    <div class="wrap">
      <header class="actualidad__head reveal">
        <div>
          <p class="kicker">{e(act['kicker'])}</p>
          <h2 class="actualidad__titulo">{e(act['titulo'])}</h2>
        </div>
        <a class="actualidad__enlace" href="blog.html">{e(act['enlace'])}{FLECHA}</a>
      </header>
      <ul class="actualidad__grid">{fichas}</ul>
    </div>
  </section>
''')

    out.append(bloque_faq(HOME['faq']))
    out.append(cta_final(base))
    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


# ──────────────────────────────────────────────────────────────────── blog ──
def blog_page():
    base = ''
    out = [head('Blog | RH·BOTS', 'Novedades, casos de uso y notas técnicas sobre robótica de '
                'servicio e industrial.', base, 'blog.html'),
           header(base, 'blog'), '<main id="contenido">']
    out.append('''
  <section class="chero">
    <div class="wrap">
      <nav class="crumbs" aria-label="Miga de pan"><a href="index.html">Inicio</a> <span>/</span> <em>Blog</em></nav>
      <h1 class="display display--left">Blog</h1>
      <p class="lede lede--left">Novedades de producto, casos de uso reales y notas técnicas
        sobre robótica de servicio e industrial.</p>
    </div>
  </section>
''')

    if POSTS:
        arts = ''
        for post in POSTS:
            img = (f'<div class="post__media"><img src="{e(post["img"])}" alt="" loading="lazy"></div>'
                   if post.get('img') else '')
            arts += f'''<li class="post reveal"><a href="{e(post['url'])}">
              {img}
              <div class="post__body">
                <p class="post__meta">{e(post.get('categoria', ''))} · {e(mes_y_ano(post.get('fecha', '')))}</p>
                <h2>{e(post['titulo'])}</h2>
                <p>{e(post.get('resumen', ''))}</p>
                <span class="pcard__more">Leer</span>
              </div></a></li>\n'''
        out.append(f'  <section class="section section--white">\n    <div class="wrap">\n'
                   f'      <ul class="postgrid">{arts}</ul>\n    </div>\n  </section>\n')
    else:
        out.append(f'''  <section class="section section--white">
    <div class="wrap wrap--narrow">
      <div class="vacio reveal">
        <span class="vacio__ico" aria-hidden="true">{MARCA_SVG}</span>
        <h2>Estamos preparando los primeros artículos</h2>
        <p>Aquí publicaremos novedades de producto, casos de uso de nuestros clientes y notas
          técnicas sobre los modelos del catálogo. Mientras tanto, puedes consultar las fichas
          técnicas o escribirnos directamente.</p>
        <div class="feat-cta">
          <a class="pill" href="robots.html"><span>Ver los robots</span>{CHEVRON}</a>
          <a class="pill pill--line" href="contacto.html"><span>Escríbenos</span>{CHEVRON}</a>
        </div>
      </div>
    </div>
  </section>
''')

    out.append(cta_final(base))
    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


# ─────────────────────────────────────────────────────────────── artículo ──
def articulo_page(post):
    base = '../'
    ruta = f'blog/{post["slug"]}.html'
    out = [head(f'{post["titulo"]} | Blog RH·BOTS', post.get('resumen', ''), base, ruta,
                og_img=post.get('img')),
           header(base, 'blog'), '<main id="contenido">']

    portada = (f'<figure class="art__portada"><img src="{base}{e(post["img"])}" '
              f'alt="{e(post["titulo"])}" loading="eager"></figure>'
              if post.get('img') else '')

    out.append(f'''
  <section class="chero chero--art">
    <div class="wrap wrap--narrow">
      <nav class="crumbs" aria-label="Miga de pan">
        <a href="{base}index.html">Inicio</a> <span>/</span>
        <a href="{base}blog.html">Blog</a> <span>/</span>
        <em>{e(post['titulo'])}</em>
      </nav>
      <p class="art__meta">{e(post.get('categoria', ''))} · {e(mes_y_ano(post.get('fecha', '')))}</p>
      <h1 class="display display--left">{e(post['titulo'])}</h1>
    </div>
  </section>

  <article class="section section--white">
    <div class="wrap wrap--narrow">
      {portada}
      <div class="art__cuerpo reveal">
        {limpiar_cuerpo(post.get('cuerpo', ''))}
      </div>
      <p class="art__volver"><a href="{base}blog.html">← Volver al blog</a></p>
    </div>
  </article>
''')

    out.append(cta_final(base))
    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


SIN_FOTO_SVG = ('<svg viewBox="0 0 64 64">'
                '<circle cx="32" cy="24" r="12"/>'
                '<path d="M12 54c0-12 9-20 20-20s20 8 20 20"/></svg>')


def bloque_equipo(equipo, base):
    if not equipo:
        return ''
    tarjetas = ''
    for foto, nombre, cargo, bio in equipo:
        if foto:
            media = (f'<div class="persona-equipo__foto"><img src="{base}{e(foto)}" alt="" '
                    f'loading="lazy"{img_dims_attr(foto)}></div>')
        else:
            media = (f'<div class="persona-equipo__foto persona-equipo__foto--vacia" '
                     f'aria-hidden="true">{SIN_FOTO_SVG}</div>')
        bio_html = f'<p class="persona-equipo__bio">{e(bio)}</p>' if bio else ''
        tarjetas += f'''<li class="persona-equipo reveal">
        {media}
        <p class="persona-equipo__nombre">{e(nombre)}</p>
        <p class="persona-equipo__cargo">{e(cargo)}</p>
        {bio_html}
      </li>\n'''
    return f'''  <section class="section section--light" id="equipo">
    <div class="wrap">
      <header class="section-head reveal"><h2 class="h-section h-section--blue">Equipo</h2></header>
      <ul class="equipo">{tarjetas}</ul>
    </div>
  </section>
'''


def rh_bots_page():
    base = ''
    r = RHBOTS
    emails = {p['nombre']: p.get('email') for p in CONTACTO.get('personas', [])}
    personas_jsonld = [schema_person(nombre, cargo, emails.get(nombre))
                       for _, nombre, cargo, _ in (r.get('equipo') or []) if nombre]
    out = [head(f'{r.get("h1", "RH·BOTS")} | RH·BOTS', r.get('lede', ''), base, 'rh-bots.html',
                extra_jsonld=personas_jsonld),
           header(base, 'rhbots'), '<main id="contenido">']

    out.append(f'''
  <section class="chero">
    <div class="wrap">
      <nav class="crumbs" aria-label="Miga de pan"><a href="index.html">Inicio</a> <span>/</span> <em>RH·BOTS</em></nav>
      {f'<p class="art__meta">{e(r["kicker"])}</p>' if r.get('kicker') else ''}
      <h1 class="display display--left">{e(r.get('h1', ''))}</h1>
      <p class="lede lede--left">{e(r.get('lede', ''))}</p>
    </div>
  </section>
''')

    if r.get('cifras'):
        celdas = ''.join(
            f'<div class="cifra reveal"><p class="cifra__valor">{e(v)}</p>'
            f'<p class="cifra__etiqueta">{e(et)}</p></div>\n'
            for v, et in r['cifras'])
        out.append(f'''  <section class="section section--white section--tight">
    <div class="wrap"><div class="cifras">{celdas}</div></div>
  </section>
''')

    if r.get('historia_cuerpo'):
        subt = (f'<h2 class="historia__subtitulo reveal">{e(r["historia_subtitulo"])}</h2>'
               if r.get('historia_subtitulo') else '')
        out.append(f'''  <section class="section section--white">
    <div class="wrap wrap--narrow">
      {subt}
      <div class="art__cuerpo reveal">{limpiar_cuerpo(r['historia_cuerpo'])}</div>
    </div>
  </section>
''')

    out.append(bloque_equipo(r.get('equipo'), base))
    out.append(cta_final(base))
    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


def legal_page():
    base = ''
    dominio = SEO['dominio'].rstrip('/')
    empresa = CONTACTO.get('empresa') or 'RH·BOTS'
    direccion = ', '.join(CONTACTO.get('direccion') or [])
    principal = CONTACTO['personas'][0] if CONTACTO.get('personas') else {}
    email = principal.get('email', '')
    tel = principal.get('tel', '')

    out = [head('Aviso legal, privacidad y cookies | RH·BOTS',
                'Aviso legal, política de privacidad y cookies de RH·BOTS.',
                base, 'legal.html'),
           header(base), '<main id="contenido">']

    out.append(f'''
  <section class="chero">
    <div class="wrap">
      <nav class="crumbs" aria-label="Miga de pan"><a href="index.html">Inicio</a> <span>/</span> <em>Aviso legal</em></nav>
      <h1 class="display display--left">Aviso legal, privacidad y cookies</h1>
    </div>
  </section>
  <section class="section section--white">
    <div class="wrap wrap--narrow art__cuerpo">
      <h2 id="aviso-legal">Aviso legal</h2>
      <p><strong>Titular del sitio web:</strong> {e(empresa)}.<br>
      <strong>CIF/NIF:</strong> [pendiente de completar por el titular].<br>
      <strong>Domicilio:</strong> {e(direccion)}.<br>
      {f'<strong>Contacto:</strong> {e(email)}' + (f' · {e(tel)}' if tel else '') + '.<br>' if email else ''}
      <strong>Dominio:</strong> {e(dominio)}</p>
      <p>El acceso y uso de este sitio web atribuye la condición de usuario e implica
      la aceptación de las condiciones aquí recogidas. {e(empresa)} es distribuidor
      oficial de AGIBOT en España y Portugal.</p>

      <h2 id="privacidad">Política de privacidad</h2>
      <p><strong>Responsable del tratamiento:</strong> {e(empresa)}{f', {e(email)}' if email else ''}.</p>
      <p><strong>Finalidad:</strong> atender las solicitudes de información, presupuesto,
      demostración o soporte que nos envíes a través del formulario de contacto,
      y gestionar la relación comercial si llega a formalizarse.</p>
      <p><strong>Legitimación:</strong> consentimiento de la persona interesada al
      enviar sus datos, y ejecución de una eventual relación contractual.</p>
      <p><strong>Conservación:</strong> mientras se mantenga la relación con el
      usuario o durante los plazos legalmente exigibles.</p>
      <p><strong>Destinatarios:</strong> no se ceden datos a terceros salvo
      obligación legal o proveedores necesarios para prestar el servicio
      solicitado (por ejemplo, Shopify para procesar un pedido).</p>
      <p><strong>Derechos:</strong> puedes ejercer tus derechos de acceso,
      rectificación, supresión, oposición, limitación y portabilidad
      escribiendo a{f' {e(email)}' if email else ' la dirección de contacto de RH·BOTS'}.</p>

      <h2 id="cookies">Política de cookies</h2>
      <p>Este sitio usa únicamente las cookies técnicas necesarias para su
      funcionamiento. Si en el futuro se activa Google Analytics u otra
      herramienta de medición, se solicitará el consentimiento previo del
      usuario antes de cargarla.</p>
    </div>
  </section>
''')
    out.append(cta_final(base))
    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


# ──────────────────────────────────────────────────────────────── contacto ──
def contacto_page():
    base = ''
    c = CONTACTO
    out = [head('Contacto | RH·BOTS', c['intro'], base, 'contacto.html'),
           header(base, 'contacto'), '<main id="contenido">']

    personas = ''
    for p in c['personas']:
        personas += f'''<li class="persona reveal">
        <h3>{e(p['nombre'])}</h3>
        <p class="persona__cargo">{e(p['cargo'])}</p>
        <p><a href="mailto:{e(p['email'])}">{e(p['email'])}</a></p>
        <p><a href="tel:{p['tel'].replace(' ', '')}">{e(p['tel'])}</a></p>
      </li>\n'''

    opciones = ''.join(f'<option>{e(m)}</option>' for m in c['motivos'])
    direccion = '<br>'.join(e(x) for x in c['direccion'])

    out.append(f'''
  <section class="chero">
    <div class="wrap">
      <nav class="crumbs" aria-label="Miga de pan"><a href="index.html">Inicio</a> <span>/</span> <em>Contacto</em></nav>
      <h1 class="display display--left">Hablemos</h1>
      <p class="lede lede--left">{e(c['intro'])}</p>
    </div>
  </section>

  <section class="section section--white">
    <div class="wrap contacto">
      <div class="contacto__form reveal">
        <h2 class="h-section h-section--blue">Escríbenos</h2>
        <form class="form" id="contactoForm" novalidate>
          <div class="form__row">
            <label for="f-nombre">Nombre y apellidos</label>
            <input id="f-nombre" name="nombre" type="text" autocomplete="name" required>
          </div>
          <div class="form__row">
            <label for="f-empresa">Empresa</label>
            <input id="f-empresa" name="empresa" type="text" autocomplete="organization">
          </div>
          <div class="form__two">
            <div class="form__row">
              <label for="f-email">Email</label>
              <input id="f-email" name="email" type="email" autocomplete="email" required>
            </div>
            <div class="form__row">
              <label for="f-tel">Teléfono</label>
              <input id="f-tel" name="tel" type="tel" autocomplete="tel">
            </div>
          </div>
          <div class="form__row">
            <label for="f-motivo">Motivo</label>
            <select id="f-motivo" name="motivo">{opciones}</select>
          </div>
          <div class="form__row">
            <label for="f-mensaje">Cuéntanos qué necesitas</label>
            <textarea id="f-mensaje" name="mensaje" rows="5" required></textarea>
          </div>
          <button class="pill" type="submit"><span>Enviar</span>{CHEVRON}</button>
          <p class="form__nota" id="formNota" role="status"></p>
        </form>
      </div>

      <aside class="contacto__datos reveal">
        <h2 class="h-section">{e(c['empresa'])}</h2>
        <address class="direccion">{direccion}</address>
        <ul class="personas">{personas}</ul>
      </aside>
    </div>
  </section>
''')

    out.append(cta_final(base))
    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


# ────────────────────────────────────────────────────────────────── main ──
# Todos los títulos (h1 y h2) acaban en un punto. Se añade aquí, al escribir,
# para no tener que acordarse en cada plantilla. El punto toma el color de la
# primera palabra del título: en «El futuro… es <span class="acento">ahora</span>.»
# va del color de «El». Los que ya cierran con signo propio (¿…?, ¡…!, comillas)
# se dejan como están; los que llevan data-punto="manual" lo ponen ellos.
_TITULO = re.compile(r'(<h([1-6])\b[^>]*>)(.*?)(</h\2>)', re.S)
_TROZO = re.compile(r'(<[^>]+>)|([^<]+)')


def _palabras(fragmento):
    """[(palabra, va_en_acento)] del HTML de un título."""
    pila, out = [], []
    for etiqueta, texto in _TROZO.findall(fragmento):
        if etiqueta:
            if etiqueta.startswith('</span'):
                if pila:
                    pila.pop()
            elif etiqueta.startswith('<span'):
                pila.append('acento' in etiqueta)
        else:
            out += [(w, any(pila)) for w in html.unescape(texto).split()
                    if re.search(r'\w', w)]
    return out


def con_punto(fragmento):
    palabras = _palabras(fragmento)
    texto = html.unescape(re.sub(r'<[^>]+>', '', fragmento)).strip()
    if not palabras or texto[-1] in '.?!:;…»"\'':
        return fragmento
    acento = palabras[0][1]
    clase = 'punto punto--acento' if acento else 'punto'
    return fragmento.rstrip() + f'<span class="{clase}" aria-hidden="true">.</span>'


def ultima_en_azul(fragmento):
    """La última palabra del titular va en azul.

    Se salta los títulos que ya traen su propio <span class="acento"> (el
    del hero, por ejemplo, donde el azul empieza antes) y los que van
    blancos sobre banda azul, donde el azul claro no se leería.
    """
    if 'acento' in fragmento or len(_palabras(fragmento)) < 2:
        return fragmento          # un título de una sola palabra no se parte
    m = re.search(r'([^\s<>]+)(\s*)$', fragmento)
    if not m or not re.search(r'\w', m.group(1)):
        return fragmento
    return (fragmento[:m.start(1)]
            + f'<span class="acento">{m.group(1)}</span>' + m.group(2))


def _titulo(m):
    abre, nivel, dentro, cierra = m.group(1), m.group(2), m.group(3), m.group(4)
    # que Google no lea «larobótica» donde hay un salto de línea
    dentro = re.sub(r'(?<=\S)<br\s*/?>', ' <br>', dentro)
    if nivel in '12' and 'sr-only' not in abre and 'onblue' not in abre:
        dentro = ultima_en_azul(dentro)
    if nivel in '12' and 'data-punto' not in abre and 'class="punto' not in dentro:
        dentro = con_punto(dentro)
    return abre + dentro + cierra


def write(path, content):
    if path.endswith('.html'):
        content = _TITULO.sub(_titulo, content)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, 'w', encoding='utf-8').write(content)
    return path


def pagina_404():
    base = ''
    out = [head('Página no encontrada | RH·BOTS',
                'La página que buscas no existe o ha cambiado de sitio.',
                base, '404.html'),
           header(base, ''), '<main id="contenido">']
    out.append(f'''
  <section class="chero">
    <div class="wrap">
      <p class="err404">404</p>
      <h1 class="display display--left">Esta página no existe</h1>
      <p class="lede lede--left">Puede que el enlace esté mal escrito o que
        hayamos movido el contenido. Desde aquí llegas a todo:</p>
      <div class="feat-cta" style="justify-content:flex-start">
        <a class="pill" href="index.html"><span>Ir al inicio</span>{CHEVRON}</a>
        <a class="pill pill--line" href="robots.html"><span>Ver los robots</span>{CHEVRON}</a>
      </div>
    </div>
  </section>
''')
    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


def sitemap():
    d = SEO['dominio'].rstrip('/')
    rutas = [('', '1.0'), ('robots.html', '0.9'), ('rh-bots.html', '0.6'),
             ('contacto.html', '0.7'), ('blog.html', '0.5'), ('legal.html', '0.2')]
    rutas += [(f'robots/{p["slug"]}.html', '0.8') for p in PRODUCTOS]
    rutas += [(p['url'], '0.6') for p in POSTS if p.get('url')]
    urls = ''.join(
        f'  <url><loc>{d}/{r}</loc><lastmod>{FECHA_BUILD}</lastmod><priority>{pr}</priority></url>\n'
        for r, pr in rutas)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f'{urls}</urlset>\n')


def llms_txt():
    """Ficha del sitio en formato llms.txt (llmstxt.org) para que un LLM
    entienda de un vistazo qué hay y a dónde ir, sin tener que rastrear
    todo el HTML."""
    d = SEO['dominio'].rstrip('/')
    out = ['# RH·BOTS\n',
           f'> Distribuidor oficial de AGIBOT en España y Portugal. Robots de limpieza '
           f'autónoma, humanoides, cuadrúpedos, AMR de intralogística y accesorios, con asesoramiento, instalación, '
           f'formación y mantenimiento. Sede en Picassent (Valencia).\n']

    out.append('## Robots\n')
    for key, nombre, _ in FAMILIAS:
        modelos = [p for p in PRODUCTOS if p['family'] == key]
        if not modelos:
            continue
        out.append(f'\n### {nombre}\n')
        for p in modelos:
            out.append(f'- [{p["name"]}]({d}/robots/{p["slug"]}.html): {p["claim"]}')
    out.append(f'\n\n## Empresa\n')
    out.append(f'- [Catálogo completo]({d}/robots.html)')
    out.append(f'- [Quiénes somos]({d}/rh-bots.html): equipo e historia de RH·BOTS')
    out.append(f'- [Contacto]({d}/contacto.html)')
    out.append(f'\n\n## Optional\n')
    out.append(f'- [Blog]({d}/blog.html)')
    out.append(f'- [Aviso legal y privacidad]({d}/legal.html)')
    return '\n'.join(out) + '\n'


def robots_txt():
    d = SEO['dominio'].rstrip('/')
    return f'User-agent: *\nAllow: /\n\nSitemap: {d}/sitemap.xml\n'


def main():
    paginas = [
        ('index.html',    home_page()),
        ('robots.html',   index_page()),
        ('rh-bots.html',  rh_bots_page()),
        ('blog.html',     blog_page()),
        ('contacto.html', contacto_page()),
        ('legal.html',    legal_page()),
    ]
    for nombre, contenido in paginas:
        write(os.path.join(WEB, nombre), contenido)
    fichas_vivas = set()
    for p in PRODUCTOS:
        fichas_vivas.add(p['slug'] + '.html')
        write(os.path.join(WEB, 'robots', p['slug'] + '.html'), product_page(p))

    # un modelo retirado del catálogo no debe dejar su ficha publicada
    for archivo in os.listdir(os.path.join(WEB, 'robots')):
        if archivo.endswith('.html') and archivo not in fichas_vivas:
            os.remove(os.path.join(WEB, 'robots', archivo))

    slugs_vivos = set()
    for post in POSTS:
        if not post.get('slug'):
            continue
        slugs_vivos.add(post['slug'] + '.html')
        write(os.path.join(WEB, 'blog', post['slug'] + '.html'), articulo_page(post))

    # las entradas borradas no deben dejar su página vieja publicada
    carpeta_blog = os.path.join(WEB, 'blog')
    if os.path.isdir(carpeta_blog):
        for archivo in os.listdir(carpeta_blog):
            if archivo not in slugs_vivos:
                os.remove(os.path.join(carpeta_blog, archivo))

    write(os.path.join(WEB, '404.html'), pagina_404())
    write(os.path.join(WEB, 'sitemap.xml'), sitemap())
    write(os.path.join(WEB, 'robots.txt'), robots_txt())
    write(os.path.join(WEB, 'llms.txt'), llms_txt())

    enlazados = [x for x in PRODUCTOS if x.get('shopify')]
    if TIENDA.get('activa'):
        agotados = [x for x in enlazados if not x['shopify'].get('disponible')]
        comprables = len(enlazados) - len(agotados) - len(AVISOS_TIENDA)
        print(f'     tienda ACTIVA · {len(enlazados)} enlazados: '
              f'{comprables} con botón de compra, {len(agotados)} sin stock, '
              f'{len(AVISOS_TIENDA)} bloqueados por precio')
        for a in AVISOS_TIENDA:
            print(f'       ! {a}')
    else:
        print(f'     tienda desactivada · {len(enlazados)} productos enlazados, sin botón')

    ga = ANALITICA.get('ga4') or ANALITICA.get('gtm') or 'sin configurar'
    print(f'OK — {len(paginas) + len(PRODUCTOS)} páginas: home, catálogo, rh-bots, blog, contacto '
          f'y {len(PRODUCTOS)} fichas')
    print(f'     sitemap.xml y robots.txt · dominio {SEO["dominio"]} · analítica: {ga}')


if __name__ == '__main__':
    main()
