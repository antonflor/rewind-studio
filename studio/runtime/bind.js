// Fills studio/base.html from window.REWIND (the display model built by studio/model.py).
// Text goes in with textContent only, so titles from a database can never inject markup.
(() => {
  const get = (obj, path) => path.split('.').reduce((acc, k) => (acc == null ? acc : acc[k]), obj);
  const truthy = (v) => !(v == null || v === false || v === '' || v === 0 || (Array.isArray(v) && v.length === 0));
  const ATTRS = '[data-k],[data-if],[data-unless],[data-css],[data-class],[data-count]';

  function apply(el, ctx) {
    const d = el.dataset;
    if (d.if !== undefined && !truthy(get(ctx, d.if))) { el.remove(); return; }
    if (d.unless !== undefined && truthy(get(ctx, d.unless))) { el.remove(); return; }
    if (d.k !== undefined) { const v = get(ctx, d.k); el.textContent = v == null ? '' : String(v); }
    if (d.css !== undefined) {
      d.css.split(';').filter(Boolean).forEach((pair) => {
        const [name, path] = pair.split(':').map((s) => s.trim());
        const v = get(ctx, path);
        if (v != null && v !== '') el.style.setProperty(name, String(v));
      });
    }
    if (d.class !== undefined) { const v = get(ctx, d.class); if (v) el.classList.add(...String(v).split(/\s+/)); }
    if (d.count !== undefined) { const v = Number(get(ctx, d.count)); if (!Number.isNaN(v)) el.dataset.target = String(v); }
    el.__bound = true;
  }

  function bindScope(node, ctx) {
    node.querySelectorAll('template[data-each]').forEach((tpl) => {
      if (tpl.__bound) return;
      const list = get(ctx, tpl.dataset.each) || [];
      list.forEach((it, i) => {
        const frag = tpl.content.cloneNode(true);
        bindScope(frag, Object.assign({}, ctx, { it, i }));
        frag.querySelectorAll('*').forEach((e) => { e.__bound = true; });
        tpl.parentNode.insertBefore(frag, tpl);
      });
      tpl.__bound = true;
      tpl.remove();
    });
    node.querySelectorAll(ATTRS).forEach((el) => { if (!el.__bound) apply(el, ctx); });
  }

  window.__bind = () => { bindScope(document, window.REWIND); document.body.dataset.ready = '1'; };
  // Shrink [--fit: 1] text until it fits on one line. Runs on a slide once it is shown (and laid out).
  function fit(slide) {
    slide.querySelectorAll('*').forEach((el) => {
      if (el.__fitted) return;
      const cs = getComputedStyle(el);
      if (cs.getPropertyValue('--fit').trim() !== '1') return;
      el.__fitted = true;
      let size = parseFloat(cs.fontSize);
      const min = size * 0.4;
      while (el.scrollWidth > el.clientWidth + 1 && size > min) {
        size *= 0.96;
        el.style.fontSize = `${size.toFixed(2)}px`;
      }
    });
  }

  window.__show = (id) => {
    document.querySelectorAll('.slide').forEach((s) => {
      const on = s.dataset.slide === id;
      s.classList.toggle('is-shown', on);
      if (on) fit(s);
    });
  };
})();
