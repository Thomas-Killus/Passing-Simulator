// Beat timeline with a playhead, plus the causal diagram drawn over it.
// Causal arrow: a throw of height h at beat t forces a throw at beat t+h-2
// in the hand that catches it.

const LEFT = 74;
const WINDOW = 14;          // beats visible at once
const COLORS = {
  pass: '#6fd3c7',        // line pass: right hand to the partner's left
  cross: '#e07ba8',       // cross pass: stays on a side, right to right
  self: '#8b95a7', zip: '#b58ce8', hold: '#e8b563',
};

export class Timeline {
  constructor(canvas, doc) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.doc = doc;
    this.ids = doc.jugglers.map((j) => j.id);
    this.showCausal = true;
    this.byKey = new Map();
    for (const e of doc.events) this.byKey.set(`${e.juggler}/${e.beat}`, e);
    this.resize();
  }

  resize() {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = Math.max(1, rect.width * dpr);
    this.canvas.height = Math.max(1, rect.height * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.w = rect.width;
    this.h = rect.height;
  }

  draw(t) {
    const { ctx, w, h } = this;
    ctx.clearRect(0, 0, w, h);
    ctx.font = '12px ui-monospace, SFMono-Regular, Menlo, monospace';
    ctx.textBaseline = 'middle';

    const start = Math.max(0, Math.floor(t) - Math.floor(WINDOW / 3));
    const PAD = 26;   // keep the first beat's box clear of the row labels
    const step = (w - LEFT - PAD - 16) / WINDOW;
    const rows = this.ids.length;
    const rowH = Math.min(58, Math.max(30, (h - 44) / rows));
    const top = 22 + (h - 22 - rows * rowH) / 2;
    const x = (beat) => LEFT + PAD + (beat - start) * step;
    const y = (i) => top + rowH / 2 + i * rowH;
    this.rowY = y;
    this.beatX = x;

    // beat gridlines
    ctx.strokeStyle = '#242b36';
    ctx.fillStyle = '#5c6676';
    ctx.lineWidth = 1;
    for (let b = start; b <= start + WINDOW; b += 1) {
      const px = Math.round(x(b)) + 0.5;
      ctx.beginPath();
      ctx.moveTo(px, 16);
      ctx.lineTo(px, y(this.ids.length - 1) + 16);
      ctx.stroke();
      ctx.textAlign = 'center';
      ctx.fillText(String(b), px, 10);
    }

    if (this.showCausal) this.drawCausal(start, x, y);

    // row baselines
    this.ids.forEach((id, i) => {
      ctx.strokeStyle = '#242b36';
      ctx.beginPath();
      ctx.moveTo(LEFT, Math.round(y(i)) + 0.5);
      ctx.lineTo(w - 16, Math.round(y(i)) + 0.5);
      ctx.stroke();
    });

    // throws
    ctx.textAlign = 'center';
    for (const e of this.doc.events) {
      if (e.beat < start - 1 || e.beat > start + WINDOW + 1) continue;
      const i = this.ids.indexOf(e.juggler);
      const kind = e.target ? (e.line ? 'pass' : 'cross')
                            : (e.height === 1 ? 'zip' : e.height === 2 ? 'hold' : 'self');
      const px = x(e.beat);
      const py = y(i);
      ctx.fillStyle = '#12151b';
      ctx.strokeStyle = COLORS[kind];
      ctx.lineWidth = e.target ? 1.6 : 1;
      roundRect(ctx, px - 19, py - 11, 38, 22, 5);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = COLORS[kind];
      ctx.fillText(e.throw, px, py);
      ctx.fillStyle = '#4d5666';
      ctx.font = '9px ui-monospace, monospace';
      ctx.fillText(e.hand, px, py - 17);
      ctx.font = '12px ui-monospace, SFMono-Regular, Menlo, monospace';
    }

    // row labels last, so a throw on the first visible beat cannot cover them
    ctx.fillStyle = '#12151b';
    ctx.fillRect(0, 0, LEFT - 8, h);
    ctx.fillStyle = '#8b95a7';
    ctx.textAlign = 'right';
    ctx.font = '13px ui-sans-serif, system-ui, sans-serif';
    this.ids.forEach((id, i) => ctx.fillText(id, LEFT - 20, y(i)));
    ctx.font = '12px ui-monospace, SFMono-Regular, Menlo, monospace';

    // playhead
    const px = x(t);
    ctx.strokeStyle = '#e8b563';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(px, 14);
    ctx.lineTo(px, y(this.ids.length - 1) + 18);
    ctx.stroke();
  }

  drawCausal(start, x, y) {
    const ctx = this.ctx;
    ctx.lineWidth = 1;
    for (const e of this.doc.events) {
      const to = e.land_beat - 2;
      if (e.beat < start - 2 || e.beat > start + WINDOW + 1) continue;
      const i = this.ids.indexOf(e.juggler);
      const j = this.ids.indexOf(e.land_juggler);
      const x0 = x(e.beat);
      const x1 = x(to);
      const y0 = y(i);
      const y1 = y(j);
      const isPass = e.juggler !== e.land_juggler;
      ctx.strokeStyle = !isPass ? 'rgba(110,122,142,.35)'
        : e.line ? 'rgba(111,211,199,.45)' : 'rgba(224,123,168,.45)';
      const lift = isPass ? 0 : -24;
      ctx.beginPath();
      ctx.moveTo(x0, y0 + (isPass ? (y1 > y0 ? 12 : -12) : -12));
      ctx.bezierCurveTo(x0 + (x1 - x0) * 0.3, y0 + lift * 1.2,
                        x1 - (x1 - x0) * 0.3, y1 + lift * 1.2,
                        x1, y1 + (isPass ? (y1 > y0 ? -12 : 12) : -12));
      ctx.stroke();
      arrowHead(ctx, x1, y1 + (isPass ? (y1 > y0 ? -12 : 12) : -12), x1 > x0 ? 1 : -1);
    }
  }
}

function arrowHead(ctx, x, y, dir) {
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x - 5 * dir, y - 4);
  ctx.moveTo(x, y);
  ctx.lineTo(x - 5 * dir, y + 4);
  ctx.stroke();
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}
