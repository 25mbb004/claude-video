// ECLIPSE — dark cinematic cut of "Ray of Solar" (clip 0:58 → 1:13, local time 0–15s)
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const W = 1920, H = 1080;

// ---------- timing (from the beat analysis, clip-local seconds) ----------
const BUILD_END = 4.70;           // drum roll stops → silence
const DROP = 5.82;                // 1:03.82 in the song
const BEAT = 0.443;               // 136 BPM
const BAR = BEAT * 4;
const CUT_BLACK = DROP + BEAT * 19; // 14.24 — hard cut to black on a beat
const ROLL = [58.05,58.18,58.38,58.52,58.61,58.74,58.83,58.95,59.05,59.27,59.39,59.51,59.72,59.83,59.95,
  60.06,60.17,60.28,60.39,60.61,60.73,60.84,60.95,61.06,61.17,61.28,61.39,61.5,61.61,61.72,61.84,61.94,
  62.06,62.16,62.28,62.4,62.51,62.63].map(t => t - 58);
const KICKS = []; for (let k = DROP; k < 15.2; k += BEAT) KICKS.push(k);

const pulse = (t, hits, rate) => {
  let s = 0; for (const h of hits) if (t >= h) s += Math.exp(-(t - h) * rate); return Math.min(s, 1.6);
};
const sstep = (a, b, x) => { const t = Math.min(Math.max((x - a) / (b - a), 0), 1); return t * t * (3 - 2 * t); };
const lerp = (a, b, t) => a + (b - a) * t;
const hash = n => { const s = Math.sin(n * 127.1) * 43758.5453; return s - Math.floor(s); };

// ---------- renderer ----------
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000000);
const camera = new THREE.PerspectiveCamera(30, W / H, 0.1, 2000);
const SUN = new THREE.Vector3(0, 14, -300);

// ---------- sky + eclipse ----------
const skyU = { uPower: { value: 0.3 }, uEclipse: { value: 1 }, uTime: { value: 0 } };
const sky = new THREE.Mesh(new THREE.PlaneGeometry(2600, 1400), new THREE.ShaderMaterial({
  uniforms: skyU, depthWrite: false,
  vertexShader: `varying vec2 vP; void main(){ vP = (modelMatrix*vec4(position,1.)).xy; gl_Position = projectionMatrix*viewMatrix*modelMatrix*vec4(position,1.); }`,
  fragmentShader: `
    varying vec2 vP; uniform float uPower, uEclipse, uTime;
    void main(){
      vec2 p = vP - vec2(0., 14.);
      float d = length(p), R = 22.;
      vec3 base = mix(vec3(0.0,0.006,0.009), vec3(0.004,0.02,0.026), smoothstep(-60., 260., p.y));
      vec3 gold = vec3(1.0,0.58,0.22), white = vec3(1.0,0.9,0.75);
      float ring   = exp(-abs(d - R) / 1.1);
      float corona = exp(-max(d - R, 0.) / (5. + 11. * (1. - uEclipse)));
      float halo   = exp(-d / 110.) * 0.12 + exp(-d / 38.) * 0.5;
      float ang = atan(p.y, p.x);
      float spikes = pow(abs(sin(ang * 7. + uTime * 0.2)), 18.) * exp(-max(d - R, 0.) / 40.) * (1. - uEclipse);
      float streak = exp(-abs(p.y) / 1.6) * exp(-abs(p.x) / 520.);
      vec3 col = base + gold * uPower * (ring * 3.0 * uEclipse + corona * 1.4 + halo + spikes * 1.5)
               + gold * streak * uPower * (0.25 + 0.9 * (1. - uEclipse));
      float disk = 1. - smoothstep(R - 0.7, R + 0.7, d);
      col = mix(col, vec3(0.0), disk * uEclipse);
      col += disk * (1. - uEclipse) * white * uPower * 2.2;
      gl_FragColor = vec4(col, 1.);
    }`
}));
sky.position.set(0, 14, -320);
scene.add(sky);

// ---------- wet ground with sun reflection ----------
const groundU = { uPower: skyU.uPower, uTime: skyU.uTime };
const ground = new THREE.Mesh(new THREE.PlaneGeometry(1200, 700), new THREE.ShaderMaterial({
  uniforms: groundU,
  vertexShader: `varying vec3 vW; void main(){ vW = (modelMatrix*vec4(position,1.)).xyz; gl_Position = projectionMatrix*viewMatrix*vec4(vW,1.); }`,
  fragmentShader: `
    varying vec3 vW; uniform float uPower, uTime;
    float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233))) * 43758.5453); }
    float n(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
      return mix(mix(h(i),h(i+vec2(1,0)),f.x), mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x), f.y); }
    void main(){
      float far = clamp(-vW.z / 300., 0., 1.);
      float width = 1.2 + (-vW.z) * 0.07;
      float sheen = exp(-abs(vW.x) / width);
      float ripple = n(vec2(vW.x * 0.6, vW.z * 2.5 + uTime * 0.6)) * 0.7 + 0.3;
      vec3 gold = vec3(1.0,0.58,0.22);
      vec3 col = vec3(0.0,0.004,0.006) + gold * min(uPower, 1.1) * sheen * ripple * (0.02 + 0.7 * far * far * far);
      col += vec3(0.0,0.01,0.014) * far;
      gl_FragColor = vec4(col, 1.);
    }`
}));
ground.rotation.x = -Math.PI / 2;
ground.position.set(0, 0, -300);
scene.add(ground);

// ---------- volumetric-ish fog layers (lit near the sun) ----------
const sunNdc = new THREE.Vector2();
const fogMats = [];
for (const [z, op, sc] of [[-12, 0.35, 0.35], [-35, 0.55, 0.12], [-90, 0.7, 0.05], [-190, 0.8, 0.025]]) {
  const m = new THREE.ShaderMaterial({
    uniforms: { uPower: skyU.uPower, uTime: skyU.uTime, uSun: { value: sunNdc }, uOp: { value: op }, uSc: { value: sc }, uRes: { value: new THREE.Vector2(W, H) } },
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: `varying vec3 vW; void main(){ vW=(modelMatrix*vec4(position,1.)).xyz; gl_Position=projectionMatrix*viewMatrix*vec4(vW,1.); }`,
    fragmentShader: `
      varying vec3 vW; uniform float uPower, uTime, uOp, uSc; uniform vec2 uSun, uRes;
      float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233))) * 43758.5453); }
      float n(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
        return mix(mix(h(i),h(i+vec2(1,0)),f.x), mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x), f.y); }
      float fbm(vec2 p){ float s=0., a=.5; for(int i=0;i<5;i++){ s+=a*n(p); p*=2.03; a*=.5; } return s; }
      void main(){
        vec2 q = vW.xy * uSc + vec2(uTime * 0.05, 0.);
        float f = fbm(q + fbm(q * 1.7 - uTime * 0.03));
        f = smoothstep(0.35, 0.9, f);
        float hfall = exp(-max(vW.y, 0.) / 9.);
        vec2 sc = (gl_FragCoord.xy / uRes) * 2. - 1.;
        float d = length((sc - uSun) * vec2(uRes.x / uRes.y, 1.));
        float lit = 0.04 + 0.75 * exp(-d * 3.2) * min(uPower, 1.2);
        vec3 col = mix(vec3(0.05,0.16,0.18), vec3(1.0,0.6,0.25), exp(-d * 2.5)) * f * lit * hfall * uOp;
        gl_FragColor = vec4(col, 1.);
      }`
  });
  fogMats.push(m);
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(900, 120), m);
  mesh.position.set(0, 40, z);
  mesh.renderOrder = 5;
  scene.add(mesh);
}

// ---------- drifting dust motes ----------
const N = 1800, pos = new Float32Array(N * 3), sz = new Float32Array(N);
for (let i = 0; i < N; i++) {
  pos[i * 3] = (hash(i + 1) - 0.5) * 60; pos[i * 3 + 1] = hash(i + 7) * 9; pos[i * 3 + 2] = -55 + hash(i + 13) * 65;
  sz[i] = 0.4 + hash(i + 29) * 1.6;
}
const dustG = new THREE.BufferGeometry();
dustG.setAttribute('position', new THREE.BufferAttribute(pos, 3));
dustG.setAttribute('aSize', new THREE.BufferAttribute(sz, 1));
const dust = new THREE.Points(dustG, new THREE.ShaderMaterial({
  uniforms: { uPower: skyU.uPower, uTime: skyU.uTime, uSun: { value: sunNdc }, uWind: { value: 0 } },
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  vertexShader: `
    attribute float aSize; uniform float uTime, uWind; uniform vec2 uSun; varying float vLit;
    void main(){
      vec3 p = position;
      p.x = mod(p.x + uTime * 0.6 * (0.5 + aSize * 0.4) + 30., 60.) - 30.;
      p.z = mod(p.z + 55. + uTime * uWind * (0.6 + aSize * 0.3), 65.) - 55.;
      p.y += sin(uTime * 0.7 + position.x) * 0.25;
      vec4 mv = modelViewMatrix * vec4(p, 1.);
      gl_Position = projectionMatrix * mv;
      vec2 ndc = gl_Position.xy / gl_Position.w;
      vLit = exp(-length((ndc - uSun) * vec2(1.78, 1.)) * 1.6);
      gl_PointSize = clamp(aSize * 70. / -mv.z, 1., 14.);
    }`,
  fragmentShader: `
    uniform float uPower; varying float vLit;
    void main(){ float d = length(gl_PointCoord - .5); float a = smoothstep(.5, .0, d);
      gl_FragColor = vec4(vec3(1.0,0.62,0.28) * a * (0.04 + vLit * 0.8) * uPower, 1.); }`
}));
dust.renderOrder = 6;
scene.add(dust);

// ---------- silhouettes (2D canvas → texture on a plane) ----------
function limb(ctx, a, b, w) { ctx.lineWidth = w; ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); }
const at = (j, ang, L) => [j[0] + L * Math.sin(ang), j[1] + L * Math.cos(ang)];

// lone figure in a long coat, facing right. run: 0 = standing, 1 = full sprint
function drawFigure(ctx, cx, groundY, s, p, run, opt = {}) {
  const lean = opt.lean ?? 0.28 * run;
  const legs = [p, p + Math.PI].map(ph => {
    const thigh = run * 0.85 * Math.sin(ph) + (1 - run) * 0.13 * (ph === p ? 1 : -1);
    const knee = run * (0.15 + 1.35 * Math.max(0, Math.cos(ph))) + (1 - run) * 0.05;
    return { thigh, shin: thigh - knee };
  });
  const L1 = 108 * s, L2 = 112 * s;
  let hip = [0, 0];
  const feet = legs.map(l => at(at(hip, l.thigh, L1), l.shin, L2));
  const drop = groundY - Math.max(feet[0][1], feet[1][1]) - run * 10 * s * Math.abs(Math.sin(p));
  hip = [cx, drop];
  const sh = [hip[0] + 150 * s * Math.sin(lean), hip[1] - 150 * s * Math.cos(lean)];
  const head = [sh[0] + 46 * s * Math.sin(lean + 0.1), sh[1] - 46 * s * Math.cos(lean + 0.1)];
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  // coat tail blowing back
  const wind = opt.wind ?? (0.35 + run);
  ctx.beginPath();
  ctx.moveTo(sh[0] - 6 * s, sh[1] + 8 * s);
  const tailX = hip[0] - (40 + 110 * wind) * s, tailY = hip[1] + (70 - 30 * wind) * s;
  ctx.bezierCurveTo(sh[0] - 40 * s * wind, sh[1] + 60 * s, tailX + 30 * s * Math.sin(p * 2), tailY - 40 * s, tailX, tailY + 12 * s * Math.sin(p * 2 + 1));
  ctx.lineTo(hip[0] + 8 * s, hip[1] + 40 * s);
  ctx.lineTo(sh[0] + 22 * s, sh[1] + 10 * s);
  ctx.closePath(); ctx.fill();
  // legs
  for (const l of legs) {
    const k = at(hip, l.thigh, L1), f = at(k, l.shin, L2);
    limb(ctx, hip, k, 34 * s); limb(ctx, k, f, 26 * s);
    limb(ctx, f, [f[0] + 24 * s, f[1] + 2 * s], 14 * s);
  }
  // torso
  limb(ctx, hip, sh, 58 * s);
  limb(ctx, sh, head, 20 * s);
  ctx.beginPath(); ctx.arc(head[0], head[1], 27 * s, 0, Math.PI * 2); ctx.fill();
  // arms
  [p + Math.PI, p].forEach((ph, i) => {
    const up = opt.reins ? 0.9 + i * 0.15 : run * 0.95 * Math.sin(ph) + (1 - run) * (i ? 0.2 : -0.12);
    const bend = opt.reins ? 0.35 : 0.1 + run * 1.35;
    const e = at(sh, up, 78 * s), hnd = at(e, up + bend, 74 * s);
    limb(ctx, sh, e, 21 * s); limb(ctx, e, hnd, 17 * s);
    if (opt.reins && i === 1) { ctx.lineWidth = 3 * s; ctx.beginPath(); ctx.moveTo(hnd[0], hnd[1]); ctx.lineTo(opt.reins[0], opt.reins[1]); ctx.stroke(); }
  });
}

function drawHorse(ctx, x, gy, s, p) {
  const bob = 7 * s * Math.sin(p * 2);
  const by = gy - 150 * s + bob;
  ctx.lineCap = 'round';
  const ell = (cx, cy, rx, ry, r = 0) => { ctx.beginPath(); ctx.ellipse(cx, cy, rx, ry, r, 0, Math.PI * 2); ctx.fill(); };
  ell(x, by, 100 * s, 40 * s); ell(x + 72 * s, by - 2 * s, 46 * s, 46 * s); ell(x - 70 * s, by - 6 * s, 50 * s, 46 * s);
  // neck + head
  const hb = 10 * s * Math.sin(p * 2 + 0.8);
  ctx.beginPath();
  ctx.moveTo(x + 60 * s, by - 35 * s); ctx.lineTo(x + 128 * s, by - 118 * s + hb); ctx.lineTo(x + 150 * s, by - 95 * s + hb);
  ctx.lineTo(x + 112 * s, by + 18 * s); ctx.closePath(); ctx.fill();
  ell(x + 165 * s, by - 92 * s + hb, 44 * s, 17 * s, 0.75);
  ctx.beginPath(); ctx.moveTo(x + 132 * s, by - 120 * s + hb); ctx.lineTo(x + 140 * s, by - 146 * s + hb); ctx.lineTo(x + 148 * s, by - 116 * s + hb); ctx.fill();
  // mane + tail streaming back
  ctx.strokeStyle = ctx.fillStyle;
  for (let i = 0; i < 5; i++) {
    ctx.lineWidth = 6 * s; ctx.beginPath();
    const mx = x + (125 - i * 15) * s, my = by - (112 - i * 17) * s + hb;
    ctx.moveTo(mx, my); ctx.quadraticCurveTo(mx - 20 * s, my - 6 * s, mx - (40 + 8 * Math.sin(p * 2 + i)) * s, my + 4 * s); ctx.stroke();
  }
  ctx.lineWidth = 16 * s; ctx.beginPath(); ctx.moveTo(x - 112 * s, by - 20 * s);
  ctx.quadraticCurveTo(x - 160 * s, by - 40 * s + 10 * s * Math.sin(p * 2), x - 205 * s, by + (10 + 14 * Math.sin(p * 2 + 1)) * s); ctx.stroke();
  // galloping legs
  [[72, 0], [60, 0.55], [-72, 2.7], [-60, 3.2]].forEach(([ox, ph], i) => {
    const front = i < 2, a = p + ph;
    const up = 0.75 * Math.sin(a);
    const flex = front ? -(0.2 + 1.3 * Math.max(0, Math.sin(a + 1.3))) : (0.15 + 1.0 * Math.max(0, Math.sin(a - 1.2)));
    const j = [x + ox * s, by + 22 * s], k = at(j, up, 62 * s), f = at(k, up + flex, 72 * s);
    limb(ctx, j, k, 22 * s); limb(ctx, k, f, 13 * s); limb(ctx, f, [f[0] + 8 * s, f[1] + 3 * s], 15 * s);
  });
}

function drawChariot(ctx, p, wheelA) {
  const gy = 500;
  drawHorse(ctx, 1060, gy - 6, 1.15, p + 0.7);
  drawHorse(ctx, 1150, gy, 1.2, p);
  // pole + cart
  ctx.lineCap = 'round'; ctx.lineWidth = 11; ctx.beginPath(); ctx.moveTo(600, 380); ctx.lineTo(1000, 340); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(400, 300); ctx.quadraticCurveTo(470, 425, 600, 412); ctx.quadraticCurveTo(650, 360, 640, 280);
  ctx.quadraticCurveTo(560, 330, 400, 300); ctx.fill();
  // wheel
  const wc = [500, gy - 100], R = 100;
  ctx.lineWidth = 13; ctx.beginPath(); ctx.arc(wc[0], wc[1], R, 0, Math.PI * 2); ctx.stroke();
  ctx.lineWidth = 6;
  for (let i = 0; i < 8; i++) { const a = wheelA + i * Math.PI / 4; limb(ctx, wc, [wc[0] + R * Math.cos(a), wc[1] + R * Math.sin(a)], 6); }
  ctx.beginPath(); ctx.arc(wc[0], wc[1], 18, 0, Math.PI * 2); ctx.fill();
  // rider braced, reins to the lead horse
  drawFigure(ctx, 520, 402, 0.82, p, 0.15, { lean: 0.42, wind: 1.6, reins: [1290, 300] });
}

function makeSil(cw, ch, ww) {
  const c = document.createElement('canvas'); c.width = cw; c.height = ch;
  const tex = new THREE.CanvasTexture(c);
  const m = new THREE.Mesh(new THREE.PlaneGeometry(ww, ww * ch / cw),
    new THREE.MeshBasicMaterial({ map: tex, color: 0x000000, transparent: true, depthWrite: false, toneMapped: false }));
  m.renderOrder = 7;
  scene.add(m);
  return { c, ctx: c.getContext('2d'), tex, m, ww, hh: ww * ch / cw };
}
const fig = makeSil(512, 512, 2.0);
const char = makeSil(1536, 512, 6.0);
function place(s, x, z) { s.m.position.set(x, s.hh / 2 - (s.hh * 12 / 512), z); }

// ---------- post: god rays → bloom → film grade → output ----------
const composer = new EffectComposer(renderer);
composer.setPixelRatio(1); composer.setSize(W, H);
composer.addPass(new RenderPass(scene, camera));
const rays = new ShaderPass({
  uniforms: { tDiffuse: { value: null }, uSun: { value: new THREE.Vector2(.5, .5) }, uHor: { value: .5 }, uExposure: { value: .6 }, uDensity: { value: .92 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform vec2 uSun; uniform float uHor, uExposure, uDensity; varying vec2 vUv;
    void main(){
      const int S = 72;
      vec2 d = (vUv - uSun) * uDensity / float(S), c = vUv;
      vec3 acc = vec3(0.); float il = 1.;
      for (int i = 0; i < S; i++) { c -= d; vec3 s = texture2D(tDiffuse, c).rgb; acc += min(max(s - 0.62, 0.), vec3(1.2)) * il * 0.034; il *= 0.972; }
      float above = mix(0.12, 1., smoothstep(uHor - 0.06, uHor + 0.005, vUv.y));
      gl_FragColor = vec4(texture2D(tDiffuse, vUv).rgb + acc * uExposure * above, 1.);
    }`
});
composer.addPass(rays);
const bloom = new UnrealBloomPass(new THREE.Vector2(W, H), 0.6, 0.6, 0.86);
composer.addPass(bloom);
const grade = new ShaderPass({
  uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uGrain: { value: .1 }, uFlash: { value: 0 }, uWhite: { value: 0 },
    uBlack: { value: 0 }, uAberr: { value: .002 }, uFlicker: { value: .06 }, uScratch: { value: 0 }, uRes: { value: new THREE.Vector2(W, H) } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform float uTime, uGrain, uFlash, uWhite, uBlack, uAberr, uFlicker, uScratch; uniform vec2 uRes; varying vec2 vUv;
    float h(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
    void main(){
      vec2 dir = vUv - .5;
      vec3 col = vec3(texture2D(tDiffuse, vUv + dir * uAberr).r, texture2D(tDiffuse, vUv).g, texture2D(tDiffuse, vUv - dir * uAberr).b);
      float l = dot(col, vec3(.299,.587,.114));
      col *= vec3(1.04, 0.97, 0.88);
      col += vec3(0., .014, .02) * (1. - smoothstep(0., .35, l));
      col *= mix(1., smoothstep(1.05, .3, length(dir * vec2(1.25, 1.))), .8);
      float fr = floor(uTime * 24.);
      col *= 1. + (h(vec2(fr, 3.)) - .5) * uFlicker;
      float xs = h(vec2(fr, 9.));
      col += vec3(.8,.7,.55) * uScratch * step(.55, h(vec2(fr, 5.))) * smoothstep(.0012, 0., abs(vUv.x - xs)) * (.4 + .6 * h(vec2(floor(vUv.y * 40.), fr)));
      col = mix(col, vec3(1., .97, .92), uWhite);
      col = mix(col, vec3(1., .96, .9), clamp(uFlash, 0., 1.));
      col *= 1. - uBlack;
      col += (h(gl_FragCoord.xy + fr * 113.7) - .5) * uGrain * (1. - uBlack);
      float bar = (1. - (16./9.) / 2.39) * .5;
      if (vUv.y < bar || vUv.y > 1. - bar) col = vec3(0.);
      gl_FragColor = vec4(clamp(col, 0., 1.), 1.);
    }`
});
composer.addPass(new OutputPass());
composer.addPass(grade);

// ---------- direction ----------
const l1 = document.getElementById('l1'), l2 = document.getElementById('l2');
const look = new THREE.Vector3();

window.renderAt = (t) => {
  const roll = t < BUILD_END ? pulse(t, ROLL, 16) : 0;
  const kick = t >= DROP ? pulse(t, KICKS, 8) : 0;
  const drop = t >= DROP;
  let power, eclipse = 1, flash = 0, white = 0, black = 0, grain = .06, godEx = .55, bloomS = .55, aberr = .002, scratch = 0, wind = 0;
  let figOn = false, charOn = false, run = 0, figX = -0.9, figZ = -4, charX = 0, charZ = -6;
  const cam = new THREE.Vector3(); look.set(0, 8, -300); let fov = 30;
  const runPhase = Math.PI * (t - DROP) / BEAT;      // one stride per beat
  const gallop = 2 * Math.PI * t / (BEAT * 1.0);     // one gallop cycle per beat

  if (t < BUILD_END) {                                // SHOT 1 — the build: slow push toward the black sun
    const u = t / BUILD_END;
    power = 0.32 + 0.55 * roll + 0.35 * u * u;
    cam.set(0, 1.5, lerp(13, 5, u * u));
    figOn = true; figX = -0.9; figZ = -4; run = 0;
    grain = .06 + .03 * u; aberr = .002 + .004 * roll; scratch = .5 * roll; godEx = .55 + .3 * roll;
  } else if (!drop) {                                 // SHOT 2 — the silence: close, near black, ring breathing
    const u = (t - BUILD_END) / (DROP - BUILD_END);
    power = 0.06 + 0.7 * u * u * u;
    cam.set(0, 0.3, 0); look.set(0, 9, -300);
    figOn = true; figX = -0.45; figZ = -7; run = 0;
    grain = .1; godEx = .4 + .6 * u; bloomS = .5;
  } else {                                            // THE DROP
    eclipse = 1 - sstep(DROP, DROP + 0.45, t);
    flash = Math.exp(-(t - DROP) * 6) * 0.95;
    power = 0.95 + 0.45 * kick;
    godEx = .42 + .4 * kick; bloomS = .4 + .3 * kick; aberr = .003 + .007 * kick; grain = .05; scratch = .25 * kick; wind = 3;
    const bar = Math.floor((t - DROP) / BAR), u = ((t - DROP) % BAR) / BAR;
    let roll = 0;
    if (t >= CUT_BLACK) { black = 1; }
    else if (bar === 0) {                             // rush low over the water toward the sun
      cam.set(0, lerp(0.7, 0.45, u), lerp(8, -14, u)); look.set(0, 10, -300); wind = 14;
    } else if (bar === 1) {                           // dutch angle, skimming the reflection
      cam.set(lerp(-3, 3, u), 0.22, lerp(-6, -24, u)); look.set(0, 12, -300); roll = 0.12; wind = 18;
    } else if (bar === 2) {                           // telephoto on the corona, breathing on kicks
      cam.set(0, 2, 20); look.set(0, 14, -300); fov = lerp(9, 7.5, u) - kick * 0.5; wind = 6; eclipse = 0.82; godEx *= 0.6; bloomS *= 0.8;
    } else if (bar === 3) {                           // high wide, the light owning the horizon
      cam.set(lerp(-2, 2, u), lerp(5, 3.5, u), 14); look.set(0, 9, -300); roll = -0.06; wind = 10;
    } else {                                          // final rush, light swallows everything
      cam.set(0, 0.5, lerp(4, -40, u * u)); look.set(0, 11, -300); fov = lerp(30, 40, u); wind = 24;
      white = Math.pow(sstep(DROP + BAR * 4 + 0.2, CUT_BLACK, t), 2) * 0.97;
      power += 0.6 * u;
    }
    window.__roll = roll;
    // kick shake
    const sh = kick * 0.035;
    cam.x += (hash(Math.floor(t * 24)) - .5) * sh; cam.y += (hash(Math.floor(t * 24) + 50) - .5) * sh;
  }

  camera.fov = fov; camera.updateProjectionMatrix();
  camera.position.copy(cam); camera.lookAt(look); if (drop && t < CUT_BLACK) camera.rotateZ(window.__roll || 0); camera.updateMatrixWorld();
  const sp = SUN.clone().project(camera);
  sunNdc.set(sp.x, sp.y);
  rays.uniforms.uSun.value.set(sp.x * .5 + .5, sp.y * .5 + .5);
  const hp = new THREE.Vector3(cam.x, 0, -640).project(camera); rays.uniforms.uHor.value = hp.y * .5 + .5;

  skyU.uPower.value = power; skyU.uEclipse.value = eclipse; skyU.uTime.value = t;
  dust.material.uniforms.uWind.value = wind;
  rays.uniforms.uExposure.value = godEx;
  bloom.strength = bloomS;
  Object.assign(grade.uniforms.uTime, { value: t });
  grade.uniforms.uGrain.value = grain; grade.uniforms.uFlash.value = flash; grade.uniforms.uWhite.value = white;
  grade.uniforms.uBlack.value = black; grade.uniforms.uAberr.value = aberr; grade.uniforms.uScratch.value = scratch;

  fig.m.visible = false; char.m.visible = false;
  if (fig.m.visible) {
    fig.ctx.clearRect(0, 0, 512, 512); fig.ctx.fillStyle = fig.ctx.strokeStyle = '#fff';
    drawFigure(fig.ctx, 230, 500, 1, runPhase, run, { wind: 0.9 + run * 0.8 + Math.sin(t * 1.3) * 0.2 });
    fig.tex.needsUpdate = true; place(fig, figX, figZ);
  }
  if (char.m.visible) {
    char.ctx.clearRect(0, 0, 1536, 512); char.ctx.fillStyle = char.ctx.strokeStyle = '#fff';
    drawChariot(char.ctx, gallop, t * 22);
    char.tex.needsUpdate = true; place(char, charX, charZ);
  }

  // titles
  l1.style.opacity = t < BUILD_END ? (sstep(0.5, 2.2, t) * 0.8).toFixed(3) : 0;
  l1.style.filter = `blur(${(1 - sstep(0.5, 2.6, t)) * 6}px)`;
  l1.style.letterSpacing = `${0.9 + t * 0.04}em`;
  l2.style.opacity = t >= CUT_BLACK ? sstep(CUT_BLACK + 0.08, CUT_BLACK + 0.55, t).toFixed(3) : 0;
  l2.style.letterSpacing = `${1.1 + (t - CUT_BLACK) * 0.12}em`;

  composer.render();
  return true;
};
window.ready = true;
