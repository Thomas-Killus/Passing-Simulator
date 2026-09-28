import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

import { clubSpin, clubState, handPosition } from './motion.js';
import { Timeline } from './timeline.js';

const doc = await (await fetch('pattern.json')).json();
const jugglers = Object.fromEntries(doc.jugglers.map((j) => [j.id, j]));

document.getElementById('title').textContent =
  `${doc.name} — ${doc.report.clubs} clubs, ${doc.jugglers.length} jugglers, period ${doc.period}`;
renderReport();

// ---------------------------------------------------------------- scene setup
const host = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(2, window.devicePixelRatio));
host.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x12151b);
scene.fog = new THREE.Fog(0x12151b, 14, 44);

const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 200);
camera.up.set(0, 0, 1);

const centre = new THREE.Vector3(
  average(doc.jugglers.map((j) => j.pos[0])),
  average(doc.jugglers.map((j) => j.pos[1])),
  1.2);
const spread = Math.max(2, ...doc.jugglers.map(
  (j) => Math.hypot(j.pos[0] - centre.x, j.pos[1] - centre.y)));
// look in from the side and a little above, so jugglers standing opposite each
// other do not hide behind one another
const back = spread * 1.05 + 2.9;
const lift = doc.jugglers.length > 2 ? 0.8 : 0.42;   // look down into a circle
camera.position.set(centre.x + back * 0.86, centre.y - back * 0.5, back * lift);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.copy(centre);
controls.enableDamping = true;

scene.add(new THREE.HemisphereLight(0xcfe3ff, 0x1b1f27, 1.5));
const key = new THREE.DirectionalLight(0xffffff, 1.4);
key.position.set(4, -6, 9);
scene.add(key);

const grid = new THREE.GridHelper(24, 24, 0x2e3745, 0x1d232c);
grid.rotation.x = Math.PI / 2;
grid.position.set(centre.x, centre.y, 0);
scene.add(grid);

// ------------------------------------------------------------------ jugglers
const handMeshes = {};
for (const j of doc.jugglers) {
  const body = new THREE.Group();
  body.position.set(j.pos[0], j.pos[1], 0);

  const torso = new THREE.Mesh(
    new THREE.CapsuleGeometry(0.17, 0.72, 4, 12),
    new THREE.MeshStandardMaterial({ color: 0x38414f, roughness: 0.85 }));
  torso.rotation.x = Math.PI / 2;
  torso.position.z = 0.78;
  body.add(torso);

  const head = new THREE.Mesh(
    new THREE.SphereGeometry(0.13, 20, 14),
    new THREE.MeshStandardMaterial({ color: 0x4c586a, roughness: 0.8 }));
  head.position.z = 1.45;
  body.add(head);

  // a wedge on the chest so you can see which way they face
  const nose = new THREE.Mesh(
    new THREE.ConeGeometry(0.07, 0.18, 4),
    new THREE.MeshStandardMaterial({ color: 0x6fd3c7 }));
  nose.position.set(j.facing[0] * 0.2, j.facing[1] * 0.2, 1.42);
  nose.quaternion.setFromUnitVectors(
    new THREE.Vector3(0, 1, 0), new THREE.Vector3(j.facing[0], j.facing[1], 0));
  body.add(nose);

  body.add(makeLabel(j.id));
  scene.add(body);

  handMeshes[j.id] = {};
  for (const hand of ['R', 'L']) {
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.055, 14, 10),
      new THREE.MeshStandardMaterial({ color: hand === 'R' ? 0xe8b563 : 0x9aa6b8 }));
    scene.add(mesh);
    handMeshes[j.id][hand] = mesh;
  }
}

// --------------------------------------------------------------------- clubs
const clubMeshes = doc.clubs.map((club) => {
  const colour = new THREE.Color().setHSL((club.id * 0.618) % 1, 0.62, 0.62);
  const group = new THREE.Group();
  const handle = new THREE.Mesh(
    new THREE.CylinderGeometry(0.012, 0.018, 0.22, 10),
    new THREE.MeshStandardMaterial({ color: 0xdfe5ee, roughness: 0.6 }));
  handle.position.y = -0.14;
  const bulb = new THREE.Mesh(
    new THREE.CylinderGeometry(0.052, 0.022, 0.26, 12),
    new THREE.MeshStandardMaterial({ color: colour, roughness: 0.45 }));
  bulb.position.y = 0.12;
  group.add(handle, bulb);
  scene.add(group);
  return group;
});

const trailGroup = new THREE.Group();
scene.add(trailGroup);

// ------------------------------------------------------------------ controls
const timeline = new Timeline(document.getElementById('timeline'), doc);
const ui = {
  play: document.getElementById('play'),
  back: document.getElementById('back'),
  fwd: document.getElementById('fwd'),
  speed: document.getElementById('speed'),
  speedout: document.getElementById('speedout'),
  clock: document.getElementById('clock'),
  causal: document.getElementById('showcausal'),
  trails: document.getElementById('trails'),
};

let beat = 0;
let playing = true;
let speed = Number(ui.speed.value);

ui.play.onclick = () => {
  playing = !playing;
  ui.play.textContent = playing ? '❚❚' : '▶';
};
ui.back.onclick = () => { beat = Math.max(0, beat - 1); draw(); };
ui.fwd.onclick = () => { beat = Math.min(lastBeat(), beat + 1); draw(); };
ui.speed.oninput = () => {
  speed = Number(ui.speed.value);
  ui.speedout.textContent = `${speed.toFixed(2)}×`;
};
ui.causal.onchange = () => { timeline.showCausal = ui.causal.checked; };
ui.trails.onchange = () => { trailGroup.visible = ui.trails.checked; rebuildTrails(); };
window.addEventListener('keydown', (e) => {
  if (e.code === 'Space') { e.preventDefault(); ui.play.click(); }
  if (e.code === 'ArrowLeft') ui.back.click();
  if (e.code === 'ArrowRight') ui.fwd.click();
});

ui.play.textContent = '❚❚';
ui.speedout.textContent = `${speed.toFixed(2)}×`;
trailGroup.visible = false;
rebuildTrails();

window.addEventListener('resize', resize);
new ResizeObserver(resize).observe(host);
new ResizeObserver(() => timeline.resize()).observe(document.getElementById('panel'));
resize();

let previous = performance.now();
renderer.setAnimationLoop((now) => {
  const dt = Math.min(0.1, (now - previous) / 1000);
  previous = now;
  if (playing) {
    beat += (dt / doc.beat) * speed;
    if (beat > lastBeat()) beat = doc.loop_start;
  }
  draw();
});

function draw() {
  for (const j of doc.jugglers) {
    for (const hand of ['R', 'L']) {
      const p = handPosition(j, hand, beat);
      handMeshes[j.id][hand].position.set(p[0], p[1], p[2]);
    }
  }

  doc.clubs.forEach((club, i) => {
    const state = clubState(club, beat, doc.gravity, jugglers);
    const mesh = clubMeshes[i];
    mesh.position.set(state.pos[0], state.pos[1], state.pos[2]);
    orientClub(mesh, state);
  });

  controls.update();
  renderer.render(scene, camera);
  timeline.draw(beat);
  ui.clock.textContent = `beat ${beat.toFixed(2)}`;
}

const UP = new THREE.Vector3(0, 0, 1);
const axis = new THREE.Vector3();

function orientClub(mesh, state) {
  const f = state.flight;
  if (!f || state.inHand || f.spin === 0) {
    mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), UP);
    return;
  }
  const spin = clubSpin(f, state.progress);
  axis.set(spin.axis[0], spin.axis[1], spin.axis[2]);
  const angle = spin.angle;
  const up = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), UP);
  mesh.quaternion.setFromAxisAngle(axis, angle).multiply(up);
}

function rebuildTrails() {
  trailGroup.clear();
  if (!trailGroup.visible) return;
  const window_ = doc.loop_start + doc.period * 2;
  for (const club of doc.clubs) {
    for (const f of club.flights) {
      if (f.t0 > window_ || f.kind === 'hold') continue;
      const points = [];
      for (let s = 0; s <= 24; s += 1) {
        const t = f.t0 + (f.t1 - f.t0) * (s / 24);
        points.push(new THREE.Vector3(...clubState(club, t, doc.gravity, jugglers).pos));
      }
      const colour = new THREE.Color().setHSL((club.id * 0.618) % 1, 0.6, 0.5);
      trailGroup.add(new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(points),
        new THREE.LineBasicMaterial({ color: colour, transparent: true, opacity: 0.35 })));
    }
  }
}

function makeLabel(text) {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 128;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#dfe5ee';
  ctx.font = 'bold 76px ui-sans-serif, system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, 64, 68);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
    map: new THREE.CanvasTexture(canvas), transparent: true, depthTest: false,
  }));
  sprite.scale.set(0.45, 0.45, 0.45);
  sprite.position.z = 1.95;
  return sprite;
}

function renderReport() {
  const r = doc.report;
  const bits = [];
  bits.push(r.ok
    ? `<span class="ok">valid</span>`
    : `<span class="bad">${r.errors.length} error(s)</span>`);
  bits.push(r.loop_closes
    ? `<span class="ok">loop closes</span>`
    : `<span class="warn">loop does not close</span>`);
  for (const e of r.errors) bits.push(`<span class="bad">${escapeHtml(e)}</span>`);
  for (const w of r.warnings) bits.push(`<span class="warn">${escapeHtml(w)}</span>`);
  document.getElementById('report').innerHTML = bits.join(' · ');
}

function escapeHtml(s) {
  return s.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
}

function resize() {
  const rect = host.getBoundingClientRect();
  renderer.setSize(rect.width, rect.height);
  camera.aspect = rect.width / Math.max(1, rect.height);
  camera.updateProjectionMatrix();
  timeline.resize();
}

function lastBeat() {
  return doc.horizon - 1;
}

function average(xs) {
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}
