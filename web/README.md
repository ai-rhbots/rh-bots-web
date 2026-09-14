# RH·BOTS — Landing RHX2

Implementación en HTML/CSS/JS de la maqueta `RH·BOTS_maqueta_web.pdf`.
Sin dependencias ni build: se abre `index.html` y funciona.

```
datos/                    ← EL CONTENIDO VIVE AQUÍ
├── productos.json        las 14 fichas
├── sitio.json            menú, home, blog, contacto, SEO, analítica
├── admin.json            hash de la contraseña (NO subir a git ni al servidor público)
└── copias/               copia de seguridad automática de cada guardado

tools/
├── admin.py              panel de administración (Flask)
├── build.py              generador del sitio
├── optimizar.py          optimizador de imágenes de producto
├── datos.py              lectura/escritura de los JSON
├── productos.py          carga datos/productos.json
└── sitio.py              carga datos/sitio.json

web/                      ⟵ TODO el HTML es generado
├── index.html            home
├── robots.html           catálogo (filtrable)
├── blog.html             blog
├── contacto.html         contacto
├── robots/*.html         14 fichas de producto
├── css/styles.css        sistema de diseño (maqueta aprobada)
├── css/catalogo.css      catálogo, fichas, home, blog y contacto
├── js/main.js
└── assets/
    ├── robot-sentado.png · robot-frontal.png · robot-aplicaciones.png
    ├── logo-rhbots.png · logo-rhx2.png
    ├── productos/        fotos de producto
    └── escenarios/       fotos de escenarios de aplicación
```

**Ningún `.html` de `web/` se edita a mano: todos se generan.** Se cambia el
contenido desde el panel, o a mano sobre los JSON de `datos/`, y se regenera:

```bash
python tools/build.py
```

## Panel de administración

```bash
python tools/admin.py
```

Abre <http://127.0.0.1:5001>. La primera vez genera una contraseña y la
imprime en la consola; para cambiarla:

```bash
python tools/admin.py --clave
```

Desde el panel se editan la home, las 14 fichas, el blog, el contacto, el menú,
el SEO y los códigos de Google, y se regenera la web con el botón **Publicar**.
Cada guardado deja una copia en `datos/copias/` y la escritura es atómica, así
que un corte a media faena no deja el archivo a medias.

### Seguridad

Está construido para poder publicarse, no sólo para local:

- contraseña guardada únicamente como hash PBKDF2;
- sesión firmada, cookie `HttpOnly` y `SameSite=Lax`;
- token CSRF obligatorio en todos los formularios;
- límite de 6 intentos por IP y bloqueo de 5 minutos;
- redirección tras el acceso limitada a rutas internas;
- sin modo depuración.

**Para subirlo a un servidor** hay que definir estas variables de entorno y
servirlo con un servidor real (no el de desarrollo de Flask):

```bash
RHBOTS_SECRET=<cadena larga y aleatoria>
RHBOTS_PASSWORD_HASH=<lo que imprime --clave>
RHBOTS_HTTPS=1
waitress-serve --port 8000 --call tools.admin:crear_app
```

El panel necesita un hosting que ejecute Python. La web pública es estática y
puede ir en cualquier sitio; el panel, no.

## Tienda (Shopify)

El botón de compra usa un **cart permalink** de Shopify:

```
https://<tienda>.myshopify.com/cart/<variante>:1?channel=buy_button
```

Añade la variante al carrito y cae directamente en el checkout de Shopify. No
necesita claves de API, ni JavaScript, ni token de Storefront en la página:
quien cobra es Shopify, la web sólo enlaza.

Se configura en el panel, en **Tienda**, o en `datos/sitio.json` → `tienda`.

### Salvaguarda de precio cero

Aunque la tienda esté activada, **no se emite botón de compra para un producto
cuyo precio sea 0,00**. Está en `boton_compra()` de `build.py` y es a propósito:
un botón de compra a cero permitiría a cualquiera pedir un robot gratis, y eso
no puede depender de acordarse de revisar un ajuste. El generador avisa por
consola de cada modelo que se salta.

### Estados que muestra cada ficha

| Situación en Shopify | Qué se ve en la web |
|---|---|
| Con stock y precio > 0 | Precio + botón **Comprar ahora** → checkout de Shopify |
| Con stock y precio 0,00 | «Precio bajo consulta» + **Pedir presupuesto** → contacto |
| Sin stock | «Sin stock» + **Avísame cuando esté** → contacto |
| Sin enlazar a Shopify | Nada (sólo los CTA normales de la ficha) |

### Estado actual

Ya resuelto en Shopify:

- **Plan Basic** (fuera del trial), país España.
- Los 8 artículos **publicados en el canal Tienda online**.
- Inventario con seguimiento activado y **5 unidades** de cada uno.

Sólo el **RHC5** tiene precio (100.000,00 SGD) y por tanto botón de compra.
Los otros cuatro enlazados salen como «Precio bajo consulta» hasta que se les
ponga precio en Shopify y se copie en el panel.

### Sincronización en vivo

La ficha consulta Shopify **en cada visita** y corrige precio y disponibilidad
si han cambiado. Usa los endpoints públicos de la tienda:

```
https://<tienda>.myshopify.com/products/<handle>.js   precio y stock
https://<tienda>.myshopify.com/meta.json              moneda
```

Ambos responden con `access-control-allow-origin: *`, así que **no hace falta
ningún token ni credencial en la página**. No hay nada que rotar ni que se
pueda filtrar.

Funciona por mejora progresiva: el HTML llega con el estado del último build
—que es lo que indexa Google y lo que se ve al instante— y el JavaScript lo
sustituye cuando Shopify responde. Si la petición falla o el visitante tiene
JavaScript desactivado, se queda el estado del build. Nunca se queda en blanco.

Para que ese estado de partida no envejezca:

```bash
python tools/sincronizar.py    # lee Shopify y actualiza datos/
python tools/build.py
```

Sólo lee de Shopify; no escribe nada. El precio y el stock siguen editándose
también a mano desde el panel, en **Tienda**.

La contraseña del escaparate ya está quitada: el enlace al carrito lleva a un
checkout real de Shopify.

Queda pendiente **en Shopify**:

1. **Los 7 precios que faltan** — sólo el C5 tiene precio. El resto sale como
   «Precio bajo consulta» hasta que se les ponga uno.
2. **La moneda** — la tienda cobra en dólares singapurenses (SGD) aunque el país
   ya es España. Cambiarlo en `Configuración › General`. En cuanto se cambie, la
   web lo recoge sola: la moneda también se lee en vivo de `/meta.json`.

### Correspondencia con el catálogo

Enlazados (5): RHC5, RHA3 Ultra, RHX2, RHX2 EDU, RHG2.

Sin enlazar y por qué:

| Modelo de la web | Motivo |
|---|---|
| RHA3 | En Shopify sólo está el A3 Ultra |
| RHX2 Ultra | No existe en Shopify |
| RHD1 Pro / Edu / Ultra / Max / MaxPro | Shopify tiene un único «D1 Series» genérico |
| RHX2 REC · RHD1 Ultra-W | Fichas provisionales: no deberían venderse |

En Shopify hay además dos productos sin ficha en la web: **Genie G2 Max** y
**OmniHand 3 Ultra-M**.

## Vídeo

```bash
python tools/optimizar_video.py          # todos
python tools/optimizar_video.py gama     # sólo uno
```

Comprime los originales de `web/assets/` a `web/assets/video/`: H.264, 1080p
como mucho (720p los que pasan de tres minutos), con `faststart` para que
empiecen a verse sin descargarlos enteros, y un fotograma de portada en JPEG.

**1.391 MB → 67 MB.** El original del X2 pesaba 958 MB en 4K.

Los reproductores llevan `preload="none"` y `poster`: no se descarga ni un byte
de vídeo hasta que alguien pulsa Reproducir. Sin eso, entrar en la home
costaría 42 MB de datos.

| Vídeo | Dónde está | Peso |
|---|---|---|
| `gama.mp4` | Home, sección «Míralos trabajando» | 42 MB |
| `x2.mp4` | Ficha del RHX2 | 21 MB |
| `a3-ultra-1.mp4` · `a3-ultra-2.mp4` | Ficha del RHA3 Ultra | 2,1 + 1,5 MB |

Para el de la gama, que dura 5:47, valdría la pena plantearse YouTube o Vimeo:
ahorra ancho de banda, ajusta la calidad a la conexión y da estadísticas.

## Imágenes de producto

Los originales (PNG de 4 a 20 MB) están en `web/assets/productos/C5|G2/` y
**no deben publicarse**: 137 MB. El optimizador genera las versiones web:

```bash
python tools/optimizar.py
```

Escribe WebP con transparencia en `web/assets/robots/` — 137 MB pasan a 1,2 MB.
Los fotogramas de una misma secuencia de giro se recortan con un encuadre común
para que el robot no cambie de tamaño al girar.

## Menú

Se define en `NAV`, dentro de [tools/sitio.py](../tools/sitio.py). Para retirar
una entrada sin borrarla basta con marcarla `'oculto': True` — así está ahora
**Accesorios**, listo para reactivarlo quitando esa línea.

Entradas actuales: Inicio · Robots · Aplicaciones · Blog · RH·BOTS · Contacto.

## Verlo en local

```bash
python -m http.server 5180 --directory web
```

Luego abrir <http://localhost:5180>. (Conviene servirlo por HTTP y no con
`file://` para que la tipografía y los assets carguen igual que en producción.)

## Sistema de diseño

Tokens definidos como variables CSS en `:root` (`css/styles.css`), tomados
literalmente de la maqueta:

| Token      | Valor     | Uso                                  |
|------------|-----------|--------------------------------------|
| `--navy`   | `#2f2483` | logotipo, footer                     |
| `--blue`   | `#009ee3` | color de marca, CTAs, acentos        |
| `--ink`    | `#282828` | texto principal                      |
| `--muted`  | `#8a8a8a` | texto secundario (= `#282828` al 66%) |
| `--light`  | `#f3f5f8` | fondos de sección                    |

Tipografía **Exo** (Google Fonts) en Regular 400 / Medium 500 / Bold 700,
según indica la maqueta. El logotipo del modelo (RHX2, tipografía *Encourage*)
va como imagen, así que no hace falta licenciar esa fuente.

## Páginas

- **Home** — hero de marca, las tres familias, cuatro modelos destacados, sectores
  donde trabajan, beneficios, servicio RH·BOTS y FAQ.
- **Robots** — catálogo de los 14 modelos, filtrable por familia. Acepta
  `robots.html?fam=cuadrupedos` para llegar ya filtrado desde la home.
- **Ficha de producto** (×14) — hero con datos rápidos, avisos de fiabilidad,
  qué hace, aplicaciones, especificaciones completas y resto de la familia.
  Si el modelo tiene 3 o más vistas en el campo `frames`, el hero se convierte
  en un **visualizador giratorio**: al pasar el ratón el robot gira a un lado y
  al otro, y moviéndolo en horizontal se controla el ángulo. También funciona
  arrastrando con el dedo y con las flechas del teclado. Ahora mismo lo tiene
  el RHC5, con seis vistas.
- **Blog** — maquetado y con estado vacío. Se activa añadiendo entradas a `POSTS`
  en `tools/sitio.py`.
- **Contacto** — formulario y datos de la empresa.

La sección de producto original de la maqueta (carrusel de aplicaciones, robot
entre columnas de características) sigue en `styles.css` — clases `.features`,
`.slider`, `.feat-cta--overlap` — por si quieres recuperarla para un modelo
concreto.

## Interacciones

- Cabecera *sticky* con sombra al hacer scroll.
- Menú hamburguesa por debajo de 860 px.
- Carrusel de aplicaciones: 5 slides, autoplay de 6 s, se pausa al pasar el
  ratón, navegable con puntos y con flechas del teclado.
- FAQ en acordeón (un panel abierto cada vez).
- Animaciones de entrada al hacer scroll, con `prefers-reduced-motion` respetado.

## Cómo cambiar las aplicaciones

Como indica la maqueta («puede cambiarse la foto en cada aplicación»), cada
slide tiene nombre e imagen propios. Se editan en el array `SLIDES` de
`js/main.js`:

```js
var SLIDES = [
  { name: 'Recepción y atención <br>al visitante', img: 'assets/recepcion.png' },
  ...
];
```

Todos los slides apuntan ahora mismo a la misma foto (`robot-aplicaciones.png`),
que es la única disponible en la maqueta.

## Catálogo de producto

14 fichas repartidas en tres familias: limpieza (1), humanoides (7) y
cuadrúpedos (6). Nomenclatura con prefijo **RH** (RHC5, RHA3, RHX2, RHG2,
RHD1…), coherente con el dossier `RHC5_VF` y con la maqueta aprobada.

Cada ficha incluye hero con datos rápidos, puntos clave, aplicaciones,
especificaciones completas agrupadas y enlaces al resto de la familia.

### Fiabilidad de los datos: esto es deliberado

Las fichas **no** homogeneizan los datos de origen. Cuando la documentación del
fabricante se contradice o falta, la web lo dice en lugar de elegir la cifra más
favorable:

| Estado | Significado | Modelos |
|---|---|---|
| *(sin distintivo)* | Ficha completa y contrastada | 11 modelos |
| `Datos parciales` | Anunciado, faltan datos oficiales | RHX2 EDU |
| `Ficha provisional` | Sin ficha oficial — **no apta para oferta contractual** | RHX2 REC, RHD1 Ultra-W |

Los avisos aparecen en un bloque destacado bajo el hero. Ejemplos: el
rendimiento del RHC5 (1.920 vs 1.980 m²/h), los grados de libertad del RHX2
Ultra (30 vs 31), su batería (421 vs 500 Wh), el peso y la batería del
RHD1 MaxPro (64/68 kg, 2.081/2.160 Wh), o la carga estática de 100 kg que no
debe usarse como carga móvil.

Las dos fichas provisionales **no reproducen especificaciones de otros modelos**
y llevan una lista numerada de la documentación que hay que pedir al fabricante
antes de ofertarlas.

## Pendiente de contenido definitivo

- **Fotos de producto**: sólo hay imagen real del RHC5 (extraída del dossier
  `RHC5_VF`) y del RHX2 (de la maqueta). Los otros 12 modelos usan un marcador
  con la silueta de su familia. En cuanto lleguen las fotos, basta con dejarlas
  en `web/assets/productos/` y añadir la ruta al campo `hero` del modelo en
  `tools/productos.py`.
- **Fotos de aplicaciones**: falta una imagen por escenario.
- **Nombres de las 4 aplicaciones** que no aparecían en la maqueta (sólo se
  veía «Asistencia en entornos industriales ligeros»); los actuales son una
  propuesta.
- **Respuestas del FAQ**: redactadas a partir de los datos técnicos de la
  maqueta; conviene que las valide RH·BOTS.
- **Formulario de contacto**: no hay backend. Al enviar valida los campos y abre
  el gestor de correo con el mensaje ya redactado hacia `mblasco@rh-bots.com`.
  Para recibirlos en el servidor hace falta conectar un endpoint (Formspree,
  Netlify Forms o un script propio) en el `submit` de `js/main.js`.
- **Datos de contacto**: nombres, correos, teléfonos y dirección están tomados
  del dossier `RHC5_VF`. Conviene confirmarlos antes de publicar.
- **Blog**: sin artículos todavía. Faltan también las páginas individuales de
  cada entrada.
- **Iconos sociales**: apuntan a `#`; faltan las URLs reales.
- **Ficha técnica en PDF**: el CTA de descarga lleva a las especificaciones de
  la web; falta el PDF.

## Origen de los assets

Las imágenes se han recortado de la maqueta en PDF (la única fuente gráfica
disponible), separando el fondo para dejarlas con transparencia. Si existen los
originales en alta resolución, conviene sustituirlas manteniendo los nombres.
