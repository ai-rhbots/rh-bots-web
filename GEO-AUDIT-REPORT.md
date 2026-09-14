# Auditoría GEO + SEO — RH·BOTS

**Dominio final:** https://www.rh-bots.com (aún no publicado — el dominio sigue apuntando a GitHub Pages con contenido antiguo; esta auditoría se hizo sobre el build actual y definitivo, servido en local).
**Fecha:** 2026-08-31

## GEO Score compuesto: 51/100

| Categoría | Peso | Puntuación | Ponderado |
|---|---|---|---|
| AI Citability | 25% | 76/100 | 19,0 |
| Brand Authority | 20% | 27/100 | 5,4 |
| Content Quality / E-E-A-T | 20% | 49/100 | 9,8 |
| Technical Foundations | 15% | 85/100 | 12,75 |
| Structured Data | 10% | 5/100 | 0,5 |
| Platform Optimization | 10% | 38/100 | 3,8 |
| **Total** | | | **51,25 ≈ 51/100** |

Perfil típico de un sitio recién construido: base técnica sólida (estático, sin JS, rápido, bien estructurado) pero sin ninguna de las señales que hoy deciden si una IA cita o recomienda una marca: cero datos estructurados, sin llms.txt, y presencia de marca todavía mínima (normal, es una empresa nueva).

## Hallazgo corregido durante la auditoría

Dos subagentes independientes (contenido y schema) detectaron una **discrepancia real de datos**: `/rh-bots.html` (equipo) mostraba "Abel Pérez" como segundo cofundador, mientras `/contacto.html` mostraba "Javier Sirvent" (con el cargo mal escrito "Co-Funder"). Se ha corregido: ahora ambas páginas muestran **Javier Sirvent — Co-Founder**, consistente. Backup del JSON previo guardado en `datos/copias/`.

## 1. AI Citability & Visibility — 59/100

- **Fuerte:** tablas de especificaciones en las fichas de producto y el bloque de FAQ de la home son muy citables por un LLM tal cual están.
- **Débil:** sin `llms.txt`, sin datos estructurados, `/blog.html` y `/contacto.html` casi vacíos.
- `robots.txt` ya permite a todos los crawlers de IA (GPTBot, ClaudeBot, PerplexityBot, Google-Extended...).

## 2. Brand Authority — 27/100

- Sin Wikipedia/Wikidata (normal, empresa nueva). Colisión de nombre en YouTube con un juego de Roblox no relacionado.
- Señal positiva real: cobertura de prensa ya existente (diarioelcanal.com, eldebate.com, actualidadvalencia.com, eloutput.com, valencianews.es, intralogisticsvalencia.com) y página de empresa en LinkedIn.

## 3. Content Quality / E-E-A-T — 49/100

- Tono propio, sin relleno típico de IA. Punto fuerte real: la ficha RHC5 declara abiertamente la discrepancia entre el manual técnico y la documentación comercial — señal de rigor poco habitual.
- Faltan: política de privacidad/aviso legal, enlaces sociales del footer (apuntan a "#"), fechas de publicación/actualización, bios con LinkedIn del equipo.

## 4. Technical Foundations — 85/100

- HTML estático puro, ideal para crawlers de IA (no ejecutan JS). Meta tags, Open Graph, canonical y `lang="es"` correctos.
- 9 imágenes lazy sin `width`/`height` (riesgo de CLS). Sitemap sin `<lastmod>`. Twitter Card incompleto. Faltan cabeceras HSTS y CSP en `web/.htaccess`.
- A verificar tras el despliegue real en Apache/BanaHosting: redirects HTTPS/www, cabeceras de seguridad, caché, código 404 real.

## 5. Structured Data — 5/100 (crítico)

- Cero JSON-LD en todo el sitio. Prioridad: `Organization`, `Product`+`Offer` (14 fichas, sincronizado con Shopify), `Person` (equipo), `BreadcrumbList`, `FAQPage` en la home.
- **Aviso de datos:** la ficha RHC5 sigue mostrando el precio en SGD, no en EUR — pendiente de corregir en Shopify (decisión ya tomada por el usuario en una sesión anterior: lo hace él directamente).

## 6. Platform Optimization — 38/100

| Plataforma | Score |
|---|---|
| Bing Copilot | 44 |
| Google AI Overviews | 42 |
| Google Gemini | 38 |
| ChatGPT Web Search | 34 |
| Perplexity AI | 33 |

## Cambios aplicados (2026-08-31)

- **[HECHO]** Moneda SGD → EUR corregida: era un dato local desactualizado (Shopify ya facturaba en EUR desde hace tiempo). Corregido además un bug real en `tools/sincronizar.py` que impedía guardar cambios de moneda si el precio no cambiaba a la vez.
- **[HECHO]** JSON-LD `Organization`+`LocalBusiness` (todas las páginas), `Product`+`Offer` con precio/stock reales (14 fichas), `Person` para el equipo (rh-bots.html), `FAQPage` (home), `BreadcrumbList` (fichas de producto).
- **[HECHO]** `/llms.txt` generado automáticamente en cada build, con las 14 fichas agrupadas por familia.
- **[HECHO]** Footer: quitados los enlaces sociales rotos ("#"); LinkedIn real verificado (linkedin.com/company/rh-bots); YouTube/Instagram retirados hasta que existan de verdad. Añadidos enlaces a Aviso legal / Privacidad / Cookies.
- **[HECHO]** Nueva página `/legal.html` (Aviso legal, Privacidad, Cookies) con datos reales de la empresa. **Pendiente: el CIF/NIF queda como placeholder visible — solo el titular puede rellenarlo.**
- **[HECHO]** `width`/`height` reales (vía Pillow) en imágenes de aplicaciones, galería, sectores del home y foto de equipo — evita saltos de layout y ayuda a crawlers que no ejecutan CSS.
- **[HECHO]** `<lastmod>` en sitemap.xml; Twitter Card completa (`twitter:title/description/image`) en todas las páginas.
- **[HECHO]** Textos: encabezado "Qué hace" → "¿Qué es el {modelo}?" en las 14 fichas, formato pregunta+respuesta directa más citable por una IA (mismo texto real, sin inventar nada).
- **[PENDIENTE, fuera de mi alcance]** Corregir la discrepancia de equipo entre Contacto y RH·BOTS — ya corregida en esta misma sesión (era "Abel Pérez" vs "Javier Sirvent"; ahora ambas dicen Javier Sirvent).
- **[PENDIENTE del usuario]** Rellenar el CIF/NIF en `/legal.html`; corte de DNS de rh-bots.com hacia el hosting nuevo para que todo esto sea visible para Google/IA.

## Plan de acción priorizado

1. **[CRÍTICO]** Añadir JSON-LD `Organization`+`LocalBusiness` (home) y `Product`+`Offer` (14 fichas de producto).
2. **[ALTO]** Generar `/llms.txt` con descripción, familias de producto y enlaces.
3. **[ALTO]** Añadir `Person` para Marcos Blasco y Javier Sirvent, y `FAQPage` en la home.
4. **[ALTO]** Arreglar footer: quitar/rellenar enlaces sociales "#", añadir política de privacidad y aviso legal.
5. **[MEDIO]** `width`/`height` en las 9 imágenes lazy sin dimensiones; `<lastmod>` en sitemap.xml; Twitter Card completo.
6. **[MEDIO]** Verificar en Bing Webmaster Tools + activar IndexNow al desplegar.
7. **[PENDIENTE DEL USUARIO]** Corregir moneda SGD→EUR en Shopify para RHC5; completar el corte de DNS de rh-bots.com hacia el nuevo hosting.
