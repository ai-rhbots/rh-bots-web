/* RH·BOTS — RHX2 landing */
(function () {
  'use strict';

  /* ---------- header sticky state ---------- */
  var header = document.getElementById('header');
  var onScroll = function () {
    header.classList.toggle('is-stuck', window.scrollY > 8);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---------- mobile nav ---------- */
  var toggle = document.getElementById('navToggle');
  var nav = document.getElementById('nav');

  toggle.addEventListener('click', function () {
    var open = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!open));
    toggle.setAttribute('aria-label', open ? 'Abrir menú' : 'Cerrar menú');
    nav.classList.toggle('is-open', !open);
  });

  nav.addEventListener('click', function (e) {
    if (e.target.tagName !== 'A') return;
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', 'Abrir menú');
    nav.classList.remove('is-open');
  });

  /* ---------- aplicaciones: carrusel ----------
     Una diapositiva por aplicación. La foto es intercambiable:
     basta con apuntar `img` a otro archivo de /assets.                       */
  var SLIDES = [
    { name: 'Recepción y atención <br>al visitante',        img: 'assets/robot-aplicaciones.png' },
    { name: 'Guía en showrooms <br>y eventos',              img: 'assets/robot-aplicaciones.png' },
    { name: 'Logística interna <br>y transporte ligero',    img: 'assets/robot-aplicaciones.png' },
    { name: 'Asistencia en entornos <br>industriales ligeros', img: 'assets/robot-aplicaciones.png' },
    { name: 'Formación <br>e investigación',                img: 'assets/robot-aplicaciones.png' }
  ];

  var START = 3;                       // 4ª aplicación, como en la maqueta
  var dotsBox = document.getElementById('dots');
  var slideName = document.getElementById('slideName');
  var slideImg = document.getElementById('slideImg');
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // el carrusel sólo existe en la portada
  if (dotsBox && slideName && slideImg) {
  var media = slideImg.parentElement;
  var current = START;
  var timer = null;

  SLIDES.forEach(function (s, i) {
    var b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('role', 'tab');
    b.setAttribute('aria-selected', String(i === START));
    b.setAttribute('aria-label', 'Aplicación ' + (i + 1) + ' de ' + SLIDES.length);
    b.addEventListener('click', function () { go(i); restart(); });
    dotsBox.appendChild(b);
  });

  function go(i) {
    if (i === current) return;
    current = i;

    slideName.classList.add('is-fading');
    media.classList.add('is-fading');

    setTimeout(function () {
      slideName.innerHTML = SLIDES[i].name;
      if (slideImg.getAttribute('src') !== SLIDES[i].img) {
        slideImg.src = SLIDES[i].img;
      }
      slideName.classList.remove('is-fading');
      media.classList.remove('is-fading');
    }, 300);

    Array.prototype.forEach.call(dotsBox.children, function (d, k) {
      d.setAttribute('aria-selected', String(k === i));
    });
  }

  function restart() {
    clearInterval(timer);
    if (reduced) return;
    timer = setInterval(function () { go((current + 1) % SLIDES.length); }, 6000);
  }
  restart();

  var slider = document.getElementById('aplicaciones-slider');
  slider.addEventListener('mouseenter', function () { clearInterval(timer); });
  slider.addEventListener('mouseleave', restart);

  /* teclado: flechas sobre los dots */
  dotsBox.addEventListener('keydown', function (e) {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    e.preventDefault();
    var next = e.key === 'ArrowRight'
      ? (current + 1) % SLIDES.length
      : (current - 1 + SLIDES.length) % SLIDES.length;
    go(next);
    dotsBox.children[next].focus();
    restart();
  });
  }

  /* ---------- fondos de vídeo ----------
     Aparecen con una transición sólo cuando hay fotogramas de verdad, para
     que no se vea el salto del poster al primer cuadro. Si el navegador
     bloquea el autoplay (política de ahorro de datos, por ejemplo), se queda
     el poster y no pasa nada.                                              */
  Array.prototype.forEach.call(document.querySelectorAll('.fondovid'), function (caja) {
    var v = caja.querySelector('video');
    if (!v || reduced) return;

    var listo = function () { caja.classList.add('is-listo'); };
    if (v.readyState >= 3) listo();
    else v.addEventListener('canplay', listo, { once: true });

    var play = v.play();
    if (play && play.catch) play.catch(function () { /* poster y ya está */ });

    // no gastar batería reproduciendo algo que no se ve
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) {
        es.forEach(function (en) {
          if (en.isIntersecting) { var p = v.play(); if (p && p.catch) p.catch(function () {}); }
          else v.pause();
        });
      }, { threshold: 0.01 }).observe(caja);
    }
  });

  /* ---------- cifras que cuentan hacia arriba ----------
     Sólo se anima la parte numérica: «hasta 1.980 m²/h» conserva el «hasta»
     y las unidades, y «131 cm» cuenta hasta 131.                           */
  function animarCifras(raiz) {
    var celdas = raiz.querySelectorAll('.keyfacts strong, .spec dd');
    Array.prototype.forEach.call(celdas, function (el) {
      if (el.dataset.contado) return;

      var texto = el.textContent;
      var m = texto.match(/^(.*?)(\d{1,3}(?:\.\d{3})*(?:,\d+)?)(.*)$/s);
      if (!m) return;

      var destino = parseFloat(m[2].replace(/\./g, '').replace(',', '.'));
      if (!isFinite(destino) || destino < 10) return;      // números pequeños no lucen

      el.dataset.contado = '1';
      el.classList.add('contando');

      var decimales = (m[2].split(',')[1] || '').length;
      var t0 = null, dur = 1100;

      // Red de seguridad: si el navegador deja de servir fotogramas a mitad
      // (pestaña en segundo plano, ahorro de energía), la cifra se quedaría
      // congelada en un valor intermedio FALSO. En una ficha técnica eso no
      // puede pasar, así que un temporizador la deja siempre en el valor real.
      var cerrado = false;
      var rescate = setTimeout(terminar, dur + 500);

      function terminar() {
        cerrado = true;                 // corta la animación: si rAF vuelve
        clearTimeout(rescate);          // a despertar, ya no pisa el valor
        el.textContent = texto;         // el valor exacto
      }

      function paso(ts) {
        if (cerrado) return;
        if (t0 === null) t0 = ts;
        var p = Math.min((ts - t0) / dur, 1);
        if (p >= 1) { terminar(); return; }
        var suave = 1 - Math.pow(1 - p, 3);               // frena al final
        var v = destino * suave;
        el.textContent = m[1] +
          v.toLocaleString('es-ES', { minimumFractionDigits: decimales,
                                      maximumFractionDigits: decimales }) + m[3];
        requestAnimationFrame(paso);
      }
      requestAnimationFrame(paso);
    });
  }

  /* Se comprueba por geometría, no con IntersectionObserver: en pestañas que
     no componen (previsualizaciones, prerender) el observador no entrega
     nunca y las cifras se quedarían sin animar. Mismo criterio que el
     revelado al hacer scroll. */
  var zonasCifras = document.querySelectorAll('.keyfacts, .specs');
  function barrerCifras() {
    if (reduced || !zonasCifras.length) return;
    var vh = window.innerHeight || document.documentElement.clientHeight;
    Array.prototype.forEach.call(zonasCifras, function (z) {
      if (z.dataset.contada) return;
      var b = z.getBoundingClientRect();
      if (b.top < vh - 30 && b.bottom > 0) {
        z.dataset.contada = '1';
        animarCifras(z);
      }
    });
  }
  window.addEventListener('scroll', barrerCifras, { passive: true });
  window.addEventListener('resize', barrerCifras, { passive: true });
  window.addEventListener('load', barrerCifras);
  setTimeout(barrerCifras, 250);

  /* ---------- precio y stock en vivo desde Shopify ----------
     Usa los endpoints públicos de la tienda (/products/<handle>.js y
     /meta.json), que responden con «access-control-allow-origin: *». No hace
     falta ningún token ni credencial en la página.

     La ficha ya llega pintada con el estado del último build: eso es lo que
     indexa Google y lo que se ve al instante. Esto sólo la corrige si Shopify
     dice otra cosa. Si la petición falla, se queda el estado del build.     */
  var compra = document.querySelector('[data-tienda]');
  if (compra && window.fetch) {
    (function () {
      var d = compra.dataset;
      if (!d.dominio || !d.handle) return;

      var base = 'https://' + d.dominio;
      var chevron = '<i class="pill__ico" aria-hidden="true">' +
                    '<svg viewBox="0 0 24 24"><path d="M9 5l7 7-7 7"/></svg></i>';

      function importe(centimos) {
        return new Intl.NumberFormat('es-ES', {
          minimumFractionDigits: 2, maximumFractionDigits: 2
        }).format(centimos / 100);
      }

      var SIMBOLOS = { EUR: '€', USD: '$', GBP: '£', JPY: '¥' };
      function simbolo(codigo) {
        return SIMBOLOS[String(codigo || '').toUpperCase()] || codigo || '';
      }

      function esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
          return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
        });
      }

      function aviso(texto, cta) {
        return '<p class="sinstock"><span class="sinstock__punto" aria-hidden="true"></span>' +
               texto + '</p><a class="pill pill--line" href="' + esc(d.contacto) +
               '"><span>' + cta + '</span>' + chevron + '</a>';
      }

      function pinta(v, moneda) {
        if (!v || !v.available) {
          return aviso('Sin stock — consúltanos la disponibilidad', 'Avísame cuando esté');
        }
        if (!v.price || v.price <= 0) {
          return aviso('Precio bajo consulta', 'Pedir presupuesto');
        }
        var precio = d.precio === '1'
          ? '<p class="precio">' + importe(v.price) +
            ' <span>' + esc(simbolo(moneda)) + '</span></p>'
          : '';
        return precio +
          '<a class="pill pill--comprar" rel="nofollow noopener" href="' +
          esc(base + '/cart/' + v.id + ':1') + '"><span>' +
          esc(d.texto) + '</span>' + chevron + '</a>';
      }

      function pedir(ruta) {
        return fetch(base + ruta, { mode: 'cors', credentials: 'omit' })
          .then(function (r) { return r.ok ? r.json() : null; })
          .catch(function () { return null; });
      }

      Promise.all([
        pedir('/products/' + encodeURIComponent(d.handle) + '.js'),
        pedir('/meta.json')
      ]).then(function (res) {
        var producto = res[0], tienda = res[1];
        if (!producto || !producto.variants || !producto.variants.length) return;

        // la variante enlazada; si ya no existe, la primera del producto
        var v = producto.variants.filter(function (x) {
          return String(x.id) === String(d.variante);
        })[0] || producto.variants[0];

        compra.innerHTML = pinta(v, tienda && tienda.currency);
        compra.setAttribute('data-vivo', '1');
      });
    })();
  }

  /* ---------- visualizador giratorio ----------
     Al pasar el ratón el robot gira a un lado y al otro. Si mueves el ratón
     en horizontal tomas el control y lo giras tú. También con arrastre táctil
     y con las flechas del teclado.                                          */
  var viewer = document.getElementById('viewer');
  if (viewer) {
    var frames = [].slice.call(viewer.querySelectorAll('.viewer__frame'));
    var N = frames.length;
    var actual = 0;
    var manual = false;
    var anim = null;
    var xInicio = 0;
    var arrastrando = false;

    function mostrar(i) {
      i = ((i % N) + N) % N;
      if (i === actual) return;
      frames[actual].classList.remove('is-on');
      frames[i].classList.add('is-on');
      actual = i;
    }

    // precarga: el giro debe ser instantáneo desde el primer momento
    frames.forEach(function (f) {
      if (f.loading === 'lazy') f.loading = 'eager';
    });

    /* --- balanceo automático al pasar por encima --- */
    var t0 = null;
    var AMPLITUD = 2;          // fotogramas a cada lado
    var PERIODO = 2600;        // ms por ciclo completo

    function balancear(ts) {
      if (t0 === null) t0 = ts;
      var f = (ts - t0) / PERIODO;
      var offset = Math.round(Math.sin(f * Math.PI * 2) * AMPLITUD);
      mostrar(offset);
      anim = requestAnimationFrame(balancear);
    }

    function arrancar() {
      if (reduced || manual || anim) return;
      t0 = null;
      anim = requestAnimationFrame(balancear);
    }

    function parar() {
      if (anim) { cancelAnimationFrame(anim); anim = null; }
    }

    function volverAlInicio() {
      parar();
      manual = false;
      viewer.classList.remove('is-active');
      mostrar(0);
    }

    viewer.addEventListener('mouseenter', function () {
      viewer.classList.add('is-active');
      arrancar();
    });
    viewer.addEventListener('mouseleave', volverAlInicio);

    /* --- el movimiento horizontal toma el control --- */
    viewer.addEventListener('mousemove', function (ev) {
      var r = viewer.getBoundingClientRect();
      var p = (ev.clientX - r.left) / r.width;          // 0 … 1
      if (!manual) {
        // sólo se toma el control tras un desplazamiento apreciable
        if (xInicio === 0) { xInicio = ev.clientX; return; }
        if (Math.abs(ev.clientX - xInicio) < 24) return;
        manual = true;
        parar();
      }
      mostrar(Math.round(p * (N - 1)));
    });
    viewer.addEventListener('mouseleave', function () { xInicio = 0; });

    /* --- táctil: arrastrar para girar --- */
    viewer.addEventListener('pointerdown', function (ev) {
      if (ev.pointerType === 'mouse') return;
      arrastrando = true;
      xInicio = ev.clientX;
      parar();
      viewer.classList.add('is-active');
      viewer.setPointerCapture(ev.pointerId);
    });
    viewer.addEventListener('pointermove', function (ev) {
      if (!arrastrando) return;
      var r = viewer.getBoundingClientRect();
      var d = (ev.clientX - xInicio) / (r.width / N);
      mostrar(Math.round(d));
    });
    viewer.addEventListener('pointerup', function () { arrastrando = false; });
    viewer.addEventListener('pointercancel', function () { arrastrando = false; });

    /* --- teclado --- */
    viewer.addEventListener('keydown', function (ev) {
      if (ev.key !== 'ArrowRight' && ev.key !== 'ArrowLeft') return;
      ev.preventDefault();
      manual = true;
      parar();
      viewer.classList.add('is-active');
      mostrar(actual + (ev.key === 'ArrowRight' ? 1 : -1));
    });
    viewer.addEventListener('focus', function () { viewer.classList.add('is-active'); });
    viewer.addEventListener('blur', volverAlInicio);
  }

  /* ---------- contacto: envío ---------- */
  var form = document.getElementById('contactoForm');
  if (form) {
    var nota = document.getElementById('formNota');

    form.addEventListener('submit', function (ev) {
      ev.preventDefault();

      if (!form.checkValidity()) {
        nota.className = 'form__nota is-err';
        nota.textContent = 'Revisa los campos obligatorios: nombre, email y mensaje.';
        form.reportValidity();
        return;
      }

      // Sin backend todavía: se abre el correo con los datos ya redactados.
      var d = new FormData(form);
      var cuerpo = [
        'Nombre: ' + (d.get('nombre') || ''),
        'Empresa: ' + (d.get('empresa') || ''),
        'Email: ' + (d.get('email') || ''),
        'Teléfono: ' + (d.get('tel') || ''),
        'Motivo: ' + (d.get('motivo') || ''),
        '', d.get('mensaje') || ''
      ].join('\n');

      nota.className = 'form__nota is-ok';
      nota.textContent = 'Abriendo tu gestor de correo con el mensaje redactado…';

      location.href = 'mailto:mblasco@rh-bots.com'
        + '?subject=' + encodeURIComponent('Web RH·BOTS — ' + (d.get('motivo') || 'Consulta'))
        + '&body=' + encodeURIComponent(cuerpo);
    });
  }

  /* ---------- FAQ acordeón ---------- */
  var questions = document.querySelectorAll('.faq__q');

  Array.prototype.forEach.call(questions, function (q) {
    var panel = q.parentElement.nextElementSibling;

    q.addEventListener('click', function () {
      var open = q.getAttribute('aria-expanded') === 'true';

      // cierra el resto (acordeón de un solo panel abierto)
      Array.prototype.forEach.call(questions, function (other) {
        if (other === q) return;
        other.setAttribute('aria-expanded', 'false');
        other.parentElement.nextElementSibling.classList.remove('is-open');
      });

      q.setAttribute('aria-expanded', String(!open));
      panel.classList.toggle('is-open', !open);
    });
  });

  /* ---------- carruseles de tarjetas ----------
     Scroll horizontal nativo (táctil y trackpad funcionan solos) con flechas
     que avanzan una tarjeta y arrastre con el ratón. Al soltar se encaja en
     la tarjeta más cercana; si se ha arrastrado, el clic no abre el enlace.  */
  Array.prototype.forEach.call(document.querySelectorAll('[data-carrusel]'), function (caja) {
    var pista = caja.querySelector('.carrusel__pista');
    var prev = caja.querySelector('.carrusel__btn--prev');
    var next = caja.querySelector('.carrusel__btn--next');
    if (!pista) return;

    var paso = function () {
      var t = pista.children;
      if (t.length < 2) return pista.clientWidth;
      return t[1].offsetLeft - t[0].offsetLeft;
    };
    var ir = function (x, suave) {
      pista.scrollTo({ left: x, behavior: suave && !reduced ? 'smooth' : 'auto' });
    };
    var botones = function () {
      var max = pista.scrollWidth - pista.clientWidth - 2;
      if (prev) prev.disabled = pista.scrollLeft <= 2;
      if (next) next.disabled = pista.scrollLeft >= max;
    };

    if (prev) prev.addEventListener('click', function () { ir(pista.scrollLeft - paso(), true); });
    if (next) next.addEventListener('click', function () { ir(pista.scrollLeft + paso(), true); });
    pista.addEventListener('scroll', botones, { passive: true });
    window.addEventListener('resize', botones);
    botones();

    pista.addEventListener('keydown', function (ev) {
      if (ev.key !== 'ArrowRight' && ev.key !== 'ArrowLeft') return;
      ev.preventDefault();
      ir(pista.scrollLeft + (ev.key === 'ArrowRight' ? paso() : -paso()), true);
    });

    /* --- arrastrar con el ratón --- */
    var abajo = false, movido = false, x0 = 0, s0 = 0;
    pista.addEventListener('pointerdown', function (ev) {
      if (ev.pointerType !== 'mouse' || ev.button !== 0) return;
      abajo = true; movido = false;
      x0 = ev.clientX; s0 = pista.scrollLeft;
    });
    window.addEventListener('pointermove', function (ev) {
      if (!abajo) return;
      var dx = ev.clientX - x0;
      if (!movido && Math.abs(dx) > 5) {
        movido = true;
        caja.classList.add('is-arrastrando');
      }
      if (movido) pista.scrollLeft = s0 - dx;
    });
    window.addEventListener('pointerup', function () {
      if (!abajo) return;
      abajo = false;
      if (!movido) return;
      caja.classList.remove('is-arrastrando');
      // encajar en la tarjeta más cercana
      var p = paso();
      ir(Math.round(pista.scrollLeft / p) * p, true);
    });
    // tras un arrastre, el clic que suelta el ratón no debe navegar
    pista.addEventListener('click', function (ev) {
      if (movido) { ev.preventDefault(); ev.stopPropagation(); movido = false; }
    }, true);
    pista.addEventListener('dragstart', function (ev) { ev.preventDefault(); });
  });

  /* ---------- reveal on scroll ---------- */
  var items = document.querySelectorAll('.reveal');

  if (!('IntersectionObserver' in window) || reduced) {
    Array.prototype.forEach.call(items, function (el) { el.classList.add('is-in'); });
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-in');
      io.unobserve(entry.target);
    });
  }, { threshold: 0, rootMargin: '0px 0px -40px 0px' });

  /* Respaldo por geometría: en pestañas que no componen (previsualizaciones,
     prerender, segundo plano) el observador puede no entregar nunca. Sin esto
     la página se quedaría en blanco. */
  function sweep() {
    var vh = window.innerHeight || document.documentElement.clientHeight;
    Array.prototype.forEach.call(items, function (el) {
      if (el.classList.contains('is-in')) return;
      var b = el.getBoundingClientRect();
      if (b.top < vh - 40 && b.bottom > 0) {
        el.classList.add('is-in');
        io.unobserve(el);
      }
    });
  }
  var ticking = false;
  window.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () { sweep(); ticking = false; });
  }, { passive: true });
  window.addEventListener('resize', sweep, { passive: true });
  window.addEventListener('load', sweep);
  setTimeout(sweep, 300);

  // escalona los elementos que comparten fila
  var groups = {};
  Array.prototype.forEach.call(items, function (el) {
    var parent = el.parentElement;
    groups[parent.className] = groups[parent.className] || [];
    var idx = groups[parent.className].length;
    groups[parent.className].push(el);
    if (el.matches('.spec, .feat, .faq__item')) {
      el.style.setProperty('--d', (idx % 5) * 80 + 'ms');
    }
    io.observe(el);
  });
})();
