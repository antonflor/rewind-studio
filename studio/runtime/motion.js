// Deterministic, seekable motion for one slide, used for video export:
//   __motion.setup(slideId, duration) -> { animEnd, outroStart, events }
//   __motion.seek(t)  // t in seconds from the start of the slide
// [data-m] elements fade up in document order; [data-target] numbers count up; .bar > i grows.
// A style can tune it with CSS custom properties on .slide:
//   --m-step (seconds between elements), --m-rise (px), --m-fade (seconds), --m-mode (fade | type)
(() => {
  const clamp = (x) => Math.max(0, Math.min(1, x));
  const ease = { out: (x) => 1 - Math.pow(1 - x, 3), quart: (x) => 1 - Math.pow(1 - x, 4),
                 inOut: (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2) };
  const prog = (t, s, d) => clamp((t - s) / d);
  let st = null;

  function cssNum(el, name, dflt) {
    const v = parseFloat(getComputedStyle(el).getPropertyValue(name));
    return Number.isNaN(v) ? dflt : v;
  }

  function setup(id, duration) {
    const slide = document.querySelector(`.slide[data-slide="${id}"]`);
    window.__show(id);
    const step = cssNum(slide, '--m-step', 0.13), rise = cssNum(slide, '--m-rise', 28), fade = cssNum(slide, '--m-fade', 0.7);
    const mode = getComputedStyle(slide).getPropertyValue('--m-mode').trim() || 'fade';
    const fades = [], counts = [], bars = [], events = [];
    const blocks = [...slide.querySelectorAll('[data-m]')].filter((el) => !el.parentElement.closest('[data-m]') || true);
    let t0 = 0.15;
    blocks.forEach((el) => {
      // a block nested in another block starts with a small offset after its parent
      fades.push({ el, start: t0 });
      events.push({ t: t0, kind: 'block' });
      el.querySelectorAll('[data-target]').forEach((c) => {
        if (c.closest('[data-m]') !== el) return;
        const txt = c.textContent.trim();
        const decimals = (txt.split('.')[1] || '').replace(/\D/g, '').length;
        const big = c.hasAttribute('data-big');
        counts.push({ el: c, start: t0 + 0.1, dur: big ? 1.5 : 1.2, target: Number(c.dataset.target), decimals, big });
        events.push({ t: t0 + 0.1 + (big ? 1.5 : 1.2), kind: big ? 'land-big' : 'land' });
      });
      el.querySelectorAll('.bar').forEach((b) => {
        if (b.closest('[data-m]') !== el) return;
        bars.push({ el: b, start: t0 + 0.3 });
      });
      t0 += step;
    });
    const animEnd = Math.max(t0, ...fades.map((f) => f.start + fade), ...counts.map((c) => c.start + c.dur), ...bars.map((b) => b.start + 1.0));
    const outroStart = duration - 0.45;
    st = { slide, fades, counts, bars, rise, fade, mode, outroStart };
    return { animEnd, outroStart, events };
  }

  const fmt = (v, d) => v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });

  function seek(t) {
    const { slide, fades, counts, bars, rise, fade, mode, outroStart } = st;
    fades.forEach(({ el, start }) => {
      const p = mode === 'type' ? (t >= start ? 1 : 0) : ease.out(prog(t, start, fade));
      el.style.opacity = p;
      el.style.transform = mode === 'type' ? '' : `translateY(${((1 - p) * rise).toFixed(2)}px)`;
    });
    counts.forEach((c) => { c.el.textContent = fmt(c.target * ease.quart(prog(t, c.start, c.dur)), c.decimals); });
    bars.forEach((b) => { b.el.style.setProperty('--grow', ease.inOut(prog(t, b.start, 1.0)).toFixed(4)); });
    slide.style.opacity = 1 - ease.inOut(prog(t, outroStart, 0.45));
  }

  window.__motion = { setup, seek };
})();
