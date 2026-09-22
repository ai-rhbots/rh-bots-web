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
from productos import PRODUCTOS, FAMILIAS, ESTADOS, BY_SLUG  # noqa: E402
from sitio import (NAV, HOME, CONTACTO, POSTS, SEO, ANALITICA, CTA, PREFOOTER, APLICACIONES,  # noqa: E402
                   TIENDA, RHBOTS)
from limpiar_html import limpiar as limpiar_cuerpo  # noqa: E402

e = html.escape

# ─────────────────────────────────────────────────────── idioma (es / en) ──
# La web se genera dos veces, una por idioma: main() recorre LANG_ES/LANG_EN,
# set_lang() intercambia los datos (NAV, HOME, PRODUCTOS…) por su versión
# traducida y t() da la cadena de interfaz que toque según el idioma activo.
# El español vive en datos/sitio.json y datos/productos.json; el inglés es
# una capa que solo pisa los campos traducibles (datos/sitio.en.json y
# datos/productos.en.json) — lo que falte en esa capa cae al español, así
# que una traducción a medias no rompe nunca la build.
LANG = 'es'
NIVEL = {'es': '', 'en': '../'}   # tramos «../» extra para bajar a /en/


def _fusiona(es, capa):
    """Superpone «capa» (inglés) sobre «es» (español), recursivo en dicts.
    Listas y valores sueltos se sustituyen enteros si la capa los trae."""
    if not isinstance(capa, dict) or not isinstance(es, dict):
        return capa if capa is not None else es
    return {k: (_fusiona(es.get(k), v) if isinstance(v, dict) and isinstance(es.get(k), dict) else v)
            for k, v in {**es, **capa}.items()}


def _carga_en(nombre):
    ruta = os.path.join(os.path.dirname(HERE), 'datos', nombre)
    if not os.path.exists(ruta):
        return {}
    with io.open(ruta, encoding='utf-8') as f:
        return json.load(f)


_SITIO_EN = _carga_en('sitio.en.json')
_PRODUCTOS_EN_POR_SLUG = _carga_en('productos.en.json')
_ESTADOS_EN = (_PRODUCTOS_EN_POR_SLUG.pop('estados', None) or {})
_FAMILIAS_EN = (_PRODUCTOS_EN_POR_SLUG.pop('familias', None) or [])
_PRODUCTOS_EN_POR_SLUG.pop('productos', None)  # por si el archivo viniera con esa envoltura

_NAV_ES, _HOME_ES, _CONTACTO_ES = NAV, HOME, CONTACTO
_CTA_ES, _PREFOOTER_ES, _POSTS_ES = CTA, PREFOOTER, POSTS
_RHBOTS_ES, _APLICACIONES_ES = RHBOTS, APLICACIONES
_FAMILIAS_ES, _ESTADOS_ES, _PRODUCTOS_ES = FAMILIAS, ESTADOS, PRODUCTOS


def _familias_en():
    if not _FAMILIAS_EN:
        return _FAMILIAS_ES
    por_clave = {k: (n, d) for k, n, d in _FAMILIAS_EN}
    return [[k, *por_clave.get(k, (n, d))] for k, n, d in _FAMILIAS_ES]


def _productos_en():
    fusion = []
    for p in _PRODUCTOS_ES:
        capa = _PRODUCTOS_EN_POR_SLUG.get(p['slug'])
        fusion.append(_fusiona(p, capa) if capa else p)
    return fusion


_NAV_EN = [_fusiona(it, capa) for it, capa in
           zip(_NAV_ES, (_SITIO_EN.get('nav') or [{}] * len(_NAV_ES)))] if _SITIO_EN.get('nav') else _NAV_ES
_HOME_EN = _fusiona(_HOME_ES, _SITIO_EN.get('home'))
_CONTACTO_EN = _fusiona(_CONTACTO_ES, _SITIO_EN.get('contacto'))
_CTA_EN = _fusiona(_CTA_ES, _SITIO_EN.get('cta'))
_PREFOOTER_EN = _fusiona(_PREFOOTER_ES, _SITIO_EN.get('prefooter'))
_RHBOTS_EN = _fusiona(_RHBOTS_ES, _SITIO_EN.get('rhbots'))
_APLICACIONES_EN = _fusiona(_APLICACIONES_ES, _SITIO_EN.get('aplicaciones'))
_POSTS_EN = ([_fusiona(es, en) for es, en in zip(_POSTS_ES, _SITIO_EN['posts'])]
             if _SITIO_EN.get('posts') and len(_SITIO_EN['posts']) == len(_POSTS_ES) else _POSTS_ES)
_ESTADOS_EN_FUSION = _fusiona(_ESTADOS_ES, _ESTADOS_EN)
_PRODUCTOS_EN = _productos_en()
_FAM_NAME_EN = {k: n for k, n, _ in _familias_en()}


def set_lang(lang):
    """Intercambia todo el contenido module-level por el del idioma pedido.
    Los f-strings del resto del archivo leen estos nombres en tiempo de
    llamada, así que basta con reasignarlos antes de generar cada página."""
    global LANG, NAV, HOME, CONTACTO, CTA, PREFOOTER, POSTS, RHBOTS, APLICACIONES
    global FAMILIAS, ESTADOS, PRODUCTOS, BY_SLUG, FAM_NAME
    LANG = lang
    if lang == 'en':
        NAV, HOME, CONTACTO = _NAV_EN, _HOME_EN, _CONTACTO_EN
        CTA, PREFOOTER, POSTS = _CTA_EN, _PREFOOTER_EN, _POSTS_EN
        RHBOTS, APLICACIONES = _RHBOTS_EN, _APLICACIONES_EN
        FAMILIAS, ESTADOS, PRODUCTOS = _familias_en(), _ESTADOS_EN_FUSION, _PRODUCTOS_EN
    else:
        NAV, HOME, CONTACTO = _NAV_ES, _HOME_ES, _CONTACTO_ES
        CTA, PREFOOTER, POSTS = _CTA_ES, _PREFOOTER_ES, _POSTS_ES
        RHBOTS, APLICACIONES = _RHBOTS_ES, _APLICACIONES_ES
        FAMILIAS, ESTADOS, PRODUCTOS = _FAMILIAS_ES, _ESTADOS_ES, _PRODUCTOS_ES
    BY_SLUG = {p['slug']: p for p in PRODUCTOS}
    FAM_NAME = {k: n for k, n, _ in FAMILIAS}


# Todas las cadenas de interfaz que no vienen de datos/*.json (botones,
# rótulos de sección, aria-labels…). t('clave') da la del idioma activo.
TEXTOS = {
    'saltar_contenido': ('Saltar al contenido', 'Skip to content'),
    'ver_todo_catalogo': ('Ver todo el catálogo', 'View full catalog'),
    'nav_inicio': ('Inicio', 'Home'),
    'nav_robots': ('Robots', 'Robots'),
    'carrito_titulo': ('Tu carrito', 'Your cart'),
    'carrito_total': ('Total', 'Total'),
    'carrito_nota_envio': ('Los gastos de envío y los impuestos se calculan al finalizar la compra.',
                            'Shipping and taxes are calculated at checkout.'),
    'carrito_finalizar': ('Finalizar compra', 'Checkout'),
    'carrito_asesor': ('¿Prefieres que te asesoremos antes? Escríbenos',
                        'Prefer to talk to us first? Get in touch'),
    'carrito_vacio': ('Todavía no has añadido ningún robot.', "You haven't added any robots yet."),
    'carrito_ver_catalogo': ('Ver el catálogo', 'View the catalog'),
    'aviso_legal': ('Aviso Legal', 'Legal Notice'),
    'politica_privacidad': ('Política de Privacidad', 'Privacy Policy'),
    'politica_cookies': ('Política de Cookies', 'Cookie Policy'),
    'recursos_humanoides': ('Recursos Humanoides', 'Humanoid Resources'),
    'pide_info': ('Pide más información', 'Ask for more information'),
    'ver_especificaciones': ('Ver especificaciones', 'View specifications'),
    'que_es_pregunta': ('¿Qué es el {n}?', 'What is the {n}?'),
    'aplicaciones_de': ('Aplicaciones del {n}', 'Applications of the {n}'),
    'escenarios_encaja': ('Escenarios en los que encaja el {n}.', 'Scenarios where the {n} fits in.'),
    'specs_tecnicas_de': ('Especificaciones técnicas del {n}', 'Technical specifications of the {n}'),
    'ver_ficha_completa': ('Ver la ficha técnica completa', 'View the full technical sheet'),
    'galeria_de': ('Galería del {n}', 'Gallery of the {n}'),
    'fotos_anteriores': ('Fotos anteriores', 'Previous photos'),
    'fotos_siguientes': ('Fotos siguientes', 'Next photos'),
    'antes_de_ofertar': ('Antes de ofertar este modelo', 'Before quoting this model'),
    'doc_a_solicitar': ('Documentación a solicitar al fabricante.', 'Documentation to request from the manufacturer.'),
    'accesorios_para': ('Accesorios para el {n}', 'Accessories for the {n}'),
    'otros_modelos_familia': ('Otros modelos de la familia', 'Other models in the range'),
    'giralo': ('Gíralo', 'Spin it'),
    'vista_giratoria': ('{n} — vista giratoria. Usa las flechas para girarlo.',
                        '{n} — 360° view. Use the arrow keys to spin it.'),
    'navegador_sin_video': ('Tu navegador no puede reproducir este vídeo.',
                             "Your browser can't play this video."),
    'en_video': ('El {n} en vídeo', 'The {n} on video'),
    'sin_stock': ('Sin stock — consúltanos la disponibilidad', 'Out of stock — ask us about availability'),
    'avisame': ('Avísame cuando esté', 'Notify me when available'),
    'precio_consulta': ('Precio bajo consulta', 'Price on request'),
    'pedir_presupuesto': ('Pedir presupuesto', 'Request a quote'),
    'anadir_carrito': ('Añadir al carrito', 'Add to cart'),
    'comprar_ahora': ('Comprar ahora', 'Buy now'),
    'pvp': ('PVP', 'RRP'),
    'preguntas_frecuentes': ('Preguntas frecuentes', 'Frequently asked questions'),
    'distribuidores_oficiales': ('Distribuidores oficiales en España y Portugal',
                                 'Official distributors in Spain and Portugal'),
    'ver_robots': ('Ver los robots', 'View the robots'),
    'habla_nosotros': ('Habla con nosotros', 'Talk to us'),
    'ver_todos_modelos': ('Ver todos los modelos', 'View all models'),
    'modelos_disponibles': ('Modelos disponibles', 'Available models'),
    'modelos_anteriores': ('Modelos anteriores', 'Previous models'),
    'modelos_siguientes': ('Modelos siguientes', 'Next models'),
    'ver_modelo': ('Ver modelo', 'View model'),
    'no_sabes_robot_titulo': ('¿No sabes qué robot encaja mejor?', 'Not sure which robot fits best?'),
    'no_sabes_robot_texto': ('Cuéntanos tu proyecto y te ayudamos a seleccionar la familia, el modelo y la '
                              'configuración más adecuada para tu empresa o centro.',
                              'Tell us about your project and we\'ll help you choose the range, model and '
                              'configuration that best suits your company or centre.'),
    'hablar_rhbots': ('Hablar con RH·BOTS', 'Talk to RH·BOTS'),
    'catalogo_kicker': ('Catálogo RH·BOTS', 'RH·BOTS Catalog'),
    'catalogo_h1': ('Robots para empresas que quieren ir un paso por delante',
                     'Robots for businesses that want to stay one step ahead'),
    'catalogo_lede': ('Humanoides, cuadrúpedos, robots de limpieza, AMR de intralogística y '
                       'accesorios para automatizar tareas, mejorar procesos y llevar la robótica avanzada a entornos '
                       'reales. {n} modelos con ficha técnica completa y acompañamiento de principio a fin.',
                       'Humanoid, quadruped and cleaning robots, intralogistics AMRs and accessories '
                       'to automate tasks, improve processes and bring advanced robotics to real environments. '
                       '{n} models with a full technical sheet and support from start to finish.'),
    'solicitar_asesoramiento': ('Solicitar asesoramiento', 'Request advice'),
    'ver_ficha_tecnica': ('Ver ficha técnica', 'View technical sheet'),
    'robots_para_uso': ('Robots para este uso', 'Robots for this use'),
    'cuentanos_tu_caso': ('Cuéntanos tu caso', 'Tell us about your case'),
    'tienes_tarea_titulo': ('¿Tienes una tarea que quieres automatizar?',
                             'Have a task you want to automate?'),
    'tienes_tarea_texto': ('Cuéntanos tu caso y te orientamos sobre qué aplicación robótica puede encajar '
                            'mejor en tu empresa.',
                            'Tell us about your case and we\'ll advise you on which robotic application '
                            'could best fit your business.'),
    'blog_kicker': ('RH·BOTS — Blog', 'RH·BOTS — Blog'),
    'blog_h1': ('Actualidad sobre <span class="acento">robótica humanoide</span>',
                'News on <span class="acento">humanoid robotics</span>'),
    'blog_lede': ('Noticias, casos de uso y recursos para entender cómo los robots humanoides '
                   'pueden integrarse en empresas reales de forma segura, útil y medible.',
                   'News, use cases and resources to understand how humanoid robots can be '
                   'integrated into real businesses safely, usefully and measurably.'),
    'ver_articulos': ('Ver artículos', 'View articles'),
    'hablar_experto': ('Hablar con un experto', 'Talk to an expert'),
    'destacado': ('Destacado', 'Featured'),
    'min_lectura': ('min de lectura', 'min read'),
    'leer_articulo': ('Leer artículo', 'Read article'),
    'leer_mas': ('Leer más', 'Read more'),
    'conocimiento_aplicado': ('Conocimiento aplicado', 'Applied knowledge'),
    'ideas_claras': ('Ideas claras para tomar mejores decisiones', 'Clear ideas for better decisions'),
    'buscar_articulos': ('Buscar artículos', 'Search articles'),
    'buscar_articulos_placeholder': ('Buscar artículos…', 'Search articles…'),
    'buscar': ('Buscar', 'Search'),
    'ultimos_articulos': ('Últimos artículos', 'Latest articles'),
    'recursos_presente': ('Recursos para entender el presente de la robótica',
                           'Resources to understand robotics today'),
    'todos': ('Todos', 'All'),
    'sin_resultados_busqueda': ('No hay artículos que coincidan con tu búsqueda.',
                                 'No articles match your search.'),
    'preparando_articulos': ('Estamos preparando los primeros artículos', 'We are preparing our first articles'),
    'preparando_articulos_texto': ('Aquí publicaremos novedades de producto, casos de uso de nuestros clientes y notas '
                                    'técnicas sobre los modelos del catálogo. Mientras tanto, puedes consultar las fichas '
                                    'técnicas o escribirnos directamente.',
                                    "We'll publish product news, customer use cases and technical notes about our "
                                    'catalog here. In the meantime, you can check the technical sheets or write to us directly.'),
    'escribenos': ('Escríbenos', 'Get in touch'),
    'necesitas_orientacion': ('¿Necesitas orientación?', 'Need guidance?'),
    'orienta_titulo': ('Te ayudamos a entender qué robot <span class="acento">encaja con tu empresa</span>',
                        'We help you understand which robot <span class="acento">fits your business</span>'),
    'orienta_texto': ('Cuéntanos tu caso y nuestro equipo te asesorará sobre modelos, aplicaciones y '
                       'próximos pasos.',
                       "Tell us about your case and our team will advise you on models, applications and next steps."),
    'solicitar_informacion': ('Solicitar información', 'Request information'),
    'volver_blog': ('← Volver al blog', '← Back to blog'),
    'pagina_404_titulo': ('Esta página no existe', "This page doesn't exist"),
    'pagina_404_texto': ('Puede que el enlace esté mal escrito o que hayamos movido el contenido. '
                          'Desde aquí llegas a todo:',
                          "The link may be mistyped, or we may have moved the content. "
                          "You can get anywhere from here:"),
    'ir_inicio': ('Ir al inicio', 'Go to homepage'),
    'formulario': ('Formulario', 'Form'),
    'solicita_info': ('Solicita información', 'Request information'),
    'respuesta_personalizada': ('Respuesta personalizada', 'Personalised reply'),
    'nombre': ('Nombre', 'First name'),
    'apellidos': ('Apellidos', 'Last name'),
    'tu_nombre': ('Tu nombre', 'Your first name'),
    'tus_apellidos': ('Tus apellidos', 'Your last name'),
    'email': ('Email', 'Email'),
    'telefono': ('Teléfono', 'Phone'),
    'empresa_campo': ('Empresa', 'Company'),
    'nombre_empresa_placeholder': ('Nombre de tu empresa', 'Your company name'),
    'que_robot_interesa': ('¿En qué robot estás interesado?', 'Which robot are you interested in?'),
    'selecciona_modelo': ('Selecciona un modelo', 'Select a model'),
    'aun_no_lo_se': ('Aún no lo sé', "I don't know yet"),
    'como_ayudarte': ('¿Cómo podemos ayudarte?', 'How can we help you?'),
    'mensaje_placeholder': ('Cuéntanos brevemente tu proyecto, necesidad o tipo de evento…',
                             'Briefly tell us about your project, need or type of event…'),
    'consiento_privacidad': ('He leído y acepto la', 'I have read and accept the'),
    'politica_privacidad_link': ('política de privacidad', 'privacy policy'),
    'consiento_privacidad_fin': ('. Consiento el tratamiento de mis datos para recibir información comercial de RH·BOTS.',
                                  '. I consent to the processing of my data to receive commercial information from RH·BOTS.'),
    'enviar_mensaje': ('Enviar mensaje', 'Send message'),
    'solicitar_asesoramiento_cta': ('Solicitar asesoramiento', 'Request advice'),
    'escribir_email': ('Escribir por email', 'Write by email'),
    'email_directo_etq': ('Email directo', 'Direct email'),
    'especialistas_en': ('Especialistas en', 'Specialists in'),
    'donde_estamos': ('Dónde estamos', 'Where we are'),
    'llamanos_al': ('También puedes llamarnos al', 'You can also call us on'),
    'escribenos_directamente': ('También puedes escribirnos directamente a', 'You can also write to us directly at'),
    'aviso_legal_titulo': ('Aviso legal, privacidad y cookies', 'Legal notice, privacy and cookies'),
    'pagina_no_encontrada': ('Página no encontrada | RH·BOTS', 'Page not found | RH·BOTS'),
    'pagina_no_encontrada_desc': ('La página que buscas no existe o ha cambiado de sitio.',
                                   "The page you're looking for doesn't exist or has moved."),
    'contacto_titulo': ('Contacto | RH·BOTS', 'Contact | RH·BOTS'),
    'blog_titulo': ('Blog | RH·BOTS', 'Blog | RH·BOTS'),
    'blog_desc': ('Novedades, casos de uso y notas técnicas sobre robótica de servicio e industrial.',
                   'News, use cases and technical notes on service and industrial robotics.'),
    'aplicaciones_titulo': ('Aplicaciones de los robots RH·BOTS por sector | RH·BOTS',
                             'RH·BOTS robots by sector | RH·BOTS'),
    'robots_catalogo_titulo': ('Robots RH·BOTS — catálogo completo | RH·BOTS',
                                'RH·BOTS Robots — full catalog | RH·BOTS'),
    'robots_catalogo_desc': ('Catálogo RH·BOTS: robots humanoides, cuadrúpedos, de limpieza y AMR de '
                              'intralogística, y accesorios, con fichas técnicas completas.',
                              'RH·BOTS catalog: humanoid, quadruped and cleaning robots, intralogistics AMRs '
                              'and accessories, with full technical sheets.'),
    'inicio_titulo': ('RH·BOTS — Recursos humanoides para tu empresa', 'RH·BOTS — Humanoid resources for your business'),
    'inicio_desc': ('Robots humanoides, cuadrúpedos, de limpieza y de intralogística. Asesoramiento, instalación, '
                     'formación y soporte en Valencia.',
                     'Humanoid, quadruped, cleaning and intralogistics robots. Advice, installation, '
                     'training and support from Valencia, Spain.'),
    'legal_meta_titulo': ('Aviso legal, privacidad y cookies | RH·BOTS', 'Legal notice, privacy and cookies | RH·BOTS'),
    'legal_meta_desc': ('Aviso legal, política de privacidad y cookies de RH·BOTS.',
                         "RH·BOTS's legal notice, privacy policy and cookie policy."),
    'blog_articulo_sufijo': (' | Blog RH·BOTS', ' | RH·BOTS Blog'),
    'lang_switch_es': ('Español', 'Spanish'),
    'lang_switch_en': ('English', 'English'),
}


def t(clave, **kw):
    es, en = TEXTOS[clave]
    txt = en if LANG == 'en' else es
    return txt.format(**kw) if kw else txt


FAM_NAME = {k: n for k, n, _ in FAMILIAS}
FECHA_BUILD = time.strftime('%Y-%m-%d')
LINKEDIN_EMPRESA = 'https://www.linkedin.com/company/rh-bots'
INSTAGRAM_EMPRESA = 'https://www.instagram.com/rhbots/'

# marcas de las que somos distribuidores oficiales (logos en assets/marcas/)
MARCAS = [('AGIBOT', 'assets/marcas/agibot.webp', 560, 95),
          ('PUDU', 'assets/marcas/pudu.webp', 560, 148)]


def logos_marcas(base, clase):
    return ''.join(
        f'<li class="{clase}"><img src="{base}{src}" alt="Logotipo de {nombre}" '
        f'width="{w}" height="{h}" loading="lazy" decoding="async"></li>'
        for nombre, src, w, h in MARCAS)


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
        'description': (
            'Official distributor of AGIBOT and PUDU in Spain and Portugal: autonomous cleaning, '
            'humanoid and quadruped robots, intralogistics AMRs and accessories, with advice, installation, '
            'training and maintenance.' if LANG == 'en' else
            'Distribuidor oficial de AGIBOT y PUDU en España y Portugal: robots de limpieza '
            'autónoma, humanoides, cuadrúpedos, AMR de intralogística y accesorios, con asesoramiento, instalación, '
            'formación y mantenimiento.'),
        'inLanguage': LANG,
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
        'brand': {'@type': 'Brand', 'name': (p.get('base') or 'AGIBOT').split()[0]},
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
    try:
        pvp = float(p.get('precio') or 0)
    except (TypeError, ValueError):
        pvp = 0
    if pvp > 0:
        data['offers'] = {
            '@type': 'Offer',
            'url': url,
            'priceCurrency': 'EUR',
            'price': f'{pvp:.2f}',
            'availability': 'https://schema.org/InStock',
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


_COLGANDO = {'de', 'del', 'a', 'al', 'con', 'para', 'por', 'en', 'y', 'o', 'sin',
             'sobre', 'el', 'la', 'los', 'las', 'un', 'una', 'que', 'su', 'sus'}


def _recorta(texto, limite, puntos=True):
    """Recorta por palabras, sin dejar la frase colgando de una preposición."""
    texto = texto.strip()
    if len(texto) <= limite:
        return texto
    palabras = texto[:limite].split(' ')[:-1]
    while palabras and (palabras[-1].lower().strip(',.;:') in _COLGANDO
                        or palabras[-1].strip(',.;:').replace('.', '').isdigit()):
        palabras.pop()
    corte = ' '.join(palabras).rstrip(' ,.;:·—-')
    return corte + ('…' if puntos else '')


def titulo_seo(title, limite=60):
    """Google enseña unos 60 caracteres del título.

    Los títulos de ficha son «MODELO · qué es | RH·BOTS»: si no caben, se
    acorta primero la descripción del medio y, si aún sobra, se quita
    entera. La marca del final y el nombre del modelo no se tocan.
    """
    if len(title) <= limite:
        return title
    # la marca es lo que va detrás de la última barra: no se toca
    if ' | ' in title:
        cuerpo, marca = title.rsplit(' | ', 1)
        sufijo = ' | ' + marca
    else:
        cuerpo, sufijo = title, ''
    hueco = limite - len(sufijo)
    if ' · ' in cuerpo:
        nombre, claim = cuerpo.split(' · ', 1)
        if len(nombre) + 3 + 12 <= hueco:      # cabe el nombre y algo de claim
            cuerpo = nombre + ' · ' + _recorta(claim, hueco - len(nombre) - 3, puntos=False)
        else:
            cuerpo = _recorta(nombre, hueco, puntos=False)
    else:
        cuerpo = _recorta(cuerpo, hueco)
    return cuerpo + sufijo


def head(title, desc, base, ruta='', extra_css=True, og_img=None, extra_jsonld=None):
    # los buscadores cortan a unos 60 y 160 caracteres: mejor cortar nosotros
    title = titulo_seo(title)
    desc = _recorta(desc, 158)
    dominio = SEO['dominio'].rstrip('/')
    limpia = '' if ruta == 'index.html' else ruta
    canonical = f'{dominio}/{"en/" if LANG == "en" else ""}{limpia}' if limpia else f'{dominio}/{"en/" if LANG == "en" else ""}'
    alterno_es = f'{dominio}/{limpia}' if limpia else dominio + '/'
    alterno_en = f'{dominio}/en/{limpia}' if limpia else f'{dominio}/en/'
    hreflang = (f'<link rel="alternate" hreflang="es" href="{e(alterno_es)}">\n'
               f'<link rel="alternate" hreflang="en" href="{e(alterno_en)}">\n'
               f'<link rel="alternate" hreflang="x-default" href="{e(alterno_es)}">\n')
    imagen = f'{dominio}/{og_img or SEO["og_imagen"]}'
    tw = (f'<meta name="twitter:site" content="{e(SEO["twitter"])}">\n'
          if SEO.get('twitter') else '')
    return f'''<!DOCTYPE html>
<html lang="{LANG}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
{hreflang}<meta name="theme-color" content="#009ee3">
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
<a class="skip-link" href="#contenido">{t('saltar_contenido')}</a>
'''


_SVG_TRAZO = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
              'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">')
ICONO_CARRITO = (_SVG_TRAZO + '<path d="M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h7.4a2 2 0 0 0 2-1.5L20.5 8H6"/>'
                 '<circle cx="10" cy="20" r="1.3"/><circle cx="17" cy="20" r="1.3"/></svg>')


def boton_carrito(base):
    """Acceso al carrito en la cabecera. Solo si la tienda está activa."""
    if not TIENDA.get('activa'):
        return ''
    return (f'<button class="carrito-abrir" type="button" data-carrito-abrir '
            f'aria-label="Abrir el carrito" aria-controls="carrito" aria-expanded="false">'
            f'{ICONO_CARRITO}<span class="carrito-abrir__num" data-carrito-num hidden>0</span>'
            f'</button>')


def panel_carrito(base):
    """Carrito lateral.

    El carrito vive en el navegador (localStorage) y al finalizar se traduce
    en un «cart permalink» de Shopify con todas las líneas, así que el cobro,
    el stock y los impuestos los sigue llevando Shopify. No hace falta ninguna
    clave de API ni que el visitante tenga sesión abierta en la tienda.
    """
    if not TIENDA.get('activa'):
        return ''
    dominio = TIENDA['dominio'].strip('/')
    return f'''
<div class="carrito" id="carrito" data-carrito data-dominio="{e(dominio)}" data-robots="{base}robots.html" hidden>
  <div class="carrito__fondo" data-carrito-cerrar></div>
  <aside class="carrito__panel" role="dialog" aria-modal="true" aria-label="Carrito">
    <header class="carrito__cab">
      <h2 class="carrito__titulo onblue" data-punto="manual">{t('carrito_titulo')}</h2>
      <button class="carrito__cerrar" type="button" data-carrito-cerrar aria-label="Cerrar el carrito">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
      </button>
    </header>
    <div class="carrito__cuerpo" data-carrito-lista></div>
    <footer class="carrito__pie" data-carrito-pie hidden>
      <p class="carrito__total"><span>{t('carrito_total')}</span><strong data-carrito-total></strong></p>
      <p class="carrito__nota">{t('carrito_nota_envio')}</p>
      <a class="pill carrito__pagar" data-carrito-pagar rel="nofollow noopener" href="#"><span>{t('carrito_finalizar')}</span>{CHEVRON}</a>
      <a class="carrito__consulta" href="{base}contacto.html">{t('carrito_asesor')}</a>
    </footer>
  </aside>
</div>
'''


BANDERA_ES = ('<svg viewBox="0 0 3 2" aria-hidden="true"><rect width="3" height="2" fill="#c60b1e"/>'
              '<rect y=".5" width="3" height="1" fill="#ffc400"/></svg>')
BANDERA_EN = ('<svg viewBox="0 0 60 30" aria-hidden="true"><clipPath id="s"><rect width="60" height="30" rx="0"/></clipPath>'
              '<g clip-path="url(#s)"><rect width="60" height="30" fill="#012169"/>'
              '<path d="M0 0 60 30M60 0 0 30" stroke="#fff" stroke-width="6"/>'
              '<path d="M0 0 60 30M60 0 0 30" stroke="#C8102E" stroke-width="2"/>'
              '<path d="M30 0v30M0 15h60" stroke="#fff" stroke-width="10"/>'
              '<path d="M30 0v30M0 15h60" stroke="#C8102E" stroke-width="6"/></g></svg>')


def selector_idioma(ruta):
    """Banderas ES/EN en la cabecera. «ruta» es la de la página actual
    (p.ej. 'robots/rhx2.html', o '' para portada), igual en los dos idiomas:
    solo cambia si lleva o no el prefijo /en/ por delante."""
    limpia = '' if ruta in ('', 'index.html') else ruta
    activo_es = ' is-on' if LANG == 'es' else ''
    activo_en = ' is-on' if LANG == 'en' else ''
    return (f'<div class="lang-switch" role="group" aria-label="Idioma / Language">'
            f'<a href="/{e(limpia)}" hreflang="es" lang="es" class="lang-switch__op{activo_es}" '
            f'aria-current="{"true" if LANG == "es" else "false"}" aria-label="{t("lang_switch_es")}">{BANDERA_ES}</a>'
            f'<a href="/en/{e(limpia)}" hreflang="en" lang="en" class="lang-switch__op{activo_en}" '
            f'aria-current="{"true" if LANG == "en" else "false"}" aria-label="{t("lang_switch_en")}">{BANDERA_EN}</a>'
            f'</div>')


def header(base, active='robots', ruta=''):
    parts = []
    for it in NAV:
        if it.get('oculto'):
            continue
        cls = ' class="is-active"' if it['key'] and it['key'] == active else ''
        enlace = '<a href="%s%s"%s>%s</a>' % (base, it['href'], cls, e(it['label']))
        if it['key'] == 'robots':
            # submenú: familias a la izquierda y fichas de los modelos a la derecha
            familias, paneles = '', ''
            primera = True
            for k, n, _ in FAMILIAS:
                modelos = [q for q in PRODUCTOS if q['family'] == k]
                if not modelos:
                    continue
                on = ' is-on' if primera else ''
                familias += (f'<li><a class="nav__fam{on}" href="{base}robots.html#{k}" '
                             f'data-fam="{k}">{e(n)}<span class="nav__famchev" aria-hidden="true">'
                             f'<svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg></span></a></li>')
                tarjetas = ''
                for q in modelos:
                    foto = (f'<img src="{base}{q["hero"]}" alt="" loading="lazy">' if q.get('hero')
                            else '')
                    tarjetas += (f'<li><a class="mcard" href="{base}robots/{q["slug"]}.html">'
                                 f'<span class="mcard__foto">{foto}</span>'
                                 f'<span class="mcard__nombre">{e(q["name"])}</span>'
                                 f'<span class="mcard__claim">{e(q["claim"])}</span></a></li>')
                # el título solo se ve en el menú del móvil, donde no hay columna de familias
                paneles += (f'<ul class="nav__modelos{on}" data-fam="{k}" '
                            f'aria-label="Modelos de {e(n)}">'
                            f'<li class="nav__modtit"><a href="{base}robots.html#{k}">{e(n)}</a></li>'
                            f'{tarjetas}</ul>')
                primera = False
            enlace = (f'<div class="nav__grupo">{enlace}'
                      f'<button type="button" class="nav__abrir" aria-expanded="false" '
                      f'aria-controls="sub-robots" aria-label="Ver familias y modelos de robots">'
                      f'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>'
                      f'<div class="nav__sub nav__sub--mega" id="sub-robots" data-menurobots>'
                      f'<ul class="nav__fams">{familias}</ul>'
                      f'<div class="nav__paneles">{paneles}'
                      f'<p class="nav__todos"><a href="{base}robots.html">'
                      f'{t("ver_todo_catalogo")}{FLECHA}</a></p></div>'
                      f'</div></div>')
        parts.append(enlace)
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
    {selector_idioma(ruta)}
    {boton_carrito(base)}
    <button class="nav-toggle" id="navToggle" aria-label="Abrir menú" aria-expanded="false" aria-controls="nav">
      <span></span><span></span><span></span>
    </button>
  </div>
</header>
{panel_carrito(base)}
'''


# iconos de marca en cuadrado índigo con el glifo en blanco (franja «Síguenos»)
# iconos de la página de contacto (trazo, heredan el color del texto)
_SVG = _SVG_TRAZO
ICONO_SOBRE = _SVG + '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>'
ICONO_TEL = _SVG + ('<path d="M6 3h3l2 5-2.5 1.5a12 12 0 0 0 6 6L16 13l5 2v3a2 2 0 0 1-2.2 2'
                    'A17 17 0 0 1 4 5.2 2 2 0 0 1 6 3z"/></svg>')
ICONO_ROBOT = _SVG + ('<rect x="4" y="8" width="16" height="11" rx="3"/><path d="M12 4v4"/>'
                      '<circle cx="9" cy="13" r="1"/><circle cx="15" cy="13" r="1"/></svg>')
ICONO_PIN = _SVG + '<path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>'


def tel_href(t):
    """«(+34) 680 40 41 41» → «+34680404141»."""
    return '+' + re.sub(r'\D', '', t) if '+' in t else re.sub(r'\D', '', t)


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
      <img src="{base}assets/logo-rhbots-vertical.webp" alt="RH·BOTS — {t('recursos_humanoides')}"
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
    <p class="footer-marca">© {time.strftime('%Y')} RH-BOTS<br>{t('recursos_humanoides')}.</p>
    <p class="footer-legal">
      <a href="{base}legal.html">{t('aviso_legal')}</a> ·
      <a href="{base}legal.html#privacidad">{t('politica_privacidad')}</a> ·
      <a href="{base}legal.html#cookies">{t('politica_cookies')}</a>
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
_ETIQUETA_FAMILIA = {
    'es': {
        'limpieza': 'Limpieza autónoma', 'humanoides': 'Robot humanoide',
        'cuadrupedos': 'Robot cuadrúpedo', 'amr': 'AMR intralogística', 'accesorios': 'Accesorio',
    },
    'en': {
        'limpieza': 'Cleaning robot', 'humanoides': 'Humanoid robot',
        'cuadrupedos': 'Quadruped robot', 'amr': 'AMR', 'accesorios': 'Accessory',
    },
}


class _EtiquetaFamilia:
    """dict-like que siempre lee la tabla del idioma activo."""
    def get(self, clave, defecto=''):
        return _ETIQUETA_FAMILIA[LANG].get(clave, defecto)


ETIQUETA_FAMILIA = _EtiquetaFamilia()


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
    """100000.0 → «100.000,00» en español (miles con punto, decimales con coma)
    o «100,000.00» en inglés (al revés), según el idioma activo."""
    entero, _, dec = f'{valor:,.2f}'.partition('.')
    if LANG == 'en':
        return entero + '.' + dec
    return entero.replace(',', '.') + ',' + dec


def formato_pvp(valor):
    """'19900' → «19.900 €»; conserva los céntimos solo si los hay."""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return ''
    if v <= 0:
        return ''
    txt = formato_precio(v)
    if txt.endswith(',00'):
        txt = txt[:-3]
    return f'{txt} €'


def precio_html(p, clase='pvp'):
    """Precio de venta al público de la tarifa RH·BOTS."""
    pvp = formato_pvp(p.get('precio'))
    if not pvp:
        return ''
    return f'<p class="{clase}"><span class="{clase}__etiqueta">{t("pvp")}</span> {pvp}</p>'


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
    etiqueta = t('comprar_ahora') if LANG == 'en' else (TIENDA.get('texto_boton') or t('comprar_ahora'))
    contacto = base + 'contacto.html'

    try:
        precio = float(sh.get('precio') or 0)
    except (TypeError, ValueError):
        precio = 0
    if sh.get('disponible') and precio <= 0:
        AVISOS_TIENDA.append(f'{p["name"]}: precio {sh.get("precio")!r} — sin botón de compra')

    # Estado del último build. Se ve al instante y es lo que indexa Google;
    # el JS lo reemplaza con el estado en vivo de Shopify en cuanto responde.
    mostrar = TIENDA.get('mostrar_precio') and not p.get('precio')
    interior = estado_compra(
        disponible=bool(sh.get('disponible')), precio=precio,
        moneda=sh.get('moneda', ''), variante=sh['variante'],
        dominio=dominio, etiqueta=etiqueta, contacto=contacto, mostrar_precio=mostrar)

    return (f'<div class="compra" data-tienda '
            f'data-dominio="{e(dominio)}" data-handle="{e(sh.get("handle", ""))}" '
            f'data-variante="{e(sh["variante"])}" data-contacto="{e(contacto)}" '
            f'data-texto="{e(etiqueta)}" '
            f'data-nombre="{e(p["name"])}" '
            f'data-foto="{e(base + p["hero"]) if p.get("hero") else ""}" '
            f'data-url="{e(base + "robots/" + p["slug"] + ".html")}" '
            f'data-moneda="{e(sh.get("moneda", TIENDA.get("moneda", "EUR")))}" '
            f'data-precio="{"1" if mostrar else "0"}">'
            f'{interior}</div>')


def tarjeta_compra(p, base):
    """Precio y botón de compra, juntos bajo la imagen del robot."""
    precio = precio_html(p)
    boton = boton_compra(p, base)
    if not precio and not boton:
        return ''
    solo = '' if boton else ' phero__compra--solo'
    return f'<div class="phero__compra{solo}">{precio}{boton}</div>'


def estado_compra(disponible, precio, moneda, variante, dominio, etiqueta, contacto,
                  mostrar_precio=True):
    """Los tres estados posibles del bloque de compra."""
    if not disponible:
        return (f'<p class="sinstock"><span class="sinstock__punto" aria-hidden="true"></span>'
                f'{t("sin_stock")}</p>'
                f'<a class="pill pill--line" href="{contacto}">'
                f'<span>{t("avisame")}</span>{CHEVRON}</a>')

    if precio <= 0:
        return (f'<p class="sinstock"><span class="sinstock__punto" aria-hidden="true"></span>'
                f'{t("precio_consulta")}</p>'
                f'<a class="pill pill--line" href="{contacto}">'
                f'<span>{t("pedir_presupuesto")}</span>{CHEVRON}</a>')

    # Sin ?channel=buy_button: ese parámetro exige tener instalado el canal de
    # ventas "Buy Button" en la tienda. Esta tienda no lo tiene, y Shopify
    # rechazaba el checkout con «Parameter Missing or Invalid: channel».
    # El cart permalink funciona igual de bien sin el parámetro.
    url = f'https://{dominio}/cart/{variante}:1'
    precio_html = ''
    if mostrar_precio and TIENDA.get('mostrar_precio'):
        precio_html = (f'<p class="precio">{e(formato_precio(precio))} '
                       f'<span>{e(formato_moneda(moneda))}</span></p>')
    anadir = (f'<button class="pill pill--anadir" type="button" data-anadir '
              f'data-variante="{e(str(variante))}" data-precio-num="{precio:.2f}">'
              f'<span>{t("anadir_carrito")}</span>'
              f'<i class="pill__ico pill__ico--carro" aria-hidden="true">{ICONO_CARRITO}</i></button>')
    return (f'{precio_html}<a class="pill pill--comprar" href="{e(url)}" '
            f'rel="nofollow noopener"><span>{e(etiqueta)}</span>{CHEVRON}</a>{anadir}')


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
            f'poster="{base}assets/video/{nombre}.webp">'
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


# Qué se enseña en la rejilla corta de especificaciones, por orden. La ficha
# completa sigue debajo, desplegable: aquí solo van los datos que alguien mira
# antes de decidir si el robot le encaja.
CLAVES_SPECS = [
    'altura', 'peso neto', 'peso', 'dimensiones de pie', 'velocidad máxima',
    'velocidad', 'autonomía', 'batería', 'tiempo de carga', 'carga máxima',
    'carga útil', 'rendimiento', 'anchura de trabajo', 'anchura de fregado',
    'depósito', 'grados de libertad', 'par máximo', 'fuerza de agarre',
    'repetibilidad', 'resolución', 'alcance', 'visión', 'sensor de movimiento',
    'navegación', 'unidad de control', 'unidad de computación', 'pendiente',
    'franqueo de obstáculos', 'protección', 'conectividad', 'garantía',
]
MAX_SPECS_DESTACADAS = 15     # tres filas de cinco


def _valor_corto(v, largo):
    """Valor en versión resumida: el detalle completo queda en la tabla."""
    v = v.split(' · ')[0].strip()
    if len(v) > largo:
        v = v.split(', ')[0].strip()
    if len(v) > largo:
        v = v.split(' (')[0].strip()
    return v if len(v) <= largo else ''


def specs_destacadas(p, maximo=MAX_SPECS_DESTACADAS, largo=44):
    """Las filas más útiles de la ficha, una por concepto y sin repetir."""
    filas = [(l, v) for _, rows in p['specs'] for l, v in rows]
    elegidas, etiquetas, conceptos = [], set(), set()
    for clave in CLAVES_SPECS:
        if clave in conceptos or len(elegidas) >= maximo:
            continue
        for l, v in filas:
            bajo = l.lower()
            if bajo in etiquetas or not bajo.startswith(clave) and clave not in bajo:
                continue
            corto = _valor_corto(v, largo)
            if not corto:
                continue
            elegidas.append((l, corto))
            etiquetas.add(bajo)
            # ese concepto ya está cubierto: nada de «Peso neto» y «Peso con embalaje»
            conceptos.update(c for c in CLAVES_SPECS if c in bajo or bajo.startswith(c))
            break
    # si el producto trae pocas coincidencias, se completa por orden
    for l, v in filas:
        if len(elegidas) >= maximo:
            break
        bajo = l.lower()
        corto = _valor_corto(v, largo)
        if bajo in etiquetas or not corto:
            continue
        if any(c in bajo for c in conceptos):     # ese concepto ya está puesto
            continue
        elegidas.append((l, corto))
        etiquetas.add(bajo)
        conceptos.update(c for c in CLAVES_SPECS if c in bajo)
    return elegidas[:maximo]


# ─────────────────────────────────────────────────────────── ficha (x14) ──
def product_page(p):
    base = NIVEL[LANG] + '../'
    fam = p['family']
    dominio = SEO['dominio'].rstrip('/')
    # si el claim entero no cabe en los ~60 caracteres que enseña Google,
    # es más limpio poner la familia que dejar la frase a medias
    title = f'{p["name"]} · {p["claim"]} | RH·BOTS'
    if len(title) > 60:
        corto = f'{p["name"]} · {ETIQUETA_FAMILIA.get(fam, FAM_NAME[fam])} | RH·BOTS'
        if len(corto) <= 60:
            title = corto
    _pfijo = f'{dominio}/en' if LANG == 'en' else dominio
    breadcrumb = schema_breadcrumb([
        (t('nav_inicio'), _pfijo + '/'),
        (t('nav_robots'), _pfijo + '/robots.html'),
        (p['name'], None),
    ])
    ruta_pagina = f'robots/{p["slug"]}.html'
    out = [head(title, p['tagline'], base, ruta_pagina,
                og_img=p.get('hero'),
                extra_jsonld=[schema_product(p), breadcrumb]),
           header(base, 'robots', ruta_pagina), '<main id="contenido">']

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
             aria-label="{e(t('vista_giratoria', n=p['name']))}"
             data-frames="{len(frames)}">
          {capas}
          <span class="viewer__hint" aria-hidden="true">
            <svg viewBox="0 0 24 24"><path d="M9 7L5 12l4 5M15 7l4 5-4 5"/></svg>
            {t('giralo')}
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
        <div class="badges">{badges(p)}</div>
        <h1 class="phero__name" data-punto="manual">{con_punto(e(p['name']))} <span class="phero__claim">{e(p['claim'])}</span></h1>
        <p class="phero__tag">{e(p['tagline'])}</p>
        <div class="phero__cta">
          <a class="pill" href="{base}contacto.html"><span>{t('pide_info')}</span>
            <i class="pill__ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg></i></a>
          <a class="pill pill--line" href="#especificaciones"><span>{t('ver_especificaciones')}</span>
            <i class="pill__ico" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg></i></a>
        </div>
        {facts}
      </div>
      <div class="phero__lado">
        <figure class="phero__media">{media}</figure>
        {tarjeta_compra(p, base)}
      </div>
    </div>
  </section>
''')

    # Los avisos («notes») son notas internas para preparar ofertas: se guardan
    # en productos.json y se ven en el panel, pero no se publican en la ficha.

    # ---- intro + highlights
    out.append('  <section class="section section--white" id="que-hace">\n    <div class="wrap">\n')
    solo = '' if p['highlights'] else ' section-head--solo'
    out.append(f'      <header class="section-head{solo} reveal"><h2 class="h-section h-section--blue">'
               f'{e(t("que_es_pregunta", n=p["name"]))}</h2>'
               f'<p class="sub">{e(p["intro"])}</p></header>\n')
    if p['highlights']:
        out.append('      <ul class="hl">\n')
        for tit, d in p['highlights']:
            out.append(f'        <li class="hl__item reveal"><h3>{e(tit)}</h3><p>{e(d)}</p></li>\n')
        out.append('      </ul>\n')
    out.append('    </div>\n  </section>\n')

    # ---- vídeo
    out.append(video_html(p.get('videos'), base,
                          t('en_video', n=p['name']) if p.get('videos') else ''))

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
      <header class="section-head reveal"><h2 class="h-section">{e(t('aplicaciones_de', n=p['name']))}</h2>
        <p class="sub">{e(t('escenarios_encaja', n=p['name']))}</p></header>
      {lista}
    </div>
  </section>
''')

    # ---- especificaciones: primero las 15 clave, y debajo la ficha completa
    destacadas = ''.join(
        f'<li class="dato-tec"><p class="dato-tec__etiqueta">{e(l)}</p>'
        f'<p class="dato-tec__valor">{e(v)}</p></li>'
        for l, v in specs_destacadas(p))
    groups = ''
    for gtitle, rows in p['specs']:
        trs = ''.join(f'<tr><th scope="row">{e(l)}</th><td>{e(v)}</td></tr>' for l, v in rows)
        groups += (f'<div class="specgrp"><h3>{e(gtitle)}</h3>'
                   f'<table class="spectable"><tbody>{trs}</tbody></table></div>\n')
    out.append(f'''  <section class="section section--white" id="especificaciones">
    <div class="wrap">
      <header class="section-head reveal"><h2 class="h-section h-section--blue">{e(t('specs_tecnicas_de', n=p['name']))}</h2></header>
      <ul class="datos-tec reveal">{destacadas}</ul>
      <details class="fichacompleta reveal">
        <summary>{t('ver_ficha_completa')}</summary>
        <div class="specgrid">{groups}</div>
      </details>
    </div>
  </section>
''')

    # ---- galería
    if p.get('gallery'):
        figs = ''.join(
            f'<li class="gal__item">'
            f'<img src="{base}{img}" alt="{e(tit)}" loading="lazy" draggable="false"{img_dims_attr(img)}>'
            f'</li>\n'
            for tit, img in p['gallery'])
        out.append(f'''  <section class="section section--white galoop" id="galeria">
    <div class="wrap">
      <header class="section-head reveal"><h2 class="h-section">{e(t('galeria_de', n=p['name']))}</h2></header>
      <div class="carrusel carrusel--gal reveal" data-carrusel>
        <ul class="carrusel__pista gal" tabindex="0" aria-label="{e(t('galeria_de', n=p['name']))}">{figs}</ul>
        <button type="button" class="carrusel__btn carrusel__btn--prev" aria-label="{t('fotos_anteriores')}">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6"/></svg></button>
        <button type="button" class="carrusel__btn carrusel__btn--next" aria-label="{t('fotos_siguientes')}">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button>
      </div>
    </div>
  </section>
''')

    # ---- checklist de compra (fichas provisionales)
    if p.get('checklist'):
        lis = ''.join(f'<li>{e(x)}</li>' for x in p['checklist'])
        out.append(f'''  <section class="section section--light" id="checklist">
    <div class="wrap wrap--narrow">
      <header class="section-head reveal"><h2 class="h-section">{t('antes_de_ofertar')}</h2>
        <p class="sub">{t('doc_a_solicitar')}</p></header>
      <ol class="checklist reveal">{lis}</ol>
    </div>
  </section>
''')

    # ---- otros modelos: accesorios específicos del robot si los tiene
    # (marcados con «compatible» en su ficha), si no, los accesorios genéricos
    # de mano en los humanoides, y si tampoco, otros modelos de la familia
    especificos = [q for q in PRODUCTOS
                   if q['family'] == 'accesorios' and p['slug'] in (q.get('compatible') or [])]
    if especificos:
        others = especificos[:4]
        titulo_otros = t('accesorios_para', n=p['name'])
    elif fam == 'humanoides':
        others = [q for q in PRODUCTOS
                  if q['family'] == 'accesorios' and not q.get('compatible')][:4]
        titulo_otros = t('accesorios_para', n=p['name'])
    else:
        others = [q for q in PRODUCTOS if q['family'] == fam and q['slug'] != p['slug']][:4]
        titulo_otros = t('otros_modelos_familia')
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
      <header class="section-head reveal"><h2 class="h-section">{e(titulo_otros)}</h2></header>
      <ul class="pgrid">{cards}</ul>
    </div>
  </section>
''')

    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


def bloque_elegir(base, titulo=None, texto=None):
    """Banda índigo de cierre del catálogo y de aplicaciones."""
    titulo = titulo if titulo is not None else t('no_sabes_robot_titulo')
    texto = texto if texto is not None else t('no_sabes_robot_texto')
    return f'''  <section class="elegir" id="elegir">
    <div class="wrap elegir__grid">
      <div class="elegir__texto reveal">
        <h2 class="elegir__titulo">{e(titulo)}</h2>
        <p class="elegir__lede">{e(texto)}</p>
      </div>
      <a class="pill elegir__boton reveal" href="{base}contacto.html"><span>{t('hablar_rhbots')}</span>{CHEVRON}</a>
    </div>
  </section>
'''


def aplicaciones_page():
    base = NIVEL[LANG]
    a = APLICACIONES
    out = [head(t('aplicaciones_titulo'), a.get('lede', ''),
                base, 'aplicaciones.html'),
           header(base, 'aplicaciones', 'aplicaciones.html'), '<main id="contenido">']

    sectores = a.get('sectores', [])
    out.append(f'''
  <section class="hero hero--catalogo hero--aplicaciones" id="inicio">
    <img class="hero__foto" src="{base}{e(a.get('imagen', ''))}" alt="" aria-hidden="true" fetchpriority="high">
    <div class="hero__velo" aria-hidden="true"></div>
    <div class="hero__diagonal" aria-hidden="true"></div>
    <div class="wrap hero__copy">
      <p class="kicker hero__kicker">{e(a.get('kicker', ''))}</p>
      <h1 class="display display--hero">{e(a.get('h1', ''))}</h1>
      <p class="lede lede--hero">{e(a.get('lede', ''))}</p>
      <div class="hero__cta">
        <a class="pill" href="contacto.html"><span>{t('cuentanos_tu_caso')}</span>{CHEVRON}</a>
        <a class="pill pill--line" href="robots.html"><span>{t('ver_robots')}</span>{CHEVRON}</a>
      </div>
    </div>
  </section>
''')

    for i, x in enumerate(sectores):
        tareas = ''.join(f'<li>{e(tar)}</li>' for tar in x.get('tareas', []))
        robots = ''
        for slug in x.get('robots', []):
            r = BY_SLUG.get(slug)
            if not r:
                continue
            foto = (f'<img src="{base}{e(r["hero"])}" alt="" loading="lazy">' if r.get('hero')
                    else placeholder(r['family'], r['name']))
            robots += (f'<li><a class="minirobot" href="{base}robots/{r["slug"]}.html">'
                       f'<span class="minirobot__foto">{foto}</span>'
                       f'<span class="minirobot__texto"><strong>{e(r["name"])}</strong>'
                       f'<span>{e(ETIQUETA_FAMILIA.get(r["family"], ""))}</span></span></a></li>')
        fondo = 'section--white' if i % 2 == 0 else 'section--light'
        lado = ' sector--invertido' if i % 2 else ''
        out.append(f'''  <section class="section {fondo} sector{lado}" id="{e(x['id'])}">
    <div class="wrap sector__grid">
      <figure class="sector__foto reveal"><img src="{base}{e(x.get('imagen', ''))}" alt="{e(x['titulo'])}" loading="lazy"></figure>
      <div class="sector__texto reveal">
        <p class="kicker">{i + 1:02d}</p>
        <h2 class="sector__titulo">{e(x['titulo'])}</h2>
        <p class="sector__lede">{e(x.get('texto', ''))}</p>
        <ul class="sector__tareas">{tareas}</ul>
        <p class="sector__sub">{t('robots_para_uso')}</p>
        <ul class="sector__robots">{robots}</ul>
      </div>
    </div>
  </section>
''')

    out.append(bloque_elegir(base, t('tienes_tarea_titulo'), t('tienes_tarea_texto')))
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
    base = NIVEL[LANG]
    out = [head(t('robots_catalogo_titulo'), t('robots_catalogo_desc'), base, 'robots.html'),
           header(base, 'robots', 'robots.html'), '<main id="contenido">']

    # portada del catálogo: fondo oscuro, robot en penumbra y franja diagonal azul
    out.append(f'''
  <section class="hero hero--catalogo" id="inicio">
    <img class="hero__foto" src="{base}assets/robots-portada.webp" alt="" aria-hidden="true"
         width="1600" height="1440" fetchpriority="high">
    <div class="hero__velo" aria-hidden="true"></div>
    <div class="hero__diagonal" aria-hidden="true"></div>
    <div class="wrap hero__copy">
      <p class="kicker hero__kicker">{t('catalogo_kicker')}</p>
      <h1 class="display display--hero">{t('catalogo_h1')}</h1>
      <p class="lede lede--hero">{t('catalogo_lede', n=len(PRODUCTOS))}</p>
      <div class="hero__cta">
        <a class="pill" href="contacto.html"><span>{t('solicitar_asesoramiento')}</span>{CHEVRON}</a>
      </div>
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
            media = (f'<img src="{base}{p["hero"]}" alt="{e(p["name"])}" loading="lazy">'
                     if p.get('hero') else placeholder(p['family'], p['name']))
            facts = ''
            if p['keyfacts']:
                facts = '<ul class="pcard__facts">' + ''.join(
                    f'<li><span>{e(l)}</span><strong>{e(v)}</strong></li>' for l, v in p['keyfacts'][:3]
                ) + '</ul>'
            cards += f'''<li class="pcard reveal">
          <a href="{base}robots/{p['slug']}.html">
            <div class="pcard__media">{media}</div>
            <div class="pcard__body">
              <div class="badges">{badges(p)}</div>
              <h3>{e(p['name'])}</h3>
              <p>{e(p['claim'])}</p>
              {facts}
              {precio_html(p, 'pcard__precio')}
              <span class="pcard__more">{t('ver_ficha_tecnica')}</span>
            </div>
          </a></li>\n'''
        fondo = 'section--white' if i % 2 == 0 else 'section--light'
        out.append(f'''  <section class="section {fondo} familia" id="{key}">
    <div class="wrap">
      <header class="familia__head reveal">
        <h2 class="familia__titulo">{e(name)}</h2>
        <p class="familia__desc">{e(desc)}</p>
      </header>
      <ul class="pgrid pgrid--big">{cards}</ul>
    </div>
  </section>
''')

    out.append(bloque_elegir(base))
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


def bloque_faq(preguntas, titulo=None):
    titulo = titulo if titulo is not None else t('preguntas_frecuentes')
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


def minutos_lectura(post):
    """Minutos de lectura a 200 palabras por minuto (mínimo 1)."""
    palabras = len(re.sub(r'<[^>]+>', ' ', post.get('cuerpo', '')).split())
    return max(1, -(-palabras // 200))


_MESES = {
    'es': ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
           'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'],
    'en': ['January', 'February', 'March', 'April', 'May', 'June', 'July',
           'August', 'September', 'October', 'November', 'December'],
}


def mes_y_ano(fecha):
    """'2026-09-10' pasa a 'septiembre 2026' o 'September 2026', según el idioma.
    Si no es una fecha ISO, se deja igual."""
    m = re.match(r'(\d{4})-(\d{2})', fecha or '')
    return f'{_MESES[LANG][int(m.group(2)) - 1]} {m.group(1)}' if m else (fecha or '')


# ──────────────────────────────────────────────────────────────────── home ──
def home_page():
    base = NIVEL[LANG]
    out = [head(t('inicio_titulo'), t('inicio_desc'), base, 'index.html',
                extra_jsonld=[schema_organization(), schema_faqpage(HOME['faq'])]),
           header(base, 'home', ''), '<main id="contenido">']

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
        <a class="pill" href="robots.html"><span>{t('ver_robots')}</span>{CHEVRON}</a>
        <a class="pill pill--line" href="contacto.html"><span>{t('habla_nosotros')}</span>{CHEVRON}</a>
      </div>
    </div>
  </section>
  <section class="marcas" id="marcas" aria-label="Marcas que distribuimos">
    <div class="wrap marcas__fila">
      <p class="marcas__rotulo">{t('distribuidores_oficiales')}</p>
      <ul class="marcas__logos">{logos_marcas(base, 'marcas__logo')}</ul>
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
                media = (f'<img src="{base}{e(p["hero"])}" alt="{e(p["name"])} — {e(p["claim"])}" '
                         f'loading="lazy" draggable="false">')
            else:
                media = placeholder(p['family'], p['name'])
            tarjetas += f'''<li class="lcard">
          <a href="{base}robots/{p['slug']}.html">
            <div class="lcard__media">{media}</div>
            <div class="lcard__body">
              <p class="lcard__cat">{e(ETIQUETA_FAMILIA.get(p['family'], FAM_NAME[p['family']]))}</p>
              <h3 class="lcard__name">{e(p['name'])}</h3>
              <p class="lcard__desc">{e(p['claim'])}</p>
              <span class="lcard__mas">{t('ver_modelo')}{FLECHA}</span>
            </div>
          </a></li>\n'''
        out.append(f'''  <section class="section section--light loop" id="nuestros-robots">
    <div class="wrap">
      <header class="loop__head reveal">
        <p class="kicker">{e(g['kicker'])}</p>
        <h2 class="loop__titulo">{g['titulo']}</h2>
      </header>
      <div class="carrusel reveal" data-carrusel>
        <ul class="carrusel__pista" tabindex="0" aria-label="{t('modelos_disponibles')}">{tarjetas}</ul>
        <button type="button" class="carrusel__btn carrusel__btn--prev" aria-label="{t('modelos_anteriores')}">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6"/></svg></button>
        <button type="button" class="carrusel__btn carrusel__btn--next" aria-label="{t('modelos_siguientes')}">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button>
      </div>
      <p class="loop__mas reveal"><a class="pill" href="robots.html"><span>{t('ver_todos_modelos')}</span>{CHEVRON}</a></p>
    </div>
  </section>
''')

    # aplicaciones por sector: bloque azul con tarjetas
    sec = HOME.get('sectores_bloque')
    if sec:
        fichas = ''.join(
            f'<li class="secbloque__ficha reveal"><h3>{e(tit)}</h3><p>{e(txt)}</p></li>\n'
            for tit, txt in sec['tarjetas'])
        out.append(f'''  <section class="secbloque" id="sectores">
    <div class="secbloque__diagonal" aria-hidden="true"></div>
    <div class="wrap secbloque__grid">
      <div class="secbloque__copy reveal">
        <p class="kicker">{e(sec['kicker'])}</p>
        <h2 class="secbloque__titulo">{e(sec['titulo'])}</h2>
        <p class="secbloque__lede">{e(sec['texto'])}</p>
        <a class="pill" href="aplicaciones.html"><span>{e(sec['boton'])}</span>{CHEVRON}</a>
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
            media = (f'<div class="ncard__media"><img src="{base}{e(post["img"])}" alt="" loading="lazy"></div>'
                     if post.get('img') else '')
            fichas += f'''<li class="ncard reveal"><a href="{base}{e(post['url'])}">
          {media}
          <div class="ncard__body">
            <p class="ncard__fecha">{e(mes_y_ano(post.get('fecha', '')))}</p>
            <h3>{e(post['titulo'])}</h3>
            <p class="ncard__resumen">{e(post.get('resumen', ''))}</p>
            <span class="ncard__mas">{t('leer_mas')}{FLECHA}</span>
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
    base = NIVEL[LANG]
    out = [head(t('blog_titulo'), t('blog_desc'), base, 'blog.html'),
           header(base, 'blog', 'blog.html'), '<main id="contenido">']
    # portada como las del catálogo y aplicaciones, con el cuadrúpedo de fondo
    out.append(f'''
  <section class="hero hero--catalogo hero--foto-ancha" id="inicio">
    <img class="hero__foto" src="{base}assets/robots/d5w/en-aparcamiento.webp" alt="" aria-hidden="true"
         fetchpriority="high">
    <div class="hero__velo" aria-hidden="true"></div>
    <div class="hero__diagonal" aria-hidden="true"></div>
    <div class="wrap hero__copy">
      <p class="kicker hero__kicker">{t('blog_kicker')}</p>
      <h1 class="display display--hero">{t('blog_h1')}</h1>
      <p class="lede lede--hero">{t('blog_lede')}</p>
      <div class="hero__cta">
        <a class="pill" href="#articulos"><span>{t('ver_articulos')}</span>{CHEVRON}</a>
        <a class="pill pill--line" href="{base}contacto.html"><span>{t('hablar_experto')}</span>{CHEVRON}</a>
      </div>
    </div>
  </section>
''')

    if POSTS:
        def buscable(post):
            texto = ' '.join([post.get('titulo', ''), post.get('resumen', ''), post.get('categoria', ''),
                              re.sub(r'<[^>]+>', ' ', post.get('cuerpo', ''))])
            return e(' '.join(texto.split()).lower())

        # artículo destacado: el más reciente
        d = POSTS[0]
        foto = (f'<div class="destacado__foto"><img src="{base}{e(d["img"])}" alt="" loading="eager"></div>'
                if d.get('img') else '')
        etiquetas = f'<span class="etiqueta">{t("destacado")}</span>'
        if d.get('categoria'):
            etiquetas += f'<span class="etiqueta">{e(d["categoria"])}</span>'
        destacado = f'''<article class="destacado reveal" data-buscar="{buscable(d)}">
        {foto}
        <div class="destacado__texto">
          <div class="destacado__etiquetas">{etiquetas}</div>
          <p class="destacado__meta">{e(mes_y_ano(d.get('fecha', '')).capitalize())} · {minutos_lectura(d)} {t('min_lectura')}</p>
          <h3 class="destacado__titulo"><a href="{base}{e(d['url'])}">{e(d['titulo'])}</a></h3>
          <p class="destacado__resumen">{e(d.get('resumen', ''))}</p>
          <a class="pill" href="{base}{e(d['url'])}"><span>{t('leer_articulo')}</span>{CHEVRON}</a>
        </div>
      </article>'''

        arts = ''
        for post in POSTS:
            cat = post.get('categoria', '')
            img = (f'<div class="artcard__foto"><img src="{base}{e(post["img"])}" alt="" loading="lazy"></div>'
                   if post.get('img') else '')
            meta = ' · '.join(x for x in [mes_y_ano(post.get('fecha', '')), cat] if x)
            arts += f'''<li class="artcard reveal" data-buscar="{buscable(post)}" data-cat="{e(cat)}">
          <a href="{base}{e(post['url'])}">
            {img}
            <div class="artcard__texto">
              <p class="artcard__meta">{e(meta)}</p>
              <h3 class="artcard__titulo">{e(post['titulo'])}</h3>
              <p class="artcard__resumen">{e(post.get('resumen', ''))}</p>
              <span class="artcard__mas">{t('leer_mas')}{FLECHA}</span>
            </div>
          </a></li>\n'''

        categorias = []
        for post in POSTS:
            if post.get('categoria') and post['categoria'] not in categorias:
                categorias.append(post['categoria'])
        filtros = f'<button type="button" class="filtro is-on" data-cat="" aria-pressed="true">{t("todos")}</button>'
        filtros += ''.join(f'<button type="button" class="filtro" data-cat="{e(c)}" aria-pressed="false">{e(c)}</button>'
                           for c in categorias)

        out.append(f'''  <section class="section section--white blogbusca" id="articulos">
    <div class="wrap">
      <header class="blogbusca__head reveal">
        <div>
          <p class="kicker">{t('conocimiento_aplicado')}</p>
          <h2 class="blogbusca__titulo">{t('ideas_claras')}</h2>
        </div>
        <form class="buscador" role="search" action="blog.html" data-buscador>
          <label class="sr-only" for="buscar-articulos">{t('buscar_articulos')}</label>
          <input id="buscar-articulos" name="q" type="search" placeholder="{t('buscar_articulos_placeholder')}" autocomplete="off">
          <button type="submit" class="buscador__btn">{t('buscar')}</button>
        </form>
      </header>
      {destacado}
    </div>
  </section>
  <section class="section section--light ultimos" id="ultimos">
    <div class="wrap">
      <header class="ultimos__head reveal">
        <p class="kicker">{t('ultimos_articulos')}</p>
        <h2 class="ultimos__titulo">{t('recursos_presente')}</h2>
      </header>
      <div class="filtros reveal" role="group" aria-label="Filtrar por categoría">{filtros}</div>
      <ul class="artgrid">{arts}</ul>
      <p class="blogbusca__vacio" hidden>{t('sin_resultados_busqueda')}</p>
    </div>
  </section>
''')
    else:
        out.append(f'''  <section class="section section--white" id="articulos">
    <div class="wrap wrap--narrow">
      <div class="vacio reveal">
        <span class="vacio__ico" aria-hidden="true">{MARCA_SVG}</span>
        <h2>{t('preparando_articulos')}</h2>
        <p>{t('preparando_articulos_texto')}</p>
        <div class="feat-cta">
          <a class="pill" href="robots.html"><span>{t('ver_robots')}</span>{CHEVRON}</a>
          <a class="pill pill--line" href="contacto.html"><span>{t('escribenos')}</span>{CHEVRON}</a>
        </div>
      </div>
    </div>
  </section>
''')

    # cierre: orientación para elegir robot
    out.append(f'''  <section class="orienta" id="orientacion">
    <div class="orienta__halo" aria-hidden="true"></div>
    <div class="wrap orienta__texto reveal">
      <p class="kicker">{t('necesitas_orientacion')}</p>
      <h2 class="orienta__titulo">{t('orienta_titulo')}</h2>
      <p class="orienta__lede">{t('orienta_texto')}</p>
      <a class="pill pill--line" href="contacto.html"><span>{t('solicitar_informacion')}</span>{CHEVRON}</a>
    </div>
  </section>
''')

    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


# ─────────────────────────────────────────────────────────────── artículo ──
def articulo_page(post):
    base = NIVEL[LANG] + '../'
    ruta = f'blog/{post["slug"]}.html'
    out = [head(f'{post["titulo"]}{t("blog_articulo_sufijo")}', post.get('resumen', ''), base, ruta,
                og_img=post.get('img')),
           header(base, 'blog', ruta), '<main id="contenido">']

    portada = (f'<figure class="art__portada"><img src="{base}{e(post["img"])}" '
              f'alt="{e(post["titulo"])}" loading="eager"></figure>'
              if post.get('img') else '')

    out.append(f'''
  <section class="chero chero--art">
    <div class="wrap wrap--narrow">
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
      <p class="art__volver"><a href="{base}blog.html">{t('volver_blog')}</a></p>
    </div>
  </article>
''')

    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


def rh_bots_page():
    base = NIVEL[LANG]
    r = RHBOTS
    emails = {p['nombre']: p.get('email') for p in CONTACTO.get('personas', [])}
    personas_jsonld = [schema_person(nombre, cargo, emails.get(nombre))
                       for _, nombre, cargo, _ in (r.get('equipo') or []) if nombre]
    out = [head(f'{r.get("h1", "RH·BOTS")} | RH·BOTS', r.get('lede', ''), base, 'rh-bots.html',
                extra_jsonld=personas_jsonld),
           header(base, 'rhbots', 'rh-bots.html'), '<main id="contenido">']

    # portada con foto, como las de robots, aplicaciones y blog
    out.append(f'''
  <section class="hero hero--catalogo hero--foto-ancha" id="inicio">
    <img class="hero__foto hero__foto--arriba" src="{base}assets/conocenos-portada.webp" alt="" aria-hidden="true"
         width="1600" height="1632" fetchpriority="high">
    <div class="hero__velo" aria-hidden="true"></div>
    <div class="hero__diagonal" aria-hidden="true"></div>
    <div class="wrap hero__copy">
      {f'<p class="kicker hero__kicker">{e(r["kicker"])}</p>' if r.get('kicker') else ''}
      <h1 class="display display--hero">{e(r.get('h1', ''))}</h1>
      <p class="lede lede--hero">{e(r.get('lede', ''))}</p>
      <div class="hero__cta">
        <a class="pill" href="contacto.html"><span>{t('habla_nosotros')}</span>{CHEVRON}</a>
        <a class="pill pill--line" href="robots.html"><span>{t('ver_robots')}</span>{CHEVRON}</a>
      </div>
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

    # misión
    m = r.get('mision')
    if m:
        parrafos = ''.join(f'<p>{e(x)}</p>' for x in m.get('parrafos', []))
        puntos = ''.join(f'<li>{e(x)}</li>' for x in m.get('puntos', []))
        out.append(f'''  <section class="section section--light mision" id="mision">
    <div class="wrap mision__grid">
      <div class="mision__cabecera reveal">
        <p class="kicker">{e(m.get('kicker', ''))}</p>
        <h2 class="mision__titulo">{m.get('titulo', '')}</h2>
      </div>
      <div class="mision__texto reveal">
        {parrafos}
        <ul class="sector__tareas mision__puntos">{puntos}</ul>
      </div>
    </div>
  </section>
''')

    # alianza: cifras con contador
    al = r.get('alianza')
    if al:
        valores = {'modelos': len(PRODUCTOS),
                   'familias': len({p['family'] for p in PRODUCTOS})}
        celdas = ''.join(
            f'<div class="alianza__cifra"><p class="alianza__valor" data-contar>{e(str(v).format(**valores))}</p>'
            f'<p class="alianza__etiqueta">{e(et)}</p></div>'
            for v, et in al.get('cifras', []))
        out.append(f'''  <section class="alianza" id="alianza">
    <div class="wrap">
      <header class="alianza__head reveal">
        <h2 class="alianza__titulo">{e(al.get('titulo', ''))}</h2>
        <p class="alianza__texto">{e(al.get('texto', ''))}</p>
      </header>
      <ul class="alianza__marcas reveal" aria-label="Marcas que distribuimos">{logos_marcas(base, 'alianza__marca')}</ul>
      <div class="alianza__cifras reveal">{celdas}</div>
    </div>
  </section>
''')

    # cómo trabajamos: cuatro pasos
    pr = r.get('proceso')
    if pr:
        pasos = ''.join(
            f'<li class="paso reveal"><p class="paso__num">{i:02d}</p>'
            f'<h3 class="paso__titulo">{e(t)}</h3><p class="paso__texto">{e(txt)}</p></li>'
            for i, (t, txt) in enumerate(pr.get('pasos', []), 1))
        out.append(f'''  <section class="section section--white proceso" id="como-trabajamos">
    <div class="wrap">
      <header class="proceso__head reveal">
        <div>
          <p class="kicker">{e(pr.get('kicker', ''))}</p>
          <h2 class="proceso__titulo">{e(pr.get('titulo', ''))}</h2>
        </div>
        <p class="proceso__texto">{e(pr.get('texto', ''))}</p>
      </header>
      <ol class="pasos">{pasos}</ol>
    </div>
  </section>
''')

    # cta: ¿hablamos de tu proyecto?
    pj = r.get('proyecto')
    if pj:
        out.append(f'''  <section class="section section--white proyecto" id="proyecto">
    <div class="wrap">
      <div class="proyecto__caja reveal">
        {f'<img class="proyecto__foto" src="{base}{e(pj["foto"])}" alt="" width="1300" height="855" loading="lazy" decoding="async">' if pj.get('foto') else ''}
        <div class="proyecto__velo" aria-hidden="true"></div>
        <div class="proyecto__texto">
          <h2 class="proyecto__titulo">{e(pj.get('titulo', ''))}</h2>
          <p class="proyecto__lede">{e(pj.get('texto', ''))}</p>
        </div>
        <a class="pill proyecto__boton" href="{base}contacto.html"><span>{e(pj.get('boton') or t('habla_nosotros'))}</span>{CHEVRON}</a>
      </div>
    </div>
  </section>
''')

    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


def legal_page():
    base = NIVEL[LANG]
    dominio = SEO['dominio'].rstrip('/')
    empresa = CONTACTO.get('empresa') or 'RH·BOTS'
    direccion = ', '.join(CONTACTO.get('direccion') or [])
    principal = CONTACTO['personas'][0] if CONTACTO.get('personas') else {}
    email = principal.get('email', '')
    tel = principal.get('tel', '')

    out = [head(t('legal_meta_titulo'), t('legal_meta_desc'),
                base, 'legal.html'),
           header(base, '', 'legal.html'), '<main id="contenido">']

    if LANG == 'en':
        out.append(f'''
  <section class="chero">
    <div class="wrap">
      <h1 class="display display--left">Legal notice, privacy and cookies</h1>
    </div>
  </section>
  <section class="section section--white">
    <div class="wrap wrap--narrow art__cuerpo">
      <p><em>This English page is a courtesy translation of our Spanish legal notice.
      In case of any discrepancy, the Spanish version (<a href="/legal.html">/legal.html</a>)
      prevails, and Spanish law applies. We recommend a professional legal review before
      relying on this translation for compliance purposes.</em></p>

      <h2 id="aviso-legal">Legal notice</h2>
      <p><strong>Website owner:</strong> {e(empresa)}.<br>
      <strong>Tax ID (CIF/NIF):</strong> [to be completed by the owner].<br>
      <strong>Registered address:</strong> {e(direccion)}.<br>
      {f'<strong>Contact:</strong> {e(email)}' + (f' · {e(tel)}' if tel else '') + '.<br>' if email else ''}
      <strong>Domain:</strong> {e(dominio)}</p>
      <p>Accessing and using this website grants you the status of user and implies
      acceptance of the conditions set out here. {e(empresa)} is an official
      distributor of AGIBOT and PUDU in Spain and Portugal.</p>

      <h2 id="privacidad">Privacy policy</h2>
      <p><strong>Data controller:</strong> {e(empresa)}{f', {e(email)}' if email else ''}.</p>
      <p><strong>Purpose:</strong> to handle requests for information, quotes,
      demonstrations or support that you send us through the contact form,
      and to manage the business relationship should it go ahead.</p>
      <p><strong>Legal basis:</strong> the consent of the data subject when
      submitting their details, and the performance of any resulting contractual
      relationship.</p>
      <p><strong>Retention:</strong> for as long as the relationship with the
      user is maintained, or for the legally required periods.</p>
      <p><strong>Recipients:</strong> data is not shared with third parties
      except where legally required, or with providers necessary to deliver
      the requested service (for example, Shopify to process an order).</p>
      <p><strong>Your rights:</strong> you can exercise your rights of access,
      rectification, erasure, objection, restriction and portability by
      writing to{f' {e(email)}' if email else " RH·BOTS's contact address"}.</p>

      <h2 id="cookies">Cookie policy</h2>
      <p>This site only uses the technical cookies strictly necessary for it
      to work. If Google Analytics or another measurement tool is enabled in
      the future, the user's prior consent will be requested before it loads.</p>
    </div>
  </section>
''')
    else:
        out.append(f'''
  <section class="chero">
    <div class="wrap">
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
      oficial de AGIBOT y PUDU en España y Portugal.</p>

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
    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


# ──────────────────────────────────────────────────────────────── contacto ──
def contacto_page():
    base = NIVEL[LANG]
    c = CONTACTO
    email = c.get('email_directo') or (c['personas'][0]['email'] if c.get('personas') else '')
    out = [head(t('contacto_titulo'), c['intro'], base, 'contacto.html'),
           header(base, 'contacto', 'contacto.html'), '<main id="contenido">']

    # portada partida: texto sobre noche y foto con la tarjeta de asesoramiento
    a = c.get('asesoria', {})
    pasos_a = ''.join(
        f'<li class="asesora__paso"><span class="asesora__num">{i:02d}</span>'
        f'<div><h3>{e(t)}</h3><p>{e(x)}</p></div></li>'
        for i, (t, x) in enumerate(a.get('pasos', []), 1))
    out.append(f'''
  <section class="ctohero" id="inicio">
    <div class="ctohero__lado ctohero__lado--foto" aria-hidden="true">
      <img src="{base}assets/video/fondo-c5.webp" alt="" width="1280" height="720" fetchpriority="high">
    </div>
    <div class="wrap ctohero__grid">
      <div class="ctohero__copy">
        <p class="kicker ctohero__kicker">{e(c.get('kicker', 'Contacto'))}</p>
        <h1 class="ctohero__titulo">{e(c.get('h1', 'Hablemos'))}</h1>
        <p class="ctohero__lede">{e(c['intro'])}</p>
        <div class="ctohero__cta">
          <a class="pill" href="#formulario"><span>{t('solicitar_asesoramiento_cta')}</span>{CHEVRON}</a>
          <a class="pill pill--borde" href="mailto:{e(email)}"><span>{t('escribir_email')}</span></a>
        </div>
      </div>
      <aside class="asesora">
        <h2 class="asesora__titulo">{e(a.get('titulo', ''))}</h2>
        <p class="asesora__texto">{e(a.get('texto', ''))}</p>
        <ol class="asesora__pasos">{pasos_a}</ol>
      </aside>
    </div>
  </section>
''')

    # formulario: tarjeta con los datos y tarjeta con el formulario
    robots = f'<option value="">{t("selecciona_modelo")}</option>'
    for key, nombre, _ in FAMILIAS:
        ps = [p for p in PRODUCTOS if p['family'] == key]
        if ps:
            robots += (f'<optgroup label="{e(nombre)}">'
                       + ''.join(f'<option>{e(p["name"])}</option>' for p in ps) + '</optgroup>')
    robots += f'<option>{t("aun_no_lo_se")}</option>'

    lado = c.get('lado', {})
    tel = c.get('telefono_directo', '')
    direccion = '<br>'.join(e(x) for x in c['direccion'])
    datos = f'''<li class="dato">
          <span class="dato__ico">{ICONO_SOBRE}</span>
          <div><p class="dato__etiqueta">{t('email_directo_etq')}</p>
          <p class="dato__valor"><a href="mailto:{e(email)}">{e(email)}</a></p></div>
        </li>'''
    if tel:
        datos += f'''<li class="dato">
          <span class="dato__ico">{ICONO_TEL}</span>
          <div><p class="dato__etiqueta">{t('telefono')}</p>
          <p class="dato__valor"><a href="tel:{tel_href(tel)}">{e(tel)}</a></p></div>
        </li>'''
    if lado.get('especialidad'):
        datos += f'''<li class="dato">
          <span class="dato__ico">{ICONO_ROBOT}</span>
          <div><p class="dato__etiqueta">{t('especialistas_en')}</p>
          <p class="dato__valor">{e(lado['especialidad'])}</p></div>
        </li>'''
    datos += f'''<li class="dato">
          <span class="dato__ico">{ICONO_PIN}</span>
          <div><p class="dato__etiqueta">{t('donde_estamos')}</p>
          <address class="dato__valor dato__valor--dir">{direccion}</address></div>
        </li>'''

    out.append(f'''
  <section class="section section--light ctoform" id="formulario">
    <div class="wrap ctoform__grid">
      <aside class="ctoform__lado reveal">
        <p class="kicker">{e(lado.get('kicker') or t('habla_nosotros'))}</p>
        <h2 class="ctoform__ladotitulo">{e(lado.get('titulo', ''))}</h2>
        <p class="ctoform__ladotexto">{e(lado.get('texto', ''))}</p>
        <ul class="datos">{datos}</ul>
      </aside>

      <div class="ctoform__caja reveal">
        <div class="ctoform__cab">
          <div>
            <p class="kicker">{t('formulario')}</p>
            <h2 class="ctoform__titulo">{t('solicita_info')}</h2>
          </div>
          <p class="ctoform__sello">{t('respuesta_personalizada')}</p>
        </div>
        <form class="form" id="contactoForm" data-email="{e(email)}" novalidate>
          <div class="form__two">
            <div class="form__row">
              <label for="f-nombre">{t('nombre')}</label>
              <input id="f-nombre" name="nombre" type="text" autocomplete="given-name" placeholder="{t('tu_nombre')}" required>
            </div>
            <div class="form__row">
              <label for="f-apellidos">{t('apellidos')}</label>
              <input id="f-apellidos" name="apellidos" type="text" autocomplete="family-name" placeholder="{t('tus_apellidos')}">
            </div>
          </div>
          <div class="form__two">
            <div class="form__row">
              <label for="f-email">{t('email')}</label>
              <input id="f-email" name="email" type="email" autocomplete="email" placeholder="tu@empresa.com" required>
            </div>
            <div class="form__row">
              <label for="f-tel">{t('telefono')}</label>
              <input id="f-tel" name="tel" type="tel" autocomplete="tel" placeholder="+34 600 000 000">
            </div>
          </div>
          <div class="form__row">
            <label for="f-empresa">{t('empresa_campo')}</label>
            <input id="f-empresa" name="empresa" type="text" autocomplete="organization" placeholder="{t('nombre_empresa_placeholder')}">
          </div>
          <div class="form__row">
            <label for="f-robot">{t('que_robot_interesa')}</label>
            <select id="f-robot" name="robot">{robots}</select>
          </div>
          <div class="form__row">
            <label for="f-mensaje">{t('como_ayudarte')}</label>
            <textarea id="f-mensaje" name="mensaje" rows="6" placeholder="{t('mensaje_placeholder')}" required></textarea>
          </div>
          <div class="form__consent">
            <input id="f-privacidad" name="privacidad" type="checkbox" required>
            <label for="f-privacidad">{t('consiento_privacidad')}
              <a href="{base}legal.html#privacidad">{t('politica_privacidad_link')}</a>{t('consiento_privacidad_fin')}</label>
          </div>
          <button class="pill pill--ancho" type="submit"><span>{t('enviar_mensaje')}</span>{CHEVRON}</button>
          <p class="form__nota" id="formNota" role="status"></p>
        </form>
      </div>
    </div>
  </section>
''')

    # cómo trabajamos: tres pasos
    pr = c.get('proceso')
    if pr:
        pasos = ''.join(
            f'<li class="ctopaso reveal"><p class="ctopaso__num">{i:02d}</p>'
            f'<h3 class="ctopaso__titulo">{e(t)}</h3><p class="ctopaso__texto">{e(x)}</p></li>'
            for i, (t, x) in enumerate(pr.get('pasos', []), 1))
        out.append(f'''  <section class="section section--white ctoproceso" id="como-trabajamos">
    <div class="wrap">
      <header class="reveal">
        <p class="kicker">{e(pr.get('kicker', ''))}</p>
        <h2 class="ctoproceso__titulo">{e(pr.get('titulo', ''))}</h2>
      </header>
      <ol class="ctopasos">{pasos}</ol>
    </div>
  </section>
''')

    # franja: teléfono (o correo, si no hubiera teléfono)
    if tel:
        out.append(f'''  <section class="ctomail" id="telefono">
    <div class="wrap ctomail__texto reveal">
      <p>{t('llamanos_al')}</p>
      <a class="ctomail__email" href="tel:{tel_href(tel)}">{e(tel)}</a>
    </div>
  </section>
''')
    elif email:
        out.append(f'''  <section class="ctomail" id="email">
    <div class="wrap ctomail__texto reveal">
      <p>{t('escribenos_directamente')}</p>
      <a class="ctomail__email" href="mailto:{e(email)}">{e(email)}</a>
    </div>
  </section>
''')

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
    """La última palabra del titular va en azul; si solo tiene una, entera.

    Se salta los títulos que ya traen su propio <span class="acento"> (el
    del hero, por ejemplo, donde el azul empieza antes) y los que van
    blancos sobre banda azul, donde el azul claro no se leería.
    """
    if 'acento' in fragmento or not _palabras(fragmento):
        return fragmento
    # un título de una sola palabra va entero en azul (y su punto también)
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


_IMG = re.compile(r'<img\b[^>]*>')


def _con_medidas(html_pagina, carpeta):
    """Añade width/height a las <img> que no los traigan.

    Sin estas medidas el navegador no reserva el hueco y la página da saltos
    al cargar (mal CLS, uno de los Core Web Vitals). Las dimensiones salen
    del archivo, así que siempre cuadran con la imagen real.
    """
    def arregla(m):
        tag = m.group(0)
        if 'width=' in tag and 'height=' in tag:
            return tag
        src = re.search(r'src="([^"]+)"', tag)
        if not src:
            return tag
        ruta = os.path.normpath(os.path.join(carpeta, src.group(1)))
        dims = dimensiones(ruta)
        return tag[:-1].rstrip() + f'{img_dims_attr(ruta)}>' if dims else tag
    return _IMG.sub(arregla, html_pagina)


def write(path, content):
    if path.endswith('.html'):
        content = _TITULO.sub(_titulo, content)
        # carpeta de la página dentro de web/, para resolver los src relativos
        carpeta = os.path.relpath(os.path.dirname(path), WEB)
        content = _con_medidas(content, '' if carpeta == '.' else carpeta)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, 'w', encoding='utf-8').write(content)
    return path


def pagina_404():
    base = NIVEL[LANG]
    out = [head(t('pagina_no_encontrada'), t('pagina_no_encontrada_desc'),
                base, '404.html'),
           header(base, '', '404.html'), '<main id="contenido">']
    out.append(f'''
  <section class="chero">
    <div class="wrap">
      <p class="err404">404</p>
      <h1 class="display display--left">{t('pagina_404_titulo')}</h1>
      <p class="lede lede--left">{t('pagina_404_texto')}</p>
      <div class="feat-cta" style="justify-content:flex-start">
        <a class="pill" href="index.html"><span>{t('ir_inicio')}</span>{CHEVRON}</a>
        <a class="pill pill--line" href="robots.html"><span>{t('ver_robots')}</span>{CHEVRON}</a>
      </div>
    </div>
  </section>
''')
    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


def sitemap():
    """Un único sitemap con las dos versiones de cada página (es/en),
    cada una apuntando a su alternativa con xhtml:link, como recomienda
    Google para sitios multilingües."""
    d = SEO['dominio'].rstrip('/')
    rutas = [('', '1.0'), ('robots.html', '0.9'), ('aplicaciones.html', '0.8'), ('rh-bots.html', '0.6'),
             ('contacto.html', '0.7'), ('blog.html', '0.5'), ('legal.html', '0.2')]
    rutas += [(f'robots/{p["slug"]}.html', '0.8') for p in _PRODUCTOS_ES]
    rutas += [(p['url'], '0.6') for p in _POSTS_ES if p.get('url')]

    def loc(ruta, lang):
        prefijo = 'en/' if lang == 'en' else ''
        return f'{d}/{prefijo}{ruta}' if ruta else f'{d}/{prefijo}'

    urls = ''
    for ruta, pr in rutas:
        for lang in ('es', 'en'):
            urls += (f'  <url><loc>{loc(ruta, lang)}</loc><lastmod>{FECHA_BUILD}</lastmod>'
                     f'<priority>{pr}</priority>'
                     f'<xhtml:link rel="alternate" hreflang="es" href="{loc(ruta, "es")}"/>'
                     f'<xhtml:link rel="alternate" hreflang="en" href="{loc(ruta, "en")}"/>'
                     f'</url>\n')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            f'{urls}</urlset>\n')


def llms_txt():
    """Ficha del sitio en formato llms.txt (llmstxt.org) para que un LLM
    entienda de un vistazo qué hay y a dónde ir, sin tener que rastrear
    todo el HTML."""
    d = SEO['dominio'].rstrip('/')
    prefijo = f'{d}/en' if LANG == 'en' else d
    if LANG == 'en':
        out = ['# RH·BOTS\n',
               '> Official distributor of AGIBOT and PUDU in Spain and Portugal. Autonomous cleaning, '
               'humanoid and quadruped robots, intralogistics AMRs and accessories, with advice, installation, '
               'training and maintenance. Based in Picassent (Valencia, Spain).\n']
    else:
        out = ['# RH·BOTS\n',
               f'> Distribuidor oficial de AGIBOT y PUDU en España y Portugal. Robots de limpieza '
               f'autónoma, humanoides, cuadrúpedos, AMR de intralogística y accesorios, con asesoramiento, instalación, '
               f'formación y mantenimiento. Sede en Picassent (Valencia).\n']

    out.append('## Robots\n')
    for key, nombre, _ in FAMILIAS:
        modelos = [p for p in PRODUCTOS if p['family'] == key]
        if not modelos:
            continue
        out.append(f'\n### {nombre}\n')
        for p in modelos:
            out.append(f'- [{p["name"]}]({prefijo}/robots/{p["slug"]}.html): {p["claim"]}')
    if LANG == 'en':
        out.append('\n\n## Company\n')
        out.append(f'- [Full catalog]({prefijo}/robots.html)')
        out.append(f'- [Applications by sector]({prefijo}/aplicaciones.html): which robot fits which use')
        out.append(f'- [About us]({prefijo}/rh-bots.html): the RH·BOTS team and story')
        out.append(f'- [Contact]({prefijo}/contacto.html)')
        out.append('\n\n## Optional\n')
        out.append(f'- [Blog]({prefijo}/blog.html)')
        out.append(f'- [Legal notice and privacy]({prefijo}/legal.html)')
    else:
        out.append(f'\n\n## Empresa\n')
        out.append(f'- [Catálogo completo]({prefijo}/robots.html)')
        out.append(f'- [Aplicaciones por sector]({prefijo}/aplicaciones.html): qué robot encaja en cada uso')
        out.append(f'- [Quiénes somos]({prefijo}/rh-bots.html): equipo e historia de RH·BOTS')
        out.append(f'- [Contacto]({prefijo}/contacto.html)')
        out.append(f'\n\n## Optional\n')
        out.append(f'- [Blog]({prefijo}/blog.html)')
        out.append(f'- [Aviso legal y privacidad]({prefijo}/legal.html)')
    return '\n'.join(out) + '\n'


def robots_txt():
    d = SEO['dominio'].rstrip('/')
    return f'User-agent: *\nAllow: /\n\nSitemap: {d}/sitemap.xml\n'


def generar_paginas(carpeta):
    """Genera el árbol completo de páginas del idioma activo (set_lang ya
    tiene que haberse llamado) dentro de «carpeta» (WEB o WEB/en)."""
    paginas = [
        ('index.html',    home_page()),
        ('robots.html',   index_page()),
        ('aplicaciones.html', aplicaciones_page()),
        ('rh-bots.html',  rh_bots_page()),
        ('blog.html',     blog_page()),
        ('contacto.html', contacto_page()),
        ('legal.html',    legal_page()),
    ]
    for nombre, contenido in paginas:
        write(os.path.join(carpeta, nombre), contenido)

    fichas_vivas = set()
    for p in PRODUCTOS:
        fichas_vivas.add(p['slug'] + '.html')
        write(os.path.join(carpeta, 'robots', p['slug'] + '.html'), product_page(p))
    carpeta_robots = os.path.join(carpeta, 'robots')
    if os.path.isdir(carpeta_robots):
        for archivo in os.listdir(carpeta_robots):
            if archivo.endswith('.html') and archivo not in fichas_vivas:
                os.remove(os.path.join(carpeta_robots, archivo))

    slugs_vivos = set()
    for post in POSTS:
        if not post.get('slug'):
            continue
        slugs_vivos.add(post['slug'] + '.html')
        write(os.path.join(carpeta, 'blog', post['slug'] + '.html'), articulo_page(post))
    carpeta_blog = os.path.join(carpeta, 'blog')
    if os.path.isdir(carpeta_blog):
        for archivo in os.listdir(carpeta_blog):
            if archivo not in slugs_vivos:
                os.remove(os.path.join(carpeta_blog, archivo))

    write(os.path.join(carpeta, '404.html'), pagina_404())
    write(os.path.join(carpeta, 'llms.txt'), llms_txt())
    return len(paginas) + len(PRODUCTOS) + len(slugs_vivos)


def main():
    total = 0
    for lang in ('es', 'en'):
        set_lang(lang)
        carpeta = WEB if lang == 'es' else os.path.join(WEB, 'en')
        total += generar_paginas(carpeta)
    set_lang('es')   # el resto del build (robots.txt, sitemap, avisos) es neutro/en la raíz

    write(os.path.join(WEB, 'sitemap.xml'), sitemap())
    write(os.path.join(WEB, 'robots.txt'), robots_txt())

    enlazados = [x for x in PRODUCTOS if x.get('shopify')]
    if TIENDA.get('activa'):
        agotados = [x for x in enlazados if not x['shopify'].get('disponible')]
        comprables = len(enlazados) - len(agotados) - len(set(AVISOS_TIENDA))
        print(f'     tienda ACTIVA · {len(enlazados)} enlazados: '
              f'{comprables} con botón de compra, {len(agotados)} sin stock, '
              f'{len(set(AVISOS_TIENDA))} bloqueados por precio')
        for a in dict.fromkeys(AVISOS_TIENDA):   # sin duplicar: se recorren las 2 pasadas de idioma
            print(f'       ! {a}')
    else:
        print(f'     tienda desactivada · {len(enlazados)} productos enlazados, sin botón')

    ga = ANALITICA.get('ga4') or ANALITICA.get('gtm') or 'sin configurar'
    print(f'OK — {total} páginas (es + en): home, catálogo, rh-bots, blog, contacto '
          f'y {len(PRODUCTOS)} fichas, en cada idioma')
    print(f'     sitemap.xml y robots.txt · dominio {SEO["dominio"]} · analítica: {ga}')


if __name__ == '__main__':

    main()
