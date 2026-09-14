/* Panel RH·BOTS — editor enriquecido, subida de imágenes y listas dinámicas.
   Sólo lo usa el propio administrador en local, así que no hace falta
   compatibilidad con navegadores antiguos: JS moderno sin dependencias. */
(() => {
  'use strict';

  const CSRF = window.RH_CSRF || '';

  async function subirImagen(archivo) {
    const datos = new FormData();
    datos.append('archivo', archivo);
    datos.append('csrf', CSRF);
    const r = await fetch('/medios/subir', { method: 'POST', body: datos });
    let j;
    try { j = await r.json(); } catch { j = null; }
    if (!r.ok || !j || !j.ok) throw new Error((j && j.error) || 'No se pudo subir la imagen.');
    return j;                                    // { ok, url, kb }
  }

  function escaparHtml(s) {
    return s.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  }

  /* ======================================================================
     EDITOR ENRIQUECIDO
     ====================================================================== */
  function iniciarEditores() {
    document.querySelectorAll('[data-editor]').forEach((caja) => {
      const area = caja.querySelector('[data-editor-area]');
      const destino = document.getElementById(caja.dataset.target);
      const archivo = caja.querySelector('[data-editor-file]');
      if (!area || !destino) return;

      area.innerHTML = destino.value || '<p></p>';

      const sincronizar = () => { destino.value = area.innerHTML; };
      area.addEventListener('input', sincronizar);
      caja.closest('form')?.addEventListener('submit', sincronizar);

      // barra de herramientas
      caja.querySelectorAll('[data-cmd]').forEach((btn) => {
        btn.addEventListener('click', () => {
          area.focus();
          document.execCommand(btn.dataset.cmd, false, btn.dataset.valor || null);
          sincronizar();
        });
      });

      caja.querySelectorAll('[data-accion]').forEach((btn) => {
        btn.addEventListener('click', () => {
          area.focus();
          if (btn.dataset.accion === 'enlace') insertarEnlace(area);
          if (btn.dataset.accion === 'imagen') archivo?.click();
          sincronizar();
        });
      });

      // insertar imagen mediante el selector de archivo
      archivo?.addEventListener('change', async () => {
        const f = archivo.files[0];
        archivo.value = '';
        if (!f) return;
        await insertarImagenSubida(area, f);
        sincronizar();
      });

      // arrastrar y soltar directamente sobre el editor
      area.addEventListener('dragover', (e) => { e.preventDefault(); area.classList.add('is-arrastrando'); });
      area.addEventListener('dragleave', () => area.classList.remove('is-arrastrando'));
      area.addEventListener('drop', async (e) => {
        e.preventDefault();
        area.classList.remove('is-arrastrando');
        const f = [...(e.dataTransfer?.files || [])].find(x => x.type.startsWith('image/'));
        if (!f) return;
        colocarCaretEn(area, e.clientX, e.clientY);
        await insertarImagenSubida(area, f);
        sincronizar();
      });

      // pegar: se limpia a una lista blanca de etiquetas, igual de estricta
      // que el saneado del servidor (que sigue siendo quien manda de verdad)
      area.addEventListener('paste', (e) => {
        e.preventDefault();
        const html = e.clipboardData?.getData('text/html');
        const plano = e.clipboardData?.getData('text/plain') || '';
        const contenido = html ? limpiarPegado(html) : textoPlanoAHtml(plano);
        document.execCommand('insertHTML', false, contenido);
        sincronizar();
      });
    });
  }

  function colocarCaretEn(area, x, y) {
    area.focus();                      // execCommand exige que el editable esté enfocado
    const sel = window.getSelection();
    const porPunto = document.caretRangeFromPoint ? document.caretRangeFromPoint(x, y) : null;

    // el punto sólo vale si cae dentro del propio editor; si el navegador
    // no lo soporta o devuelve algo fuera (p. ej. la cabecera), se inserta
    // al final del contenido en vez de perder la imagen en silencio
    if (porPunto && area.contains(porPunto.startContainer)) {
      sel.removeAllRanges();
      sel.addRange(porPunto);
      return;
    }
    const alFinal = document.createRange();
    alFinal.selectNodeContents(area);
    alFinal.collapse(false);
    sel.removeAllRanges();
    sel.addRange(alFinal);
  }

  async function insertarImagenSubida(area, archivo) {
    area.classList.add('is-subiendo');
    try {
      const { url } = await subirImagen(archivo);
      document.execCommand('insertImage', false, url);
    } catch (ex) {
      alert(ex.message);
    } finally {
      area.classList.remove('is-subiendo');
    }
  }

  function insertarEnlace(area) {
    const url = window.prompt('URL del enlace (con https://):', 'https://');
    if (!url) return;
    document.execCommand('createLink', false, url);
    let nodo = window.getSelection()?.anchorNode;
    while (nodo && nodo.nodeName !== 'A') nodo = nodo.parentNode;
    if (nodo) { nodo.target = '_blank'; nodo.rel = 'noopener noreferrer'; }
  }

  function textoPlanoAHtml(texto) {
    return texto.split(/\n{2,}/).map(p => `<p>${escaparHtml(p).replace(/\n/g, '<br>')}</p>`).join('');
  }

  const ETIQUETAS_PEGADO = new Set(['P', 'BR', 'STRONG', 'B', 'EM', 'I', 'U', 'S',
    'H2', 'H3', 'H4', 'UL', 'OL', 'LI', 'BLOCKQUOTE', 'A', 'IMG', 'HR', 'CODE', 'PRE']);
  const ATRIBUTOS_PEGADO = { A: ['href'], IMG: ['src', 'alt'] };

  function limpiarPegado(htmlBruto) {
    const tmp = document.createElement('div');
    tmp.innerHTML = htmlBruto;
    (function recorrer(n) {
      [...n.childNodes].forEach((hijo) => {
        if (hijo.nodeType === 3) return;          // texto: se conserva tal cual
        if (hijo.nodeType !== 1) { hijo.remove(); return; }
        if (!ETIQUETAS_PEGADO.has(hijo.tagName)) {
          while (hijo.firstChild) hijo.parentNode.insertBefore(hijo.firstChild, hijo);
          hijo.remove();
          return;
        }
        [...hijo.attributes].forEach((a) => {
          if (!(ATRIBUTOS_PEGADO[hijo.tagName] || []).includes(a.name)) hijo.removeAttribute(a.name);
        });
        recorrer(hijo);
      });
    }(tmp));
    return tmp.innerHTML;
  }

  /* ======================================================================
     SELECTOR DE IMAGEN (campo único con vista previa)
     ====================================================================== */
  function iniciarSelectoresImagen() {
    document.querySelectorAll('[data-imgpicker]').forEach((caja) => {
      const campo = caja.querySelector('input[type="text"], input[type="hidden"]');
      const zona = caja.querySelector('[data-imgpicker-zona]');
      const previa = caja.querySelector('[data-imgpicker-preview]');
      const texto = caja.querySelector('[data-imgpicker-texto]');
      const archivo = caja.querySelector('[data-imgpicker-file]');
      const quitar = caja.querySelector('[data-imgpicker-quitar]');
      if (!campo || !zona) return;

      const refrescar = () => {
        if (campo.value) {
          previa.src = '/vista/' + campo.value;    // rutas relativas a web/
          previa.hidden = false;
          if (texto) texto.hidden = true;
          if (quitar) quitar.hidden = false;
        } else {
          previa.hidden = true;
          if (texto) texto.hidden = false;
          if (quitar) quitar.hidden = true;
        }
      };
      refrescar();

      const subir = async (f) => {
        if (!f || !f.type.startsWith('image/')) return;
        zona.classList.add('is-subiendo');
        try {
          const { url } = await subirImagen(f);
          campo.value = url;
          campo.dispatchEvent(new Event('input', { bubbles: true }));
          refrescar();
        } catch (ex) {
          alert(ex.message);
        } finally {
          zona.classList.remove('is-subiendo');
        }
      };

      zona.addEventListener('click', () => archivo?.click());
      zona.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); archivo?.click(); }
      });
      archivo?.addEventListener('change', () => { subir(archivo.files[0]); archivo.value = ''; });

      zona.addEventListener('dragover', (e) => { e.preventDefault(); zona.classList.add('is-arrastrando'); });
      zona.addEventListener('dragleave', () => zona.classList.remove('is-arrastrando'));
      zona.addEventListener('drop', (e) => {
        e.preventDefault();
        zona.classList.remove('is-arrastrando');
        subir(e.dataTransfer?.files?.[0]);
      });

      quitar?.addEventListener('click', (e) => {
        e.preventDefault();
        campo.value = '';
        campo.dispatchEvent(new Event('input', { bubbles: true }));
        refrescar();
      });

      campo.addEventListener('input', refrescar);
    });
  }

  /* ======================================================================
     LISTAS DINÁMICAS (sustituyen los textarea «A | B | C» por filas de
     verdad, con botones de añadir/quitar/mover). El textarea original se
     mantiene oculto y sincronizado: el servidor no cambia ni una línea.
     ====================================================================== */
  function iniciarListas() {
    document.querySelectorAll('[data-filas]').forEach((caja) => {
      const destino = document.getElementById(caja.dataset.target);
      const lista = caja.querySelector('[data-filas-lista]');
      const botonAdd = caja.querySelector('[data-filas-add]');
      if (!destino || !lista) return;

      let cols;
      try { cols = JSON.parse(caja.dataset.cols); } catch { cols = [{ label: 'Valor', tipo: 'texto' }]; }

      const filasIniciales = (destino.value || '')
        .replace(/\r/g, '').split('\n')
        .map(l => l.trim()).filter(Boolean)
        .map(l => {
          const partes = l.split('|').map(x => x.trim());
          while (partes.length < cols.length) partes.push('');
          return partes.slice(0, cols.length);
        });

      const sincronizar = () => {
        const filas = [...lista.children].map((fila) => {
          const valores = [...fila.querySelectorAll('[data-campo]')].map((el) => {
            if (el.type === 'checkbox') return el.checked ? (el.dataset.valorSi || 'si') : '';
            // cada fila es una línea del textarea oculto: un salto de línea
            // real dentro de un campo rompería el formato, así que se evita
            return el.value.replace(/\r?\n+/g, ' ').replace(/\s+/g, ' ').trim();
          });
          return valores.join(' | ');
        });
        destino.value = filas.join('\n');
      };

      function fila(valores) {
        const el = document.createElement('div');
        el.className = 'filafila';
        cols.forEach((col, i) => {
          const v = valores[i] || '';
          const envoltorio = document.createElement('div');
          envoltorio.className = 'filafila__campo';
          if (col.label) {
            const et = document.createElement('label');
            et.textContent = col.label;
            envoltorio.appendChild(et);
          }
          let input;
          if (col.tipo === 'select') {
            input = document.createElement('select');
            (col.opciones || []).forEach((op) => {
              const o = document.createElement('option');
              o.value = op.valor ?? op;
              o.textContent = op.texto ?? op;
              if (o.value === v) o.selected = true;
              input.appendChild(o);
            });
          } else if (col.tipo === 'bool') {
            input = document.createElement('input');
            input.type = 'checkbox';
            input.checked = !!v;
            input.dataset.valorSi = col.valorSi || 'si';
          } else if (col.tipo === 'textarea') {
            input = document.createElement('textarea');
            input.rows = 2;
            input.value = v;
          } else if (col.tipo === 'imagen') {
            input = document.createElement('input');
            input.type = 'text';
            input.value = v;
            input.placeholder = col.placeholder || 'assets/…';
          } else {
            input = document.createElement('input');
            input.type = 'text';
            input.value = v;
            input.placeholder = col.placeholder || '';
          }
          input.dataset.campo = '1';
          input.addEventListener('input', sincronizar);
          input.addEventListener('change', sincronizar);
          envoltorio.appendChild(input);

          if (col.tipo === 'imagen') {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'filafila__subir';
            btn.textContent = '⤒ Subir';
            btn.title = 'Subir una imagen desde el ordenador';
            const fInput = document.createElement('input');
            fInput.type = 'file'; fInput.accept = 'image/*'; fInput.hidden = true;
            fInput.addEventListener('change', async () => {
              const f = fInput.files[0]; fInput.value = '';
              if (!f) return;
              btn.disabled = true; btn.textContent = 'Subiendo…';
              try {
                const { url } = await subirImagen(f);
                input.value = url;
                sincronizar();
              } catch (ex) { alert(ex.message); }
              finally { btn.disabled = false; btn.textContent = '⤒ Subir'; }
            });
            btn.addEventListener('click', () => fInput.click());
            envoltorio.appendChild(btn);
            envoltorio.appendChild(fInput);
          }
          el.appendChild(envoltorio);
        });

        const acciones = document.createElement('div');
        acciones.className = 'filafila__acciones';
        const subir_ = boton('↑', 'Subir', () => mover(el, -1));
        const bajar_ = boton('↓', 'Bajar', () => mover(el, 1));
        const borrar_ = boton('✕', 'Quitar', () => { el.remove(); sincronizar(); });
        borrar_.classList.add('filafila__borrar');
        acciones.append(subir_, bajar_, borrar_);
        el.appendChild(acciones);
        return el;
      }

      function boton(texto, titulo, fn) {
        const b = document.createElement('button');
        b.type = 'button'; b.textContent = texto; b.title = titulo;
        b.addEventListener('click', fn);
        return b;
      }

      function mover(el, dir) {
        if (dir < 0 && el.previousElementSibling) lista.insertBefore(el, el.previousElementSibling);
        if (dir > 0 && el.nextElementSibling) lista.insertBefore(el.nextElementSibling, el);
        sincronizar();
      }

      filasIniciales.forEach(v => lista.appendChild(fila(v)));
      botonAdd?.addEventListener('click', () => {
        lista.appendChild(fila(cols.map(() => '')));
        sincronizar();
      });

      caja.closest('form')?.addEventListener('submit', sincronizar);
      sincronizar();
    });
  }

  /* ======================================================================
     BIBLIOTECA DE MEDIOS (subida múltiple con arrastrar y soltar)
     ====================================================================== */
  function iniciarBiblioteca() {
    const zona = document.querySelector('[data-biblioteca-zona]');
    if (!zona) return;
    const archivo = document.querySelector('[data-biblioteca-file]');
    const estado = document.querySelector('[data-biblioteca-estado]');

    const subirVarias = async (lista) => {
      const imagenes = [...lista].filter(f => f.type.startsWith('image/'));
      if (!imagenes.length) return;
      for (let i = 0; i < imagenes.length; i++) {
        if (estado) estado.textContent = `Subiendo ${i + 1} de ${imagenes.length}…`;
        try { await subirImagen(imagenes[i]); }
        catch (ex) { alert(`${imagenes[i].name}: ${ex.message}`); }
      }
      if (estado) estado.textContent = '';
      location.reload();
    };

    zona.addEventListener('click', () => archivo?.click());
    archivo?.addEventListener('change', () => subirVarias(archivo.files));
    zona.addEventListener('dragover', (e) => { e.preventDefault(); zona.classList.add('is-arrastrando'); });
    zona.addEventListener('dragleave', () => zona.classList.remove('is-arrastrando'));
    zona.addEventListener('drop', (e) => {
      e.preventDefault();
      zona.classList.remove('is-arrastrando');
      subirVarias(e.dataTransfer?.files || []);
    });

    document.querySelectorAll('[data-copiar-ruta]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(btn.dataset.copiarRuta);
          const orig = btn.textContent;
          btn.textContent = '✓ Copiada';
          setTimeout(() => { btn.textContent = orig; }, 1400);
        } catch {
          window.prompt('Copia la ruta:', btn.dataset.copiarRuta);
        }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    iniciarEditores();
    iniciarSelectoresImagen();
    iniciarListas();
    iniciarBiblioteca();
  });
})();
