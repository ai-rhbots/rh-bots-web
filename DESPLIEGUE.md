# Subir la web a BanaHosting

Panel: <https://sc-europe80.banahosting.com:2083/>

La web es **HTML estático**: no necesita PHP, ni base de datos, ni Node. Se
copian los archivos y funciona. Es el caso más sencillo que existe en cPanel.

---

## 1. Generar el paquete

```bash
python tools/sincronizar.py    # trae precios y stock de Shopify
python tools/build.py          # regenera las 19 páginas
python tools/empaquetar.py     # crea los .zip en publicar/
```

Deja tres archivos en `publicar/`:

| Archivo | Contenido | Peso |
|---|---|---|
| `rh-bots-sitio.zip` | Todo menos los vídeos | 2,9 MB |
| `rh-bots-video.zip` | Sólo los 4 vídeos | 69,4 MB |
| `rh-bots-web.zip` | Todo junto | 72,2 MB |

**Sube primero el pequeño y luego el de vídeo.** El gestor de archivos de
cPanel suele tener un límite de subida y con 72 MB de una vez es fácil que
falle a medias.

El empaquetador incluye **sólo lo que la web referencia de verdad**: recorre el
HTML, el CSS y el JS y mete lo que encuentra. Los 1,5 GB de originales (los PNG
de 20 MB y los MP4 de hasta 958 MB) se quedan fuera solos.

---

## 2. Subir por el gestor de archivos

1. Entra en el panel y abre **File Manager**.
2. Ve a `public_html`.
   - Si hay un `index.html` o `default.html` de bienvenida de BanaHosting,
     bórralo o te tapará la web.
3. **Upload** → sube `rh-bots-sitio.zip`.
4. Vuelve a `public_html`, clic derecho en el zip → **Extract**.
5. Repite con `rh-bots-video.zip`.
6. Borra los dos `.zip` cuando termines.

Debe quedar así:

```
public_html/
├── index.html
├── robots.html · blog.html · contacto.html · 404.html
├── robots/        (las 14 fichas)
├── css/  js/  assets/
├── .htaccess
├── sitemap.xml  robots.txt
```

> **Si no ves el `.htaccess`**, activa *Settings → Show Hidden Files* en el
> gestor. Sin él pierdes HTTPS forzado, compresión y caché.

### Por FTP (alternativa)

Si prefieres FTP, en cPanel → **FTP Accounts** tienes los datos. Con FileZilla:
subes el contenido de `web/` a `public_html/`. Más cómodo si vas a actualizar
a menudo, y no tiene el límite de tamaño del gestor web.

---

## 3. Conectar el dominio

Depende de dónde esté registrado:

### Si el dominio ya está en BanaHosting

Suele estar listo. Comprueba en cPanel → **Domains** que `rh-bots.com` apunta a
`public_html`. Si aparece como *Addon Domain*, su carpeta será
`public_html/rh-bots.com` y ahí es donde hay que subir los archivos.

### Si está registrado en otro sitio

En el panel del registrador, cambia los **nameservers** a los de BanaHosting.
Los tienes en cPanel, arriba a la derecha, en *General Information → Name
Servers* (algo como `ns1.banahosting.com` / `ns2.banahosting.com`).

La propagación tarda de unos minutos a 24 horas.

### Comprobar que resuelve

```bash
nslookup rh-bots.com
```

---

## 4. Activar el HTTPS

cPanel → **SSL/TLS Status** → selecciona el dominio → **Run AutoSSL**.

Emite un certificado Let's Encrypt gratis en unos minutos. Hasta que no esté,
**no** funcionará bien: el `.htaccess` fuerza HTTPS y sin certificado el
navegador dará aviso de sitio no seguro.

Una vez emitido, entra en `https://rh-bots.com` y comprueba el candado.

---

## 5. Ajustar el dominio en la web

El sitio está generado con `https://www.rh-bots.com` como dominio. Sirve para
las URL canónicas, el sitemap y las tarjetas al compartir en redes.

Si el dominio final es otro (o prefieres sin `www`):

1. Panel de administración → **SEO y analítica** → campo *Dominio*.
2. **Publicar cambios**.
3. Vuelve a empaquetar y subir.

Y en `web/.htaccess`, la redirección de `www`: por defecto manda todo a
`www.rh-bots.com`. Si lo quieres al revés, están las dos reglas escritas —
comenta un par de líneas y descomenta las otras.

---

## 6. Comprobaciones

- [ ] `https://rh-bots.com` carga con candado
- [ ] El menú lleva a Robots, Blog y Contacto
- [ ] Una ficha de robot muestra precio y **Comprar ahora**
- [ ] Ese botón lleva al checkout de Shopify
- [ ] Los vídeos se reproducen (home y fichas del RHX2 y RHA3 Ultra)
- [ ] El visualizador del RHC5 gira al pasar el ratón
- [ ] Una URL inventada (`/loquesea`) muestra el 404 con el diseño del sitio
- [ ] `https://rh-bots.com/sitemap.xml` responde

---

## El panel de administración: déjalo en local

El panel es una aplicación **Flask**, no HTML estático. Para publicarlo haría
falta cPanel → *Setup Python App*, definir las variables de entorno y servirlo
con Passenger. Se puede, pero **no hace falta y no lo recomiendo**:

- súbelo y expones un punto de entrada más a internet;
- el flujo actual funciona igual de bien: editas en local, pulsas *Publicar*,
  vuelves a empaquetar y subes.

Si algún día lo quieres accesible desde fuera, está preparado: contraseña con
hash, CSRF, límite de intentos y configuración por variables de entorno. Sólo
hay que definir `RHBOTS_SECRET`, `RHBOTS_PASSWORD_HASH` y `RHBOTS_HTTPS=1`.

---

## Para actualizar más adelante

```bash
python tools/sincronizar.py && python tools/build.py && python tools/empaquetar.py
```

Y sube `rh-bots-sitio.zip` otra vez (los vídeos sólo si los has cambiado).

Recuerda que **los precios ya se leen en vivo de Shopify**: si sólo cambias un
precio, la web lo refleja sola y no hace falta volver a subir nada. Regenerar
sirve para que el HTML que ve Google también esté al día.
