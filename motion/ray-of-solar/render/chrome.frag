// LIQUID CHROME — raymarched mercury SDF in a black studio with gold light
// shot 0: build (rippling blob + satellites) · 1: silence (ferrofluid spikes, frozen) · 2: DROP (explosion)
float smin(float a, float b, float k){ float h = clamp(.5 + .5 * (b - a) / k, 0., 1.); return mix(b, a, h) - k * h * (1. - h); }
float sdCaps(vec3 p, vec3 a, vec3 b, float r){ vec3 pa = p - a, ba = b - a; float h = clamp(dot(pa, ba) / dot(ba, ba), 0., 1.); return length(pa - ba * h) - r; }
float sdRoundCone(vec3 p, vec3 a, vec3 b, float r1, float r2){
  vec3 ba = b - a; float l2 = dot(ba, ba); float rr = r1 - r2; float a2 = l2 - rr * rr; float il2 = 1. / l2;
  vec3 pa = p - a; float y = dot(pa, ba); float z = y - l2; vec3 xv = pa * l2 - ba * y; float x2 = dot(xv, xv);
  float y2 = y * y * l2, z2 = z * z * l2; float k = sign(rr) * rr * rr * x2;
  if (sign(z) * a2 * z2 > k) return sqrt(x2 + z2) * il2 - r2;
  if (sign(y) * a2 * y2 < k) return sqrt(x2 + y2) * il2 - r1;
  return (sqrt(x2 * a2 * il2) + y * rr) * il2 - r1; }
vec3 hash3(float n){ return fract(sin(vec3(n, n + 1.7, n + 3.1)) * vec3(43758.5453, 22578.145, 19642.349)); }

float map(vec3 p){
  if (uShot < .5) {
    float r = length(p);
    vec3 q = p + .25 * vec3(fbm3(p * 1.3, 3), fbm3(p * 1.3 + 5.2, 3), fbm3(p * 1.3 + 9.1, 3));
    float wob = sin(q.x * 3.1 + q.y * 2.3) * sin(q.z * 2.7 - q.y * 1.9) * .07;
    float d = r - 1. - wob - (fbm3(q * 2.2, 3) - .5) * .06;
    d = smin(d, length(p - vec3(1.62, .72, .25)) - .2, .32);
    d = smin(d, length(p - vec3(-1.5, -.55, .55)) - .12, .28);
    d = smin(d, length(p - vec3(-.9, 1.25, -.4)) - .08, .2);
    return d * .7;
  } else if (uShot < 1.5) {
    return length(p) - 1.;
  } else {
    vec3 n = normalize(p);
    float sp = abs(sin(5.5 * n.x + .3) * sin(5.5 * n.y + 1.1) * sin(5.5 * n.z + .7));
    float spikes = pow(sp, 3.2) * 1.15;
    float r = length(p);
    return (r - .85 - spikes - (fbm3(p * 2.5, 2) - .5) * .05) * .22;
  }
}
vec3 calcN(vec3 p){ const vec2 e = vec2(.0012, -.0012);
  return normalize(e.xyy * map(p + e.xyy) + e.yyx * map(p + e.yyx) + e.yxy * map(p + e.yxy) + e.xxx * map(p + e.xxx)); }
float march(vec3 ro, vec3 rd, float tmax){ float t = 0.; for (int i = 0; i < 220; i++){ float h = map(ro + rd * t); if (h < .0006 * t || t > tmax) break; t += h; } return t; }

vec3 env(vec3 d){
  vec3 gold = vec3(1., .55, .18), white = vec3(1., .96, .9);
  float e = uShot > 1.5 ? 1.6 : (uShot > .5 ? .55 : 1.);
  vec3 c = vec3(.0015, .002, .003);
  // overhead softbox
  // two overhead strip softboxes
  float sb = smoothstep(.8, .84, d.y) * (smoothstep(.07, .04, abs(d.x - .22)) + smoothstep(.07, .04, abs(d.x + .22))) * smoothstep(.6, .4, abs(d.z));
  c += white * sb * 5. * (uShot > .5 && uShot < 1.5 ? 0. : 1.);
  // horizon all around: dark warm floor, gold line, black sky
  c += vec3(.05, .025, .01) * smoothstep(.0, -.3, d.y) * e;
  c += gold * exp(-abs(d.y + .01) * 40.) * .9 * e;
  // vertical strip lights
  float az = atan(d.x, d.z);
  float vert = smoothstep(.75, .5, abs(d.y));
  c += white * smoothstep(.045, .0, abs(az - 1.25)) * vert * 4. * (uShot > .5 && uShot < 1.5 ? 0. : 1.);
  c += gold * smoothstep(.06, .0, abs(az + 1.1)) * vert * 5.;
  // gold sun on the horizon behind
  float sun = max(dot(d, normalize(vec3(.25, .06, -1.))), 0.);
  c += gold * (pow(sun, 900.) * 40. + pow(sun, 60.) * 1.4 + pow(sun, 8.) * .12) * e;
  if (uShot > .5 && uShot < 1.5) c += gold * smoothstep(.04, .0, abs(az - 2.6)) * vert * 6.; // rim for silence
  return c;
}
vec3 bg(vec3 d){
  vec3 gold = vec3(1., .55, .18);
  float e = uShot > 1.5 ? 1.6 : (uShot > .5 ? .5 : 1.);
  float sun = max(dot(d, normalize(vec3(.25, .06, -1.))), 0.);
  return vec3(.002, .002, .003) + gold * e * (pow(sun, 900.) * 30. + pow(sun, 90.) * 1.0 + pow(sun, 16.) * .025 + exp(-abs(d.y + .01) * 90.) * .14);
}
vec3 shade(vec3 ro, vec3 rd){
  float t = march(ro, rd, 14.);
  if (t > 14.) return bg(rd);
  vec3 p = ro + rd * t, n = calcN(p);
  vec3 r = reflect(rd, n);
  float fr = pow(1. - max(dot(n, -rd), 0.), 5.);
  vec3 F0 = vec3(.82, .80, .77);
  vec3 F = F0 + (1. - F0) * fr;
  // one bounce of inter-reflection
  vec3 ro2 = p + n * .004;
  float t2 = march(ro2, r, 6.);
  vec3 refl;
  if (t2 < 6.) { vec3 p2 = ro2 + r * t2, n2 = calcN(p2); refl = env(reflect(r, n2)) * F0 * .9; }
  else refl = env(r);
  return refl * F;
}
vec3 render(vec2 fc){
  vec2 uv = (fc - .5 * uRes) / uRes.y;
  vec3 ro = uShot > 1.5 ? vec3(.5, -.55, 5.4) : (uShot > .5 ? vec3(-.7, .3, 5.2) : vec3(.15, .3, 4.3));
  vec3 ta = uShot > 1.5 ? vec3(0., .15, 0.) : vec3(0., .02, 0.);
  vec3 f = normalize(ta - ro), rgt = normalize(cross(f, vec3(0, 1, 0))), up = cross(rgt, f);
  float zoom = uShot > .5 && uShot < 1.5 ? 1.9 : 1.75;
  // 2x supersampling (rotated grid)
  vec3 col = vec3(0.);
  for (int s = 0; s < 2; s++) {
    vec2 o = (s == 0 ? vec2(.25, -.25) : vec2(-.25, .25)) / uRes.y;
    vec3 rd = normalize(f * zoom + (uv.x + o.x) * rgt + (uv.y + o.y) * up);
    col += shade(ro, rd);
  }
  col *= .5;
  return finish(col * 1.1, fc, .035, .6);
}
