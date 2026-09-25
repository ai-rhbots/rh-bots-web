/* RH·BOTS — RHX2 landing */
(function () {
  'use strict';

  /* ---------- idioma: las cadenas que genera el propio JS (el resto ya
     viene traducido desde el HTML) leen el <html lang="es|pt|en|fr|de|zh|ar|ca">
     de la página */
  var IDIOMAS = ['es', 'pt', 'en', 'fr', 'de', 'zh', 'ar', 'ca'];
  var LANG = IDIOMAS.indexOf(document.documentElement.lang) > -1 ? document.documentElement.lang : 'es';
  var LOCALES = { es: 'es-ES', pt: 'pt-PT', en: 'en-GB', fr: 'fr-FR',
                  de: 'de-DE', zh: 'zh-CN', ar: 'ar-AE', ca: 'ca-ES' };
  /* IVA español: la empresa factura desde España */
  var IVA = 0.21;
  var TXT = {
    es: {
      asuntoEvento: 'Alquiler de humanoide para evento',
      ivaNoIncluido: 'IVA no incluido',
      conIva: 'Con IVA (21 %): {n}',
      abrirMenu: 'Abrir menú', cerrarMenu: 'Cerrar menú',
      sinStock: 'Sin stock — consúltanos la disponibilidad',
      avisame: 'Avísame cuando esté',
      precioConsulta: 'Precio bajo consulta',
      pedirPresupuesto: 'Pedir presupuesto',
      anadirCarrito: 'Añadir al carrito',
      carritoVacio: 'Todavía no has añadido ningún robot.',
      verCatalogo: 'Ver el catálogo',
      quitarUnidad: 'Quitar una unidad',
      anadirUnidad: 'Añadir una unidad',
      quitar: 'Quitar',
      formIncompleto: 'Revisa los campos obligatorios: nombre, email, mensaje y la política de privacidad.',
      formSinPrivacidad: 'Para enviar el mensaje tienes que aceptar la política de privacidad.',
      abriendoCorreo: 'Abriendo tu gestor de correo con el mensaje redactado…',
      campoNombre: 'Nombre: ', campoEmpresa: 'Empresa: ', campoEmail: 'Email: ',
      campoTelefono: 'Teléfono: ', campoRobot: 'Robot de interés: ', sinIndicar: 'sin indicar',
      asuntoWeb: 'Web RH·BOTS — ', asuntoConsulta: 'Consulta sobre ', asuntoSolicitud: 'Solicitud de información',
      consentimientoCorreo: '\n\n---\nAcepto la política de privacidad y el tratamiento de mis datos para recibir información comercial de RH·BOTS.'
    },
    pt: {
      asuntoEvento: 'Aluguer de humanoide para evento',
      ivaNoIncluido: 'IVA não incluído',
      conIva: 'Com IVA (21 %): {n}',
      abrirMenu: 'Abrir menu', cerrarMenu: 'Fechar menu',
      sinStock: 'Sem stock — consulte-nos a disponibilidade',
      avisame: 'Avisem-me quando estiver disponível',
      precioConsulta: 'Preço sob consulta',
      pedirPresupuesto: 'Pedir orçamento',
      anadirCarrito: 'Adicionar ao carrinho',
      carritoVacio: 'Ainda não adicionou nenhum robô.',
      verCatalogo: 'Ver o catálogo',
      quitarUnidad: 'Remover uma unidade',
      anadirUnidad: 'Adicionar uma unidade',
      quitar: 'Remover',
      formIncompleto: 'Reveja os campos obrigatórios: nome, email, mensagem e a política de privacidade.',
      formSinPrivacidad: 'Para enviar a mensagem tem de aceitar a política de privacidade.',
      abriendoCorreo: 'A abrir o seu gestor de email com a mensagem redigida…',
      campoNombre: 'Nome: ', campoEmpresa: 'Empresa: ', campoEmail: 'Email: ',
      campoTelefono: 'Telefone: ', campoRobot: 'Robô de interesse: ', sinIndicar: 'não indicado',
      asuntoWeb: 'Site RH·BOTS — ', asuntoConsulta: 'Consulta sobre ', asuntoSolicitud: 'Pedido de informação',
      consentimientoCorreo: '\n\n---\nAceito a política de privacidade e o tratamento dos meus dados para receber informação comercial da RH·BOTS.'
    },
    en: {
      asuntoEvento: 'Humanoid rental for an event',
      ivaNoIncluido: 'VAT not included',
      conIva: 'With VAT (21%): {n}',
      abrirMenu: 'Open menu', cerrarMenu: 'Close menu',
      sinStock: 'Out of stock — ask us about availability',
      avisame: 'Notify me when available',
      precioConsulta: 'Price on request',
      pedirPresupuesto: 'Request a quote',
      anadirCarrito: 'Add to cart',
      carritoVacio: "You haven't added any robots yet.",
      verCatalogo: 'View the catalog',
      quitarUnidad: 'Remove one unit',
      anadirUnidad: 'Add one unit',
      quitar: 'Remove',
      formIncompleto: 'Please check the required fields: name, email, message and the privacy policy.',
      formSinPrivacidad: 'You need to accept the privacy policy to send the message.',
      abriendoCorreo: 'Opening your email client with the drafted message…',
      campoNombre: 'Name: ', campoEmpresa: 'Company: ', campoEmail: 'Email: ',
      campoTelefono: 'Phone: ', campoRobot: 'Robot of interest: ', sinIndicar: 'not specified',
      asuntoWeb: 'RH·BOTS website — ', asuntoConsulta: 'Enquiry about ', asuntoSolicitud: 'Information request',
      consentimientoCorreo: '\n\n---\nI accept the privacy policy and the processing of my data to receive commercial information from RH·BOTS.'
    },
    fr: {
      asuntoEvento: "Location d'humanoïde pour un événement",
      ivaNoIncluido: 'TVA non incluse',
      conIva: 'TVA comprise (21 %) : {n}',
      abrirMenu: 'Ouvrir le menu', cerrarMenu: 'Fermer le menu',
      sinStock: 'Rupture de stock — demandez-nous la disponibilité',
      avisame: 'M\'avertir quand disponible',
      precioConsulta: 'Prix sur demande',
      pedirPresupuesto: 'Demander un devis',
      anadirCarrito: 'Ajouter au panier',
      carritoVacio: "Vous n'avez encore ajouté aucun robot.",
      verCatalogo: 'Voir le catalogue',
      quitarUnidad: 'Retirer une unité',
      anadirUnidad: 'Ajouter une unité',
      quitar: 'Retirer',
      formIncompleto: 'Vérifiez les champs obligatoires : nom, email, message et la politique de confidentialité.',
      formSinPrivacidad: 'Pour envoyer le message, vous devez accepter la politique de confidentialité.',
      abriendoCorreo: 'Ouverture de votre messagerie avec le message rédigé…',
      campoNombre: 'Nom : ', campoEmpresa: 'Entreprise : ', campoEmail: 'Email : ',
      campoTelefono: 'Téléphone : ', campoRobot: 'Robot qui vous intéresse : ', sinIndicar: 'non précisé',
      asuntoWeb: 'Site RH·BOTS — ', asuntoConsulta: 'Question sur ', asuntoSolicitud: "Demande d'information",
      consentimientoCorreo: '\n\n---\nJ\'accepte la politique de confidentialité et le traitement de mes données pour recevoir des informations commerciales de RH·BOTS.'
    },
    de: {
      asuntoEvento: 'Miete eines Humanoiden für eine Veranstaltung',
      ivaNoIncluido: 'zzgl. MwSt.',
      conIva: 'Mit MwSt. (21 %): {n}',
      abrirMenu: 'Menü öffnen', cerrarMenu: 'Menü schließen',
      sinStock: 'Nicht auf Lager — fragen Sie uns nach der Verfügbarkeit',
      avisame: 'Benachrichtigt mich, sobald verfügbar',
      precioConsulta: 'Preis auf Anfrage',
      pedirPresupuesto: 'Angebot anfordern',
      anadirCarrito: 'In den Warenkorb',
      carritoVacio: 'Sie haben noch keinen Roboter hinzugefügt.',
      verCatalogo: 'Zum Katalog',
      quitarUnidad: 'Eine Einheit entfernen',
      anadirUnidad: 'Eine Einheit hinzufügen',
      quitar: 'Entfernen',
      formIncompleto: 'Bitte prüfen Sie die Pflichtfelder: Name, E-Mail, Nachricht und die Datenschutzerklärung.',
      formSinPrivacidad: 'Um die Nachricht zu senden, müssen Sie die Datenschutzerklärung akzeptieren.',
      abriendoCorreo: 'Ihr E-Mail-Programm wird mit der fertigen Nachricht geöffnet…',
      campoNombre: 'Name: ', campoEmpresa: 'Unternehmen: ', campoEmail: 'E-Mail: ',
      campoTelefono: 'Telefon: ', campoRobot: 'Roboter von Interesse: ', sinIndicar: 'keine Angabe',
      asuntoWeb: 'RH·BOTS Website — ', asuntoConsulta: 'Anfrage zu ', asuntoSolicitud: 'Informationsanfrage',
      consentimientoCorreo: '\n\n---\nIch akzeptiere die Datenschutzerklärung und die Verarbeitung meiner Daten, um Informationen von RH·BOTS zu erhalten.'
    },
    zh: {
      asuntoEvento: '活动人形机器人租赁',
      ivaNoIncluido: '不含增值税',
      conIva: '含增值税（21%）：{n}',
      abrirMenu: '打开菜单', cerrarMenu: '关闭菜单',
      sinStock: '无现货 — 请咨询我们了解供货情况',
      avisame: '到货时通知我',
      precioConsulta: '价格面议',
      pedirPresupuesto: '索取报价',
      anadirCarrito: '加入购物车',
      carritoVacio: '您还没有添加任何机器人。',
      verCatalogo: '查看产品目录',
      quitarUnidad: '减少一件',
      anadirUnidad: '增加一件',
      quitar: '移除',
      formIncompleto: '请检查必填项：姓名、邮箱、留言以及隐私政策同意选项。',
      formSinPrivacidad: '发送留言前需要接受隐私政策。',
      abriendoCorreo: '正在打开您的邮件客户端，留言内容已自动填写…',
      campoNombre: '姓名：', campoEmpresa: '公司：', campoEmail: '邮箱：',
      campoTelefono: '电话：', campoRobot: '感兴趣的机器人：', sinIndicar: '未指定',
      asuntoWeb: 'RH·BOTS网站 — ', asuntoConsulta: '咨询关于 ', asuntoSolicitud: '信息申请',
      consentimientoCorreo: '\n\n---\n我接受隐私政策，并同意处理我的数据以接收RH·BOTS的商业信息。'
    },
    ar: {
      asuntoEvento: 'تأجير روبوت بشري لفعالية',
      ivaNoIncluido: 'غير شامل ضريبة القيمة المضافة',
      conIva: 'شامل ضريبة القيمة المضافة (21%): {n}',
      abrirMenu: 'فتح القائمة', cerrarMenu: 'إغلاق القائمة',
      sinStock: 'غير متوفر — تواصل معنا لمعرفة موعد التوفر',
      avisame: 'أبلغوني عند التوفر',
      precioConsulta: 'السعر عند الطلب',
      pedirPresupuesto: 'طلب عرض سعر',
      anadirCarrito: 'أضف إلى السلة',
      carritoVacio: 'لم تُضف أي روبوت بعد.',
      verCatalogo: 'تصفّح الكتالوج',
      quitarUnidad: 'إنقاص وحدة',
      anadirUnidad: 'إضافة وحدة',
      quitar: 'إزالة',
      formIncompleto: 'يرجى مراجعة الحقول الإلزامية: الاسم والبريد الإلكتروني والرسالة وسياسة الخصوصية.',
      formSinPrivacidad: 'لإرسال الرسالة عليك قبول سياسة الخصوصية.',
      abriendoCorreo: 'يجري فتح برنامج البريد لديك والرسالة جاهزة…',
      campoNombre: 'الاسم: ', campoEmpresa: 'الشركة: ', campoEmail: 'البريد الإلكتروني: ',
      campoTelefono: 'الهاتف: ', campoRobot: 'الروبوت محل الاهتمام: ', sinIndicar: 'غير محدد',
      asuntoWeb: 'موقع RH·BOTS — ', asuntoConsulta: 'استفسار عن ', asuntoSolicitud: 'طلب معلومات',
      consentimientoCorreo: '\n\n---\nأوافق على سياسة الخصوصية وعلى معالجة بياناتي لتلقي معلومات تجارية من RH·BOTS.'
    },
    ca: {
      asuntoEvento: "Lloguer d'humanoide per a esdeveniment",
      ivaNoIncluido: 'IVA no inclòs',
      conIva: 'Amb IVA (21 %): {n}',
      abrirMenu: 'Obre el menú', cerrarMenu: 'Tanca el menú',
      sinStock: 'Sense estoc — consulta\'ns la disponibilitat',
      avisame: 'Avisa\'m quan hi sigui',
      precioConsulta: 'Preu sota consulta',
      pedirPresupuesto: 'Demanar pressupost',
      anadirCarrito: 'Afegeix al carret',
      carritoVacio: 'Encara no has afegit cap robot.',
      verCatalogo: 'Veure el catàleg',
      quitarUnidad: 'Treu una unitat',
      anadirUnidad: 'Afegeix una unitat',
      quitar: 'Treu',
      formIncompleto: 'Revisa els camps obligatoris: nom, email, missatge i la política de privacitat.',
      formSinPrivacidad: 'Per enviar el missatge cal acceptar la política de privacitat.',
      abriendoCorreo: 'S\'està obrint el teu gestor de correu amb el missatge redactat…',
      campoNombre: 'Nom: ', campoEmpresa: 'Empresa: ', campoEmail: 'Email: ',
      campoTelefono: 'Telèfon: ', campoRobot: 'Robot d\'interès: ', sinIndicar: 'sense indicar',
      asuntoWeb: 'Web RH·BOTS — ', asuntoConsulta: 'Consulta sobre ', asuntoSolicitud: 'Sol·licitud d\'informació',
      consentimientoCorreo: '\n\n---\nAccepto la política de privacitat i el tractament de les meves dades per rebre informació comercial de RH·BOTS.'
    }
  }[LANG];

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
    toggle.setAttribute('aria-label', open ? TXT.abrirMenu : TXT.cerrarMenu);
    nav.classList.toggle('is-open', !open);
  });

  /* ---------- submenú de familias ----------
     En escritorio se abre al pasar el ratón (CSS) o con la flecha; en móvil,
     solo con la flecha, como un acordeón. Escape y un clic fuera lo cierran. */
  Array.prototype.forEach.call(nav.querySelectorAll('.nav__grupo'), function (grupo) {
    var boton = grupo.querySelector('.nav__abrir');
    var cerrar = function () {
      grupo.classList.remove('is-open');
      boton.setAttribute('aria-expanded', 'false');
    };
    boton.addEventListener('click', function (ev) {
      ev.stopPropagation();
      var abierto = grupo.classList.toggle('is-open');
      boton.setAttribute('aria-expanded', String(abierto));
    });
    document.addEventListener('click', function (ev) {
      if (!grupo.contains(ev.target)) cerrar();
    });
    grupo.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape') { cerrar(); boton.focus(); }
    });
  });

  /* ---------- panel de robots: la familia señalada manda ----------
     Al pasar el ratón (o al enfocar con el teclado) por una familia se
     muestran sus modelos. El enlace de la familia sigue llevando a su
     sección del catálogo; en móvil no hace falta, ahí se ven todas. */
  Array.prototype.forEach.call(document.querySelectorAll('[data-menurobots]'), function (panel) {
    var familias = panel.querySelectorAll('.nav__fam');
    var listas = panel.querySelectorAll('.nav__modelos');
    var mostrar = function (clave) {
      Array.prototype.forEach.call(familias, function (f) {
        f.classList.toggle('is-on', f.dataset.fam === clave);
      });
      Array.prototype.forEach.call(listas, function (l) {
        l.classList.toggle('is-on', l.dataset.fam === clave);
      });
    };
    Array.prototype.forEach.call(familias, function (f) {
      var ir = function () { mostrar(f.dataset.fam); };
      f.addEventListener('mouseenter', ir);
      f.addEventListener('focus', ir);
    });
  });

  nav.addEventListener('click', function (e) {
    if (e.target.tagName !== 'A') return;
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', TXT.abrirMenu);
    nav.classList.remove('is-open');
  });

  /* ---------- selector de idioma: desplegable de banderas ----------
     Mismo patrón que el submenú de familias: clic para abrir/cerrar,
     clic fuera y Escape lo cierran. */
  var langSwitch = document.querySelector('.lang-switch');
  if (langSwitch) {
    var langBoton = langSwitch.querySelector('.lang-switch__abrir');
    var cerrarLang = function () {
      langSwitch.classList.remove('is-open');
      langBoton.setAttribute('aria-expanded', 'false');
    };
    langBoton.addEventListener('click', function (ev) {
      ev.stopPropagation();
      var abierto = langSwitch.classList.toggle('is-open');
      langBoton.setAttribute('aria-expanded', String(abierto));
    });
    document.addEventListener('click', function (ev) {
      if (!langSwitch.contains(ev.target)) cerrarLang();
    });
    langSwitch.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape') { cerrarLang(); langBoton.focus(); }
    });
  }

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
    var celdas = raiz.querySelectorAll('.keyfacts strong, .spec dd, [data-contar]');
    Array.prototype.forEach.call(celdas, function (el) {
      if (el.dataset.contado) return;

      var texto = el.textContent;
      var m = texto.match(/^(.*?)(\d{1,3}(?:\.\d{3})*(?:,\d+)?)(.*)$/s);
      if (!m) return;

      var destino = parseFloat(m[2].replace(/\./g, '').replace(',', '.'));
      // números pequeños no lucen, salvo en los contadores marcados a propósito
      if (!isFinite(destino) || (destino < 10 && !el.hasAttribute('data-contar'))) return;

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
          v.toLocaleString(LOCALES[LANG], { minimumFractionDigits: decimales,
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
  var zonasCifras = document.querySelectorAll('.keyfacts, .specs, .alianza__cifras');
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
        return new Intl.NumberFormat(LOCALES[LANG], {
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

      function textoIva(neto, moneda) {
        /* el precio sin IVA sigue mandando; al lado, el mismo importe con IVA */
        if (!neto || neto <= 0) return esc(TXT.ivaNoIncluido);
        return esc(TXT.ivaNoIncluido) + ' · <strong class="coniva">' +
               esc(TXT.conIva.replace('{n}', importe(Math.round(neto * (1 + IVA) * 100))
                                                + ' ' + simbolo(moneda))) + '</strong>';
      }

      function pinta(v, moneda) {
        if (!v || !v.available) {
          return aviso(TXT.sinStock, TXT.avisame);
        }
        if (!v.price || v.price <= 0) {
          return aviso(TXT.precioConsulta, TXT.pedirPresupuesto);
        }
        var precio = d.precio === '1'
          ? '<p class="precio">' + importe(v.price) +
            ' <span>' + esc(simbolo(moneda)) + '</span>' +
            '<span class="precio__iva">' + textoIva(v.price / 100, moneda) + '</span></p>'
          : '';
        var carro = '<i class="pill__ico pill__ico--carro" aria-hidden="true">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" ' +
          'stroke-linecap="round" stroke-linejoin="round">' +
          '<path d="M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h7.4a2 2 0 0 0 2-1.5L20.5 8H6"/>' +
          '<circle cx="10" cy="20" r="1.3"/><circle cx="17" cy="20" r="1.3"/></svg></i>';
        return precio +
          '<a class="pill pill--comprar" rel="nofollow noopener" href="' +
          esc(base + '/cart/' + v.id + ':1') + '"><span>' +
          esc(d.texto) + '</span>' + chevron + '</a>' +
          '<button class="pill pill--anadir" type="button" data-anadir data-variante="' +
          esc(v.id) + '" data-precio-num="' + (v.price / 100) + '">' +
          '<span>' + esc(TXT.anadirCarrito) + '</span>' + carro + '</button>';
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

  /* ---------- carrito ----------
     El carrito se guarda en el navegador (localStorage). Al finalizar, las
     líneas se traducen en un «cart permalink» de Shopify
     (/cart/<variante>:<unidades>,…), así que el cobro, el stock, los envíos
     y los impuestos los sigue llevando Shopify: aquí no hay ni claves ni
     datos de pago.                                                          */
  var cajaCarrito = document.querySelector('[data-carrito]');
  if (cajaCarrito) {
    (function () {
      var LLAVE = 'rhbots-carrito';
      var dominio = cajaCarrito.dataset.dominio;
      var lista = cajaCarrito.querySelector('[data-carrito-lista]');
      var pie = cajaCarrito.querySelector('[data-carrito-pie]');
      var totalEl = cajaCarrito.querySelector('[data-carrito-total]');
      var pagar = cajaCarrito.querySelector('[data-carrito-pagar]');
      var abrir = document.querySelector('[data-carrito-abrir]');
      var numero = document.querySelector('[data-carrito-num]');

      function leer() {
        try { return JSON.parse(localStorage.getItem(LLAVE)) || []; }
        catch (e) { return []; }
      }
      function guardar(items) {
        try { localStorage.setItem(LLAVE, JSON.stringify(items)); } catch (e) {}
      }
      function esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
          return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
        });
      }
      function dinero(n, moneda) {
        try {
          return new Intl.NumberFormat(LOCALES[LANG], {
            style: 'currency', currency: moneda || 'EUR', maximumFractionDigits: 0
          }).format(n);
        } catch (e) { return n + ' ' + (moneda || ''); }
      }

      function pinta() {
        var items = leer();
        var unidades = items.reduce(function (n, i) { return n + i.uds; }, 0);
        if (numero) {
          numero.textContent = unidades;
          numero.hidden = unidades === 0;
        }
        if (!items.length) {
          lista.innerHTML = '<p class="carrito__vacio">' + esc(TXT.carritoVacio) +
            '<a href="' + esc(cajaCarrito.dataset.robots || 'robots.html') + '">' + esc(TXT.verCatalogo) + '</a></p>';
          pie.hidden = true;
          return;
        }
        var total = 0, moneda = 'EUR';
        lista.innerHTML = items.map(function (i) {
          total += i.precio * i.uds;
          moneda = i.moneda || moneda;
          return '<article class="citem" data-variante="' + esc(i.id) + '">' +
            (i.foto ? '<a class="citem__foto" href="' + esc(i.url) + '">' +
                      '<img src="' + esc(i.foto) + '" alt="" loading="lazy"></a>' : '') +
            '<div class="citem__texto">' +
              '<a class="citem__nombre" href="' + esc(i.url) + '">' + esc(i.nombre) + '</a>' +
              '<p class="citem__precio">' + esc(dinero(i.precio, i.moneda)) + '</p>' +
              '<div class="citem__uds">' +
                '<button type="button" data-menos aria-label="' + esc(TXT.quitarUnidad) + '">−</button>' +
                '<span>' + i.uds + '</span>' +
                '<button type="button" data-mas aria-label="' + esc(TXT.anadirUnidad) + '">+</button>' +
                '<button type="button" class="citem__quitar" data-quitar>' + esc(TXT.quitar) + '</button>' +
              '</div>' +
            '</div></article>';
        }).join('');
        totalEl.textContent = dinero(total, moneda);
        var avisoIva = cajaCarrito.querySelector('.carrito__iva');
        if (avisoIva) {
          avisoIva.innerHTML = esc(TXT.ivaNoIncluido) + ' · <strong class="coniva">' +
            esc(TXT.conIva.replace('{n}', dinero(total * (1 + IVA), moneda))) + '</strong>';
        }
        pagar.href = 'https://' + dominio + '/cart/' + items.map(function (i) {
          return i.id + ':' + i.uds;
        }).join(',');
        pie.hidden = false;
      }

      function abrirPanel(si) {
        cajaCarrito.hidden = !si;
        cajaCarrito.classList.toggle('is-open', si);
        document.documentElement.classList.toggle('sin-scroll', si);
        if (abrir) abrir.setAttribute('aria-expanded', String(si));
      }

      function anadir(datos) {
        var items = leer();
        var ya = items.filter(function (i) { return i.id === datos.id; })[0];
        if (ya) ya.uds += 1; else items.push(datos);
        guardar(items);
        pinta();
        abrirPanel(true);
      }

      // botones «añadir al carrito» (los repinta el bloque de precio en vivo)
      document.addEventListener('click', function (ev) {
        var b = ev.target.closest && ev.target.closest('[data-anadir]');
        if (!b) return;
        var caja = b.closest('[data-tienda]');
        if (!caja) return;
        ev.preventDefault();
        anadir({
          id: b.dataset.variante || caja.dataset.variante,
          nombre: caja.dataset.nombre || document.title,
          precio: Number(b.dataset.precioNum || caja.dataset.precioNum || 0),
          moneda: caja.dataset.moneda || 'EUR',
          foto: caja.dataset.foto || '',
          url: caja.dataset.url || location.pathname,
          uds: 1
        });
      });

      // abrir, cerrar y cambiar unidades
      if (abrir) abrir.addEventListener('click', function () { abrirPanel(true); });
      cajaCarrito.addEventListener('click', function (ev) {
        if (ev.target.closest('[data-carrito-cerrar]')) return abrirPanel(false);
        var fila = ev.target.closest('.citem');
        if (!fila) return;
        var items = leer();
        var i = items.filter(function (x) { return String(x.id) === fila.dataset.variante; })[0];
        if (!i) return;
        if (ev.target.closest('[data-mas]')) i.uds += 1;
        else if (ev.target.closest('[data-menos]')) i.uds -= 1;
        else if (ev.target.closest('[data-quitar]')) i.uds = 0;
        else return;
        guardar(items.filter(function (x) { return x.uds > 0; }));
        pinta();
      });
      document.addEventListener('keydown', function (ev) {
        if (ev.key === 'Escape' && cajaCarrito.classList.contains('is-open')) abrirPanel(false);
      });

      pinta();
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
        var falta = form.querySelector('#f-privacidad');
        nota.className = 'form__nota is-err';
        nota.textContent = (falta && !falta.checked && form.querySelector(':invalid') === falta)
          ? TXT.formSinPrivacidad
          : TXT.formIncompleto;
        form.reportValidity();
        return;
      }

      // Sin backend todavía: se abre el correo con los datos ya redactados.
      var d = new FormData(form);
      var robot = d.get('robot') || '';
      var cuerpo = [
        TXT.campoNombre + [d.get('nombre'), d.get('apellidos')].filter(Boolean).join(' '),
        TXT.campoEmpresa + (d.get('empresa') || ''),
        TXT.campoEmail + (d.get('email') || ''),
        TXT.campoTelefono + (d.get('tel') || ''),
        TXT.campoRobot + (robot || TXT.sinIndicar),
        '', d.get('mensaje') || ''
      ].join('\n');

      nota.className = 'form__nota is-ok';
      nota.textContent = TXT.abriendoCorreo;

      location.href = 'mailto:' + (form.getAttribute('data-email') || 'info@rh-bots.com')
        + '?subject=' + encodeURIComponent(TXT.asuntoWeb + (robot ? TXT.asuntoConsulta + robot : TXT.asuntoSolicitud))
        + '&body=' + encodeURIComponent(cuerpo + TXT.consentimientoCorreo);
    });
  }

  /* ---------- formulario de eventos ----------
     Mismo envío por correo que el de contacto, pero con campos propios: el
     cuerpo se arma leyendo la etiqueta visible de cada campo, así no hay que
     duplicar las traducciones aquí. */
  var formEvento = document.getElementById('eventoForm');
  if (formEvento) {
    var notaEvento = document.getElementById('eventoNota');

    formEvento.addEventListener('submit', function (ev) {
      ev.preventDefault();

      if (!formEvento.checkValidity()) {
        var privacidad = formEvento.querySelector('#ev-privacidad');
        notaEvento.className = 'form__nota is-err';
        notaEvento.textContent = (privacidad && !privacidad.checked &&
                                  formEvento.querySelector(':invalid') === privacidad)
          ? TXT.formSinPrivacidad
          : TXT.formIncompleto;
        formEvento.reportValidity();
        return;
      }

      var lineas = [];
      Array.prototype.forEach.call(formEvento.querySelectorAll('input[name], textarea[name]'), function (campo) {
        if (campo.type === 'checkbox' || !campo.value.trim()) return;
        var etiqueta = formEvento.querySelector('label[for="' + campo.id + '"]');
        lineas.push((etiqueta ? etiqueta.textContent.trim() : campo.name) + ': ' + campo.value.trim());
      });

      notaEvento.className = 'form__nota is-ok';
      notaEvento.textContent = TXT.abriendoCorreo;

      location.href = 'mailto:' + (formEvento.getAttribute('data-email') || 'info@rh-bots.com')
        + '?subject=' + encodeURIComponent(TXT.asuntoWeb + TXT.asuntoEvento)
        + '&body=' + encodeURIComponent(lineas.join('\n') + TXT.consentimientoCorreo);
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

  /* ---------- blog: buscador y filtro por categoría ----------
     Filtran en la propia página: cada artículo lleva su texto en data-buscar
     y su categoría en data-cat. La búsqueda no distingue mayúsculas ni
     tildes y exige todas las palabras; el filtro se suma a la búsqueda.
     Admite ?q= en la dirección.                                            */
  var buscador = document.querySelector('[data-buscador]');
  if (buscador) {
    var campo = buscador.querySelector('input');
    var fichas = document.querySelectorAll('[data-buscar]');
    var vacio = document.querySelector('.blogbusca__vacio');
    var filtros = document.querySelectorAll('.filtro');
    var categoria = '';
    var llano = function (t) {
      return String(t || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    };
    var aplicar = function () {
      var palabras = llano(campo.value).split(/\s+/).filter(Boolean);
      var enRejilla = 0;
      Array.prototype.forEach.call(fichas, function (f) {
        var texto = llano(f.getAttribute('data-buscar'));
        var ok = palabras.every(function (p) { return texto.indexOf(p) !== -1; });
        // el destacado no tiene data-cat: solo le afecta la búsqueda
        if (ok && categoria && f.hasAttribute('data-cat')) ok = f.getAttribute('data-cat') === categoria;
        f.hidden = !ok;
        if (ok) f.classList.add('is-in');
        if (ok && f.hasAttribute('data-cat')) enRejilla++;
      });
      if (vacio) vacio.hidden = enRejilla > 0;
    };
    Array.prototype.forEach.call(filtros, function (b) {
      b.addEventListener('click', function () {
        categoria = b.getAttribute('data-cat');
        Array.prototype.forEach.call(filtros, function (x) {
          var on = x === b;
          x.classList.toggle('is-on', on);
          x.setAttribute('aria-pressed', String(on));
        });
        aplicar();
      });
    });
    buscador.addEventListener('submit', function (ev) {
      ev.preventDefault();
      aplicar();
      var destino = document.getElementById('ultimos');
      if (destino) destino.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth' });
    });
    campo.addEventListener('input', aplicar);
    var inicial = new URLSearchParams(location.search).get('q');
    if (inicial) { campo.value = inicial; aplicar(); }
  }

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
