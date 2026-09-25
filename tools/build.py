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
                   TIENDA, RHBOTS, ALQUILER)
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
IDIOMAS = ['es', 'pt', 'en', 'fr', 'de', 'zh', 'ar', 'ca']  # orden en el desplegable
NOMBRE_IDIOMA = {
    'es': 'Español', 'pt': 'Português', 'en': 'English', 'fr': 'Français',
    'de': 'Deutsch', 'zh': '中文', 'ar': 'العربية', 'ca': 'Català',
}
# idiomas que se escriben de derecha a izquierda
RTL = {'ar'}
# og:locale de cada idioma (el sitio.json solo trae el español)
LOCALE_OG = {
    'es': 'es_ES', 'pt': 'pt_PT', 'en': 'en_GB', 'fr': 'fr_FR',
    'de': 'de_DE', 'zh': 'zh_CN', 'ar': 'ar_AE', 'ca': 'ca_ES',
}


def dir_html(lang=None):
    return 'rtl' if (lang or LANG) in RTL else 'ltr'


def nivel(lang):
    """Tramos «../» extra para bajar de /{lang}/ a la raíz. El español vive
    en la raíz (sin prefijo); el resto, cada uno en su propia subcarpeta."""
    return '' if lang == 'es' else '../'


def _fusiona(es, capa):
    """Superpone «capa» (la traducción) sobre «es» (español), recursivo en
    dicts. Listas y valores sueltos se sustituyen enteros si la capa los
    trae; lo que falte en la capa cae al español, así que una traducción a
    medias no rompe nunca la build."""
    if not isinstance(capa, dict) or not isinstance(es, dict):
        return capa if capa is not None else es
    return {k: (_fusiona(es.get(k), v) if isinstance(v, dict) and isinstance(es.get(k), dict) else v)
            for k, v in {**es, **capa}.items()}


def _carga_json(nombre):
    ruta = os.path.join(os.path.dirname(HERE), 'datos', nombre)
    if not os.path.exists(ruta):
        return {}
    with io.open(ruta, encoding='utf-8') as f:
        return json.load(f)


_SITIO_ES = {'nav': NAV, 'home': HOME, 'contacto': CONTACTO, 'cta': CTA,
             'prefooter': PREFOOTER, 'posts': POSTS, 'rhbots': RHBOTS,
             'aplicaciones': APLICACIONES,
             'alquiler': ALQUILER}
_PRODUCTOS_ES, _FAMILIAS_ES, _ESTADOS_ES = PRODUCTOS, FAMILIAS, ESTADOS


def _familias_fusionadas(familias_capa):
    if not familias_capa:
        return _FAMILIAS_ES
    por_clave = {k: (n, d) for k, n, d in familias_capa}
    return [[k, *por_clave.get(k, (n, d))] for k, n, d in _FAMILIAS_ES]


def _productos_fusionados(productos_capa):
    return [_fusiona(p, productos_capa.get(p['slug'])) if productos_capa.get(p['slug']) else p
            for p in _PRODUCTOS_ES]


# capa de traducción por idioma: {} para español (es la base), y el
# contenido de datos/sitio.<lang>.json / productos.<lang>.json para el resto
_SITIO_POR_LANG = {'es': _SITIO_ES}
_PRODUCTOS_POR_LANG = {'es': _PRODUCTOS_ES}
_FAMILIAS_POR_LANG = {'es': _FAMILIAS_ES}
_ESTADOS_POR_LANG = {'es': _ESTADOS_ES}

for _lang in IDIOMAS:
    if _lang == 'es':
        continue
    _capa_sitio = _carga_json(f'sitio.{_lang}.json')
    _capa_prod = _carga_json(f'productos.{_lang}.json')
    _familias_capa = _capa_prod.pop('familias', None) or []
    _estados_capa = _capa_prod.pop('estados', None) or {}
    _capa_prod.pop('productos', None)   # por si el archivo viniera con esa envoltura

    _SITIO_POR_LANG[_lang] = {k: _fusiona(_SITIO_ES.get(k), _capa_sitio.get(k)) for k in _SITIO_ES}
    _PRODUCTOS_POR_LANG[_lang] = _productos_fusionados(_capa_prod)
    _FAMILIAS_POR_LANG[_lang] = _familias_fusionadas(_familias_capa)
    _ESTADOS_POR_LANG[_lang] = _fusiona(_ESTADOS_ES, _estados_capa)

# los posts (artículos del blog) son una lista: si la capa no trae el mismo
# número de entradas, mejor quedarse con el español entero que mezclar mal
for _lang in IDIOMAS:
    _posts_lang = _SITIO_POR_LANG[_lang].get('posts')
    if _lang != 'es' and (not _posts_lang or len(_posts_lang) != len(POSTS)):
        _SITIO_POR_LANG[_lang]['posts'] = POSTS
    _nav_lang = _SITIO_POR_LANG[_lang].get('nav')
    if _lang != 'es' and (not _nav_lang or len(_nav_lang) != len(NAV)):
        _SITIO_POR_LANG[_lang]['nav'] = NAV


def set_lang(lang):
    """Intercambia todo el contenido module-level por el del idioma pedido.
    Los f-strings del resto del archivo leen estos nombres en tiempo de
    llamada, así que basta con reasignarlos antes de generar cada página."""
    global LANG, NAV, HOME, CONTACTO, CTA, PREFOOTER, POSTS, RHBOTS, APLICACIONES, ALQUILER
    global FAMILIAS, ESTADOS, PRODUCTOS, BY_SLUG, FAM_NAME
    LANG = lang
    d = _SITIO_POR_LANG[lang]
    NAV, HOME, CONTACTO = d['nav'], d['home'], d['contacto']
    CTA, PREFOOTER, POSTS = d['cta'], d['prefooter'], d['posts']
    RHBOTS, APLICACIONES = d['rhbots'], d['aplicaciones']
    ALQUILER = d['alquiler']
    FAMILIAS, ESTADOS, PRODUCTOS = _FAMILIAS_POR_LANG[lang], _ESTADOS_POR_LANG[lang], _PRODUCTOS_POR_LANG[lang]
    BY_SLUG = {p['slug']: p for p in PRODUCTOS}
    FAM_NAME = {k: n for k, n, _ in FAMILIAS}


# Todas las cadenas de interfaz que no vienen de datos/*.json (botones,
# rótulos de sección, aria-labels…). t('clave') da la del idioma activo.
TEXTOS = {
    'saltar_contenido': {'es': 'Saltar al contenido', 'pt': 'Saltar para o conteúdo', 'en': 'Skip to content', 'fr': 'Passer au contenu', 'zh': '跳至内容', 'ca': 'Saltar al contingut'},
    'ver_todo_catalogo': {'es': 'Ver todo el catálogo', 'pt': 'Ver todo o catálogo', 'en': 'View full catalog', 'fr': 'Voir tout le catalogue', 'zh': '查看完整产品目录', 'ca': 'Veure tot el catàleg'},
    'nav_inicio': {'es': 'Inicio', 'pt': 'Início', 'en': 'Home', 'fr': 'Accueil', 'zh': '首页', 'ca': 'Inici'},
    'nav_robots': {'es': 'Robots', 'pt': 'Robôs', 'en': 'Robots', 'fr': 'Robots', 'zh': '机器人', 'ca': 'Robots'},
    'carrito_titulo': {'es': 'Tu carrito', 'pt': 'O seu carrinho', 'en': 'Your cart', 'fr': 'Votre panier', 'zh': '您的购物车', 'ca': 'El teu carret'},
    'carrito_total': {'es': 'Total', 'pt': 'Total', 'en': 'Total', 'fr': 'Total', 'zh': '总计', 'ca': 'Total'},
    'carrito_nota_envio': {'es': 'Los gastos de envío y los impuestos se calculan al finalizar la compra.', 'pt': 'Os custos de envio e os impostos são calculados na finalização da compra.', 'en': 'Shipping and taxes are calculated at checkout.', 'fr': 'Les frais de livraison et les taxes sont calculés lors du paiement.', 'zh': '运费和税费将在结算时计算。', 'ca': "Les despeses d'enviament i els impostos es calculen en finalitzar la compra."},
    'carrito_finalizar': {'es': 'Finalizar compra', 'pt': 'Finalizar compra', 'en': 'Checkout', 'fr': 'Finaliser la commande', 'zh': '结算', 'ca': 'Finalitzar la compra'},
    'carrito_asesor': {'es': '¿Prefieres que te asesoremos antes? Escríbenos', 'pt': 'Prefere que o aconselhemos antes? Escreva-nos', 'en': 'Prefer to talk to us first? Get in touch', 'fr': 'Vous préférez être conseillé au préalable ? Contactez-nous', 'zh': '希望先获得咨询？请联系我们', 'ca': "Prefereixes que t'assessorem abans? Escriu-nos"},
    'carrito_vacio': {'es': 'Todavía no has añadido ningún robot.', 'pt': 'Ainda não adicionou nenhum robô.', 'en': "You haven't added any robots yet.", 'fr': "Vous n'avez encore ajouté aucun robot.", 'zh': '您还未添加任何机器人。', 'ca': 'Encara no has afegit cap robot.'},
    'carrito_ver_catalogo': {'es': 'Ver el catálogo', 'pt': 'Ver o catálogo', 'en': 'View the catalog', 'fr': 'Voir le catalogue', 'zh': '查看产品目录', 'ca': 'Veure el catàleg'},
    'aviso_legal': {'es': 'Aviso Legal', 'pt': 'Aviso Legal', 'en': 'Legal Notice', 'fr': 'Mentions légales', 'zh': '法律声明', 'ca': 'Avís Legal'},
    'politica_privacidad': {'es': 'Política de Privacidad', 'pt': 'Política de Privacidade', 'en': 'Privacy Policy', 'fr': 'Politique de confidentialité', 'zh': '隐私政策', 'ca': 'Política de Privacitat'},
    'politica_cookies': {'es': 'Política de Cookies', 'pt': 'Política de Cookies', 'en': 'Cookie Policy', 'fr': 'Politique de cookies', 'zh': 'Cookie政策', 'ca': 'Política de Cookies'},
    'recursos_humanoides': {'es': 'Recursos Humanoides', 'pt': 'Recursos Humanoides', 'en': 'Humanoid Resources', 'fr': 'Ressources Humanoïdes', 'zh': '人形资源', 'ca': 'Recursos Humanoides'},
    'pide_info': {'es': 'Pide más información', 'pt': 'Peça mais informações', 'en': 'Ask for more information', 'fr': "Demandez plus d'informations", 'zh': '获取更多信息', 'ca': 'Demana més informació'},
    'ver_especificaciones': {'es': 'Ver especificaciones', 'pt': 'Ver especificações', 'en': 'View specifications', 'fr': 'Voir les spécifications', 'zh': '查看技术参数', 'ca': 'Veure especificacions'},
    'que_es_pregunta': {'es': '¿Qué es el {n}?', 'pt': 'O que é o {n}?', 'en': 'What is the {n}?', 'fr': "Qu'est-ce que le {n} ?", 'zh': '{n} 是什么？', 'ca': 'Què és el {n}?'},
    'aplicaciones_de': {'es': 'Aplicaciones del {n}', 'pt': 'Aplicações do {n}', 'en': 'Applications of the {n}', 'fr': 'Applications du {n}', 'zh': '{n} 的应用场景', 'ca': 'Aplicacions del {n}'},
    'escenarios_encaja': {'es': 'Escenarios en los que encaja el {n}.', 'pt': 'Cenários em que o {n} se enquadra.', 'en': 'Scenarios where the {n} fits in.', 'fr': 'Scénarios dans lesquels le {n} trouve sa place.', 'zh': '{n} 适用的应用场景。', 'ca': 'Escenaris en què encaixa el {n}.'},
    'specs_tecnicas_de': {'es': 'Especificaciones técnicas del {n}', 'pt': 'Especificações técnicas do {n}', 'en': 'Technical specifications of the {n}', 'fr': 'Spécifications techniques du {n}', 'zh': '{n} 的技术参数', 'ca': 'Especificacions tècniques del {n}'},
    'ver_ficha_completa': {'es': 'Ver la ficha técnica completa', 'pt': 'Ver a ficha técnica completa', 'en': 'View the full technical sheet', 'fr': 'Voir la fiche technique complète', 'zh': '查看完整技术资料', 'ca': 'Veure la fitxa tècnica completa'},
    'galeria_de': {'es': 'Galería del {n}', 'pt': 'Galeria do {n}', 'en': 'Gallery of the {n}', 'fr': 'Galerie du {n}', 'zh': '{n} 图库', 'ca': 'Galeria del {n}'},
    'fotos_anteriores': {'es': 'Fotos anteriores', 'pt': 'Fotos anteriores', 'en': 'Previous photos', 'fr': 'Photos précédentes', 'zh': '上一组照片', 'ca': 'Fotos anteriors'},
    'fotos_siguientes': {'es': 'Fotos siguientes', 'pt': 'Fotos seguintes', 'en': 'Next photos', 'fr': 'Photos suivantes', 'zh': '下一组照片', 'ca': 'Fotos següents'},
    'antes_de_ofertar': {'es': 'Antes de ofertar este modelo', 'pt': 'Antes de orçamentar este modelo', 'en': 'Before quoting this model', 'fr': 'Avant de proposer ce modèle', 'zh': '报价此型号前须知', 'ca': 'Abans de pressupostar aquest model'},
    'doc_a_solicitar': {'es': 'Documentación a solicitar al fabricante.', 'pt': 'Documentação a solicitar ao fabricante.', 'en': 'Documentation to request from the manufacturer.', 'fr': 'Documentation à demander au fabricant.', 'zh': '需向制造商索取的文件。', 'ca': 'Documentació que cal sol·licitar al fabricant.'},
    'accesorios_para': {'es': 'Accesorios para el {n}', 'pt': 'Acessórios para o {n}', 'en': 'Accessories for the {n}', 'fr': 'Accessoires pour le {n}', 'zh': '{n} 配件', 'ca': 'Accessoris per al {n}'},
    'otros_modelos_familia': {'es': 'Otros modelos de la familia', 'pt': 'Outros modelos da família', 'en': 'Other models in the range', 'fr': 'Autres modèles de la gamme', 'zh': '同系列其他型号', 'ca': 'Altres models de la família'},
    'giralo': {'es': 'Gíralo', 'pt': 'Rode-o', 'en': 'Spin it', 'fr': 'Faites-le pivoter', 'zh': '旋转查看', 'ca': "Gira'l"},
    'vista_giratoria': {'es': '{n} — vista giratoria. Usa las flechas para girarlo.', 'pt': '{n} — vista giratória. Use as setas para o rodar.', 'en': '{n} — 360° view. Use the arrow keys to spin it.', 'fr': '{n} — vue à 360°. Utilisez les flèches pour le faire pivoter.', 'zh': '{n} — 360° 旋转视图。使用方向键旋转。', 'ca': '{n} — vista giratòria. Utilitza les fletxes per girar-lo.'},
    'navegador_sin_video': {'es': 'Tu navegador no puede reproducir este vídeo.', 'pt': 'O seu navegador não consegue reproduzir este vídeo.', 'en': "Your browser can't play this video.", 'fr': 'Votre navigateur ne peut pas lire cette vidéo.', 'zh': '您的浏览器无法播放此视频。', 'ca': 'El teu navegador no pot reproduir aquest vídeo.'},
    'en_video': {'es': 'El {n} en vídeo', 'pt': 'O {n} em vídeo', 'en': 'The {n} on video', 'fr': 'Le {n} en vidéo', 'zh': '{n} 视频介绍', 'ca': 'El {n} en vídeo'},
    'sin_stock': {'es': 'Sin stock — consúltanos la disponibilidad', 'pt': 'Sem stock — consulte-nos sobre a disponibilidade', 'en': 'Out of stock — ask us about availability', 'fr': 'Rupture de stock — contactez-nous pour connaître la disponibilité', 'zh': '暂无库存——请咨询我们了解供货情况', 'ca': "Sense estoc — consulta'ns la disponibilitat"},
    'avisame': {'es': 'Avísame cuando esté', 'pt': 'Avise-me quando estiver disponível', 'en': 'Notify me when available', 'fr': 'Prévenez-moi quand il sera disponible', 'zh': '到货时通知我', 'ca': "Avisa'm quan estigui disponible"},
    'precio_consulta': {'es': 'Precio bajo consulta', 'pt': 'Preço sob consulta', 'en': 'Price on request', 'fr': 'Prix sur demande', 'zh': '价格详询', 'ca': 'Preu a consultar'},
    'pedir_presupuesto': {'es': 'Pedir presupuesto', 'pt': 'Pedir orçamento', 'en': 'Request a quote', 'fr': 'Demander un devis', 'zh': '索取报价', 'ca': 'Demanar pressupost'},
    'anadir_carrito': {'es': 'Añadir al carrito', 'pt': 'Adicionar ao carrinho', 'en': 'Add to cart', 'fr': 'Ajouter au panier', 'zh': '加入购物车', 'ca': 'Afegir al carret'},
    'comprar_ahora': {'es': 'Comprar ahora', 'pt': 'Comprar agora', 'en': 'Buy now', 'fr': 'Acheter maintenant', 'zh': '立即购买', 'ca': 'Comprar ara'},
    'pvp': {'es': 'PVP', 'pt': 'PVP', 'en': 'RRP', 'fr': 'Prix public', 'zh': '建议零售价', 'ca': 'PVP'},
    'preguntas_frecuentes': {'es': 'Preguntas frecuentes', 'pt': 'Perguntas frequentes', 'en': 'Frequently asked questions', 'fr': 'Questions fréquentes', 'zh': '常见问题', 'ca': 'Preguntes freqüents'},
    'distribuidores_oficiales': {'es': 'Distribuidores oficiales en España y Portugal', 'pt': 'Distribuidores oficiais em Espanha e Portugal', 'en': 'Official distributors in Spain and Portugal', 'fr': 'Distributeurs officiels en Espagne et au Portugal', 'zh': '西班牙和葡萄牙官方经销商', 'ca': 'Distribuïdors oficials a Espanya i Portugal'},
    'ver_robots': {'es': 'Ver los robots', 'pt': 'Ver os robôs', 'en': 'View the robots', 'fr': 'Voir les robots', 'zh': '查看机器人', 'ca': 'Veure els robots'},
    'habla_nosotros': {'es': 'Habla con nosotros', 'pt': 'Fale connosco', 'en': 'Talk to us', 'fr': 'Parlez-nous', 'zh': '联系我们', 'ca': 'Parla amb nosaltres'},
    'ver_todos_modelos': {'es': 'Ver todos los modelos', 'pt': 'Ver todos os modelos', 'en': 'View all models', 'fr': 'Voir tous les modèles', 'zh': '查看所有型号', 'ca': 'Veure tots els models'},
    'modelos_disponibles': {'es': 'Modelos disponibles', 'pt': 'Modelos disponíveis', 'en': 'Available models', 'fr': 'Modèles disponibles', 'zh': '可选型号', 'ca': 'Models disponibles'},
    'modelos_anteriores': {'es': 'Modelos anteriores', 'pt': 'Modelos anteriores', 'en': 'Previous models', 'fr': 'Modèles précédents', 'zh': '上一组型号', 'ca': 'Models anteriors'},
    'modelos_siguientes': {'es': 'Modelos siguientes', 'pt': 'Modelos seguintes', 'en': 'Next models', 'fr': 'Modèles suivants', 'zh': '下一组型号', 'ca': 'Models següents'},
    'ver_modelo': {'es': 'Ver modelo', 'pt': 'Ver modelo', 'en': 'View model', 'fr': 'Voir le modèle', 'zh': '查看型号', 'ca': 'Veure model'},
    'no_sabes_robot_titulo': {'es': '¿No sabes qué robot encaja mejor?', 'pt': 'Não sabe que robô se adapta melhor?', 'en': 'Not sure which robot fits best?', 'fr': 'Vous ne savez pas quel robot convient le mieux ?', 'zh': '不确定哪款机器人最适合您？', 'ca': 'No saps quin robot encaixa millor?'},
    'no_sabes_robot_texto': {'es': 'Cuéntanos tu proyecto y te ayudamos a seleccionar la familia, el modelo y la configuración más adecuada para tu empresa o centro.', 'pt': 'Conte-nos o seu projeto e ajudamo-lo a selecionar a família, o modelo e a configuração mais adequada para a sua empresa ou centro.', 'en': "Tell us about your project and we'll help you choose the range, model and configuration that best suits your company or centre.", 'fr': 'Parlez-nous de votre projet et nous vous aiderons à choisir la gamme, le modèle et la configuration les plus adaptés à votre entreprise ou établissement.', 'zh': '告诉我们您的项目需求，我们将协助您为企业或机构挑选最合适的系列、型号和配置。', 'ca': "Explica'ns el teu projecte i t'ajudem a seleccionar la família, el model i la configuració més adequada per a la teva empresa o centre."},
    'hablar_rhbots': {'es': 'Hablar con RH·BOTS', 'pt': 'Falar com a RH·BOTS', 'en': 'Talk to RH·BOTS', 'fr': 'Parler avec RH·BOTS', 'zh': '联系 RH·BOTS', 'ca': 'Parlar amb RH·BOTS'},
    'catalogo_kicker': {'es': 'Catálogo RH·BOTS', 'pt': 'Catálogo RH·BOTS', 'en': 'RH·BOTS Catalog', 'fr': 'Catalogue RH·BOTS', 'zh': 'RH·BOTS 产品目录', 'ca': 'Catàleg RH·BOTS'},
    'catalogo_h1': {'es': 'Robots para empresas que quieren ir un paso por delante', 'pt': 'Robôs para empresas que querem estar um passo à frente', 'en': 'Robots for businesses that want to stay one step ahead', 'fr': "Des robots pour les entreprises qui veulent garder une longueur d'avance", 'zh': '为追求领先一步的企业打造的机器人', 'ca': 'Robots per a empreses que volen anar un pas per davant'},
    'catalogo_lede': {'es': 'Humanoides, cuadrúpedos, robots de limpieza, AMR de intralogística y accesorios para automatizar tareas, mejorar procesos y llevar la robótica avanzada a entornos reales. {n} modelos con ficha técnica completa y acompañamiento de principio a fin.', 'pt': 'Humanoides, quadrúpedes, robôs de limpeza, AMR de intralogística e acessórios para automatizar tarefas, melhorar processos e levar a robótica avançada a ambientes reais. {n} modelos com ficha técnica completa e acompanhamento do início ao fim.', 'en': 'Humanoid, quadruped and cleaning robots, intralogistics AMRs and accessories to automate tasks, improve processes and bring advanced robotics to real environments. {n} models with a full technical sheet and support from start to finish.', 'fr': "Humanoïdes, quadrupèdes, robots de nettoyage, AMR d'intralogistique et accessoires pour automatiser des tâches, améliorer les processus et apporter la robotique avancée dans des environnements réels. {n} modèles avec fiche technique complète et accompagnement de bout en bout.", 'zh': '人形机器人、四足机器人、清洁机器人、智能物流 AMR 及配件，助力任务自动化、优化流程，将先进机器人技术引入实际应用场景。{n} 款机型，配备完整技术资料，并提供从头到尾的全程支持。', 'ca': "Humanoides, quadrúpedes, robots de neteja, AMR d'intralogística i accessoris per automatitzar tasques, millorar processos i portar la robòtica avançada a entorns reals. {n} models amb fitxa tècnica completa i acompanyament de principi a fi."},
    'solicitar_asesoramiento': {'es': 'Solicitar asesoramiento', 'pt': 'Solicitar aconselhamento', 'en': 'Request advice', 'fr': 'Demander conseil', 'zh': '申请咨询', 'ca': 'Sol·licitar assessorament'},
    'ver_ficha_tecnica': {'es': 'Ver ficha técnica', 'pt': 'Ver ficha técnica', 'en': 'View technical sheet', 'fr': 'Voir la fiche technique', 'zh': '查看技术资料', 'ca': 'Veure fitxa tècnica'},
    'robots_para_uso': {'es': 'Robots para este uso', 'pt': 'Robôs para este uso', 'en': 'Robots for this use', 'fr': 'Robots pour cet usage', 'zh': '适用于此场景的机器人', 'ca': 'Robots per a aquest ús'},
    'cuentanos_tu_caso': {'es': 'Cuéntanos tu caso', 'pt': 'Conte-nos o seu caso', 'en': 'Tell us about your case', 'fr': 'Parlez-nous de votre cas', 'zh': '告诉我们您的需求', 'ca': "Explica'ns el teu cas"},
    'tienes_tarea_titulo': {'es': '¿Tienes una tarea que quieres automatizar?', 'pt': 'Tem uma tarefa que quer automatizar?', 'en': 'Have a task you want to automate?', 'fr': 'Vous avez une tâche que vous souhaitez automatiser ?', 'zh': '有想要实现自动化的任务吗？', 'ca': 'Tens una tasca que vols automatitzar?'},
    'tienes_tarea_texto': {'es': 'Cuéntanos tu caso y te orientamos sobre qué aplicación robótica puede encajar mejor en tu empresa.', 'pt': 'Conte-nos o seu caso e orientamo-lo sobre que aplicação robótica pode encaixar melhor na sua empresa.', 'en': "Tell us about your case and we'll advise you on which robotic application could best fit your business.", 'fr': "Parlez-nous de votre cas et nous vous orienterons vers l'application robotique la plus adaptée à votre entreprise.", 'zh': '告诉我们您的情况，我们将为您推荐最适合贵公司的机器人应用方案。', 'ca': "Explica'ns el teu cas i t'orientem sobre quina aplicació robòtica pot encaixar millor a la teva empresa."},
    'blog_kicker': {'es': 'RH·BOTS — Blog', 'pt': 'RH·BOTS — Blog', 'en': 'RH·BOTS — Blog', 'fr': 'RH·BOTS — Blog', 'zh': 'RH·BOTS — 博客', 'ca': 'RH·BOTS — Blog'},
    'blog_h1': {'es': 'Actualidad sobre <span class="acento">robótica humanoide</span>', 'pt': 'Atualidade sobre <span class="acento">robótica humanoide</span>', 'en': 'News on <span class="acento">humanoid robotics</span>', 'fr': 'Actualité sur <span class="acento">la robotique humanoïde</span>', 'zh': '关于<span class="acento">人形机器人技术</span>的最新资讯', 'ca': 'Actualitat sobre <span class="acento">robòtica humanoide</span>'},
    'blog_lede': {'es': 'Noticias, casos de uso y recursos para entender cómo los robots humanoides pueden integrarse en empresas reales de forma segura, útil y medible.', 'pt': 'Notícias, casos de uso e recursos para compreender como os robôs humanoides podem integrar-se em empresas reais de forma segura, útil e mensurável.', 'en': 'News, use cases and resources to understand how humanoid robots can be integrated into real businesses safely, usefully and measurably.', 'fr': "Actualités, cas d'usage et ressources pour comprendre comment les robots humanoïdes peuvent s'intégrer dans des entreprises réelles de manière sûre, utile et mesurable.", 'zh': '新闻资讯、应用案例和资源，帮助您了解人形机器人如何以安全、实用且可衡量的方式融入实际企业运营。', 'ca': "Notícies, casos d'ús i recursos per entendre com els robots humanoides poden integrar-se en empreses reals de manera segura, útil i mesurable."},
    'ver_articulos': {'es': 'Ver artículos', 'pt': 'Ver artigos', 'en': 'View articles', 'fr': 'Voir les articles', 'zh': '查看文章', 'ca': 'Veure articles'},
    'hablar_experto': {'es': 'Hablar con un experto', 'pt': 'Falar com um especialista', 'en': 'Talk to an expert', 'fr': 'Parler à un expert', 'zh': '咨询专家', 'ca': 'Parlar amb un expert'},
    'destacado': {'es': 'Destacado', 'pt': 'Destaque', 'en': 'Featured', 'fr': 'À la une', 'zh': '精选', 'ca': 'Destacat'},
    'min_lectura': {'es': 'min de lectura', 'pt': 'min de leitura', 'en': 'min read', 'fr': 'min de lecture', 'zh': '分钟阅读', 'ca': 'min de lectura'},
    'leer_articulo': {'es': 'Leer artículo', 'pt': 'Ler artigo', 'en': 'Read article', 'fr': "Lire l'article", 'zh': '阅读文章', 'ca': 'Llegir article'},
    'leer_mas': {'es': 'Leer más', 'pt': 'Ler mais', 'en': 'Read more', 'fr': 'Lire la suite', 'zh': '阅读更多', 'ca': 'Llegir més'},
    'mas_informacion': {'es': 'Más información', 'pt': 'Mais informações', 'en': 'More information',
                         'fr': "Plus d'informations", 'zh': '了解更多', 'ca': 'Més informació'},
    'conocimiento_aplicado': {'es': 'Conocimiento aplicado', 'pt': 'Conhecimento aplicado', 'en': 'Applied knowledge', 'fr': 'Connaissances appliquées', 'zh': '实用知识', 'ca': 'Coneixement aplicat'},
    'ideas_claras': {'es': 'Ideas claras para tomar mejores decisiones', 'pt': 'Ideias claras para tomar melhores decisões', 'en': 'Clear ideas for better decisions', 'fr': 'Des idées claires pour mieux décider', 'zh': '清晰的思路，助您做出更好的决策', 'ca': 'Idees clares per prendre millors decisions'},
    'buscar_articulos': {'es': 'Buscar artículos', 'pt': 'Pesquisar artigos', 'en': 'Search articles', 'fr': 'Rechercher des articles', 'zh': '搜索文章', 'ca': 'Cercar articles'},
    'buscar_articulos_placeholder': {'es': 'Buscar artículos…', 'pt': 'Pesquisar artigos…', 'en': 'Search articles…', 'fr': 'Rechercher des articles…', 'zh': '搜索文章……', 'ca': 'Cercar articles…'},
    'buscar': {'es': 'Buscar', 'pt': 'Pesquisar', 'en': 'Search', 'fr': 'Rechercher', 'zh': '搜索', 'ca': 'Cercar'},
    'ultimos_articulos': {'es': 'Últimos artículos', 'pt': 'Últimos artigos', 'en': 'Latest articles', 'fr': 'Derniers articles', 'zh': '最新文章', 'ca': 'Últims articles'},
    'recursos_presente': {'es': 'Recursos para entender el presente de la robótica', 'pt': 'Recursos para compreender o presente da robótica', 'en': 'Resources to understand robotics today', 'fr': "Des ressources pour comprendre la robotique d'aujourd'hui", 'zh': '了解机器人技术现状的资源', 'ca': 'Recursos per entendre el present de la robòtica'},
    'todos': {'es': 'Todos', 'pt': 'Todos', 'en': 'All', 'fr': 'Tous', 'zh': '全部', 'ca': 'Tots'},
    'sin_resultados_busqueda': {'es': 'No hay artículos que coincidan con tu búsqueda.', 'pt': 'Não há artigos que correspondam à sua pesquisa.', 'en': 'No articles match your search.', 'fr': 'Aucun article ne correspond à votre recherche.', 'zh': '没有与您的搜索匹配的文章。', 'ca': 'No hi ha articles que coincideixin amb la teva cerca.'},
    'preparando_articulos': {'es': 'Estamos preparando los primeros artículos', 'pt': 'Estamos a preparar os primeiros artigos', 'en': 'We are preparing our first articles', 'fr': 'Nous préparons nos premiers articles', 'zh': '我们正在准备首批文章', 'ca': 'Estem preparant els primers articles'},
    'preparando_articulos_texto': {'es': 'Aquí publicaremos novedades de producto, casos de uso de nuestros clientes y notas técnicas sobre los modelos del catálogo. Mientras tanto, puedes consultar las fichas técnicas o escribirnos directamente.', 'pt': 'Aqui publicaremos novidades de produto, casos de uso dos nossos clientes e notas técnicas sobre os modelos do catálogo. Entretanto, pode consultar as fichas técnicas ou escrever-nos diretamente.', 'en': "We'll publish product news, customer use cases and technical notes about our catalog here. In the meantime, you can check the technical sheets or write to us directly.", 'fr': "Nous y publierons des nouveautés produit, des cas d'usage de nos clients et des notes techniques sur les modèles du catalogue. En attendant, vous pouvez consulter les fiches techniques ou nous écrire directement.", 'zh': '我们将在这里发布产品动态、客户应用案例以及产品目录中各型号的技术说明。与此同时，您可以查阅技术资料或直接与我们联系。', 'ca': "Aquí publicarem novetats de producte, casos d'ús dels nostres clients i notes tècniques sobre els models del catàleg. Mentrestant, pots consultar les fitxes tècniques o escriure'ns directament."},
    'escribenos': {'es': 'Escríbenos', 'pt': 'Escreva-nos', 'en': 'Get in touch', 'fr': 'Contactez-nous', 'zh': '联系我们', 'ca': 'Escriu-nos'},
    'necesitas_orientacion': {'es': '¿Necesitas orientación?', 'pt': 'Precisa de orientação?', 'en': 'Need guidance?', 'fr': "Besoin d'être orienté ?", 'zh': '需要指导建议吗？', 'ca': 'Necessites orientació?'},
    'orienta_titulo': {'es': 'Te ayudamos a entender qué robot <span class="acento">encaja con tu empresa</span>', 'pt': 'Ajudamo-lo a compreender que robô <span class="acento">se adapta à sua empresa</span>', 'en': 'We help you understand which robot <span class="acento">fits your business</span>', 'fr': 'Nous vous aidons à comprendre quel robot <span class="acento">convient à votre entreprise</span>', 'zh': '我们帮您了解哪款机器人<span class="acento">适合您的企业</span>', 'ca': 'T\'ajudem a entendre quin robot <span class="acento">encaixa amb la teva empresa</span>'},
    'orienta_texto': {'es': 'Cuéntanos tu caso y nuestro equipo te asesorará sobre modelos, aplicaciones y próximos pasos.', 'pt': 'Conte-nos o seu caso e a nossa equipa aconselhá-lo-á sobre modelos, aplicações e próximos passos.', 'en': 'Tell us about your case and our team will advise you on models, applications and next steps.', 'fr': 'Parlez-nous de votre cas et notre équipe vous conseillera sur les modèles, les applications et les prochaines étapes.', 'zh': '告诉我们您的情况，我们的团队将为您提供关于型号、应用方案及后续步骤的建议。', 'ca': "Explica'ns el teu cas i el nostre equip t'assessorarà sobre models, aplicacions i propers passos."},
    'solicitar_informacion': {'es': 'Solicitar información', 'pt': 'Solicitar informação', 'en': 'Request information', 'fr': 'Demander des informations', 'zh': '索取资料', 'ca': 'Sol·licitar informació'},
    'volver_blog': {'es': '← Volver al blog', 'pt': '← Voltar ao blog', 'en': '← Back to blog', 'fr': '← Retour au blog', 'zh': '← 返回博客', 'ca': '← Tornar al blog'},
    'pagina_404_titulo': {'es': 'Esta página no existe', 'pt': 'Esta página não existe', 'en': "This page doesn't exist", 'fr': "Cette page n'existe pas", 'zh': '该页面不存在', 'ca': 'Aquesta pàgina no existeix'},
    'pagina_404_texto': {'es': 'Puede que el enlace esté mal escrito o que hayamos movido el contenido. Desde aquí llegas a todo:', 'pt': 'O link pode estar mal escrito ou podemos ter movido o conteúdo. A partir daqui chega a tudo:', 'en': 'The link may be mistyped, or we may have moved the content. You can get anywhere from here:', 'fr': 'Le lien est peut-être mal orthographié, ou nous avons déplacé le contenu. Vous pouvez tout retrouver depuis ici :', 'zh': '链接可能有误，或内容已被移动。您可以从这里访问全部内容：', 'ca': "Pot ser que l'enllaç estigui mal escrit o que hàgim mogut el contingut. Des d'aquí arribes a tot:"},
    'ir_inicio': {'es': 'Ir al inicio', 'pt': 'Ir para o início', 'en': 'Go to homepage', 'fr': "Aller à l'accueil", 'zh': '返回首页', 'ca': "Anar a l'inici"},
    'formulario': {'es': 'Formulario', 'pt': 'Formulário', 'en': 'Form', 'fr': 'Formulaire', 'zh': '表单', 'ca': 'Formulari'},
    'solicita_info': {'es': 'Solicita información', 'pt': 'Solicite informação', 'en': 'Request information', 'fr': 'Demandez des informations', 'zh': '索取资料', 'ca': 'Sol·licita informació'},
    'respuesta_personalizada': {'es': 'Respuesta personalizada', 'pt': 'Resposta personalizada', 'en': 'Personalised reply', 'fr': 'Réponse personnalisée', 'zh': '个性化回复', 'ca': 'Resposta personalitzada'},
    'nombre': {'es': 'Nombre', 'pt': 'Nome', 'en': 'First name', 'fr': 'Prénom', 'zh': '名字', 'ca': 'Nom'},
    'apellidos': {'es': 'Apellidos', 'pt': 'Apelido', 'en': 'Last name', 'fr': 'Nom', 'zh': '姓氏', 'ca': 'Cognoms'},
    'tu_nombre': {'es': 'Tu nombre', 'pt': 'O seu nome', 'en': 'Your first name', 'fr': 'Votre prénom', 'zh': '您的名字', 'ca': 'El teu nom'},
    'tus_apellidos': {'es': 'Tus apellidos', 'pt': 'O seu apelido', 'en': 'Your last name', 'fr': 'Votre nom', 'zh': '您的姓氏', 'ca': 'Els teus cognoms'},
    'email': {'es': 'Email', 'pt': 'Email', 'en': 'Email', 'fr': 'E-mail', 'zh': '邮箱', 'ca': 'Email'},
    'telefono': {'es': 'Teléfono', 'pt': 'Telefone', 'en': 'Phone', 'fr': 'Téléphone', 'zh': '电话', 'ca': 'Telèfon'},
    'empresa_campo': {'es': 'Empresa', 'pt': 'Empresa', 'en': 'Company', 'fr': 'Entreprise', 'zh': '公司', 'ca': 'Empresa'},
    'nombre_empresa_placeholder': {'es': 'Nombre de tu empresa', 'pt': 'Nome da sua empresa', 'en': 'Your company name', 'fr': 'Nom de votre entreprise', 'zh': '您的公司名称', 'ca': 'Nom de la teva empresa'},
    'que_robot_interesa': {'es': '¿En qué robot estás interesado?', 'pt': 'Em que robô está interessado?', 'en': 'Which robot are you interested in?', 'fr': 'Quel robot vous intéresse ?', 'zh': '您对哪款机器人感兴趣？', 'ca': 'En quin robot estàs interessat?'},
    'selecciona_modelo': {'es': 'Selecciona un modelo', 'pt': 'Selecione um modelo', 'en': 'Select a model', 'fr': 'Sélectionnez un modèle', 'zh': '请选择型号', 'ca': 'Selecciona un model'},
    'aun_no_lo_se': {'es': 'Aún no lo sé', 'pt': 'Ainda não sei', 'en': "I don't know yet", 'fr': 'Je ne sais pas encore', 'zh': '暂不确定', 'ca': 'Encara no ho sé'},
    'como_ayudarte': {'es': '¿Cómo podemos ayudarte?', 'pt': 'Como podemos ajudá-lo?', 'en': 'How can we help you?', 'fr': 'Comment pouvons-nous vous aider ?', 'zh': '我们能为您提供什么帮助？', 'ca': 'Com et podem ajudar?'},
    'mensaje_placeholder': {'es': 'Cuéntanos brevemente tu proyecto, necesidad o tipo de evento…', 'pt': 'Conte-nos brevemente o seu projeto, necessidade ou tipo de evento…', 'en': 'Briefly tell us about your project, need or type of event…', 'fr': "Décrivez-nous brièvement votre projet, votre besoin ou le type d'événement…", 'zh': '请简要介绍您的项目、需求或活动类型……', 'ca': "Explica'ns breument el teu projecte, necessitat o tipus d'esdeveniment…"},
    'consiento_privacidad': {'es': 'He leído y acepto la', 'pt': 'Li e aceito a', 'en': 'I have read and accept the', 'fr': "J'ai lu et j'accepte la", 'zh': '我已阅读并接受', 'ca': 'He llegit i accepto la'},
    'politica_privacidad_link': {'es': 'política de privacidad', 'pt': 'política de privacidade', 'en': 'privacy policy', 'fr': 'politique de confidentialité', 'zh': '隐私政策', 'ca': 'política de privacitat'},
    'consiento_privacidad_fin': {'es': '. Consiento el tratamiento de mis datos para recibir información comercial de RH·BOTS.', 'pt': '. Consinto o tratamento dos meus dados para receber informação comercial da RH·BOTS.', 'en': '. I consent to the processing of my data to receive commercial information from RH·BOTS.', 'fr': '. Je consens au traitement de mes données pour recevoir des informations commerciales de RH·BOTS.', 'zh': '。我同意 RH·BOTS 处理我的个人数据，以接收商业信息。', 'ca': '. Consento el tractament de les meves dades per rebre informació comercial de RH·BOTS.'},
    'enviar_mensaje': {'es': 'Enviar mensaje', 'pt': 'Enviar mensagem', 'en': 'Send message', 'fr': 'Envoyer le message', 'zh': '发送信息', 'ca': 'Enviar missatge'},
    'solicitar_asesoramiento_cta': {'es': 'Solicitar asesoramiento', 'pt': 'Solicitar aconselhamento', 'en': 'Request advice', 'fr': 'Demander conseil', 'zh': '申请咨询', 'ca': 'Sol·licitar assessorament'},
    'escribir_email': {'es': 'Escribir por email', 'pt': 'Escrever por email', 'en': 'Write by email', 'fr': 'Écrire par e-mail', 'zh': '发送邮件', 'ca': 'Escriure per email'},
    'email_directo_etq': {'es': 'Email directo', 'pt': 'Email direto', 'en': 'Direct email', 'fr': 'E-mail direct', 'zh': '直接邮箱', 'ca': 'Email directe'},
    'especialistas_en': {'es': 'Especialistas en', 'pt': 'Especialistas em', 'en': 'Specialists in', 'fr': 'Spécialistes en', 'zh': '专业领域', 'ca': 'Especialistes en'},
    'donde_estamos': {'es': 'Dónde estamos', 'pt': 'Onde estamos', 'en': 'Where we are', 'fr': 'Où nous trouver', 'zh': '我们的位置', 'ca': 'On som'},
    'llamanos_al': {'es': 'También puedes llamarnos al', 'pt': 'Também pode ligar-nos para o', 'en': 'You can also call us on', 'fr': 'Vous pouvez aussi nous appeler au', 'zh': '您也可以致电', 'ca': 'També ens pots trucar al'},
    'escribenos_directamente': {'es': 'También puedes escribirnos directamente a', 'pt': 'Também pode escrever-nos diretamente para', 'en': 'You can also write to us directly at', 'fr': 'Vous pouvez aussi nous écrire directement à', 'zh': '您也可以直接发邮件至', 'ca': 'També ens pots escriure directament a'},
    'aviso_legal_titulo': {'es': 'Aviso legal, privacidad y cookies', 'pt': 'Aviso legal, privacidade e cookies', 'en': 'Legal notice, privacy and cookies', 'fr': 'Mentions légales, confidentialité et cookies', 'zh': '法律声明、隐私与Cookie政策', 'ca': 'Avís legal, privacitat i cookies'},
    'pagina_no_encontrada': {'es': 'Página no encontrada | RH·BOTS', 'pt': 'Página não encontrada | RH·BOTS', 'en': 'Page not found | RH·BOTS', 'fr': 'Page non trouvée | RH·BOTS', 'zh': '页面未找到 | RH·BOTS', 'ca': 'Pàgina no trobada | RH·BOTS'},
    'pagina_no_encontrada_desc': {'es': 'La página que buscas no existe o ha cambiado de sitio.', 'pt': 'A página que procura não existe ou mudou de sítio.', 'en': "The page you're looking for doesn't exist or has moved.", 'fr': "La page que vous recherchez n'existe pas ou a changé d'adresse.", 'zh': '您访问的页面不存在或已移动。', 'ca': 'La pàgina que busques no existeix o ha canviat de lloc.'},
    'contacto_titulo': {'es': 'Contacto | RH·BOTS', 'pt': 'Contacto | RH·BOTS', 'en': 'Contact | RH·BOTS', 'fr': 'Contact | RH·BOTS', 'zh': '联系我们 | RH·BOTS', 'ca': 'Contacte | RH·BOTS'},
    'blog_titulo': {'es': 'Blog | RH·BOTS', 'pt': 'Blog | RH·BOTS', 'en': 'Blog | RH·BOTS', 'fr': 'Blog | RH·BOTS', 'zh': '博客 | RH·BOTS', 'ca': 'Blog | RH·BOTS'},
    'blog_desc': {'es': 'Novedades, casos de uso y notas técnicas sobre robótica de servicio e industrial.', 'pt': 'Novidades, casos de uso e notas técnicas sobre robótica de serviço e industrial.', 'en': 'News, use cases and technical notes on service and industrial robotics.', 'fr': "Actualités, cas d'usage et notes techniques sur la robotique de service et industrielle.", 'zh': '关于服务机器人和工业机器人的最新资讯、应用案例和技术说明。', 'ca': "Novetats, casos d'ús i notes tècniques sobre robòtica de servei i industrial."},
    'aplicaciones_titulo': {'es': 'Aplicaciones de los robots RH·BOTS por sector | RH·BOTS', 'pt': 'Aplicações dos robôs RH·BOTS por setor | RH·BOTS', 'en': 'RH·BOTS robots by sector | RH·BOTS', 'fr': 'Applications des robots RH·BOTS par secteur | RH·BOTS', 'zh': 'RH·BOTS 机器人行业应用 | RH·BOTS', 'ca': 'Aplicacions dels robots RH·BOTS per sector | RH·BOTS'},
    'robots_catalogo_titulo': {'es': 'Robots RH·BOTS — catálogo completo | RH·BOTS', 'pt': 'Robôs RH·BOTS — catálogo completo | RH·BOTS', 'en': 'RH·BOTS Robots — full catalog | RH·BOTS', 'fr': 'Robots RH·BOTS — catalogue complet | RH·BOTS', 'zh': 'RH·BOTS 机器人——完整产品目录 | RH·BOTS', 'ca': 'Robots RH·BOTS — catàleg complet | RH·BOTS'},
    'robots_catalogo_desc': {'es': 'Catálogo RH·BOTS: robots humanoides, cuadrúpedos, de limpieza y AMR de intralogística, y accesorios, con fichas técnicas completas.', 'pt': 'Catálogo RH·BOTS: robôs humanoides, quadrúpedes, de limpeza e AMR de intralogística, e acessórios, com fichas técnicas completas.', 'en': 'RH·BOTS catalog: humanoid, quadruped and cleaning robots, intralogistics AMRs and accessories, with full technical sheets.', 'fr': "Catalogue RH·BOTS : robots humanoïdes, quadrupèdes, de nettoyage et AMR d'intralogistique, ainsi que des accessoires, avec fiches techniques complètes.", 'zh': 'RH·BOTS 产品目录：人形机器人、四足机器人、清洁机器人、智能物流 AMR 及配件，配备完整技术资料。', 'ca': "Catàleg RH·BOTS: robots humanoides, quadrúpedes, de neteja i AMR d'intralogística, i accessoris, amb fitxes tècniques completes."},
    'inicio_titulo': {'es': 'RH·BOTS — Recursos humanoides para tu empresa', 'pt': 'RH·BOTS — Recursos humanoides para a sua empresa', 'en': 'RH·BOTS — Humanoid resources for your business', 'fr': 'RH·BOTS — Ressources humanoïdes pour votre entreprise', 'zh': 'RH·BOTS — 为企业提供人形资源', 'ca': 'RH·BOTS — Recursos humanoides per a la teva empresa'},
    'inicio_desc': {'es': 'Robots humanoides, cuadrúpedos, de limpieza y de intralogística. Asesoramiento, instalación, formación y soporte en Valencia.', 'pt': 'Robôs humanoides, quadrúpedes, de limpeza e de intralogística. Aconselhamento, instalação, formação e suporte em Valência.', 'en': 'Humanoid, quadruped, cleaning and intralogistics robots. Advice, installation, training and support from Valencia, Spain.', 'fr': "Robots humanoïdes, quadrupèdes, de nettoyage et d'intralogistique. Conseil, installation, formation et assistance à Valencia.", 'zh': '人形机器人、四足机器人、清洁机器人及物流机器人。在巴伦西亚为您提供咨询、安装、培训与支持服务。', 'ca': "Robots humanoides, quadrúpedes, de neteja i d'intralogística. Assessorament, instal·lació, formació i suport a València."},
    'legal_meta_titulo': {'es': 'Aviso legal, privacidad y cookies | RH·BOTS', 'pt': 'Aviso legal, privacidade e cookies | RH·BOTS', 'en': 'Legal notice, privacy and cookies | RH·BOTS', 'fr': 'Mentions légales, confidentialité et cookies | RH·BOTS', 'zh': '法律声明、隐私与Cookie政策 | RH·BOTS', 'ca': 'Avís legal, privacitat i cookies | RH·BOTS'},
    'legal_meta_desc': {'es': 'Aviso legal, política de privacidad y cookies de RH·BOTS.', 'pt': 'Aviso legal, política de privacidade e cookies da RH·BOTS.', 'en': "RH·BOTS's legal notice, privacy policy and cookie policy.", 'fr': 'Mentions légales, politique de confidentialité et cookies de RH·BOTS.', 'zh': 'RH·BOTS 的法律声明、隐私政策与Cookie政策。', 'ca': 'Avís legal, política de privacitat i cookies de RH·BOTS.'},
    'blog_articulo_sufijo': {'es': ' | Blog RH·BOTS', 'pt': ' | Blog RH·BOTS', 'en': ' | RH·BOTS Blog', 'fr': ' | Blog RH·BOTS', 'zh': ' | RH·BOTS 博客', 'ca': ' | Blog RH·BOTS'},
    'lang_switch_boton': {'es': 'Cambiar idioma', 'pt': 'Mudar de idioma', 'en': 'Change language', 'fr': 'Changer de langue', 'zh': '切换语言', 'ca': 'Canvia d\'idioma'},
    'carrito_abrir_boton': {'es': 'Abrir el carrito', 'pt': 'Abrir o carrinho', 'en': 'Open the cart', 'fr': 'Ouvrir le panier', 'zh': '打开购物车', 'ca': 'Obrir el carret'},
    'carrito_cerrar_boton': {'es': 'Cerrar el carrito', 'pt': 'Fechar o carrinho', 'en': 'Close the cart', 'fr': 'Fermer le panier', 'zh': '关闭购物车', 'ca': 'Tancar el carret'},
    'nav_ver_familias_aria': {'es': 'Ver familias y modelos de robots', 'pt': 'Ver famílias e modelos de robôs',
                               'en': 'View robot families and models', 'fr': 'Voir les familles et modèles de robots',
                               'zh': '查看机器人系列和型号', 'ca': 'Veure famílies i models de robots'},
    'nav_principal_aria': {'es': 'Navegación principal', 'pt': 'Navegação principal', 'en': 'Main navigation',
                            'fr': 'Navigation principale', 'zh': '主导航', 'ca': 'Navegació principal'},
    'nav_abrir_menu': {'es': 'Abrir menú', 'pt': 'Abrir menu', 'en': 'Open menu', 'fr': 'Ouvrir le menu',
                        'zh': '打开菜单', 'ca': 'Obre el menú'},
    'nav_cerrar_menu': {'es': 'Cerrar menú', 'pt': 'Fechar menu', 'en': 'Close menu', 'fr': 'Fermer le menu',
                         'zh': '关闭菜单', 'ca': 'Tanca el menú'},
    'marcas_distribuimos_aria': {'es': 'Marcas que distribuimos', 'pt': 'Marcas que distribuímos',
                                  'en': 'Brands we distribute', 'fr': 'Marques que nous distribuons',
                                  'zh': '我们经销的品牌', 'ca': 'Marques que distribuïm'},
    'filtrar_categoria_aria': {'es': 'Filtrar por categoría', 'pt': 'Filtrar por categoria', 'en': 'Filter by category',
                                'fr': 'Filtrer par catégorie', 'zh': '按类别筛选', 'ca': 'Filtrar per categoria'},
    'requiere_accesorio_titulo': {'es': 'Accesorio necesario', 'pt': 'Acessório necessário',
                                   'en': 'Required accessory', 'fr': 'Accessoire nécessaire',
                                   'zh': '必需配件', 'ca': 'Accessori necessari'},
    'iva_corto': {'es': '+ IVA', 'pt': '+ IVA', 'en': '+ VAT', 'fr': '+ TVA',
                   'zh': '+ 增值税', 'ca': '+ IVA'},
    'ev_modelo': {'es': 'Bonico es nuestro RHX2 Ultra', 'pt': 'O Bonico é o nosso RHX2 Ultra',
                   'en': 'Bonico is our RHX2 Ultra', 'fr': 'Bonico est notre RHX2 Ultra',
                   'zh': 'Bonico 就是我们的 RHX2 Ultra', 'ca': 'En Bonico és el nostre RHX2 Ultra'},
    'ev_foto_alt': {'es': 'Bonico, nuestro robot humanoide, atendiendo a un medio de comunicación',
                     'pt': 'O Bonico, o nosso robô humanoide, a atender um meio de comunicação',
                     'en': 'Bonico, our humanoid robot, being interviewed by a news outlet',
                     'fr': 'Bonico, notre robot humanoïde, interviewé par un média',
                     'zh': '我们的人形机器人 Bonico 正在接受媒体采访',
                     'ca': "En Bonico, el nostre robot humanoide, atenent un mitjà de comunicació"},
    'ev_solicitar': {'es': 'Solicitar presupuesto', 'pt': 'Pedir orçamento', 'en': 'Request a quote',
                      'fr': 'Demander un devis', 'zh': '索取报价', 'ca': 'Sol·licitar pressupost'},
    'ev_como_funciona': {'es': 'Ver cómo funciona', 'pt': 'Ver como funciona', 'en': 'See how it works',
                          'fr': 'Voir comment ça marche', 'zh': '了解服务流程', 'ca': 'Veure com funciona'},
    'ev_desde': {'es': 'Desde', 'pt': 'Desde', 'en': 'From', 'fr': 'À partir de', 'zh': '起价', 'ca': 'Des de'},
    'ev_dia': {'es': '/ día', 'pt': '/ dia', 'en': '/ day', 'fr': '/ jour', 'zh': '/ 天', 'ca': '/ dia'},
    'ev_personalizar': {'es': 'Quiero personalizar a Bonico', 'pt': 'Quero personalizar o Bonico',
                         'en': 'I want to customise Bonico', 'fr': 'Je veux personnaliser Bonico',
                         'zh': '我想定制 Bonico', 'ca': 'Vull personalitzar en Bonico'},
    'ev_personalizacion_desde': {'es': 'Personalización desde', 'pt': 'Personalização desde',
                                  'en': 'Customisation from', 'fr': 'Personnalisation à partir de',
                                  'zh': '定制起价', 'ca': 'Personalització des de'},
    'ev_form_titulo': {'es': 'Cuéntanos tu evento', 'pt': 'Fale-nos do seu evento', 'en': 'Tell us about your event',
                        'fr': 'Parlez-nous de votre événement', 'zh': '介绍您的活动', 'ca': "Explica'ns el teu esdeveniment"},
    'ev_form_sello': {'es': 'Respuesta en 24-48 h laborables', 'pt': 'Resposta em 24-48 h úteis',
                       'en': 'Reply within 24-48 working hours', 'fr': 'Réponse sous 24-48 h ouvrées',
                       'zh': '24-48个工作小时内回复', 'ca': 'Resposta en 24-48 h laborables'},
    'ev_fecha': {'es': 'Fecha del evento', 'pt': 'Data do evento', 'en': 'Event date',
                  'fr': "Date de l'événement", 'zh': '活动日期', 'ca': 'Data de l\'esdeveniment'},
    'ev_ciudad': {'es': 'Ciudad', 'pt': 'Cidade', 'en': 'City', 'fr': 'Ville', 'zh': '城市', 'ca': 'Ciutat'},
    'ev_ciudad_ph': {'es': 'Valencia, Madrid, Lisboa…', 'pt': 'Lisboa, Porto, Madrid…',
                      'en': 'Valencia, Madrid, Lisbon…', 'fr': 'Valence, Madrid, Lisbonne…',
                      'zh': '瓦伦西亚、马德里、里斯本……', 'ca': 'València, Madrid, Lisboa…'},
    'ev_dias': {'es': 'Número de días', 'pt': 'Número de dias', 'en': 'Number of days',
                 'fr': 'Nombre de jours', 'zh': '天数', 'ca': 'Nombre de dies'},
    'ev_tipo': {'es': 'Tipo de evento', 'pt': 'Tipo de evento', 'en': 'Type of event',
                 'fr': "Type d'événement", 'zh': '活动类型', 'ca': "Tipus d'esdeveniment"},
    'ev_tipo_ph': {'es': 'Feria, congreso, lanzamiento…', 'pt': 'Feira, congresso, lançamento…',
                    'en': 'Trade fair, congress, product launch…', 'fr': 'Salon, congrès, lancement…',
                    'zh': '展会、大会、新品发布……', 'ca': 'Fira, congrés, llançament…'},
    'ev_que_haga': {'es': '¿Qué te gustaría que hiciera Bonico?', 'pt': 'O que gostaria que o Bonico fizesse?',
                     'en': 'What would you like Bonico to do?', 'fr': 'Que souhaitez-vous que Bonico fasse ?',
                     'zh': '您希望 Bonico 做什么？', 'ca': "Què t'agradaria que fes en Bonico?"},
    'ev_que_haga_ph': {'es': 'Bailar, recibir visitantes, presentar un producto…',
                        'pt': 'Dançar, receber visitantes, apresentar um produto…',
                        'en': 'Dance, greet visitors, present a product…',
                        'fr': 'Danser, accueillir les visiteurs, présenter un produit…',
                        'zh': '跳舞、迎宾、介绍产品……',
                        'ca': 'Ballar, rebre visitants, presentar un producte…'},
    'ev_mensaje': {'es': 'Mensaje', 'pt': 'Mensagem', 'en': 'Message', 'fr': 'Message',
                    'zh': '留言', 'ca': 'Missatge'},
    'ev_mensaje_ph': {'es': 'Cualquier detalle que nos ayude a preparar la propuesta.',
                       'pt': 'Qualquer detalhe que nos ajude a preparar a proposta.',
                       'en': 'Anything else that helps us prepare the proposal.',
                       'fr': 'Tout détail qui nous aide à préparer la proposition.',
                       'zh': '任何有助于我们准备方案的细节。',
                       'ca': 'Qualsevol detall que ens ajudi a preparar la proposta.'},
    'con_iva': {'es': 'Con IVA (21 %): {n}', 'pt': 'Com IVA (21 %): {n}',
                 'en': 'With VAT (21%): {n}', 'fr': 'TVA comprise (21 %) : {n}',
                 'zh': '含增值税（21%）：{n}', 'ca': 'Amb IVA (21 %): {n}'},
    'iva_no_incluido': {'es': 'IVA no incluido', 'pt': 'IVA não incluído',
                         'en': 'VAT not included', 'fr': 'TVA non incluse',
                         'zh': '不含增值税', 'ca': 'IVA no inclòs'},
    'nav_ver_alquiler_aria': {'es': 'Ver opciones de alquiler', 'pt': 'Ver opções de aluguer',
                               'en': 'View rental options', 'fr': 'Voir les options de location',
                               'zh': '查看租赁方案', 'ca': 'Veure opcions de lloguer'},
    'alquiler_limpieza_nav': {'es': 'Robots de limpieza industrial', 'pt': 'Robôs de limpeza industrial',
                               'en': 'Industrial cleaning robots', 'fr': 'Robots de nettoyage industriel',
                               'zh': '工业清洁机器人', 'ca': 'Robots de neteja industrial'},
    'alquiler_humanoides_nav': {'es': 'Humanoides para eventos', 'pt': 'Humanoides para eventos',
                                 'en': 'Humanoids for events', 'fr': 'Humanoïdes pour événements',
                                 'zh': '活动用人形机器人', 'ca': 'Humanoides per a esdeveniments'},
    'alquiler_titulo': {'es': 'Alquiler de robots | RH·BOTS', 'pt': 'Aluguer de robôs | RH·BOTS',
                         'en': 'Robot rental | RH·BOTS', 'fr': 'Location de robots | RH·BOTS',
                         'zh': '机器人租赁 | RH·BOTS', 'ca': 'Lloguer de robots | RH·BOTS'},
    'alquiler_limpieza_titulo': {'es': 'Alquiler de robots de limpieza industrial | RH·BOTS',
                                  'pt': 'Aluguer de robôs de limpeza industrial | RH·BOTS',
                                  'en': 'Industrial cleaning robot rental | RH·BOTS',
                                  'fr': 'Location de robots de nettoyage industriel | RH·BOTS',
                                  'zh': '工业清洁机器人租赁 | RH·BOTS',
                                  'ca': 'Lloguer de robots de neteja industrial | RH·BOTS'},
    'alquiler_humanoides_titulo': {'es': 'Bonico: alquiler de robot humanoide para eventos | RH·BOTS',
                                    'pt': 'Bonico: aluguer de robô humanoide para eventos | RH·BOTS',
                                    'en': 'Bonico: humanoid robot hire for events | RH·BOTS',
                                    'fr': "Bonico : location de robot humanoïde pour événements | RH·BOTS",
                                    'zh': 'Bonico：活动与展会人形机器人租赁 | RH·BOTS',
                                    'ca': "Bonico: lloguer de robot humanoide per a esdeveniments | RH·BOTS"},
    'alquiler_humanoides_desc': {'es': 'Alquila a Bonico, nuestro robot humanoide, para ferias, congresos, '
                                        'stands y eventos corporativos. Baila, interactúa y atrae visitantes '
                                        'a tu marca. Desde 1.200 €/día + IVA.',
                                  'pt': 'Alugue o Bonico, o nosso robô humanoide, para feiras, congressos, '
                                        'stands e eventos corporativos. Dança, interage e atrai visitantes à '
                                        'sua marca. Desde 1.200 €/dia + IVA.',
                                  'en': 'Hire Bonico, our humanoid robot, for trade fairs, conferences, stands '
                                        'and corporate events. It dances, interacts and draws visitors to your '
                                        'brand. From 1,200 €/day + VAT.',
                                  'fr': 'Louez Bonico, notre robot humanoïde, pour salons, congrès, stands et '
                                        "événements d'entreprise. Il danse, interagit et attire les visiteurs "
                                        'vers votre marque. À partir de 1 200 €/jour + TVA.',
                                  'zh': '租赁我们的人形机器人 Bonico，用于展会、大会、展台和企业活动。它会跳舞、'
                                        '与观众互动，为您的品牌吸引人流。每天1,200 €起（不含增值税）。',
                                  'ca': "Lloga en Bonico, el nostre robot humanoide, per a fires, congressos, "
                                        'estands i esdeveniments corporatius. Balla, interactua i atrau '
                                        'visitants a la teva marca. Des de 1.200 €/dia + IVA.'},
    'tarifa_titulo': {'es': 'Cuotas de alquiler', 'pt': 'Mensalidades de aluguer',
                       'en': 'Rental rates', 'fr': 'Loyers mensuels',
                       'zh': '租赁月费', 'ca': 'Quotes de lloguer'},
    'tarifa_plazo': {'es': 'Plazo', 'pt': 'Prazo', 'en': 'Term', 'fr': 'Durée du contrat',
                      'zh': '租期', 'ca': 'Termini'},
    'tarifa_duracion': {'es': 'Duración', 'pt': 'Duração', 'en': 'Length', 'fr': 'Durée',
                         'zh': '时长', 'ca': 'Durada'},
    'tarifa_cuota': {'es': 'Cuota mensual', 'pt': 'Mensalidade', 'en': 'Monthly rate',
                      'fr': 'Loyer mensuel', 'zh': '月费', 'ca': 'Quota mensual'},
    'tarifa_desde': {'es': 'Desde {n}/mes', 'pt': 'Desde {n}/mês', 'en': 'From {n}/month',
                      'fr': 'À partir de {n}/mois', 'zh': '每月{n}起', 'ca': 'Des de {n}/mes'},
    'tarifa_cuota_sin': {'es': 'Cuota sin IVA', 'pt': 'Mensalidade sem IVA', 'en': 'Monthly rate excl. VAT',
                          'fr': 'Loyer HT', 'zh': '月费（不含税）', 'ca': 'Quota sense IVA'},
    'tarifa_cuota_con': {'es': 'Cuota con IVA', 'pt': 'Mensalidade com IVA', 'en': 'Monthly rate incl. VAT',
                          'fr': 'Loyer TTC', 'zh': '月费（含税）', 'ca': 'Quota amb IVA'},
    'con_iva_generico': {'es': 'los importes con IVA incluyen el 21 % español',
                          'pt': 'os valores com IVA incluem os 21 % espanhóis',
                          'en': 'prices with VAT include the 21% Spanish rate',
                          'fr': 'les montants TTC incluent la TVA espagnole de 21 %',
                          'zh': '含税金额按西班牙 21% 的税率计算',
                          'ca': 'els imports amb IVA inclouen el 21 % espanyol'},
    'alquiler_incluye': {'es': 'Qué incluye la cuota', 'pt': 'O que inclui a mensalidade',
                          'en': "What's included in the rate", 'fr': 'Ce que comprend le loyer',
                          'zh': '月费包含内容', 'ca': 'Què inclou la quota'},
    'alquiler_incluye_si': {'es': 'Incluido', 'pt': 'Incluído', 'en': 'Included',
                             'fr': 'Inclus', 'zh': '包含', 'ca': 'Inclòs'},
    'alquiler_incluye_no': {'es': 'No incluido', 'pt': 'Não incluído', 'en': 'Not included',
                             'fr': 'Non inclus', 'zh': '不包含', 'ca': 'No inclòs'},
    'home_alquiler_kicker': {'es': 'Alquiler', 'pt': 'Aluguer', 'en': 'Rental',
                              'fr': 'Location', 'zh': '租赁', 'ca': 'Lloguer'},
    'home_alquiler_titulo': {'es': 'También puedes alquilar el robot',
                              'pt': 'Também pode alugar o robô',
                              'en': 'You can also rent the robot',
                              'fr': 'Vous pouvez aussi louer le robot',
                              'zh': '机器人也可以租',
                              'ca': 'També pots llogar el robot'},
    'alquiler_cta_titulo': {'es': '¿Te encaja el alquiler?', 'pt': 'O aluguer encaixa consigo?',
                             'en': 'Does renting fit your case?', 'fr': 'La location vous convient ?',
                             'zh': '租赁方案适合您吗？', 'ca': 'T\'encaixa el lloguer?'},
    'alquiler_cta_texto': {'es': 'Cuéntanos qué superficie tienes que limpiar o qué evento organizas y te '
                                  'preparamos una propuesta con el modelo y el plazo que mejor encajen.',
                            'pt': 'Diga-nos que superfície tem de limpar ou que evento organiza e preparamos '
                                  'uma proposta com o modelo e o prazo que melhor se adequem.',
                            'en': 'Tell us the area you need to clean or the event you are organising and '
                                  "we'll put together a proposal with the right model and term.",
                            'fr': 'Dites-nous quelle surface vous devez nettoyer ou quel événement vous '
                                  'organisez et nous préparons une proposition avec le modèle et la durée adaptés.',
                            'zh': '告诉我们您需要清洁的面积或举办的活动，我们会为您准备合适机型与租期的方案。',
                            'ca': "Explica'ns quina superfície has de netejar o quin esdeveniment organitzes i "
                                  'et preparem una proposta amb el model i el termini que millor encaixin.'},
    'alquiler_cta_eventos': {'es': 'Cuéntanos qué evento organizas, cuántos días y qué quieres que haga el '
                                   'robot, y te preparamos una propuesta cerrada.',
                              'pt': 'Diga-nos que evento organiza, quantos dias e o que quer que o robô faça, e '
                                    'preparamos uma proposta fechada.',
                              'en': 'Tell us what event you are organising, how many days and what you want the '
                                    'robot to do, and we will put together a firm proposal.',
                              'fr': 'Dites-nous quel événement vous organisez, combien de jours et ce que vous '
                                    'attendez du robot, et nous préparons une proposition ferme.',
                              'zh': '告诉我们您举办什么活动、租期几天、希望机器人做什么，我们会为您准备一份确定的方案。',
                              'ca': "Explica'ns quin esdeveniment organitzes, quants dies i què vols que faci el "
                                    'robot, i et preparem una proposta tancada.'},
    'alquiler_solicitar': {'es': 'Solicitar este robot', 'pt': 'Solicitar este robô',
                            'en': 'Request this robot', 'fr': 'Demander ce robot',
                            'zh': '咨询此机型', 'ca': 'Sol·licitar aquest robot'},
    'requiere_accesorio_texto': {'es': 'Necesario para el {n}. Se vende por separado.',
                                  'pt': 'Necessário para o {n}. Vendido em separado.',
                                  'en': 'Required for the {n}. Sold separately.',
                                  'fr': 'Nécessaire pour le {n}. Vendu séparément.',
                                  'zh': '{n}必需配件，需单独购买。',
                                  'ca': 'Necessari per al {n}. Es ven per separat.'},
}


# ── alemán y árabe: se añaden sobre TEXTOS para no tocar el bloque original ──
TEXTOS_DE = {
    'saltar_contenido': 'Zum Inhalt springen',
    'ver_todo_catalogo': 'Gesamten Katalog ansehen',
    'nav_inicio': 'Start',
    'nav_robots': 'Roboter',
    'carrito_titulo': 'Ihr Warenkorb',
    'carrito_total': 'Gesamt',
    'carrito_nota_envio': 'Versandkosten und Steuern werden beim Bezahlvorgang berechnet.',
    'carrito_finalizar': 'Zur Kasse',
    'carrito_asesor': 'Lieber vorher beraten lassen? Schreiben Sie uns',
    'carrito_vacio': 'Sie haben noch keinen Roboter hinzugefügt.',
    'carrito_ver_catalogo': 'Zum Katalog',
    'aviso_legal': 'Impressum',
    'politica_privacidad': 'Datenschutzerklärung',
    'politica_cookies': 'Cookie-Richtlinie',
    'recursos_humanoides': 'Humanoide Ressourcen',
    'pide_info': 'Weitere Informationen anfordern',
    'ver_especificaciones': 'Technische Daten ansehen',
    'que_es_pregunta': 'Was ist der {n}?',
    'aplicaciones_de': 'Anwendungen des {n}',
    'escenarios_encaja': 'Szenarien, in die der {n} passt.',
    'specs_tecnicas_de': 'Technische Daten des {n}',
    'ver_ficha_completa': 'Vollständiges Datenblatt ansehen',
    'galeria_de': 'Galerie des {n}',
    'fotos_anteriores': 'Vorherige Fotos',
    'fotos_siguientes': 'Nächste Fotos',
    'antes_de_ofertar': 'Bevor Sie dieses Modell anbieten',
    'doc_a_solicitar': 'Beim Hersteller anzufordernde Unterlagen.',
    'accesorios_para': 'Zubehör für den {n}',
    'otros_modelos_familia': 'Weitere Modelle der Reihe',
    'giralo': 'Drehen',
    'vista_giratoria': '{n} — 360°-Ansicht. Mit den Pfeiltasten drehen.',
    'navegador_sin_video': 'Ihr Browser kann dieses Video nicht abspielen.',
    'en_video': 'Der {n} im Video',
    'sin_stock': 'Nicht auf Lager — fragen Sie uns nach der Verfügbarkeit',
    'avisame': 'Benachrichtigt mich, sobald verfügbar',
    'precio_consulta': 'Preis auf Anfrage',
    'pedir_presupuesto': 'Angebot anfordern',
    'anadir_carrito': 'In den Warenkorb',
    'comprar_ahora': 'Jetzt kaufen',
    'pvp': 'UVP',
    'preguntas_frecuentes': 'Häufige Fragen',
    'distribuidores_oficiales': 'Offizieller Vertriebspartner in Spanien und Portugal',
    'ver_robots': 'Roboter ansehen',
    'habla_nosotros': 'Sprechen Sie mit uns',
    'ver_todos_modelos': 'Alle Modelle ansehen',
    'modelos_disponibles': 'Verfügbare Modelle',
    'modelos_anteriores': 'Vorherige Modelle',
    'modelos_siguientes': 'Nächste Modelle',
    'ver_modelo': 'Modell ansehen',
    'no_sabes_robot_titulo': 'Sie wissen nicht, welcher Roboter am besten passt?',
    'no_sabes_robot_texto': 'Erzählen Sie uns von Ihrem Projekt und wir helfen Ihnen, die passende Reihe, das passende Modell und die passende Konfiguration für Ihr Unternehmen oder Ihre Einrichtung zu finden.',
    'hablar_rhbots': 'Mit RH·BOTS sprechen',
    'catalogo_kicker': 'RH·BOTS Katalog',
    'catalogo_h1': 'Roboter für Unternehmen, die einen Schritt voraus sein wollen',
    'catalogo_lede': 'Humanoide, vierbeinige Roboter, Reinigungsroboter, AMR für die Intralogistik und Zubehör, um Aufgaben zu automatisieren, Prozesse zu verbessern und fortschrittliche Robotik in reale Umgebungen zu bringen. {n} Modelle mit vollständigem Datenblatt und Begleitung von Anfang bis Ende.',
    'solicitar_asesoramiento': 'Beratung anfordern',
    'ver_ficha_tecnica': 'Datenblatt ansehen',
    'robots_para_uso': 'Roboter für diesen Einsatz',
    'cuentanos_tu_caso': 'Erzählen Sie uns Ihren Fall',
    'tienes_tarea_titulo': 'Haben Sie eine Aufgabe, die Sie automatisieren möchten?',
    'tienes_tarea_texto': 'Erzählen Sie uns Ihren Fall und wir beraten Sie, welche Robotikanwendung am besten zu Ihrem Unternehmen passt.',
    'blog_kicker': 'RH·BOTS — Blog',
    'blog_h1': 'Neues aus der <span class="acento">humanoiden Robotik</span>',
    'blog_lede': 'Nachrichten, Anwendungsfälle und Ressourcen, um zu verstehen, wie sich humanoide Roboter sicher, nützlich und messbar in reale Unternehmen integrieren lassen.',
    'ver_articulos': 'Beiträge ansehen',
    'hablar_experto': 'Mit einem Experten sprechen',
    'destacado': 'Empfohlen',
    'min_lectura': 'Min. Lesezeit',
    'leer_articulo': 'Beitrag lesen',
    'leer_mas': 'Weiterlesen',
    'mas_informacion': 'Mehr Informationen',
    'conocimiento_aplicado': 'Angewandtes Wissen',
    'ideas_claras': 'Klare Ideen für bessere Entscheidungen',
    'buscar_articulos': 'Beiträge suchen',
    'buscar_articulos_placeholder': 'Beiträge suchen…',
    'buscar': 'Suchen',
    'ultimos_articulos': 'Neueste Beiträge',
    'recursos_presente': 'Ressourcen, um die Robotik von heute zu verstehen',
    'todos': 'Alle',
    'sin_resultados_busqueda': 'Keine Beiträge passen zu Ihrer Suche.',
    'preparando_articulos': 'Wir bereiten unsere ersten Beiträge vor',
    'preparando_articulos_texto': 'Hier veröffentlichen wir Produktneuheiten, Anwendungsfälle unserer Kunden und technische Hinweise zu den Modellen des Katalogs. In der Zwischenzeit können Sie die Datenblätter ansehen oder uns direkt schreiben.',
    'escribenos': 'Schreiben Sie uns',
    'necesitas_orientacion': 'Brauchen Sie Orientierung?',
    'orienta_titulo': 'Wir helfen Ihnen zu verstehen, welcher Roboter <span class="acento">zu Ihrem Unternehmen passt</span>',
    'orienta_texto': 'Erzählen Sie uns Ihren Fall und unser Team berät Sie zu Modellen, Anwendungen und nächsten Schritten.',
    'solicitar_informacion': 'Informationen anfordern',
    'volver_blog': '← Zurück zum Blog',
    'pagina_404_titulo': 'Diese Seite gibt es nicht',
    'pagina_404_texto': 'Vielleicht ist der Link falsch geschrieben oder wir haben den Inhalt verschoben. Von hier aus kommen Sie überall hin:',
    'ir_inicio': 'Zur Startseite',
    'formulario': 'Formular',
    'solicita_info': 'Informationen anfordern',
    'respuesta_personalizada': 'Persönliche Antwort',
    'nombre': 'Vorname',
    'apellidos': 'Nachname',
    'tu_nombre': 'Ihr Vorname',
    'tus_apellidos': 'Ihr Nachname',
    'email': 'E-Mail',
    'telefono': 'Telefon',
    'empresa_campo': 'Unternehmen',
    'nombre_empresa_placeholder': 'Name Ihres Unternehmens',
    'que_robot_interesa': 'Für welchen Roboter interessieren Sie sich?',
    'selecciona_modelo': 'Modell auswählen',
    'aun_no_lo_se': 'Weiß ich noch nicht',
    'como_ayudarte': 'Wie können wir Ihnen helfen?',
    'mensaje_placeholder': 'Beschreiben Sie kurz Ihr Projekt, Ihren Bedarf oder Ihre Veranstaltung…',
    'consiento_privacidad': 'Ich habe die',
    'politica_privacidad_link': 'Datenschutzerklärung',
    'consiento_privacidad_fin': ' gelesen und akzeptiere sie. Ich willige in die Verarbeitung meiner Daten ein, um Informationen von RH·BOTS zu erhalten.',
    'enviar_mensaje': 'Nachricht senden',
    'solicitar_asesoramiento_cta': 'Beratung anfordern',
    'escribir_email': 'Per E-Mail schreiben',
    'email_directo_etq': 'Direkte E-Mail',
    'especialistas_en': 'Spezialisten für',
    'donde_estamos': 'Wo Sie uns finden',
    'llamanos_al': 'Sie können uns auch anrufen unter',
    'escribenos_directamente': 'Sie können uns auch direkt schreiben an',
    'aviso_legal_titulo': 'Impressum, Datenschutz und Cookies',
    'pagina_no_encontrada': 'Seite nicht gefunden | RH·BOTS',
    'pagina_no_encontrada_desc': 'Die gesuchte Seite gibt es nicht oder sie wurde verschoben.',
    'contacto_titulo': 'Kontakt | RH·BOTS',
    'blog_titulo': 'Blog | RH·BOTS',
    'blog_desc': 'Neuigkeiten, Anwendungsfälle und technische Hinweise zu Service- und Industrierobotik.',
    'aplicaciones_titulo': 'Anwendungen der RH·BOTS Roboter nach Branche | RH·BOTS',
    'robots_catalogo_titulo': 'RH·BOTS Roboter — kompletter Katalog | RH·BOTS',
    'robots_catalogo_desc': 'RH·BOTS Katalog: humanoide, vierbeinige und Reinigungsroboter, AMR für die Intralogistik und Zubehör, mit vollständigen Datenblättern.',
    'inicio_titulo': 'RH·BOTS — Humanoide Ressourcen für Ihr Unternehmen',
    'inicio_desc': 'Humanoide, vierbeinige, Reinigungs- und Intralogistikroboter. Beratung, Installation, Schulung und Support aus Valencia, Spanien.',
    'legal_meta_titulo': 'Impressum, Datenschutz und Cookies | RH·BOTS',
    'legal_meta_desc': 'Impressum, Datenschutzerklärung und Cookie-Richtlinie von RH·BOTS.',
    'blog_articulo_sufijo': ' | RH·BOTS Blog',
    'lang_switch_boton': 'Sprache wechseln',
    'carrito_abrir_boton': 'Warenkorb öffnen',
    'carrito_cerrar_boton': 'Warenkorb schließen',
    'nav_ver_familias_aria': 'Roboterreihen und Modelle ansehen',
    'nav_principal_aria': 'Hauptnavigation',
    'nav_abrir_menu': 'Menü öffnen',
    'nav_cerrar_menu': 'Menü schließen',
    'marcas_distribuimos_aria': 'Marken, die wir vertreiben',
    'filtrar_categoria_aria': 'Nach Kategorie filtern',
    'requiere_accesorio_titulo': 'Erforderliches Zubehör',
    'iva_corto': '+ MwSt.',
    'ev_modelo': 'Bonico ist unser RHX2 Ultra',
    'ev_foto_alt': 'Bonico, unser humanoider Roboter, im Interview mit einem Medienvertreter',
    'ev_solicitar': 'Angebot anfordern',
    'ev_como_funciona': 'So funktioniert es',
    'ev_desde': 'Ab',
    'ev_dia': '/ Tag',
    'ev_personalizar': 'Ich möchte Bonico anpassen',
    'ev_personalizacion_desde': 'Anpassung ab',
    'ev_form_titulo': 'Erzählen Sie uns von Ihrer Veranstaltung',
    'ev_form_sello': 'Antwort innerhalb von 24-48 Werkstunden',
    'ev_fecha': 'Datum der Veranstaltung',
    'ev_ciudad': 'Stadt',
    'ev_ciudad_ph': 'Valencia, Madrid, Berlin…',
    'ev_dias': 'Anzahl der Tage',
    'ev_tipo': 'Art der Veranstaltung',
    'ev_tipo_ph': 'Messe, Kongress, Produkteinführung…',
    'ev_que_haga': 'Was soll Bonico tun?',
    'ev_que_haga_ph': 'Tanzen, Besucher empfangen, ein Produkt vorstellen…',
    'ev_mensaje': 'Nachricht',
    'ev_mensaje_ph': 'Alles, was uns hilft, das Angebot vorzubereiten.',
    'con_iva': 'Mit MwSt. (21 %): {n}',
    'iva_no_incluido': 'zzgl. MwSt.',
    'nav_ver_alquiler_aria': 'Mietoptionen ansehen',
    'alquiler_limpieza_nav': 'Industrielle Reinigungsroboter',
    'alquiler_humanoides_nav': 'Humanoide für Veranstaltungen',
    'alquiler_titulo': 'Robotermiete | RH·BOTS',
    'alquiler_limpieza_titulo': 'Miete von industriellen Reinigungsrobotern | RH·BOTS',
    'alquiler_humanoides_titulo': 'Bonico: humanoider Roboter für Events mieten | RH·BOTS',
    'alquiler_humanoides_desc': 'Mieten Sie Bonico, unseren humanoiden Roboter, für Messen, Kongresse, Stände und Firmenevents. Er tanzt, interagiert und zieht Besucher zu Ihrer Marke. Ab 1.200 €/Tag zzgl. MwSt.',
    'tarifa_titulo': 'Mietraten',
    'tarifa_plazo': 'Laufzeit',
    'tarifa_duracion': 'Dauer',
    'tarifa_cuota': 'Monatsrate',
    'tarifa_cuota_sin': 'Monatsrate ohne MwSt.',
    'tarifa_cuota_con': 'Monatsrate mit MwSt.',
    'con_iva_generico': 'die Beträge mit MwSt. enthalten die spanischen 21 %',
    'tarifa_desde': 'Ab {n}/Monat',
    'alquiler_incluye': 'Was die Rate umfasst',
    'alquiler_incluye_si': 'Inbegriffen',
    'alquiler_incluye_no': 'Nicht inbegriffen',
    'home_alquiler_kicker': 'Miete',
    'home_alquiler_titulo': 'Sie können den Roboter auch mieten',
    'alquiler_cta_titulo': 'Passt Mieten zu Ihnen?',
    'alquiler_cta_texto': 'Sagen Sie uns, welche Fläche Sie reinigen müssen oder welche Veranstaltung Sie organisieren, und wir erstellen Ihnen ein Angebot mit dem passenden Modell und der passenden Laufzeit.',
    'alquiler_cta_eventos': 'Sagen Sie uns, welche Veranstaltung Sie organisieren, für wie viele Tage und was der Roboter tun soll, und wir erstellen Ihnen ein verbindliches Angebot.',
    'alquiler_solicitar': 'Diesen Roboter anfragen',
    'requiere_accesorio_texto': 'Erforderlich für den {n}. Wird separat verkauft.',
}

TEXTOS_AR = {
    'saltar_contenido': 'تخطَّ إلى المحتوى',
    'ver_todo_catalogo': 'تصفّح الكتالوج كاملاً',
    'nav_inicio': 'الرئيسية',
    'nav_robots': 'الروبوتات',
    'carrito_titulo': 'سلّتك',
    'carrito_total': 'الإجمالي',
    'carrito_nota_envio': 'تُحتسب رسوم الشحن والضرائب عند إتمام الشراء.',
    'carrito_finalizar': 'إتمام الشراء',
    'carrito_asesor': 'تفضّل استشارتنا أولاً؟ راسِلنا',
    'carrito_vacio': 'لم تُضف أي روبوت بعد.',
    'carrito_ver_catalogo': 'تصفّح الكتالوج',
    'aviso_legal': 'إشعار قانوني',
    'politica_privacidad': 'سياسة الخصوصية',
    'politica_cookies': 'سياسة ملفات تعريف الارتباط',
    'recursos_humanoides': 'موارد بشرية آلية',
    'pide_info': 'اطلب مزيداً من المعلومات',
    'ver_especificaciones': 'عرض المواصفات',
    'que_es_pregunta': 'ما هو {n}؟',
    'aplicaciones_de': 'تطبيقات {n}',
    'escenarios_encaja': 'المجالات التي يناسبها {n}.',
    'specs_tecnicas_de': 'المواصفات التقنية لـ {n}',
    'ver_ficha_completa': 'عرض البطاقة التقنية كاملة',
    'galeria_de': 'معرض صور {n}',
    'fotos_anteriores': 'الصور السابقة',
    'fotos_siguientes': 'الصور التالية',
    'antes_de_ofertar': 'قبل عرض هذا الطراز',
    'doc_a_solicitar': 'الوثائق المطلوب طلبها من الشركة المصنّعة.',
    'accesorios_para': 'ملحقات {n}',
    'otros_modelos_familia': 'طرازات أخرى من الفئة',
    'giralo': 'أدِرْه',
    'vista_giratoria': '{n} — عرض بزاوية 360 درجة. استخدم مفاتيح الأسهم لإدارته.',
    'navegador_sin_video': 'متصفحك لا يستطيع تشغيل هذا الفيديو.',
    'en_video': '{n} في الفيديو',
    'sin_stock': 'غير متوفر — تواصل معنا لمعرفة موعد التوفر',
    'avisame': 'أبلغوني عند التوفر',
    'precio_consulta': 'السعر عند الطلب',
    'pedir_presupuesto': 'طلب عرض سعر',
    'anadir_carrito': 'أضف إلى السلة',
    'comprar_ahora': 'اشترِ الآن',
    'pvp': 'السعر',
    'preguntas_frecuentes': 'الأسئلة الشائعة',
    'distribuidores_oficiales': 'موزّعون معتمدون في إسبانيا والبرتغال',
    'ver_robots': 'عرض الروبوتات',
    'habla_nosotros': 'تحدّث إلينا',
    'ver_todos_modelos': 'عرض جميع الطرازات',
    'modelos_disponibles': 'الطرازات المتاحة',
    'modelos_anteriores': 'الطرازات السابقة',
    'modelos_siguientes': 'الطرازات التالية',
    'ver_modelo': 'عرض الطراز',
    'no_sabes_robot_titulo': 'لا تعرف أي روبوت يناسبك أكثر؟',
    'no_sabes_robot_texto': 'أخبرنا عن مشروعك وسنساعدك في اختيار الفئة والطراز والتهيئة الأنسب لشركتك أو لمركزك.',
    'hablar_rhbots': 'تحدّث مع RH·BOTS',
    'catalogo_kicker': 'كتالوج RH·BOTS',
    'catalogo_h1': 'روبوتات للشركات التي تريد أن تسبق غيرها بخطوة',
    'catalogo_lede': 'روبوتات بشرية ورباعية الأرجل وروبوتات تنظيف وروبوتات AMR للخدمات اللوجستية الداخلية وملحقات، لأتمتة المهام وتحسين العمليات ونقل الروبوتات المتقدمة إلى بيئات العمل الحقيقية. {n} طرازاً ببطاقة تقنية كاملة ومرافقة من البداية إلى النهاية.',
    'solicitar_asesoramiento': 'اطلب استشارة',
    'ver_ficha_tecnica': 'عرض البطاقة التقنية',
    'robots_para_uso': 'روبوتات لهذا الاستخدام',
    'cuentanos_tu_caso': 'أخبرنا عن حالتك',
    'tienes_tarea_titulo': 'هل لديك مهمة تريد أتمتتها؟',
    'tienes_tarea_texto': 'أخبرنا عن حالتك وسنرشدك إلى التطبيق الروبوتي الأنسب لشركتك.',
    'blog_kicker': 'RH·BOTS — المدوّنة',
    'blog_h1': 'أخبار <span class="acento">الروبوتات البشرية</span>',
    'blog_lede': 'أخبار وحالات استخدام وموارد لفهم كيف يمكن دمج الروبوتات البشرية في شركات حقيقية بشكل آمن ومفيد وقابل للقياس.',
    'ver_articulos': 'عرض المقالات',
    'hablar_experto': 'تحدّث مع خبير',
    'destacado': 'مميّز',
    'min_lectura': 'دقيقة قراءة',
    'leer_articulo': 'قراءة المقال',
    'leer_mas': 'اقرأ المزيد',
    'mas_informacion': 'مزيد من المعلومات',
    'conocimiento_aplicado': 'معرفة تطبيقية',
    'ideas_claras': 'أفكار واضحة لاتخاذ قرارات أفضل',
    'buscar_articulos': 'البحث في المقالات',
    'buscar_articulos_placeholder': 'ابحث في المقالات…',
    'buscar': 'بحث',
    'ultimos_articulos': 'أحدث المقالات',
    'recursos_presente': 'موارد لفهم حاضر الروبوتات',
    'todos': 'الكل',
    'sin_resultados_busqueda': 'لا توجد مقالات تطابق بحثك.',
    'preparando_articulos': 'نحن نُعدّ أولى المقالات',
    'preparando_articulos_texto': 'سننشر هنا مستجدات المنتجات وحالات استخدام عملائنا وملاحظات تقنية عن طرازات الكتالوج. في هذه الأثناء يمكنك الاطلاع على البطاقات التقنية أو مراسلتنا مباشرة.',
    'escribenos': 'راسِلنا',
    'necesitas_orientacion': 'هل تحتاج إلى إرشاد؟',
    'orienta_titulo': 'نساعدك على معرفة الروبوت <span class="acento">الذي يناسب شركتك</span>',
    'orienta_texto': 'أخبرنا عن حالتك وسيرشدك فريقنا إلى الطرازات والتطبيقات والخطوات التالية.',
    'solicitar_informacion': 'اطلب معلومات',
    'volver_blog': '← العودة إلى المدوّنة',
    'pagina_404_titulo': 'هذه الصفحة غير موجودة',
    'pagina_404_texto': 'ربما يكون الرابط مكتوباً بشكل خاطئ أو نقلنا المحتوى. من هنا تصل إلى كل شيء:',
    'ir_inicio': 'الذهاب إلى الصفحة الرئيسية',
    'formulario': 'نموذج',
    'solicita_info': 'اطلب معلومات',
    'respuesta_personalizada': 'ردّ مخصّص',
    'nombre': 'الاسم',
    'apellidos': 'اسم العائلة',
    'tu_nombre': 'اسمك',
    'tus_apellidos': 'اسم عائلتك',
    'email': 'البريد الإلكتروني',
    'telefono': 'الهاتف',
    'empresa_campo': 'الشركة',
    'nombre_empresa_placeholder': 'اسم شركتك',
    'que_robot_interesa': 'ما الروبوت الذي يهمّك؟',
    'selecciona_modelo': 'اختر طرازاً',
    'aun_no_lo_se': 'لا أعرف بعد',
    'como_ayudarte': 'كيف يمكننا مساعدتك؟',
    'mensaje_placeholder': 'أخبرنا باختصار عن مشروعك أو احتياجك أو نوع الفعالية…',
    'consiento_privacidad': 'لقد قرأت وأوافق على',
    'politica_privacidad_link': 'سياسة الخصوصية',
    'consiento_privacidad_fin': '. أوافق على معالجة بياناتي لتلقي معلومات تجارية من RH·BOTS.',
    'enviar_mensaje': 'إرسال الرسالة',
    'solicitar_asesoramiento_cta': 'اطلب استشارة',
    'escribir_email': 'المراسلة بالبريد الإلكتروني',
    'email_directo_etq': 'بريد مباشر',
    'especialistas_en': 'متخصصون في',
    'donde_estamos': 'أين نحن',
    'llamanos_al': 'يمكنك أيضاً الاتصال بنا على',
    'escribenos_directamente': 'يمكنك أيضاً مراسلتنا مباشرة على',
    'aviso_legal_titulo': 'إشعار قانوني والخصوصية وملفات تعريف الارتباط',
    'pagina_no_encontrada': 'الصفحة غير موجودة | RH·BOTS',
    'pagina_no_encontrada_desc': 'الصفحة التي تبحث عنها غير موجودة أو تم نقلها.',
    'contacto_titulo': 'اتصل بنا | RH·BOTS',
    'blog_titulo': 'المدوّنة | RH·BOTS',
    'blog_desc': 'أخبار وحالات استخدام وملاحظات تقنية عن روبوتات الخدمة والروبوتات الصناعية.',
    'aplicaciones_titulo': 'تطبيقات روبوتات RH·BOTS حسب القطاع | RH·BOTS',
    'robots_catalogo_titulo': 'روبوتات RH·BOTS — الكتالوج الكامل | RH·BOTS',
    'robots_catalogo_desc': 'كتالوج RH·BOTS: روبوتات بشرية ورباعية الأرجل وروبوتات تنظيف وروبوتات AMR للخدمات اللوجستية الداخلية وملحقات، ببطاقات تقنية كاملة.',
    'inicio_titulo': 'RH·BOTS — موارد بشرية آلية لشركتك',
    'inicio_desc': 'روبوتات بشرية ورباعية الأرجل وروبوتات تنظيف وروبوتات لوجستية. استشارة وتركيب وتدريب ودعم من فالنسيا، إسبانيا.',
    'legal_meta_titulo': 'إشعار قانوني والخصوصية وملفات تعريف الارتباط | RH·BOTS',
    'legal_meta_desc': 'الإشعار القانوني وسياسة الخصوصية وسياسة ملفات تعريف الارتباط لدى RH·BOTS.',
    'blog_articulo_sufijo': ' | مدوّنة RH·BOTS',
    'lang_switch_boton': 'تغيير اللغة',
    'carrito_abrir_boton': 'فتح السلة',
    'carrito_cerrar_boton': 'إغلاق السلة',
    'nav_ver_familias_aria': 'عرض فئات الروبوتات وطرازاتها',
    'nav_principal_aria': 'التنقل الرئيسي',
    'nav_abrir_menu': 'فتح القائمة',
    'nav_cerrar_menu': 'إغلاق القائمة',
    'marcas_distribuimos_aria': 'العلامات التجارية التي نوزّعها',
    'filtrar_categoria_aria': 'التصفية حسب الفئة',
    'requiere_accesorio_titulo': 'ملحق ضروري',
    'iva_corto': '+ ضريبة القيمة المضافة',
    'ev_modelo': 'Bonico هو طراز RHX2 Ultra لدينا',
    'ev_foto_alt': 'Bonico، روبوتنا البشري، أثناء مقابلة مع إحدى وسائل الإعلام',
    'ev_solicitar': 'طلب عرض سعر',
    'ev_como_funciona': 'شاهد كيف يعمل',
    'ev_desde': 'ابتداءً من',
    'ev_dia': '/ اليوم',
    'ev_personalizar': 'أريد تخصيص Bonico',
    'ev_personalizacion_desde': 'التخصيص ابتداءً من',
    'ev_form_titulo': 'أخبرنا عن فعاليتك',
    'ev_form_sello': 'الرد خلال 24-48 ساعة عمل',
    'ev_fecha': 'تاريخ الفعالية',
    'ev_ciudad': 'المدينة',
    'ev_ciudad_ph': 'دبي، الرياض، فالنسيا…',
    'ev_dias': 'عدد الأيام',
    'ev_tipo': 'نوع الفعالية',
    'ev_tipo_ph': 'معرض، مؤتمر، إطلاق منتج…',
    'ev_que_haga': 'ما الذي تودّ أن يفعله Bonico؟',
    'ev_que_haga_ph': 'الرقص، استقبال الزوار، تقديم منتج…',
    'ev_mensaje': 'الرسالة',
    'ev_mensaje_ph': 'أي تفاصيل تساعدنا على إعداد العرض.',
    'con_iva': 'شامل ضريبة القيمة المضافة (21%): {n}',
    'iva_no_incluido': 'غير شامل ضريبة القيمة المضافة',
    'nav_ver_alquiler_aria': 'عرض خيارات التأجير',
    'alquiler_limpieza_nav': 'روبوتات التنظيف الصناعي',
    'alquiler_humanoides_nav': 'روبوتات بشرية للفعاليات',
    'alquiler_titulo': 'تأجير الروبوتات | RH·BOTS',
    'alquiler_limpieza_titulo': 'تأجير روبوتات التنظيف الصناعي | RH·BOTS',
    'alquiler_humanoides_titulo': 'Bonico: تأجير روبوت بشري للفعاليات | RH·BOTS',
    'alquiler_humanoides_desc': 'استأجر Bonico، روبوتنا البشري، للمعارض والمؤتمرات والأجنحة وفعاليات الشركات. يرقص ويتفاعل ويجذب الزوار إلى علامتك التجارية. ابتداءً من 1,200 € في اليوم، غير شامل ضريبة القيمة المضافة.',
    'tarifa_titulo': 'أقساط التأجير',
    'tarifa_plazo': 'المدة التعاقدية',
    'tarifa_duracion': 'المدة',
    'tarifa_cuota': 'القسط الشهري',
    'tarifa_cuota_sin': 'القسط دون ضريبة',
    'tarifa_cuota_con': 'القسط شامل الضريبة',
    'con_iva_generico': 'المبالغ الشاملة للضريبة تحتسب ضريبة إسبانيا البالغة 21%',
    'tarifa_desde': 'ابتداءً من {n} شهرياً',
    'alquiler_incluye': 'ما يشمله القسط',
    'alquiler_incluye_si': 'مشمول',
    'alquiler_incluye_no': 'غير مشمول',
    'home_alquiler_kicker': 'التأجير',
    'home_alquiler_titulo': 'يمكنك أيضاً استئجار الروبوت',
    'alquiler_cta_titulo': 'هل يناسبك التأجير؟',
    'alquiler_cta_texto': 'أخبرنا بالمساحة التي تحتاج إلى تنظيفها أو بالفعالية التي تنظّمها، وسنعدّ لك عرضاً بالطراز والمدة الأنسب.',
    'alquiler_cta_eventos': 'أخبرنا بالفعالية التي تنظّمها وعدد الأيام وما تريد أن يفعله الروبوت، وسنعدّ لك عرضاً نهائياً.',
    'alquiler_solicitar': 'اطلب هذا الروبوت',
    'requiere_accesorio_texto': 'ضروري لـ {n}. يُباع بشكل منفصل.',
}

for _lang, _pares in (('de', TEXTOS_DE), ('ar', TEXTOS_AR)):
    _faltan = [k for k in TEXTOS if k not in _pares]
    if _faltan:
        raise SystemExit(f'Faltan textos en {_lang}: {_faltan[:5]}')
    for _k, _v in _pares.items():
        TEXTOS[_k][_lang] = _v


def t(clave, **kw):
    txt = TEXTOS[clave][LANG]
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
        'description': {
            'es': 'Distribuidor oficial de AGIBOT y PUDU en España y Portugal: robots de limpieza '
                  'autónoma, humanoides, cuadrúpedos, AMR de intralogística y accesorios, con asesoramiento, instalación, '
                  'formación y mantenimiento.',
            'pt': 'Distribuidor oficial da AGIBOT e da PUDU em Espanha e Portugal: robôs de limpeza '
                  'autónoma, humanoides, quadrúpedes, AMR de intralogística e acessórios, com aconselhamento, instalação, '
                  'formação e manutenção.',
            'en': 'Official distributor of AGIBOT and PUDU in Spain and Portugal: autonomous cleaning, '
                  'humanoid and quadruped robots, intralogistics AMRs and accessories, with advice, installation, '
                  'training and maintenance.',
            'fr': 'Distributeur officiel d\'AGIBOT et de PUDU en Espagne et au Portugal : robots de nettoyage '
                  'autonome, humanoïdes, quadrupèdes, AMR d\'intralogistique et accessoires, avec conseil, installation, '
                  'formation et maintenance.',
            'zh': 'AGIBOT和PUDU在西班牙和葡萄牙的官方经销商：自主清洁机器人、人形机器人、四足机器人、AMR移动机器人及配件，'
                  '提供咨询、安装、培训和维护服务。',
            'ca': 'Distribuïdor oficial d\'AGIBOT i PUDU a Espanya i Portugal: robots de neteja '
                  'autònoma, humanoides, quadrúpedes, AMR d\'intralogística i accessoris, amb assessorament, instal·lació, '
                  'formació i manteniment.',
            'de': 'Offizieller Vertriebspartner von AGIBOT und PUDU in Spanien und Portugal: autonome '
                  'Reinigungsroboter, Humanoide, Vierbeiner, AMR für die Intralogistik und Zubehör, mit Beratung, '
                  'Installation, Schulung und Wartung.',
            'ar': 'موزّع معتمد لشركتي AGIBOT وPUDU في إسبانيا والبرتغال: روبوتات تنظيف ذاتية وروبوتات بشرية '
                  'ورباعية الأرجل وروبوتات AMR للخدمات اللوجستية الداخلية وملحقات، مع الاستشارة والتركيب '
                  'والتدريب والصيانة.',
        }[LANG],
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
    prefijo_actual = f'{LANG}/' if LANG != 'es' else ''
    canonical = f'{dominio}/{prefijo_actual}{limpia}' if limpia else f'{dominio}/{prefijo_actual}'
    hreflang = ''
    alterno_es = ''
    for cod in IDIOMAS:
        prefijo = f'{cod}/' if cod != 'es' else ''
        alterno = f'{dominio}/{prefijo}{limpia}' if limpia else f'{dominio}/{prefijo}'
        if cod == 'es':
            alterno_es = alterno
        hreflang += f'<link rel="alternate" hreflang="{cod}" href="{e(alterno)}">\n'
    hreflang += f'<link rel="alternate" hreflang="x-default" href="{e(alterno_es)}">\n'
    imagen = f'{dominio}/{og_img or SEO["og_imagen"]}'
    tw = (f'<meta name="twitter:site" content="{e(SEO["twitter"])}">\n'
          if SEO.get('twitter') else '')
    return f'''<!DOCTYPE html>
<html lang="{LANG}" dir="{dir_html()}">
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
<meta property="og:locale" content="{e(LOCALE_OG.get(LANG, SEO['locale']))}">
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
{'<link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;600;700&display=swap" rel="stylesheet">' if LANG in RTL else ''}
<script>document.documentElement.classList.add('js')</script>
<link rel="stylesheet" href="{base}css/styles.css">
{'<link rel="stylesheet" href="%scss/catalogo.css">' % base if extra_css else ''}
{'<link rel="stylesheet" href="%scss/rtl.css">' % base if LANG in RTL else ''}
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
            f'aria-label="{t("carrito_abrir_boton")}" aria-controls="carrito" aria-expanded="false">'
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
  <aside class="carrito__panel" role="dialog" aria-modal="true" aria-label="{t('carrito_titulo')}">
    <header class="carrito__cab">
      <h2 class="carrito__titulo onblue" data-punto="manual">{t('carrito_titulo')}</h2>
      <button class="carrito__cerrar" type="button" data-carrito-cerrar aria-label="{t('carrito_cerrar_boton')}">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
      </button>
    </header>
    <div class="carrito__cuerpo" data-carrito-lista></div>
    <footer class="carrito__pie" data-carrito-pie hidden>
      <p class="carrito__total"><span>{t('carrito_total')}</span><strong data-carrito-total></strong>
        <span class="carrito__iva">{t('iva_no_incluido')}</span></p>
      <p class="carrito__nota">{t('carrito_nota_envio')}</p>
      <a class="pill carrito__pagar" data-carrito-pagar rel="nofollow noopener" href="#"><span>{t('carrito_finalizar')}</span>{CHEVRON}</a>
      <a class="carrito__consulta" href="{base}contacto.html">{t('carrito_asesor')}</a>
    </footer>
  </aside>
</div>
'''


BANDERAS = {
    'es': ('<svg viewBox="0 0 3 2" aria-hidden="true"><rect width="3" height="2" fill="#c60b1e"/>'
           '<rect y=".5" width="3" height="1" fill="#ffc400"/></svg>'),
    'pt': ('<svg viewBox="0 0 3 2" aria-hidden="true"><rect width="1.2" height="2" fill="#046a38"/>'
           '<rect x="1.2" width="1.8" height="2" fill="#da291c"/>'
           '<circle cx="1.2" cy="1" r=".34" fill="#ffe900" stroke="#046a38" stroke-width=".04"/></svg>'),
    'en': ('<svg viewBox="0 0 60 30" aria-hidden="true"><clipPath id="s"><rect width="60" height="30" rx="0"/></clipPath>'
           '<g clip-path="url(#s)"><rect width="60" height="30" fill="#012169"/>'
           '<path d="M0 0 60 30M60 0 0 30" stroke="#fff" stroke-width="6"/>'
           '<path d="M0 0 60 30M60 0 0 30" stroke="#C8102E" stroke-width="2"/>'
           '<path d="M30 0v30M0 15h60" stroke="#fff" stroke-width="10"/>'
           '<path d="M30 0v30M0 15h60" stroke="#C8102E" stroke-width="6"/></g></svg>'),
    'fr': ('<svg viewBox="0 0 3 2" aria-hidden="true"><rect width="1" height="2" fill="#0055a4"/>'
           '<rect x="1" width="1" height="2" fill="#fff"/><rect x="2" width="1" height="2" fill="#ef4135"/></svg>'),
    'zh': ('<svg viewBox="0 0 3 2" aria-hidden="true"><rect width="3" height="2" fill="#de2910"/>'
           '<g fill="#ffde00">'
           '<polygon points="0.90,0.35 0.96,0.56 1.19,0.56 1.00,0.68 1.08,0.89 0.90,0.76 0.72,0.89 0.80,0.68 0.61,0.56 0.84,0.56"/>'
           '<polygon points="1.64,0.26 1.58,0.29 1.60,0.35 1.55,0.31 1.49,0.35 1.52,0.29 1.47,0.25 1.53,0.25 1.55,0.19 1.57,0.25"/>'
           '<polygon points="1.84,0.51 1.77,0.52 1.77,0.59 1.74,0.53 1.67,0.54 1.72,0.50 1.69,0.44 1.74,0.47 1.79,0.42 1.78,0.48"/>'
           '<polygon points="1.82,0.84 1.76,0.81 1.72,0.86 1.72,0.80 1.66,0.77 1.72,0.76 1.73,0.69 1.76,0.75 1.83,0.73 1.78,0.78"/>'
           '<polygon points="1.58,1.08 1.54,1.03 1.48,1.06 1.52,1.00 1.48,0.95 1.54,0.97 1.57,0.91 1.58,0.98 1.64,1.00 1.58,1.02"/>'
           '</g></svg>'),
    'de': ('<svg viewBox="0 0 3 2" aria-hidden="true"><rect width="3" height="2" fill="#000"/>'
           '<rect y=".667" width="3" height=".667" fill="#dd0000"/>'
           '<rect y="1.333" width="3" height=".667" fill="#ffce00"/></svg>'),
    # árabe: bandera de los Emiratos, el mercado árabe de referencia para eventos
    'ar': ('<svg viewBox="0 0 3 2" aria-hidden="true"><rect width="3" height="2" fill="#fff"/>'
           '<rect width="3" height=".667" fill="#00732f"/>'
           '<rect y="1.333" width="3" height=".667" fill="#000"/>'
           '<rect width=".75" height="2" fill="#ff0000"/></svg>'),
    'ca': ('<svg viewBox="0 0 3 2" aria-hidden="true"><rect width="3" height="2" fill="#fcdd09"/>'
           '<g fill="#da121a">'
           '<rect y=".222" width="3" height=".222"/><rect y=".667" width="3" height=".222"/>'
           '<rect y="1.111" width="3" height=".222"/><rect y="1.556" width="3" height=".222"/>'
           '</g></svg>'),
}


def selector_idioma(ruta):
    """Desplegable con las banderas de los idiomas disponibles. «ruta» es la
    de la página actual (p.ej. 'robots/rhx2.html', o '' para portada),
    igual en todos los idiomas: solo cambia el prefijo de carpeta."""
    limpia = '' if ruta in ('', 'index.html') else ruta
    opciones = ''
    for cod in IDIOMAS:
        prefijo = '' if cod == 'es' else f'{cod}/'
        activo = cod == LANG
        opciones += (f'<li><a href="/{prefijo}{e(limpia)}" hreflang="{cod}" lang="{cod}" '
                     f'class="lang-menu__op{" is-on" if activo else ""}" '
                     f'aria-current="{"true" if activo else "false"}">'
                     f'<span class="lang-menu__bandera">{BANDERAS[cod]}</span>'
                     f'<span class="lang-menu__nombre">{e(NOMBRE_IDIOMA[cod])}</span></a></li>')
    return (f'<div class="lang-switch">'
            f'<button type="button" class="lang-switch__abrir" aria-haspopup="true" '
            f'aria-expanded="false" aria-controls="lang-menu" '
            f'aria-label="{t("lang_switch_boton")}">'
            f'<span class="lang-switch__bandera">{BANDERAS[LANG]}</span>'
            f'<svg class="lang-switch__chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>'
            f'</button>'
            f'<ul class="lang-menu" id="lang-menu" role="menu" aria-label="{t("lang_switch_boton")}">{opciones}</ul>'
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
                modelos = [q for q in PRODUCTOS if q['family'] == k and q.get('ficha', True)]
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
                      f'aria-controls="sub-robots" aria-label="{t("nav_ver_familias_aria")}">'
                      f'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>'
                      f'<div class="nav__sub nav__sub--mega" id="sub-robots" data-menurobots>'
                      f'<ul class="nav__fams">{familias}</ul>'
                      f'<div class="nav__paneles">{paneles}'
                      f'<p class="nav__todos"><a href="{base}robots.html">'
                      f'{t("ver_todo_catalogo")}{FLECHA}</a></p></div>'
                      f'</div></div>')
        elif it['key'] == 'alquiler':
            # desplegable simple: las dos modalidades de alquiler
            opciones = (
                f'<a href="{base}alquiler-limpieza.html">{t("alquiler_limpieza_nav")}</a>'
                f'<a href="{base}alquiler-humanoides.html">{t("alquiler_humanoides_nav")}</a>')
            enlace = (f'<div class="nav__grupo nav__grupo--simple">{enlace}'
                      f'<button type="button" class="nav__abrir" aria-expanded="false" '
                      f'aria-controls="sub-alquiler" aria-label="{t("nav_ver_alquiler_aria")}">'
                      f'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>'
                      f'<div class="nav__sub" id="sub-alquiler">{opciones}</div></div>')
        parts.append(enlace)
    links = '\n      '.join(parts)
    return f'''
<header class="site-header" id="header">
  <div class="wrap header-inner">
    <a class="logo" href="{base}index.html" aria-label="RH·BOTS — inicio">
      <img src="{base}assets/logo-rhbots.png" alt="RH·BOTS" width="348" height="72">
    </a>
    <nav class="nav" id="nav" aria-label="{t('nav_principal_aria')}">
      {links}
    </nav>
    {selector_idioma(ruta)}
    {boton_carrito(base)}
    <button class="nav-toggle" id="navToggle" aria-label="{t('nav_abrir_menu')}" aria-expanded="false" aria-controls="nav">
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
    'pt': {
        'limpieza': 'Limpeza autónoma', 'humanoides': 'Robô humanoide',
        'cuadrupedos': 'Robô quadrúpede', 'amr': 'AMR intralogística', 'accesorios': 'Acessório',
    },
    'fr': {
        'limpieza': 'Nettoyage autonome', 'humanoides': 'Robot humanoïde',
        'cuadrupedos': 'Robot quadrupède', 'amr': 'AMR intralogistique', 'accesorios': 'Accessoire',
    },
    'zh': {
        'limpieza': '清洁机器人', 'humanoides': '人形机器人',
        'cuadrupedos': '四足机器人', 'amr': 'AMR 移动机器人', 'accesorios': '配件',
    },
    'ca': {
        'limpieza': 'Neteja autònoma', 'humanoides': 'Robot humanoide',
        'cuadrupedos': 'Robot quadrúpede', 'amr': 'AMR intralogística', 'accesorios': 'Accessori',
    },
    'de': {
        'limpieza': 'Reinigungsroboter', 'humanoides': 'Humanoider Roboter',
        'cuadrupedos': 'Vierbeiniger Roboter', 'amr': 'AMR Intralogistik', 'accesorios': 'Zubehör',
    },
    'ar': {
        'limpieza': 'روبوت تنظيف', 'humanoides': 'روبوت بشري',
        'cuadrupedos': 'روبوت رباعي الأرجل', 'amr': 'روبوت AMR', 'accesorios': 'ملحق',
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
    if LANG in ('en', 'zh', 'ar'):
        return entero + '.' + dec
    return entero.replace(',', '.') + ',' + dec


# IVA español: la empresa factura desde España, así que los importes con
# impuestos que mostramos son los de aquí
IVA = 0.21


def con_iva(valor):
    """Importe con el IVA incluido, ya formateado. Cadena vacía si no hay precio."""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return ''
    return formato_pvp(v * (1 + IVA)) if v > 0 else ''


def importe_de_texto(txt):
    """«1.200 €» o «1,200 €» → 1200.0. Devuelve 0 si no hay número."""
    limpio = re.sub(r'[^\d.,]', '', txt or '')
    if not limpio:
        return 0.0
    # el último separador seguido de exactamente dos cifras son los decimales
    m = re.search(r'[.,](\d{2})$', limpio)
    dec = m.group(1) if m else ''
    entero = limpio[:m.start()] if m else limpio
    entero = re.sub(r'[.,]', '', entero)
    try:
        return float(entero + ('.' + dec if dec else ''))
    except ValueError:
        return 0.0


def nota_iva(valor, clase):
    """«IVA no incluido · Con IVA (21 %): X»: se ven los dos importes."""
    bruto = con_iva(valor)
    texto = t('iva_no_incluido') if not bruto else f"{t('iva_no_incluido')} · {t('con_iva', n=bruto)}"
    return f'<span class="{clase}">{texto}</span>'


def formato_pvp(valor):
    """'19900' → «19.900 €»; conserva los céntimos solo si los hay."""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return ''
    if v <= 0:
        return ''
    txt = formato_precio(v)
    # los céntimos a cero sobran, tanto con coma decimal como con punto
    if txt.endswith(',00') or txt.endswith('.00'):
        txt = txt[:-3]
    return f'{txt} €'


def precio_html(p, clase='pvp'):
    """Precio de venta al público de la tarifa RH·BOTS."""
    pvp = formato_pvp(p.get('precio'))
    if not pvp:
        return ''
    return (f'<p class="{clase}"><span class="{clase}__etiqueta">{t("pvp")}</span> {pvp}'
            f'{nota_iva(p.get("precio"), f"{clase}__iva")}</p>')


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
    etiqueta = (TIENDA.get('texto_boton') or t('comprar_ahora')) if LANG == 'es' else t('comprar_ahora')
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


# robot → accesorio (cargador/estación de carga) que necesita sí o sí para
# funcionar, aunque se venda como línea aparte en la tarifa
REQUIERE_ACCESORIO = {
    'd5w': 'd5w-estacion-carga',
    'mt1': 'mt1-estacion-carga',
    'mt1-max': 'mt1-estacion-carga',
    't150': 'amr-cargador',
    't300': 'amr-cargador',
    't600': 'amr-cargador',
    't600-underride': 'amr-cargador',
}


def nota_accesorio_requerido(p, base):
    """Cargador o estación de carga que el robot necesita para funcionar.

    Estos accesorios no tienen ficha propia (ver «ficha: false» en
    productos.json): se venden solo junto con su robot, así que se
    muestran aquí mismo en vez de enlazar a una página que no existe.
    """
    slug_acc = REQUIERE_ACCESORIO.get(p['slug'])
    acc = BY_SLUG.get(slug_acc) if slug_acc else None
    if not acc:
        return ''
    if acc.get('hero'):
        media = f'<img src="{base}{acc["hero"]}" alt="" loading="lazy">'
    else:
        media = placeholder(acc['family'], acc['name'])
    pvp = formato_pvp(acc.get('precio'))
    precio_html_acc = f'<p class="accnec__precio">{pvp}</p>' if pvp else ''
    return (f'<div class="accnec">'
            f'<p class="accnec__etiqueta">{t("requiere_accesorio_titulo")}</p>'
            f'<div class="accnec__card">'
            f'<div class="accnec__media">{media}</div>'
            f'<div class="accnec__body">'
            f'<h3>{e(acc["name"])}</h3>'
            f'<p class="accnec__desc">{t("requiere_accesorio_texto", n=e(p["name"]))}</p>'
            f'{precio_html_acc}'
            f'</div></div></div>')


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
                       f'<span>{e(formato_moneda(moneda))}</span>'
                       f'{nota_iva(precio, "precio__iva")}</p>')
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
            f'{t("navegador_sin_video")}'
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
    base = nivel(LANG) + '../'
    fam = p['family']
    dominio = SEO['dominio'].rstrip('/')
    # si el claim entero no cabe en los ~60 caracteres que enseña Google,
    # es más limpio poner la familia que dejar la frase a medias
    title = f'{p["name"]} · {p["claim"]} | RH·BOTS'
    if len(title) > 60:
        corto = f'{p["name"]} · {ETIQUETA_FAMILIA.get(fam, FAM_NAME[fam])} | RH·BOTS'
        if len(corto) <= 60:
            title = corto
    _pfijo = f'{dominio}/{LANG}' if LANG != 'es' else dominio
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
        {nota_accesorio_requerido(p, base)}
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
                   if q['family'] == 'accesorios' and q.get('ficha', True)
                   and p['slug'] in (q.get('compatible') or [])]
    if especificos:
        others = especificos[:4]
        titulo_otros = t('accesorios_para', n=p['name'])
    elif fam == 'humanoides':
        others = [q for q in PRODUCTOS
                  if q['family'] == 'accesorios' and q.get('ficha', True) and not q.get('compatible')][:4]
        titulo_otros = t('accesorios_para', n=p['name'])
    else:
        others = [q for q in PRODUCTOS
                  if q['family'] == fam and q['slug'] != p['slug'] and q.get('ficha', True)][:4]
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
                '<h3>%s</h3><p>%s</p>%s</div></a></li>\n'
                % (q['slug'], media, badges(q), e(q['name']), e(q['claim']), precio_html(q, 'pcard__precio')))
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
    base = nivel(LANG)
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
    base = nivel(LANG)
    out = [head(t('robots_catalogo_titulo'), t('robots_catalogo_desc'), base, 'robots.html'),
           header(base, 'robots', 'robots.html'), '<main id="contenido">']

    # portada del catálogo: fondo oscuro, robot en penumbra y franja diagonal azul
    out.append(f'''
  <section class="hero hero--catalogo" id="inicio">
    <img class="hero__foto" src="{base}assets/robots/rha3/tres-poses.webp" alt="" aria-hidden="true"
         width="1600" height="1440" fetchpriority="high">
    <div class="hero__velo" aria-hidden="true"></div>
    <div class="hero__diagonal" aria-hidden="true"></div>
    <div class="wrap hero__copy">
      <p class="kicker hero__kicker">{t('catalogo_kicker')}</p>
      <h1 class="display display--hero">{t('catalogo_h1')}</h1>
      <p class="lede lede--hero">{t('catalogo_lede', n=len([p for p in PRODUCTOS if p.get('ficha', True)]))}</p>
      <div class="hero__cta">
        <a class="pill" href="contacto.html"><span>{t('solicitar_asesoramiento')}</span>{CHEVRON}</a>
      </div>
    </div>
  </section>
''')

    # una sección por familia
    for i, (key, name, desc) in enumerate(FAMILIAS):
        modelos = [p for p in PRODUCTOS if p['family'] == key and p.get('ficha', True)]
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
    'pt': ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
           'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'],
    'fr': ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
           'août', 'septembre', 'octobre', 'novembre', 'décembre'],
    'zh': ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
    'ca': ['gener', 'febrer', 'març', 'abril', 'maig', 'juny', 'juliol',
           'agost', 'setembre', 'octubre', 'novembre', 'desembre'],
    'de': ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli',
           'August', 'September', 'Oktober', 'November', 'Dezember'],
    'ar': ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو',
           'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'],
}


def mes_y_ano(fecha):
    """'2026-09-10' pasa a 'septiembre 2026' o 'September 2026', según el idioma.
    Si no es una fecha ISO, se deja igual."""
    m = re.match(r'(\d{4})-(\d{2})', fecha or '')
    return f'{_MESES[LANG][int(m.group(2)) - 1]} {m.group(1)}' if m else (fecha or '')


# ──────────────────────────────────────────────────────────────────── home ──
def home_page():
    base = nivel(LANG)
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
  <section class="marcas" id="marcas" aria-label="{t('marcas_distribuimos_aria')}">
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
            if p['status'] != 'disponible' or not p.get('ficha', True):
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

    # alquiler: las dos modalidades, con sus fotos y su llamada a la acción
    if ALQUILER.get('opciones'):
        tarjetas = ''
        for op in ALQUILER['opciones']:
            tarjetas += (
                f'<li class="pcard reveal"><a href="{e(op["href"])}">'
                f'<div class="pcard__media pcard__media--escena">'
                f'<img src="{base}{e(op.get("imagen", ""))}" alt="{e(op["titulo"])}" loading="lazy"></div>'
                f'<div class="pcard__body"><h3>{e(op["titulo"])}</h3>'
                f'<p>{e(op.get("texto", ""))}</p>'
                f'<span class="pcard__more">{t("mas_informacion")}</span></div></a></li>')
        out.append(f'''  <section class="section section--white alqhome" id="alquiler">
    <div class="wrap">
      <header class="section-head reveal">
        <p class="kicker">{t('home_alquiler_kicker')}</p>
        <h2 class="h-section">{t('home_alquiler_titulo')}</h2>
      </header>
      <ul class="pgrid pgrid--duo">{tarjetas}</ul>
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
    base = nivel(LANG)
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
      <div class="filtros reveal" role="group" aria-label="{t('filtrar_categoria_aria')}">{filtros}</div>
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
    base = nivel(LANG) + '../'
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
    base = nivel(LANG)
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
        valores = {'modelos': len([p for p in PRODUCTOS if p.get('ficha', True)]),
                   'familias': len({p['family'] for p in PRODUCTOS if p.get('ficha', True)})}
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
      <ul class="alianza__marcas reveal" aria-label="{t('marcas_distribuimos_aria')}">{logos_marcas(base, 'alianza__marca')}</ul>
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
    base = nivel(LANG)
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
    elif LANG == 'pt':
        out.append(f'''
  <section class="chero">
    <div class="wrap">
      <h1 class="display display--left">Aviso legal, privacidade e cookies</h1>
    </div>
  </section>
  <section class="section section--white">
    <div class="wrap wrap--narrow art__cuerpo">
      <p><em>Esta página em português é uma tradução de cortesia do nosso aviso legal
      em espanhol. Em caso de discrepância, prevalece a versão em espanhol
      (<a href="/legal.html">/legal.html</a>) e aplica-se a lei espanhola. Recomendamos
      uma revisão jurídica profissional antes de utilizar esta tradução para fins de
      conformidade.</em></p>

      <h2 id="aviso-legal">Aviso legal</h2>
      <p><strong>Titular do sítio web:</strong> {e(empresa)}.<br>
      <strong>NIF:</strong> [a completar pelo titular].<br>
      <strong>Morada:</strong> {e(direccion)}.<br>
      {f'<strong>Contacto:</strong> {e(email)}' + (f' · {e(tel)}' if tel else '') + '.<br>' if email else ''}
      <strong>Domínio:</strong> {e(dominio)}</p>
      <p>O acesso e a utilização deste sítio web atribui a condição de utilizador e
      implica a aceitação das condições aqui descritas. {e(empresa)} é distribuidor
      oficial da AGIBOT e da PUDU em Espanha e Portugal.</p>

      <h2 id="privacidad">Política de privacidade</h2>
      <p><strong>Responsável pelo tratamento:</strong> {e(empresa)}{f', {e(email)}' if email else ''}.</p>
      <p><strong>Finalidade:</strong> responder aos pedidos de informação, orçamento,
      demonstração ou apoio que nos envie através do formulário de contacto, e gerir
      a relação comercial caso se venha a formalizar.</p>
      <p><strong>Fundamento:</strong> consentimento da pessoa interessada ao enviar
      os seus dados, e execução de uma eventual relação contratual.</p>
      <p><strong>Conservação:</strong> enquanto se mantiver a relação com o utilizador
      ou durante os prazos legalmente exigíveis.</p>
      <p><strong>Destinatários:</strong> não se cedem dados a terceiros, salvo
      obrigação legal ou fornecedores necessários para prestar o serviço solicitado
      (por exemplo, a Shopify para processar uma encomenda).</p>
      <p><strong>Direitos:</strong> pode exercer os seus direitos de acesso,
      retificação, apagamento, oposição, limitação e portabilidade escrevendo
      para{f' {e(email)}' if email else ' o endereço de contacto da RH·BOTS'}.</p>

      <h2 id="cookies">Política de cookies</h2>
      <p>Este sítio usa apenas os cookies técnicos estritamente necessários para o
      seu funcionamento. Se no futuro for ativado o Google Analytics ou outra
      ferramenta de medição, será pedido o consentimento prévio do utilizador
      antes de a carregar.</p>
    </div>
  </section>
''')
    elif LANG == 'fr':
        out.append(f'''
  <section class="chero">
    <div class="wrap">
      <h1 class="display display--left">Mentions légales, confidentialité et cookies</h1>
    </div>
  </section>
  <section class="section section--white">
    <div class="wrap wrap--narrow art__cuerpo">
      <p><em>Cette page en français est une traduction de courtoisie de nos mentions
      légales en espagnol. En cas de divergence, la version espagnole
      (<a href="/legal.html">/legal.html</a>) prévaut et le droit espagnol s'applique.
      Nous recommandons une relecture juridique professionnelle avant d'utiliser
      cette traduction à des fins de conformité.</em></p>

      <h2 id="aviso-legal">Mentions légales</h2>
      <p><strong>Titulaire du site web :</strong> {e(empresa)}.<br>
      <strong>Numéro fiscal (CIF/NIF) :</strong> [à compléter par le titulaire].<br>
      <strong>Adresse :</strong> {e(direccion)}.<br>
      {f'<strong>Contact :</strong> {e(email)}' + (f' · {e(tel)}' if tel else '') + '.<br>' if email else ''}
      <strong>Domaine :</strong> {e(dominio)}</p>
      <p>L'accès et l'utilisation de ce site web confèrent la qualité d'utilisateur
      et impliquent l'acceptation des conditions énoncées ici. {e(empresa)} est
      distributeur officiel d'AGIBOT et de PUDU en Espagne et au Portugal.</p>

      <h2 id="privacidad">Politique de confidentialité</h2>
      <p><strong>Responsable du traitement :</strong> {e(empresa)}{f', {e(email)}' if email else ''}.</p>
      <p><strong>Finalité :</strong> répondre aux demandes d'information, de devis,
      de démonstration ou d'assistance que vous nous envoyez via le formulaire de
      contact, et gérer la relation commerciale si elle se concrétise.</p>
      <p><strong>Base légale :</strong> le consentement de la personne concernée
      lors de l'envoi de ses données, et l'exécution d'une éventuelle relation
      contractuelle.</p>
      <p><strong>Conservation :</strong> pendant toute la durée de la relation avec
      l'utilisateur, ou pendant les délais légalement exigibles.</p>
      <p><strong>Destinataires :</strong> les données ne sont pas cédées à des tiers,
      sauf obligation légale ou prestataires nécessaires à la fourniture du service
      demandé (par exemple, Shopify pour traiter une commande).</p>
      <p><strong>Vos droits :</strong> vous pouvez exercer vos droits d'accès, de
      rectification, d'effacement, d'opposition, de limitation et de portabilité en
      écrivant à{f' {e(email)}' if email else " l'adresse de contact de RH·BOTS"}.</p>

      <h2 id="cookies">Politique de cookies</h2>
      <p>Ce site utilise uniquement les cookies techniques strictement nécessaires
      à son fonctionnement. Si Google Analytics ou un autre outil de mesure est
      activé à l'avenir, le consentement préalable de l'utilisateur sera demandé
      avant son chargement.</p>
    </div>
  </section>
''')
    elif LANG == 'zh':
        out.append(f'''
  <section class="chero">
    <div class="wrap">
      <h1 class="display display--left">法律声明、隐私与Cookie政策</h1>
    </div>
  </section>
  <section class="section section--white">
    <div class="wrap wrap--narrow art__cuerpo">
      <p><em>本中文页面是我们西班牙语法律声明的礼节性翻译。如有任何差异，以西班牙语版本
      （<a href="/legal.html">/legal.html</a>）为准，并适用西班牙法律。在将本翻译用于合规目的之前，
      建议先进行专业法律审查。</em></p>

      <h2 id="aviso-legal">法律声明</h2>
      <p><strong>网站所有者：</strong>{e(empresa)}。<br>
      <strong>税号（CIF/NIF）：</strong>[待所有者补充]。<br>
      <strong>注册地址：</strong>{e(direccion)}。<br>
      {f'<strong>联系方式：</strong>{e(email)}' + (f' · {e(tel)}' if tel else '') + '。<br>' if email else ''}
      <strong>域名：</strong>{e(dominio)}</p>
      <p>访问和使用本网站即代表您成为用户，并表示您接受此处所列条款。{e(empresa)}是
      AGIBOT和PUDU在西班牙和葡萄牙的官方经销商。</p>

      <h2 id="privacidad">隐私政策</h2>
      <p><strong>数据处理负责方：</strong>{e(empresa)}{f'，{e(email)}' if email else ''}。</p>
      <p><strong>处理目的：</strong>处理您通过联系表单发送给我们的信息、报价、演示或
      支持请求，并在业务关系达成后进行管理。</p>
      <p><strong>法律依据：</strong>数据主体在提交其信息时给予的同意，以及可能产生的
      合同关系的履行。</p>
      <p><strong>保留期限：</strong>在与用户保持关系期间，或在法律规定的期限内。</p>
      <p><strong>数据接收方：</strong>除法律要求外，我们不会将数据提供给第三方，除非
      是提供所请求服务所必需的服务商（例如，Shopify用于处理订单）。</p>
      <p><strong>您的权利：</strong>您可以通过{f'{e(email)}' if email else 'RH·BOTS的联系方式'}
      行使访问、更正、删除、反对、限制处理和数据可携带等权利。</p>

      <h2 id="cookies">Cookie政策</h2>
      <p>本网站仅使用网站正常运行所必需的技术性Cookie。如果未来启用Google Analytics
      或其他统计工具，将在加载前征求用户的事先同意。</p>
    </div>
  </section>
''')
    elif LANG == 'ca':
        out.append(f'''
  <section class="chero">
    <div class="wrap">
      <h1 class="display display--left">Avís legal, privacitat i galetes</h1>
    </div>
  </section>
  <section class="section section--white">
    <div class="wrap wrap--narrow art__cuerpo">
      <p><em>Aquesta pàgina en català és una traducció de cortesia del nostre avís
      legal en castellà. En cas de discrepància, preval la versió en castellà
      (<a href="/legal.html">/legal.html</a>) i s'aplica la llei espanyola. Recomanem
      una revisió jurídica professional abans d'utilitzar aquesta traducció amb
      finalitats de compliment normatiu.</em></p>

      <h2 id="aviso-legal">Avís legal</h2>
      <p><strong>Titular del lloc web:</strong> {e(empresa)}.<br>
      <strong>CIF/NIF:</strong> [pendent de completar pel titular].<br>
      <strong>Domicili:</strong> {e(direccion)}.<br>
      {f'<strong>Contacte:</strong> {e(email)}' + (f' · {e(tel)}' if tel else '') + '.<br>' if email else ''}
      <strong>Domini:</strong> {e(dominio)}</p>
      <p>L'accés i l'ús d'aquest lloc web atribueix la condició d'usuari i implica
      l'acceptació de les condicions aquí recollides. {e(empresa)} és distribuïdor
      oficial d'AGIBOT i PUDU a Espanya i Portugal.</p>

      <h2 id="privacidad">Política de privacitat</h2>
      <p><strong>Responsable del tractament:</strong> {e(empresa)}{f', {e(email)}' if email else ''}.</p>
      <p><strong>Finalitat:</strong> atendre les sol·licituds d'informació, pressupost,
      demostració o suport que ens enviïs a través del formulari de contacte, i
      gestionar la relació comercial si arriba a formalitzar-se.</p>
      <p><strong>Legitimació:</strong> consentiment de la persona interessada en
      enviar les seves dades, i execució d'una eventual relació contractual.</p>
      <p><strong>Conservació:</strong> mentre es mantingui la relació amb l'usuari
      o durant els terminis legalment exigibles.</p>
      <p><strong>Destinataris:</strong> no se cedeixen dades a tercers llevat
      d'obligació legal o proveïdors necessaris per prestar el servei sol·licitat
      (per exemple, Shopify per processar una comanda).</p>
      <p><strong>Drets:</strong> pots exercir els teus drets d'accés, rectificació,
      supressió, oposició, limitació i portabilitat escrivint a{f' {e(email)}' if email else " l'adreça de contacte de RH·BOTS"}.</p>

      <h2 id="cookies">Política de galetes</h2>
      <p>Aquest lloc utilitza únicament les galetes tècniques necessàries per al seu
      funcionament. Si en el futur s'activa Google Analytics o una altra eina de
      mesurament, se sol·licitarà el consentiment previ de l'usuari abans de
      carregar-la.</p>
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

# ──────────────────────────────────────────────────────────────── alquiler ──
def _sin_punto_final(txt):
    """Quita el punto final para encadenar la nota con « · »."""
    return txt.rstrip().rstrip('.。')


def _cuota(valor):
    """Cuota mensual con el formato de número del idioma activo."""
    return f'{formato_precio(float(valor))} €'


def _tarifa_tabla(modelo):
    """Tabla de cuotas de un modelo, con la cuota sin IVA y con IVA."""
    filas = ''
    for plazo, duracion, cuota in modelo.get('tarifas', []):
        filas += (f'<tr><td>{e(plazo)}</td><td>{e(duracion)}</td>'
                  f'<td class="tarifa__cuota">{e(_cuota(cuota))}</td>'
                  f'<td class="tarifa__cuota tarifa__cuota--iva">{e(con_iva(cuota))}</td></tr>')
    if not filas:
        return ''
    return (f'<table class="tarifa"><caption class="tarifa__titulo">{t("tarifa_titulo")}</caption>'
            f'<thead><tr><th scope="col">{t("tarifa_plazo")}</th>'
            f'<th scope="col">{t("tarifa_duracion")}</th>'
            f'<th scope="col">{t("tarifa_cuota_sin")}</th>'
            f'<th scope="col">{t("tarifa_cuota_con")}</th></tr></thead>'
            f'<tbody>{filas}</tbody></table>')


def _cuota_mas_baja_num(modelo):
    """El importe (sin formatear) de la cuota del plazo más largo."""
    tarifas = modelo.get('tarifas') or []
    return tarifas[-1][2] if tarifas else 0


def _cuota_mas_baja(modelo):
    """La cuota del plazo más largo, para el «desde X/mes» de la cabecera."""
    tarifas = modelo.get('tarifas') or []
    return _cuota(tarifas[-1][2]) if tarifas else ''


def alquiler_page():
    """Portada de la sección: las dos modalidades de alquiler."""
    base = nivel(LANG)
    a = ALQUILER
    out = [head(t('alquiler_titulo'), a.get('lede', ''), base, 'alquiler.html'),
           header(base, 'alquiler', 'alquiler.html'), '<main id="contenido">']

    out.append(f'''
  <section class="hero hero--catalogo" id="inicio">
    <img class="hero__foto" src="{base}{e(a.get('imagen', ''))}" alt="" aria-hidden="true" fetchpriority="high">
    <div class="hero__velo" aria-hidden="true"></div>
    <div class="hero__diagonal" aria-hidden="true"></div>
    <div class="wrap hero__copy">
      <p class="kicker hero__kicker">{e(a.get('kicker', ''))}</p>
      <h1 class="display display--hero">{e(a.get('h1', ''))}</h1>
      <p class="lede lede--hero">{e(a.get('lede', ''))}</p>
      <div class="hero__cta">
        <a class="pill" href="{base}contacto.html"><span>{t('pedir_presupuesto')}</span>{CHEVRON}</a>
      </div>
    </div>
  </section>
''')

    tarjetas = ''
    for op in a.get('opciones', []):
        tarjetas += (
            f'<li class="pcard reveal"><a href="{base}{e(op["href"])}">'
            f'<div class="pcard__media pcard__media--escena">'
            f'<img src="{base}{e(op.get("imagen", ""))}" alt="{e(op["titulo"])}" loading="lazy"></div>'
            f'<div class="pcard__body"><h3>{e(op["titulo"])}</h3>'
            f'<p>{e(op.get("texto", ""))}</p>'
            f'<span class="pcard__more">{t("mas_informacion")}</span></div></a></li>')
    out.append(f'''  <section class="section section--white">
    <div class="wrap">
      <ul class="pgrid pgrid--duo">{tarjetas}</ul>
    </div>
  </section>
''')

    out.append(bloque_elegir(base, t('alquiler_cta_titulo'), t('alquiler_cta_texto')))
    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


def alquiler_limpieza_page():
    """Fregadoras y barredoras en alquiler, con las cuotas de la tarifa."""
    base = nivel(LANG)
    a = ALQUILER.get('limpieza', {})
    # el botón del hero baja al primer modelo de esta misma página
    modelos = a.get('modelos', [])
    primer = modelos[0].get('slug', '') if modelos else ''
    out = [head(t('alquiler_limpieza_titulo'), a.get('lede', ''), base, 'alquiler-limpieza.html'),
           header(base, 'alquiler', 'alquiler-limpieza.html'), '<main id="contenido">']

    out.append(f'''
  <section class="hero hero--catalogo" id="inicio">
    <img class="hero__foto" src="{base}{e(a.get('imagen', ''))}" alt="" aria-hidden="true" fetchpriority="high">
    <div class="hero__velo" aria-hidden="true"></div>
    <div class="hero__diagonal" aria-hidden="true"></div>
    <div class="wrap hero__copy">
      <p class="kicker hero__kicker">{e(a.get('kicker', ''))}</p>
      <h1 class="display display--hero">{e(a.get('h1', ''))}</h1>
      <p class="lede lede--hero">{e(a.get('lede', ''))}</p>
      <div class="hero__cta">
        <a class="pill" href="{base}contacto.html"><span>{t('pedir_presupuesto')}</span>{CHEVRON}</a>
        <a class="pill pill--line" href="#{e(primer)}"><span>{t('ver_robots')}</span>{CHEVRON}</a>
      </div>
    </div>
  </section>
''')

    for i, m in enumerate(a.get('modelos', [])):
        prod = BY_SLUG.get(m.get('slug'))
        nombre = prod['name'] if prod else m.get('slug', '')
        if prod and prod.get('hero'):
            foto = (f'<img src="{base}{e(prod["hero"])}" alt="{e(nombre)}" loading="lazy">')
        else:
            foto = placeholder('limpieza', nombre)
        chips = ''.join(f'<li>{e(x)}</li>' for x in m.get('destacados', []))
        desde = _cuota_mas_baja(m)
        ficha = ''
        if prod and prod.get('ficha', True):
            ficha = (f'<a class="pill pill--line" href="{base}robots/{prod["slug"]}.html">'
                     f'<span>{t("ver_ficha_tecnica")}</span>{CHEVRON}</a>')
        fondo = 'section--white' if i % 2 == 0 else 'section--light'
        lado = ' sector--invertido' if i % 2 else ''
        out.append(f'''  <section class="section {fondo} sector sector--alq{lado}" id="{e(m.get("slug", ""))}">
    <div class="wrap sector__grid">
      <figure class="sector__foto sector__foto--producto reveal">{foto}</figure>
      <div class="sector__texto reveal">
        <p class="kicker">{e(m.get('etiqueta', ''))}</p>
        <h2 class="sector__titulo">{e(nombre)}</h2>
        <p class="sector__lede">{e(m.get('claim', ''))}</p>
        <p class="alq__desde">{t('tarifa_desde', n=e(desde))}
          {nota_iva(_cuota_mas_baja_num(m), 'alq__desde-iva')}</p>
        <p class="alq__texto">{e(m.get('texto', ''))}</p>
        <ul class="sector__tareas">{chips}</ul>
        {_tarifa_tabla(m)}
        <p class="alq__nota">{e(_sin_punto_final(a.get('cuota_nota', '')))} · {t('iva_no_incluido')}; {t('con_iva_generico')}</p>
        <div class="alq__cta">
          <a class="pill" href="{base}contacto.html"><span>{t('alquiler_solicitar')}</span>{CHEVRON}</a>
          {ficha}
        </div>
      </div>
    </div>
  </section>
''')

    incluye = ''.join(f'<li>{e(x)}</li>' for x in a.get('incluye', []))
    no_incluye = ''.join(f'<li>{e(x)}</li>' for x in a.get('no_incluye', []))
    if incluye or no_incluye:
        out.append(f'''  <section class="section section--light" id="condiciones">
    <div class="wrap">
      <header class="section-head reveal"><h2 class="h-section">{t('alquiler_incluye')}</h2></header>
      <div class="incluye reveal">
        <div class="incluye__col incluye__col--si">
          <h3 class="incluye__titulo">{t('alquiler_incluye_si')}</h3>
          <ul class="incluye__lista">{incluye}</ul>
        </div>
        <div class="incluye__col incluye__col--no">
          <h3 class="incluye__titulo">{t('alquiler_incluye_no')}</h3>
          <ul class="incluye__lista">{no_incluye}</ul>
        </div>
      </div>
    </div>
  </section>
''')

    out.append(bloque_elegir(base, t('alquiler_cta_titulo'), t('alquiler_cta_texto')))
    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


def alquiler_humanoides_page():
    """Alquiler de humanoides para eventos: una experiencia, no una máquina."""
    base = nivel(LANG)
    a = ALQUILER.get('humanoides', {})
    precio = f"{t('ev_desde')} {a.get('precio_desde', '')} {a.get('precio_unidad', '')} + IVA"
    out = [head(t('alquiler_humanoides_titulo'), t('alquiler_humanoides_desc'), base, 'alquiler-humanoides.html',
                og_img=a.get('imagen'), extra_jsonld=[schema_faqpage(a.get("faq", []))]),
           header(base, 'alquiler', 'alquiler-humanoides.html'), '<main id="contenido">']

    # ---- 1 · hero
    out.append(f'''
  <section class="hero hero--catalogo hero--evento" id="inicio">
    <img class="hero__foto" src="{base}{e(a.get('imagen', ''))}" alt="" aria-hidden="true" fetchpriority="high">
    <div class="hero__velo" aria-hidden="true"></div>
    <div class="hero__diagonal" aria-hidden="true"></div>
    <div class="wrap hero__copy">
      <p class="kicker hero__kicker">{e(a.get('kicker', ''))}</p>
      <h1 class="display display--hero">{e(a.get('h1', ''))}</h1>
      <p class="lede lede--hero">{e(a.get('lede', ''))}</p>
      <div class="hero__cta">
        <a class="pill" href="#presupuesto"><span>{t('ev_solicitar')}</span>{CHEVRON}</a>
        <a class="pill pill--line" href="#como-funciona"><span>{t('ev_como_funciona')}</span>{CHEVRON}</a>
      </div>
    </div>
  </section>
''')

    # ---- 2 · una experiencia que atrae miradas
    at = a.get('atrae')
    if at:
        parrafos = ''.join(f'<p class="sector__lede">{e(x)}</p>' for x in at.get('parrafos', []))
        out.append(f'''  <section class="section section--white sector" id="atraccion">
    <div class="wrap sector__grid">
      <figure class="sector__foto sector__foto--producto reveal">
        <img src="{base}{e(at.get('imagen', ''))}" alt="{e(at.get('titulo', ''))}" loading="lazy">
      </figure>
      <div class="sector__texto reveal">
        <p class="kicker">{e(at.get('kicker', ''))}</p>
        <h2 class="sector__titulo">{e(at.get('titulo', ''))}</h2>
        {parrafos}
        <p class="evmodelo">{t('ev_modelo')}
          <a href="{base}robots/rhx2-ultra.html">{t('ver_ficha_tecnica')}</a></p>
        <p class="evprecio">
          <span class="evprecio__etq">{t('ev_desde')}</span>
          <strong class="evprecio__num">{e(a.get('precio_desde', ''))}</strong>
          <span class="evprecio__unidad">{e(a.get('precio_unidad', ''))} {t('iva_corto')}</span>
        </p>
        <p class="evprecio__coniva">{t('con_iva', n=con_iva(importe_de_texto(a.get('precio_desde', ''))))} {e(a.get('precio_unidad', ''))}</p>
        <p class="evprecio__nota">{e(a.get('precio_nota', ''))}</p>
        <div class="alq__cta">
          <a class="pill" href="#presupuesto"><span>{t('ev_solicitar')}</span>{CHEVRON}</a>
        </div>
      </div>
    </div>
  </section>
''')

    # ---- 3 · qué puede hacer
    cap = a.get('capacidades')
    if cap:
        tarjetas = ''.join(
            f'<li class="evcard reveal"><span class="evcard__num" aria-hidden="true">{i:02d}</span>'
            f'<h3>{e(tit)}</h3><p>{e(txt)}</p></li>'
            for i, (tit, txt) in enumerate(cap.get('items', []), 1))
        out.append(f'''  <section class="section section--navy" id="capacidades">
    <div class="wrap">
      <header class="section-head reveal"><p class="kicker">{e(cap.get('kicker', ''))}</p>
        <h2 class="h-section h-section--onblue onblue">{e(cap.get('titulo', ''))}</h2></header>
      <ul class="evcards">{tarjetas}</ul>
    </div>
  </section>
''')

    # ---- 4 · personalización
    pz = a.get('personaliza')
    if pz:
        chips = ''.join(f'<li>{e(x)}</li>' for x in pz.get('opciones', []))
        out.append(f'''  <section class="section section--white sector sector--invertido" id="personalizar">
    <div class="wrap sector__grid">
      <figure class="sector__foto reveal">
        <img src="{base}{e(pz.get('imagen', ''))}" alt="{t('ev_foto_alt')}" loading="lazy">
      </figure>
      <div class="sector__texto reveal">
        <p class="kicker">{e(pz.get('kicker', ''))}</p>
        <h2 class="sector__titulo">{e(pz.get('titulo', ''))}</h2>
        <p class="sector__lede">{e(pz.get('texto', ''))}</p>
        <ul class="evchips">{chips}</ul>
        <p class="evprecio evprecio--linea">
          <span class="evprecio__etq">{t('ev_personalizacion_desde')}</span>
          <strong class="evprecio__num evprecio__num--sm">{e(pz.get('precio_desde', ''))}</strong>
          <span class="evprecio__unidad">{t('iva_corto')}</span>
        </p>
        <p class="evprecio__coniva">{t('con_iva', n=con_iva(importe_de_texto(pz.get('precio_desde', ''))))}</p>
        <p class="alq__nota">{e(pz.get('precio_nota', ''))}</p>
        <div class="alq__cta">
          <a class="pill" href="#presupuesto"><span>{t('ev_personalizar')}</span>{CHEVRON}</a>
        </div>
      </div>
    </div>
  </section>
''')

    # ---- 5 · tarifa
    tf = a.get('tarifa')
    if tf:
        incluye = ''.join(f'<li>{e(x)}</li>' for x in tf.get('incluye', []))
        out.append(f'''  <section class="section section--navy section--compacta" id="tarifas">
    <div class="wrap wrap--narrow">
      <header class="section-head section-head--compacta reveal"><p class="kicker">{e(tf.get('kicker', ''))}</p>
        <h2 class="h-section h-section--onblue onblue">{e(tf.get('titulo', ''))}</h2></header>
      <div class="evtarifa reveal">
        <div class="evtarifa__col">
          <p class="evprecio evprecio--grande">
            <span class="evprecio__etq">{t('ev_desde')}</span>
            <strong class="evprecio__num">{e(a.get('precio_desde', ''))}</strong>
            <span class="evprecio__unidad">{e(a.get('precio_unidad', ''))} {t('iva_corto')}</span>
          </p>
          <p class="evprecio__coniva">{t('con_iva', n=con_iva(importe_de_texto(a.get('precio_desde', ''))))} {e(a.get('precio_unidad', ''))}</p>
          <p class="evtarifa__nota">{e(tf.get('nota', ''))}</p>
          <a class="pill" href="#presupuesto"><span>{t('ev_solicitar')}</span>{CHEVRON}</a>
        </div>
        <div class="evtarifa__col">
          <p class="evtarifa__titulo">{e(tf.get('incluye_titulo', ''))}</p>
          <ul class="evtarifa__lista">{incluye}</ul>
        </div>
      </div>
    </div>
  </section>
''')

    # ---- 6 · ideal para
    idl = a.get('ideal')
    if idl:
        items = ''.join(f'<li class="reveal">{e(x)}</li>' for x in idl.get('items', []))
        out.append(f'''  <section class="section section--white" id="ideal">
    <div class="wrap">
      <header class="section-head reveal"><p class="kicker">{e(idl.get('kicker', ''))}</p>
        <h2 class="h-section">{e(idl.get('titulo', ''))}</h2></header>
      <ul class="evideal">{items}</ul>
    </div>
  </section>
''')

    # ---- 7 · cómo funciona, con el vídeo debajo de los pasos (sin titular propio)
    pr = a.get('proceso')
    if pr:
        pasos = ''.join(
            f'<li class="ctopaso reveal"><p class="ctopaso__num">{i:02d}</p>'
            f'<h3 class="ctopaso__titulo">{e(tit)}</h3><p class="ctopaso__texto">{e(txt)}</p></li>'
            for i, (tit, txt) in enumerate(pr.get('pasos', []), 1))
        videos = (a.get('galeria') or {}).get('videos') or []
        v = videos[0] if videos else None
        video = '' if not v else (
            f'<div class="evvideo reveal">'
            f'<video controls preload="none" playsinline aria-label="{e(v.get("titulo", ""))}" '
            f'poster="{base}{e(v["poster"])}">'
            f'<source src="{base}{e(v["src"])}" type="video/mp4">'
            f'{t("navegador_sin_video")}</video></div>')
        out.append(f'''  <section class="section section--light" id="como-funciona">
    <div class="wrap">
      <header class="section-head reveal"><p class="kicker">{e(pr.get('kicker', ''))}</p>
        <h2 class="h-section">{e(pr.get('titulo', ''))}</h2></header>
      <ul class="ctopasos ctopasos--ev">{pasos}</ul>
      {video}
    </div>
  </section>
''')

    # ---- 10 · preguntas frecuentes
    if a.get('faq'):
        out.append(bloque_faq(a['faq']))

    # ---- 11 · cierre con formulario
    out.append(formulario_evento(base, a.get('cierre', {})))

    out.append('</main>')
    out.append(footer(base))
    return ''.join(out)


def formulario_evento(base, cierre):
    """Cierre de la página de eventos, con la misma estructura que contacto:
    columna de texto a la izquierda y tarjeta con el formulario a la derecha."""
    principal = CONTACTO['personas'][0] if CONTACTO.get('personas') else {}
    email = CONTACTO.get('email_directo') or principal.get('email', 'info@rh-bots.com')
    return f'''  <section class="section section--navy section--compacta ctoform evform" id="presupuesto">
    <div class="wrap ctoform__grid">
      <aside class="ctoform__lado reveal">
        <p class="kicker">{t('ev_solicitar')}</p>
        <h2 class="ctoform__ladotitulo">{e(cierre.get('titulo', ''))}</h2>
        <p class="ctoform__ladotexto">{e(cierre.get('texto', ''))}</p>
      </aside>

      <div class="ctoform__caja reveal">
        <div class="ctoform__cab">
          <div>
            <p class="kicker">{t('formulario')}</p>
            <h2 class="ctoform__titulo">{t('ev_form_titulo')}</h2>
          </div>
          <p class="ctoform__sello">{t('ev_form_sello')}</p>
        </div>
        <form class="form" id="eventoForm" data-email="{e(email)}" novalidate>
          <div class="form__two">
            <div class="form__row">
              <label for="ev-nombre">{t('nombre')}</label>
              <input id="ev-nombre" name="nombre" type="text" autocomplete="name" placeholder="{t('tu_nombre')}" required>
            </div>
            <div class="form__row">
              <label for="ev-empresa">{t('empresa_campo')}</label>
              <input id="ev-empresa" name="empresa" type="text" autocomplete="organization" placeholder="{t('nombre_empresa_placeholder')}">
            </div>
          </div>
          <div class="form__two">
            <div class="form__row">
              <label for="ev-email">{t('email')}</label>
              <input id="ev-email" name="email" type="email" autocomplete="email" placeholder="tu@empresa.com" required>
            </div>
            <div class="form__row">
              <label for="ev-tel">{t('telefono')}</label>
              <input id="ev-tel" name="tel" type="tel" autocomplete="tel" placeholder="+34 600 000 000">
            </div>
          </div>
          <div class="form__two">
            <div class="form__row">
              <label for="ev-fecha">{t('ev_fecha')}</label>
              <input id="ev-fecha" name="fecha" type="date">
            </div>
            <div class="form__row">
              <label for="ev-ciudad">{t('ev_ciudad')}</label>
              <input id="ev-ciudad" name="ciudad" type="text" placeholder="{t('ev_ciudad_ph')}">
            </div>
          </div>
          <div class="form__two">
            <div class="form__row">
              <label for="ev-dias">{t('ev_dias')}</label>
              <input id="ev-dias" name="dias" type="number" min="1" step="1" placeholder="1">
            </div>
            <div class="form__row">
              <label for="ev-tipo">{t('ev_tipo')}</label>
              <input id="ev-tipo" name="tipo" type="text" placeholder="{t('ev_tipo_ph')}">
            </div>
          </div>
          <div class="form__row">
            <label for="ev-haria">{t('ev_que_haga')}</label>
            <textarea id="ev-haria" name="haria" rows="2" placeholder="{t('ev_que_haga_ph')}"></textarea>
          </div>
          <div class="form__row">
            <label for="ev-mensaje">{t('ev_mensaje')}</label>
            <textarea id="ev-mensaje" name="mensaje" rows="3" placeholder="{t('ev_mensaje_ph')}" required></textarea>
          </div>
          <div class="form__consent">
            <input id="ev-privacidad" name="privacidad" type="checkbox" required>
            <label for="ev-privacidad">{t('consiento_privacidad')}
              <a href="{base}legal.html#privacidad">{t('politica_privacidad_link')}</a>{t('consiento_privacidad_fin')}</label>
          </div>
          <button class="pill pill--ancho" type="submit"><span>{t('ev_solicitar')}</span>{CHEVRON}</button>
          <p class="form__nota" id="eventoNota" role="status"></p>
        </form>
      </div>
    </div>
  </section>
'''


def contacto_page():
    base = nivel(LANG)
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
        ps = [p for p in PRODUCTOS if p['family'] == key and p.get('ficha', True)]
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
    base = nivel(LANG)
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
    """Un único sitemap con las seis versiones de cada página (una por
    idioma), cada una apuntando a sus alternativas con xhtml:link, como
    recomienda Google para sitios multilingües."""
    d = SEO['dominio'].rstrip('/')
    rutas = [('', '1.0'), ('robots.html', '0.9'), ('aplicaciones.html', '0.8'), ('rh-bots.html', '0.6'),
             ('alquiler.html', '0.8'), ('alquiler-limpieza.html', '0.8'),
             ('alquiler-humanoides.html', '0.7'),
             ('contacto.html', '0.7'), ('blog.html', '0.5'), ('legal.html', '0.2')]
    rutas += [(f'robots/{p["slug"]}.html', '0.8') for p in _PRODUCTOS_ES if p.get('ficha', True)]
    rutas += [(p['url'], '0.6') for p in _SITIO_ES['posts'] if p.get('url')]

    def loc(ruta, lang):
        prefijo = f'{lang}/' if lang != 'es' else ''
        return f'{d}/{prefijo}{ruta}' if ruta else f'{d}/{prefijo}'

    urls = ''
    for ruta, pr in rutas:
        enlaces = ''.join(
            f'<xhtml:link rel="alternate" hreflang="{cod}" href="{loc(ruta, cod)}"/>' for cod in IDIOMAS)
        for lang in IDIOMAS:
            urls += (f'  <url><loc>{loc(ruta, lang)}</loc><lastmod>{FECHA_BUILD}</lastmod>'
                     f'<priority>{pr}</priority>'
                     f'{enlaces}'
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
    prefijo = f'{d}/{LANG}' if LANG != 'es' else d

    _INTRO = {
        'es': 'Distribuidor oficial de AGIBOT y PUDU en España y Portugal. Robots de limpieza '
              'autónoma, humanoides, cuadrúpedos, AMR de intralogística y accesorios, con asesoramiento, instalación, '
              'formación y mantenimiento. Sede en Picassent (Valencia).',
        'pt': 'Distribuidor oficial da AGIBOT e da PUDU em Espanha e Portugal. Robôs de limpeza '
              'autónoma, humanoides, quadrúpedes, AMR de intralogística e acessórios, com aconselhamento, instalação, '
              'formação e manutenção. Sede em Picassent (Valência, Espanha).',
        'en': 'Official distributor of AGIBOT and PUDU in Spain and Portugal. Autonomous cleaning, '
              'humanoid and quadruped robots, intralogistics AMRs and accessories, with advice, installation, '
              'training and maintenance. Based in Picassent (Valencia, Spain).',
        'fr': 'Distributeur officiel d\'AGIBOT et de PUDU en Espagne et au Portugal. Robots de nettoyage '
              'autonome, humanoïdes, quadrupèdes, AMR d\'intralogistique et accessoires, avec conseil, installation, '
              'formation et maintenance. Basé à Picassent (Valence, Espagne).',
        'zh': 'AGIBOT和PUDU在西班牙和葡萄牙的官方经销商。自主清洁机器人、人形机器人、四足机器人、AMR移动机器人及配件，'
              '提供咨询、安装、培训和维护服务。总部位于西班牙巴伦西亚皮卡森特（Picassent）。',
        'ca': 'Distribuïdor oficial d\'AGIBOT i PUDU a Espanya i Portugal. Robots de neteja '
              'autònoma, humanoides, quadrúpedes, AMR d\'intralogística i accessoris, amb assessorament, instal·lació, '
              'formació i manteniment. Seu a Picassent (València).',
        'de': 'Offizieller Vertriebspartner von AGIBOT und PUDU in Spanien und Portugal. Autonome '
              'Reinigungsroboter, Humanoide, Vierbeiner, AMR für die Intralogistik und Zubehör, mit Beratung, '
              'Installation, Schulung und Wartung. Sitz in Picassent (Valencia).',
        'ar': 'موزّع معتمد لشركتي AGIBOT وPUDU في إسبانيا والبرتغال. روبوتات تنظيف ذاتية وروبوتات بشرية '
              'ورباعية الأرجل وروبوتات AMR للخدمات اللوجستية الداخلية وملحقات، مع الاستشارة والتركيب والتدريب '
              'والصيانة. المقر في بيكاسنت (فالنسيا).',
    }
    _ROBOTS_H2 = {'es': 'Robots', 'pt': 'Robôs', 'en': 'Robots', 'fr': 'Robots', 'zh': '机器人', 'ca': 'Robots',
                  'de': 'Roboter', 'ar': 'الروبوتات'}
    _EMPRESA_H2 = {'es': 'Empresa', 'pt': 'Empresa', 'en': 'Company', 'fr': 'Entreprise', 'zh': '公司', 'ca': 'Empresa',
                   'de': 'Unternehmen', 'ar': 'الشركة'}
    _CATALOGO = {'es': 'Catálogo completo', 'pt': 'Catálogo completo', 'en': 'Full catalog',
                 'fr': 'Catalogue complet', 'zh': '完整产品目录', 'ca': 'Catàleg complet',
                 'de': 'Vollständiger Katalog', 'ar': 'الكتالوج الكامل'}
    _APLICACIONES = {'es': 'Aplicaciones por sector: qué robot encaja en cada uso',
                      'pt': 'Aplicações por setor: que robô se adapta a cada uso',
                      'en': 'Applications by sector: which robot fits which use',
                      'fr': 'Applications par secteur : quel robot correspond à quel usage',
                      'zh': '按行业分类的应用：哪种机器人适合哪种用途',
                      'ca': 'Aplicacions per sector: quin robot encaixa en cada ús',
                      'de': 'Anwendungen nach Branche: welcher Roboter zu welchem Einsatz passt',
                      'ar': 'التطبيقات حسب القطاع: أي روبوت يناسب كل استخدام'}
    _QUIENES = {'es': 'Quiénes somos: equipo e historia de RH·BOTS',
                'pt': 'Quem somos: equipa e história da RH·BOTS',
                'en': 'About us: the RH·BOTS team and story',
                'fr': 'Qui sommes-nous : l\'équipe et l\'histoire de RH·BOTS',
                'zh': '关于我们：RH·BOTS团队与历史',
                'ca': 'Qui som: equip i història de RH·BOTS',
                'de': 'Über uns: Team und Geschichte von RH·BOTS',
                'ar': 'من نحن: فريق RH·BOTS وقصتها'}
    _CONTACTO_L = {'es': 'Contacto', 'pt': 'Contacto', 'en': 'Contact', 'fr': 'Contact', 'zh': '联系我们', 'ca': 'Contacte',
                   'de': 'Kontakt', 'ar': 'اتصل بنا'}
    _OPCIONAL = {'es': 'Optional', 'pt': 'Optional', 'en': 'Optional', 'fr': 'Optional', 'zh': 'Optional', 'ca': 'Optional',
                 'de': 'Optional', 'ar': 'Optional'}
    _BLOG_L = {'es': 'Blog', 'pt': 'Blog', 'en': 'Blog', 'fr': 'Blog', 'zh': '博客', 'ca': 'Blog',
               'de': 'Blog', 'ar': 'المدوّنة'}
    _LEGAL_L = {'es': 'Aviso legal y privacidad', 'pt': 'Aviso legal e privacidade',
                'en': 'Legal notice and privacy', 'fr': 'Mentions légales et confidentialité',
                'zh': '法律声明与隐私', 'ca': 'Avís legal i privacitat',
                'de': 'Impressum und Datenschutz', 'ar': 'إشعار قانوني وخصوصية'}

    out = ['# RH·BOTS\n', f'> {_INTRO[LANG]}\n']

    out.append(f'## {_ROBOTS_H2[LANG]}\n')
    for key, nombre, _ in FAMILIAS:
        modelos = [p for p in PRODUCTOS if p['family'] == key and p.get('ficha', True)]
        if not modelos:
            continue
        out.append(f'\n### {nombre}\n')
        for p in modelos:
            out.append(f'- [{p["name"]}]({prefijo}/robots/{p["slug"]}.html): {p["claim"]}')

    out.append(f'\n\n## {_EMPRESA_H2[LANG]}\n')
    out.append(f'- [{_CATALOGO[LANG]}]({prefijo}/robots.html)')
    out.append(f'- [{_APLICACIONES[LANG]}]({prefijo}/aplicaciones.html)')
    out.append(f'- [{_QUIENES[LANG]}]({prefijo}/rh-bots.html)')
    out.append(f'- [{_CONTACTO_L[LANG]}]({prefijo}/contacto.html)')
    out.append(f'\n\n## {_OPCIONAL[LANG]}\n')
    out.append(f'- [{_BLOG_L[LANG]}]({prefijo}/blog.html)')
    out.append(f'- [{_LEGAL_L[LANG]}]({prefijo}/legal.html)')
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
        ('alquiler.html',  alquiler_page()),
        ('alquiler-limpieza.html', alquiler_limpieza_page()),
        ('alquiler-humanoides.html', alquiler_humanoides_page()),
        ('rh-bots.html',  rh_bots_page()),
        ('blog.html',     blog_page()),
        ('contacto.html', contacto_page()),
        ('legal.html',    legal_page()),
    ]
    for nombre, contenido in paginas:
        write(os.path.join(carpeta, nombre), contenido)

    fichas_vivas = set()
    for p in PRODUCTOS:
        if not p.get('ficha', True):
            continue
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
    return len(paginas) + len(fichas_vivas) + len(slugs_vivos)


def main():
    total = 0
    for lang in IDIOMAS:
        set_lang(lang)
        carpeta = WEB if lang == 'es' else os.path.join(WEB, lang)
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
    con_ficha = len([p for p in PRODUCTOS if p.get('ficha', True)])
    print(f'OK — {total} páginas ({"+".join(IDIOMAS)}): home, catálogo, rh-bots, blog, contacto '
          f'y {con_ficha} fichas, en cada idioma')
    print(f'     sitemap.xml y robots.txt · dominio {SEO["dominio"]} · analítica: {ga}')


if __name__ == '__main__':

    main()
