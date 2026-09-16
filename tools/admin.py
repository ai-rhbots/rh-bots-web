# -*- coding: utf-8 -*-
"""
Panel de administración de RH·BOTS.

    python tools/admin.py              arranca en http://127.0.0.1:5001
    python tools/admin.py --clave      cambia la contraseña

Edita el contenido (textos, blog, SEO, analítica, fichas) sobre los JSON de
datos/. Cada «Guardar» regenera la web al momento — no hace falta ningún
paso aparte de «Publicar».

── Seguridad ────────────────────────────────────────────────────────────────
Pensado para poder publicarse tal cual:
  · contraseña guardada sólo como hash PBKDF2, nunca en claro;
  · sesión firmada, cookie HttpOnly y SameSite=Lax;
  · token CSRF obligatorio en cada formulario;
  · límite de intentos de acceso por IP;
  · sin modo depuración.

Al subirlo a un servidor hay que definir estas variables de entorno:
    RHBOTS_SECRET=<cadena larga y aleatoria>
    RHBOTS_PASSWORD_HASH=<lo que imprime «--clave»>
    RHBOTS_HTTPS=1          activa la cookie Secure (obligatorio con HTTPS)
y servirlo con un servidor real, p. ej.:
    gunicorn "tools.admin:crear_app()"

── Sincronización con GitHub (para hosting con disco efímero) ───────────────
El disco de un servicio como Render no es persistente: en cada reinicio
vuelve a como estaba en el último despliegue. Para que los cambios hechos
desde el panel no se pierdan, y para que lleguen a Vercel, hay que activar
la sincronización con git:
    RHBOTS_GIT_PUSH=1
    GITHUB_TOKEN=<token con permiso "repo" sobre este repositorio>
Con esto, cada «Guardar» hace además `git add/commit/push`, y al arrancar
el panel hace `git pull` para partir del último contenido publicado.
"""
import io
import json
import os
import re
import secrets
import subprocess
import sys
import time
import unicodedata
from functools import wraps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from flask import (Flask, abort, flash, jsonify, redirect,  # noqa: E402
                   render_template, request, send_from_directory, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash  # noqa: E402

import datos as D  # noqa: E402
import medios as M  # noqa: E402
from limpiar_html import limpiar, resumir  # noqa: E402
from productos import FAMILIAS  # noqa: E402

ARCHIVO_CLAVE = os.path.join(ROOT, 'datos', 'admin.json')
USUARIO = os.environ.get('RHBOTS_USER', 'admin')

MAX_INTENTOS = 6
BLOQUEO_SEG = 300
_intentos = {}


# ── contraseña ────────────────────────────────────────────────────────────
def _hash_guardado():
    if os.environ.get('RHBOTS_PASSWORD_HASH'):
        return os.environ['RHBOTS_PASSWORD_HASH']
    if os.path.exists(ARCHIVO_CLAVE):
        with io.open(ARCHIVO_CLAVE, encoding='utf-8') as f:
            return json.load(f).get('hash')
    return None


def _guardar_hash(h):
    os.makedirs(os.path.dirname(ARCHIVO_CLAVE), exist_ok=True)
    with io.open(ARCHIVO_CLAVE, 'w', encoding='utf-8') as f:
        json.dump({'hash': h}, f)


def establecer_clave():
    import getpass
    c1 = getpass.getpass('Nueva contraseña: ')
    if len(c1) < 10:
        print('Demasiado corta: usa 10 caracteres o más.')
        return 1
    if c1 != getpass.getpass('Repítela: '):
        print('No coinciden.')
        return 1
    h = generate_password_hash(c1)
    _guardar_hash(h)
    print('\nContraseña actualizada.')
    print('En el servidor, define en su lugar esta variable de entorno:')
    print(f'  RHBOTS_PASSWORD_HASH={h}')
    return 0


# ── utilidades de formulario ──────────────────────────────────────────────
def lineas(texto):
    """Textarea → lista de líneas no vacías."""
    return [l.strip() for l in (texto or '').replace('\r', '').split('\n') if l.strip()]


def filas(texto, n):
    """Textarea con campos separados por « | » → lista de listas de n campos."""
    out = []
    for l in lineas(texto):
        partes = [p.strip() for p in l.split('|')]
        partes += [''] * (n - len(partes))
        out.append(partes[:n])
    return out


def slug_base(texto):
    """«¿Qué robot elegir?» → «que-robot-elegir»."""
    t = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode()
    t = re.sub(r'[^a-zA-Z0-9]+', '-', t).strip('-').lower()
    return t[:70] or 'entrada'


def slug_unico(titulo, posts, excluir=None):
    """Slug a partir del título, sin chocar con otra entrada existente.

    `excluir` es el índice de la propia entrada al editar, para que no
    choque consigo misma cuando se guarda sin tocar el título.
    """
    base = slug_base(titulo)
    ocupados = {p['slug'] for k, p in enumerate(posts) if p.get('slug') and k != excluir}
    slug = base
    n = 2
    while slug in ocupados:
        slug = f'{base}-{n}'
        n += 1
    return slug


def a_texto(items):
    """Lista de listas → textarea con « | »."""
    if not items:
        return ''
    return '\n'.join(' | '.join('' if x is None else str(x) for x in fila)
                     if isinstance(fila, (list, tuple)) else str(fila)
                     for fila in items)


# ── publicación automática ──────────────────────────────────────────────
def _publicar():
    """Regenera las páginas estáticas a partir de los JSON de datos/.

    Antes esto sólo pasaba al pulsar «Publicar cambios», un paso aparte del
    guardado. Ahora se llama justo después de cada guardado, así que un
    cambio en el panel se ve en la web sin ningún paso adicional.
    """
    r = subprocess.run([sys.executable, os.path.join(HERE, 'build.py')],
                       capture_output=True, text=True, cwd=ROOT, timeout=180)
    return r.returncode == 0, (r.stdout or '') + (r.stderr or '')


# ── sincronización con git (hosting con disco efímero) ───────────────────
GIT_PUSH = os.environ.get('RHBOTS_GIT_PUSH') == '1'
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GIT_REMOTE = os.environ.get('RHBOTS_GIT_REMOTE', 'origin')
GIT_BRANCH = os.environ.get('RHBOTS_GIT_BRANCH', 'master')
GIT_URL = os.environ.get('RHBOTS_GIT_URL', 'https://github.com/ai-rhbots/rh-bots-web.git')
GIT_IDENTIDAD = ['-c', 'user.name=RH-BOTS Panel', '-c', 'user.email=ai.rhbots@gmail.com']


def _git(*args, timeout=60):
    extra = []
    if GITHUB_TOKEN:
        # Inyecta el token sólo para esta llamada (no queda escrito en
        # .git/config ni en la URL del remoto).
        extra = ['-c', f'http.https://github.com/.extraheader=AUTHORIZATION: bearer {GITHUB_TOKEN}']
    try:
        r = subprocess.run(['git'] + extra + list(args), capture_output=True,
                           text=True, cwd=ROOT, timeout=timeout)
        return r.returncode == 0, (r.stdout or '') + (r.stderr or '')
    except (subprocess.SubprocessError, OSError) as ex:
        return False, str(ex)


def _asegurar_remoto():
    """Da de alta el remoto si el checkout del hosting no lo trae.

    Render (y algún otro hosting) despliega el repositorio sin dejar el
    remoto «origin» apuntando a GitHub — a veces no hay ningún remoto, a
    veces apunta a la propia infraestructura del hosting. Sin esto, cada
    push fallaba con «'origin' does not appear to be a git repository».
    """
    ok, _ = _git('remote', 'get-url', GIT_REMOTE)
    if not ok:
        _git('remote', 'add', GIT_REMOTE, GIT_URL)
    else:
        _git('remote', 'set-url', GIT_REMOTE, GIT_URL)


def _sincronizar_git(mensaje):
    """Sube a GitHub lo que ha cambiado (datos/, web/) tras un guardado.

    En local (RHBOTS_GIT_PUSH sin definir) no hace nada: seguimos usando el
    flujo normal de git a mano. En el servidor del panel sí, por dos razones
    a la vez: es como los cambios llegan a Vercel, y es cómo sobreviven a un
    reinicio del servicio (su disco es efímero; git es el almacén real).
    """
    if not GIT_PUSH:
        return True, ''
    if not GITHUB_TOKEN:
        return False, ('Falta la variable de entorno GITHUB_TOKEN en el servidor — '
                       'sin ella no hay forma de autenticarse contra GitHub. '
                       'Ponla en Render - el servicio - Environment.')
    _asegurar_remoto()
    _git('add', '-A')
    ok_commit, salida_commit = _git(*GIT_IDENTIDAD, 'commit', '-m', f'Panel: {mensaje}')
    if not ok_commit and 'nothing to commit' not in salida_commit.lower():
        return False, salida_commit
    # HEAD:<rama>, no <rama> a secas: el checkout del hosting puede estar
    # en HEAD desacoplado o con la rama local llamada de otra forma.
    return _git('push', GIT_REMOTE, f'HEAD:{GIT_BRANCH}')


def _sincronizar_git_inicio():
    """Al arrancar, parte del último contenido publicado en GitHub."""
    if not GIT_PUSH:
        return
    if not GITHUB_TOKEN:
        print('AVISO: RHBOTS_GIT_PUSH=1 pero falta GITHUB_TOKEN — no se puede '
             'sincronizar con GitHub. Ponla en Render - el servicio - Environment.')
        return
    _asegurar_remoto()
    ok, salida = _git('fetch', GIT_REMOTE, GIT_BRANCH)
    if not ok:
        print(f'AVISO: no se pudo sincronizar con git al arrancar: {salida[-300:]}')
        return
    ok, salida = _git('reset', '--hard', f'{GIT_REMOTE}/{GIT_BRANCH}')
    if not ok:
        print(f'AVISO: no se pudo sincronizar con git al arrancar: {salida[-300:]}')


# ── aplicación ────────────────────────────────────────────────────────────
def crear_app():
    _sincronizar_git_inicio()

    app = Flask(__name__,
                template_folder=os.path.join(HERE, 'admin_plantillas'),
                static_folder=os.path.join(HERE, 'admin_estatico'),
                static_url_path='/estatico')

    secreto = os.environ.get('RHBOTS_SECRET')
    if not secreto:
        secreto = secrets.token_hex(32)
        print('AVISO: RHBOTS_SECRET no definida; se usa una clave temporal.')
        print('       Las sesiones se cerrarán al reiniciar. Defínela en el servidor.')
    app.secret_key = secreto

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('RHBOTS_HTTPS') == '1',
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    )

    # ---- CSRF ----
    def token():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)
        return session['csrf']

    app.jinja_env.globals['csrf_token'] = token

    @app.before_request
    def _protege():
        if request.method == 'POST':
            enviado = request.form.get('csrf', '')
            if not enviado or not secrets.compare_digest(enviado, session.get('csrf', '')):
                abort(400, 'Token de seguridad no válido. Recarga la página.')

    def guardar_y_publicar(nombre_datos, datos, mensaje_ok):
        """Guarda un JSON, regenera la web y (si toca) la sube a GitHub."""
        D.guardar(nombre_datos, datos)
        ok, salida = _publicar()
        if not ok:
            flash(f'{mensaje_ok} Pero la web NO se pudo regenerar: {salida[-300:]}', 'error')
            return ok
        ok_git, salida_git = _sincronizar_git(mensaje_ok)
        if ok_git:
            flash(mensaje_ok + ' Ya está en la web.')
        else:
            flash(f'{mensaje_ok} Se regeneró, pero NO se pudo subir a GitHub: '
                 f'{salida_git[-300:]}', 'error')
        return ok and ok_git

    def requiere_acceso(f):
        @wraps(f)
        def envoltura(*a, **kw):
            if not session.get('dentro'):
                return redirect(url_for('login', siguiente=request.path))
            return f(*a, **kw)
        return envoltura

    # ── acceso ────────────────────────────────────────────────────────────
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        ip = request.remote_addr or '?'
        intentos, hasta = _intentos.get(ip, (0, 0))
        if intentos >= MAX_INTENTOS and time.time() < hasta:
            espera = int((hasta - time.time()) / 60) + 1
            return render_template('login.html',
                                   error=f'Demasiados intentos. Prueba en {espera} min.'), 429

        if request.method == 'POST':
            h = _hash_guardado()
            usuario_ok = secrets.compare_digest(request.form.get('usuario', ''), USUARIO)
            clave_ok = h and check_password_hash(h, request.form.get('clave', ''))
            if usuario_ok and clave_ok:
                _intentos.pop(ip, None)
                session.clear()
                session['dentro'] = True
                session.permanent = False
                token()
                destino = request.args.get('siguiente', '')
                # sólo rutas internas: evita redirecciones a sitios externos
                if not destino.startswith('/') or destino.startswith('//'):
                    destino = url_for('panel')
                return redirect(destino)

            _intentos[ip] = (intentos + 1, time.time() + BLOQUEO_SEG)
            time.sleep(0.6)
            return render_template('login.html', error='Usuario o contraseña incorrectos.'), 401

        return render_template('login.html')

    @app.route('/logout', methods=['POST'])
    def logout():
        session.clear()
        return redirect(url_for('login'))

    # ── panel ─────────────────────────────────────────────────────────────
    @app.route('/')
    @requiere_acceso
    def panel():
        s = D.cargar('sitio')
        p = D.cargar('productos')
        return render_template('panel.html', sitio=s, productos=p['productos'],
                               generado=_ultima_generacion())

    def _ultima_generacion():
        f = os.path.join(ROOT, 'web', 'index.html')
        if not os.path.exists(f):
            return None
        return time.strftime('%d/%m/%Y %H:%M', time.localtime(os.path.getmtime(f)))

    # ── SEO y analítica ───────────────────────────────────────────────────
    @app.route('/seo', methods=['GET', 'POST'])
    @requiere_acceso
    def seo():
        s = D.cargar('sitio')
        if request.method == 'POST':
            f = request.form
            s['seo'].update({
                'dominio': f.get('dominio', '').strip().rstrip('/'),
                'nombre': f.get('nombre', '').strip(),
                'og_imagen': f.get('og_imagen', '').strip(),
                'twitter': f.get('twitter', '').strip(),
                'locale': f.get('locale', '').strip() or 'es_ES',
            })
            s['analitica'].update({
                'ga4': f.get('ga4', '').strip(),
                'gtm': f.get('gtm', '').strip(),
                'google_site_verification': f.get('verificacion', '').strip(),
            })
            guardar_y_publicar('sitio', s, 'SEO y analítica guardados.')
            return redirect(url_for('seo'))
        return render_template('seo.html', seo=s['seo'], an=s['analitica'])

    # ── home ──────────────────────────────────────────────────────────────
    @app.route('/home', methods=['GET', 'POST'])
    @requiere_acceso
    def home():
        s = D.cargar('sitio')
        if request.method == 'POST':
            f = request.form
            s['home'].update({
                'kicker': f.get('kicker', '').strip(),
                'h1': f.get('h1', '').strip(),
                'lede': f.get('lede', '').strip(),
                'sectores': filas(f.get('sectores', ''), 2),
                'faq': filas(f.get('faq', ''), 2),
                'que_hacemos': {
                    'kicker': f.get('q_kicker', '').strip(),
                    'titulo': f.get('q_titulo', '').strip(),
                    'texto': f.get('q_texto', '').strip(),
                    'destacado': f.get('q_destacado', '').strip(),
                    'detalle': f.get('q_detalle', '').strip(),
                },
                'robots_grid': {
                    'kicker': f.get('g_kicker', '').strip(),
                    'titulo': f.get('g_titulo', '').strip(),
                },
                'sectores_bloque': {
                    'kicker': f.get('s_kicker', '').strip(),
                    'titulo': f.get('s_titulo', '').strip(),
                    'texto': f.get('s_texto', '').strip(),
                    'boton': f.get('s_boton', '').strip(),
                    'tarjetas': filas(f.get('s_tarjetas', ''), 2),
                },
                'actualidad': {
                    'kicker': f.get('a_kicker', '').strip(),
                    'titulo': f.get('a_titulo', '').strip(),
                    'enlace': f.get('a_enlace', '').strip(),
                },
                'metodo': {
                    'kicker': f.get('m_kicker', '').strip(),
                    'titulo': f.get('m_titulo', '').strip(),
                    'boton': f.get('m_boton', '').strip(),
                    'pasos': filas(f.get('m_pasos', ''), 2),
                },
            })
            guardar_y_publicar('sitio', s, 'Home guardada.')
            return redirect(url_for('home'))
        prods = D.cargar('productos')['productos']
        return render_template('home.html', h=s['home'], a_texto=a_texto,
                               opciones_modelo=[{'valor': p['slug'], 'texto': p['name']} for p in prods])

    # ── menú ──────────────────────────────────────────────────────────────
    @app.route('/menu', methods=['GET', 'POST'])
    @requiere_acceso
    def menu():
        s = D.cargar('sitio')
        if request.method == 'POST':
            nuevo = []
            for fila in filas(request.form.get('nav', ''), 4):
                etiqueta, href, clave, oculto = fila
                if not etiqueta:
                    continue
                item = {'label': etiqueta, 'href': href, 'key': clave}
                if oculto.lower() in ('si', 'sí', 'x', 'true', '1', 'oculto'):
                    item['oculto'] = True
                nuevo.append(item)
            s['nav'] = nuevo
            guardar_y_publicar('sitio', s, 'Menú guardado.')
            return redirect(url_for('menu'))
        texto = '\n'.join(
            ' | '.join([i.get('label', ''), i.get('href', ''), i.get('key', ''),
                        'oculto' if i.get('oculto') else ''])
            for i in s['nav'])
        return render_template('menu.html', nav=texto)

    # ── contacto ──────────────────────────────────────────────────────────
    @app.route('/contacto', methods=['GET', 'POST'])
    @requiere_acceso
    def contacto():
        s = D.cargar('sitio')
        if request.method == 'POST':
            f = request.form
            s['contacto'].update({
                'intro': f.get('intro', '').strip(),
                'empresa': f.get('empresa', '').strip(),
                'direccion': lineas(f.get('direccion', '')),
                'motivos': lineas(f.get('motivos', '')),
                'personas': [
                    {'nombre': n, 'cargo': c, 'email': e_, 'tel': t}
                    for n, c, e_, t in filas(f.get('personas', ''), 4) if n
                ],
            })
            guardar_y_publicar('sitio', s, 'Contacto guardado.')
            return redirect(url_for('contacto'))
        c = s['contacto']
        personas = '\n'.join(' | '.join([p.get('nombre', ''), p.get('cargo', ''),
                                         p.get('email', ''), p.get('tel', '')])
                             for p in c['personas'])
        return render_template('contacto.html', c=c, personas=personas)

    # ── RH·BOTS (equipo e historia) ──────────────────────────────────────
    @app.route('/rh-bots', methods=['GET', 'POST'])
    @requiere_acceso
    def rhbots():
        s = D.cargar('sitio')
        r = s.setdefault('rhbots', {
            'kicker': '', 'h1': 'RH·BOTS', 'lede': '',
            'historia_subtitulo': '', 'historia_cuerpo': '',
            'cifras': [], 'equipo': [],
        })
        if request.method == 'POST':
            f = request.form
            r.update({
                'kicker': f.get('kicker', '').strip(),
                'h1': f.get('h1', '').strip(),
                'lede': f.get('lede', '').strip(),
                'historia_subtitulo': f.get('historia_subtitulo', '').strip(),
                'historia_cuerpo': limpiar(f.get('historia_cuerpo', '')),
                'cifras': [[v, et] for v, et in filas(f.get('cifras', ''), 2) if v or et],
                'equipo': [[foto, nombre, cargo, bio]
                          for foto, nombre, cargo, bio in filas(f.get('equipo', ''), 4) if nombre],
            })
            guardar_y_publicar('sitio', s, 'RH·BOTS guardado.')
            return redirect(url_for('rhbots'))
        cifras = a_texto(r['cifras'])
        equipo = a_texto(r['equipo'])
        return render_template('rhbots.html', r=r, cifras=cifras, equipo=equipo)

    # ── blog ──────────────────────────────────────────────────────────────
    @app.route('/blog')
    @requiere_acceso
    def blog():
        return render_template('blog.html', posts=D.cargar('sitio')['posts'])

    @app.route('/blog/nuevo', methods=['GET', 'POST'])
    @app.route('/blog/<int:i>', methods=['GET', 'POST'])
    @requiere_acceso
    def post(i=None):
        s = D.cargar('sitio')
        posts = s['posts']
        if i is not None and (i < 0 or i >= len(posts)):
            abort(404)

        if request.method == 'POST':
            f = request.form
            if f.get('accion') == 'borrar' and i is not None:
                posts.pop(i)
                guardar_y_publicar('sitio', s, 'Entrada eliminada.')
                return redirect(url_for('blog'))

            titulo = f.get('titulo', '').strip()
            cuerpo = limpiar(f.get('cuerpo', ''))
            resumen = f.get('resumen', '').strip() or resumir(cuerpo)

            actual = posts[i] if i is not None else None
            slug = slug_unico(titulo, posts, excluir=i)

            nuevo = {
                'titulo': titulo,
                'fecha': f.get('fecha', '').strip() or time.strftime('%Y-%m-%d'),
                'categoria': f.get('categoria', '').strip(),
                'resumen': resumen,
                'cuerpo': cuerpo,
                'slug': slug,
                'url': f'blog/{slug}.html',
                'img': f.get('img', '').strip() or None,
            }

            if not titulo:
                flash('El título es obligatorio.', 'error')
                return render_template('post.html', p={**(actual or {}), **nuevo}, i=i)
            if not re.sub(r'<[^>]+>', '', cuerpo).strip():
                flash('El artículo no puede quedar vacío.', 'error')
                return render_template('post.html', p={**(actual or {}), **nuevo}, i=i)

            if i is None:
                posts.insert(0, nuevo)
            else:
                posts[i] = nuevo
            guardar_y_publicar('sitio', s, 'Entrada guardada.')
            return redirect(url_for('blog'))

        vacio = {'titulo': '', 'fecha': time.strftime('%Y-%m-%d'), 'categoria': '',
                 'resumen': '', 'cuerpo': '', 'url': '', 'img': ''}
        return render_template('post.html', p=posts[i] if i is not None else vacio, i=i)

    # ── vista previa de archivos publicados ──────────────────────────────
    # El panel no sirve web/ normalmente; esto sólo deja ver las imágenes
    # (portadas, aplicaciones, biblioteca…) dentro de los formularios.
    @app.route('/vista/<path:ruta>')
    @requiere_acceso
    def vista_archivo(ruta):
        return send_from_directory(os.path.join(ROOT, 'web'), ruta)

    # ── biblioteca de imágenes ───────────────────────────────────────────
    # Usada por el editor de artículos (arrastrar y soltar) y por cualquier
    # campo de imagen del panel (portada, aplicaciones, sectores…).
    @app.route('/medios', methods=['GET'])
    @requiere_acceso
    def medios():
        return render_template('medios.html', imagenes=M.listar())

    @app.route('/medios/subir', methods=['POST'])
    @requiere_acceso
    def medios_subir():
        archivo = request.files.get('archivo')
        if not archivo or not archivo.filename:
            return jsonify(ok=False, error='No se recibió ningún archivo.'), 400
        try:
            url, peso = M.guardar(archivo.stream, archivo.filename)
        except M.ErrorMedio as ex:
            return jsonify(ok=False, error=str(ex)), 400
        return jsonify(ok=True, url=url, kb=round(peso / 1024))

    @app.route('/medios/borrar', methods=['POST'])
    @requiere_acceso
    def medios_borrar():
        try:
            M.borrar(request.form.get('nombre', ''))
        except M.ErrorMedio as ex:
            flash(str(ex), 'error')
        else:
            flash('Imagen eliminada de la biblioteca.')
        return redirect(url_for('medios'))

    # ── productos ─────────────────────────────────────────────────────────
    @app.route('/productos')
    @requiere_acceso
    def productos():
        d = D.cargar('productos')
        return render_template('productos.html', productos=d['productos'],
                               estados=d['estados'])

    @app.route('/productos/nuevo', methods=['GET', 'POST'])
    @requiere_acceso
    def producto_nuevo():
        d = D.cargar('productos')
        if request.method == 'POST':
            f = request.form
            nombre = f.get('name', '').strip()
            familia = f.get('family', '')
            familias_validas = {clave for clave, _, _ in FAMILIAS}
            if not nombre:
                flash('El nombre es obligatorio.', 'error')
                return render_template('producto_nuevo.html', familias=FAMILIAS,
                                       name=nombre, family=familia)
            if familia not in familias_validas:
                flash('Elige una familia válida.', 'error')
                return render_template('producto_nuevo.html', familias=FAMILIAS,
                                       name=nombre, family=familia)

            slug = slug_unico(nombre, d['productos'])
            d['productos'].append({
                'slug': slug, 'name': nombre, 'base': '', 'family': familia,
                'status': 'disponible', 'claim': '', 'tagline': '',
                'hero': None, 'hero_alt': '', 'frames': [], 'gallery': [],
                'intro': '', 'keyfacts': [], 'highlights': [],
                'specs': [], 'applications': [], 'notes': [],
            })
            guardar_y_publicar('productos', d, f'Robot «{nombre}» creado.')
            return redirect(url_for('producto', slug=slug))

        return render_template('producto_nuevo.html', familias=FAMILIAS)

    @app.route('/productos/<slug>', methods=['GET', 'POST'])
    @requiere_acceso
    def producto(slug):
        d = D.cargar('productos')
        idx = next((k for k, p in enumerate(d['productos']) if p['slug'] == slug), None)
        if idx is None:
            abort(404)
        p = d['productos'][idx]

        if request.method == 'POST':
            f = request.form
            try:
                specs = json.loads(f.get('specs') or '[]')
            except json.JSONDecodeError as ex:
                flash(f'Las especificaciones no son JSON válido: {ex}', 'error')
                return render_template('producto.html', p=p, estados=d['estados'],
                                       a_texto=a_texto, specs_txt=f.get('specs', ''))
            p.update({
                'name': f.get('name', '').strip(),
                'claim': f.get('claim', '').strip(),
                'tagline': f.get('tagline', '').strip(),
                'intro': f.get('intro', '').strip(),
                'status': f.get('status', 'disponible'),
                'keyfacts': filas(f.get('keyfacts', ''), 2),
                'highlights': filas(f.get('highlights', ''), 2),
                'applications': [[n, (img or None)]
                                 for n, img in filas(f.get('applications', ''), 2)],
                'notes': filas(f.get('notes', ''), 3),
                'specs': specs,
            })
            guardar_y_publicar('productos', d, f'{p["name"]} guardado.')
            return redirect(url_for('producto', slug=slug))

        return render_template('producto.html', p=p, estados=d['estados'],
                               a_texto=a_texto,
                               specs_txt=json.dumps(p.get('specs', []),
                                                    ensure_ascii=False, indent=2))

    # ── tienda (Shopify) ──────────────────────────────────────────────────
    @app.route('/tienda', methods=['GET', 'POST'])
    @requiere_acceso
    def tienda():
        s = D.cargar('sitio')
        d = D.cargar('productos')

        if request.method == 'POST':
            f = request.form
            s.setdefault('tienda', {}).update({
                'dominio': f.get('dominio', '').strip().strip('/'),
                'moneda': f.get('moneda', '').strip(),
                'texto_boton': f.get('texto_boton', '').strip() or 'Comprar ahora',
                'activa': f.get('activa') == 'si',
                'mostrar_precio': f.get('mostrar_precio') == 'si',
            })
            D.guardar('sitio', s)

            # precio y variante por producto
            for p in d['productos']:
                variante = f.get('var_' + p['slug'], '').strip()
                precio = f.get('pre_' + p['slug'], '').strip()
                if not variante:
                    p.pop('shopify', None)
                    continue
                sh = p.setdefault('shopify', {})
                sh['variante'] = variante
                sh['precio'] = precio or '0.00'
                sh['disponible'] = f.get('dis_' + p['slug']) == 'si'
                sh.setdefault('moneda', s['tienda'].get('moneda', ''))
            D.guardar('productos', d)

            ok, salida = _publicar()
            if ok:
                flash('Tienda guardada. Ya está en la web.')
            else:
                flash(f'Tienda guardada. Pero la web NO se pudo regenerar: {salida[-300:]}', 'error')
            return redirect(url_for('tienda'))

        t = s.get('tienda', {})
        sin_precio = [p['name'] for p in d['productos']
                      if p.get('shopify') and float(p['shopify'].get('precio') or 0) <= 0]
        return render_template('tienda.html', t=t, productos=d['productos'],
                               sin_precio=sin_precio)

    # ── publicar a mano ──────────────────────────────────────────────────
    # Cada «Guardar» ya publica solo. Este botón se deja para forzar una
    # regeneración cuando los datos han cambiado por otra vía — por ejemplo
    # tras ejecutar tools/sincronizar.py desde la terminal.
    @app.route('/publicar', methods=['POST'])
    @requiere_acceso
    def publicar():
        ok, salida = _publicar()
        if not ok:
            flash('Error al generar: ' + salida[-400:], 'error')
            return redirect(request.referrer or url_for('panel'))
        ok_git, salida_git = _sincronizar_git('Publicación manual.')
        if ok_git:
            primera = (salida.strip().splitlines() or [''])[0]
            flash('Web regenerada. ' + primera)
        else:
            flash('Se regeneró, pero NO se pudo subir a GitHub: ' + salida_git[-400:], 'error')
        return redirect(request.referrer or url_for('panel'))

    return app


# ── arranque ──────────────────────────────────────────────────────────────
def main():
    if '--clave' in sys.argv:
        return establecer_clave()

    if not _hash_guardado():
        temporal = secrets.token_urlsafe(12)
        _guardar_hash(generate_password_hash(temporal))
        print('=' * 62)
        print(' No había contraseña, así que he generado una:')
        print(f'   usuario:    {USUARIO}')
        print(f'   contraseña: {temporal}')
        print(' Cámbiala cuando quieras con:  python tools/admin.py --clave')
        print('=' * 62)

    app = crear_app()
    print('Panel en http://127.0.0.1:5001  (Ctrl+C para parar)')
    app.run(host='127.0.0.1', port=5001, debug=False)
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
