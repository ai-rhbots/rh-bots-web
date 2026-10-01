# Publicar la web en BanaHosting

Panel: <https://sc-europe80.banahosting.com:2083/>

La web es **HTML estático**: no necesita PHP, ni base de datos, ni Node. Se
copian los archivos y funciona.

Hoy `rh-bots.com` apunta a BanaHosting (IP 75.102.57.42) y sirve la web
anterior. Para que sirva esta hay que sustituir el contenido de
`public_html`. No hay que tocar el DNS ni el dominio.

---

## Cómo se reparte el trabajo

1. Se piden los cambios y se hacen sobre el proyecto.
2. Se regenera el sitio y se crea el paquete:

   ```bash
   python tools/build.py        # regenera las 288 páginas
   python tools/empaquetar.py   # crea los .zip en publicar/
   ```

3. El informático sube el `.zip` por el gestor de archivos del panel y lo
   descomprime en `public_html`.

Los `.zip` se quedan fuera del repositorio: hay que pasarlos aparte.

---

## Qué genera el empaquetador

| Archivo | Contenido | Peso |
|---|---|---|
| `rh-bots-sitio.zip` | Todo menos los vídeos | ~8,5 MB |
| `rh-bots-video.zip` | Sólo los 8 vídeos | ~19 MB |
| `rh-bots-web.zip` | Todo junto | ~27,6 MB |

**Sube primero el pequeño y después el de vídeo.** El gestor de cPanel tiene
límite de subida y con el paquete entero es fácil que falle a medias.

El empaquetador recorre el HTML, el CSS y el JS y mete **sólo lo que la web
referencia de verdad**. Los originales de imagen y vídeo (1,4 GB) se quedan
fuera solos.

---

## La primera vez

### 1. Copia de seguridad de lo que hay

Antes de tocar nada, en el panel: **Herramientas → Copia de seguridad →
Descargar una copia del directorio raíz** (o comprime `public_html` desde el
gestor de archivos y descarga el zip). Al subir la web nueva se reemplaza la
anterior, y sin copia no hay vuelta atrás.

Las cuentas de correo, las bases de datos y los subdominios **no** viven en
`public_html`: no se ven afectados.

### 2. Vaciar `public_html`

Borra el contenido de la web antigua. Deja en su sitio, si existen:

- `cgi-bin/`
- `.well-known/` (certificados y verificaciones de dominio)
- cualquier carpeta de otra aplicación que siga en uso

### 3. Subir y descomprimir

1. **Upload** → `rh-bots-sitio.zip` en `public_html`.
2. Clic derecho en el zip → **Extract**.
3. Repite con `rh-bots-video.zip`.
4. Borra los dos `.zip`.

Debe quedar así:

```
public_html/
├── index.html · robots.html · aplicaciones.html · alquiler.html
├── alquiler-limpieza.html · alquiler-humanoides.html
├── rh-bots.html · blog.html · contacto.html · legal.html · 404.html
├── robots/     (las 22 fichas)
├── blog/       (los 3 artículos)
├── pt/ en/ fr/ de/ zh/ ar/ ca/   (lo mismo en cada idioma)
├── css/  js/  assets/
├── .htaccess
├── favicon.ico · favicon-32.png · favicon-192.png · favicon-512.png
├── apple-touch-icon.png
└── sitemap.xml  robots.txt
```

> **Si no ves el `.htaccess`**, activa *Settings → Show Hidden Files* en el
> gestor. Sin él se pierden el HTTPS forzado, las URL limpias, la compresión
> y la caché.

### 4. Comprobar

- `https://www.rh-bots.com` carga la web nueva.
- `https://rh-bots.com` redirige a `www` (lo hace el `.htaccess`).
- `https://www.rh-bots.com/de/` sale en alemán y el menú se queda en alemán.
- `https://www.rh-bots.com/favicon.ico` responde.
- El formulario de contacto envía y llega a info@rh-bots.com.

### 5. Después de publicar

- En **Web3Forms**, añadir `rh-bots.com` en los ajustes del formulario.
- En **Google Search Console**, enviar `https://www.rh-bots.com/sitemap.xml`.

---

## Las siguientes veces

Ya no hay que vaciar nada: se sube el zip y se descomprime encima,
sobrescribiendo. Si una página deja de existir, hay que borrarla a mano del
servidor, porque descomprimir no elimina lo que sobra.

Si sólo han cambiado textos o precios, basta con `rh-bots-sitio.zip`: los
vídeos pesan 19 MB y casi nunca cambian.

---

## Lo que configura el `.htaccess`

- Fuerza HTTPS y redirige `rh-bots.com` → `www.rh-bots.com`, que es el dominio
  canónico declarado en todas las páginas. Para invertirlo, están las dos
  líneas comentadas al principio del archivo.
- URL limpias: `/robots/rhc5` sirve `robots/rhc5.html`.
- Compresión, caché larga para imágenes y vídeo, corta para el HTML.
- Cabeceras de seguridad y página 404 propia.
