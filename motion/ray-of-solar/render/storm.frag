// STORM ASCENT — volumetric raymarched clouds
// shot 0: build (inside the storm, lightning) · 1: silence (black cloud, a gold gap above) · 2: DROP (burst above the cloud sea at sunrise)
const vec3 SUN = normalize(vec3(.12, .07, -1.));
float cloudD(vec3 p){
  if (uShot > .5 && uShot < 1.5) {        // eye of the storm: a funnel of cloud walls
    if (p.y > 2.4) return 0.;
    float r = length(p.xz - vec2(0., -.3));
    float an = p.y * .7; vec2 c = p.xz - vec2(0., -.3);
    vec2 rp = mat2(cos(an), -sin(an), sin(an), cos(an)) * c;
    float wall = r - (.38 + .13 * (p.y + 1.6)) + (fbm3(vec3(rp.x * 2.2, p.y * 1.6, rp.y * 2.2), 5) - .5) * .75;
    return clamp(wall * 6., 0., 1.) * smoothstep(2.4, 2.1, p.y);
  }
  float h = (p.y + 3.) / 5.5;
  if (h < 0. || h > 1.) return 0.;
  float shape = smoothstep(0., .12, h);
  vec3 q = p * vec3(.3, .42, .3);
  q.xz += .5 * vec2(noise3(q * .6), noise3(q * .6 + 3.3));
  float n = fbm3(q, 5);
  float d = n * shape - (.3 + .42 * h);
  if (uShot > .5 && uShot < 1.5) {        // the gap above the silence shot
    d += .45;
    vec2 g = p.xz - vec2(.5, -2.6);
    float gap = length(g) + (fbm3(p * 1.1, 3) - .5) * 1.4;
    d -= smoothstep(2.2, .9, gap) * smoothstep(-1.5, -.6, p.y) * 2.;
  }
  return clamp(d * 6.5, 0., 1.);
}
float lightMarch(vec3 p, vec3 ld){
  float s = 0.;
  for (int i = 1; i <= 6; i++) s += cloudD(p + ld * float(i) * .42);
  return s * .42;
}
float hg(float c, float g){ float g2 = g * g; return (1. - g2) / (4. * PI * pow(1. + g2 - 2. * g * c, 1.5)); }

// jagged lightning bolt (2D overlay, screen space)
float bolt(vec2 uv, vec2 a, vec2 b, float seed){
  float d = 1e3; vec2 prev = a;
  vec2 dir = b - a, perp = normalize(vec2(-dir.y, dir.x));
  for (int i = 1; i <= 48; i++) {
    float f = float(i) / 48.;
    float j = (noise2(vec2(f * 5., seed)) - .5) * .22 + (noise2(vec2(f * 22., seed + 7.)) - .5) * .07 + (hash12(vec2(float(i), seed)) - .5) * .025;
    vec2 pt = mix(a, b, f) + perp * j * sin(f * PI * .9 + .2);
    vec2 pa = uv - prev, ba = pt - prev; float h = clamp(dot(pa, ba) / dot(ba, ba), 0., 1.);
    d = min(d, length(pa - ba * h) * (1. + f * 1.5));
    prev = pt;
  }
  return d;
}
vec3 sky(vec3 rd){
  float y = max(rd.y, 0.);
  vec3 c = mix(vec3(1., .4, .1) * .55, vec3(.02, .03, .07), smoothstep(0., .1, y));
  c = mix(c, vec3(.002, .003, .01), smoothstep(.1, .55, y));
  float s = max(dot(rd, SUN), 0.);
  c += vec3(1., .75, .45) * pow(s, 2500.) * 80. + vec3(1., .5, .15) * (pow(s, 60.) * .9 + pow(s, 8.) * .14);
  return c;
}

vec3 render(vec2 fc){
  vec2 uv = (fc - .5 * uRes) / uRes.y;
  vec3 ro, ta; float zoom = 1.3;
  if (uShot < .5)      { ro = vec3(0., -1.6, 2.); ta = vec3(.6, 1.2, -6.); }
  else if (uShot < 1.5){ ro = vec3(0., -1.4, -.3); ta = vec3(.22, 3., -.75); zoom = .95; }
  else                 { ro = vec3(0., 2.35, 4.); ta = vec3(0., 1.9, -10.); zoom = 1.3; }
  vec3 f = normalize(ta - ro), r = normalize(cross(f, vec3(0, 1, 0))), u = cross(r, f);
  vec3 rd = normalize(f * zoom + uv.x * r + uv.y * u);

  vec3 L = uShot < .5 ? vec3(1.8, .2, -7.) : vec3(0.);   // lightning position inside the storm
  vec3 ld = uShot > 1.5 ? SUN : (uShot > .5 ? normalize(vec3(.05, 1., -.1)) : vec3(0., 1., 0.));
  vec3 sunCol = uShot > 1.5 ? vec3(1., .55, .2) * 1.25 : (uShot > .5 ? vec3(1., .55, .2) * 2.4 : vec3(.3, .35, .5) * .25);
  vec3 amb = uShot > 1.5 ? vec3(.008, .014, .032) : (uShot > .5 ? vec3(.0005, .0007, .0012) : vec3(.012, .016, .03));

  float t = 0., tmax = uShot > 1.5 ? 70. : 30.;
  tmax = uShot > 1.5 ? 95. : tmax;
  vec3 col = vec3(0.); float T = 1.;
  float cs = dot(rd, ld);
  float ph = min(mix(hg(cs, .6), hg(cs, -.2), .3) * 4. * PI, 4.);
  for (int i = 0; i < 210; i++) {
    if (t > tmax || T < .01) break;
    float dt = .045 + t * .02;
    vec3 p = ro + rd * (t + dt * hash12(fc + float(i)));
    if (p.y > 2.7 && rd.y > 0.) break;
    float d = cloudD(p) * (uShot > 1.5 ? smoothstep(95., 45., t) : 1.);
    if (d > .005) {
      float lm = lightMarch(p, ld);
      float beer = exp(-lm * 3.4), powder = 1. - exp(-lm * 4. - d * 3.);
      vec3 lit = sunCol * beer * mix(1., powder, .55) * ph;
      if (uShot > .5 && uShot < 1.5) lit *= pow(smoothstep(-.6, 2.35, p.y), 2.5) * 1.8;
      if (uShot < .5) { float dl = length(p - L); lit += vec3(.7, .76, 1.) * 14. * exp(-dl * .5) * (.35 + .65 * beer); }
      float hgt = clamp((p.y + 3.) / 5.5, 0., 1.);
      vec3 S = (lit + amb * (.3 + hgt)) * d;
      float ext = d * 7.;
      float a = exp(-ext * dt);
      col += T * S * (1. - a) / max(ext, 1e-4);
      T *= a;
    }
    t += dt;
  }
  vec3 bgc = uShot > 1.5 ? sky(rd) : (uShot > .5 ? vec3(1., .55, .2) * (.18 + pow(max(dot(rd, ld), 0.), 400.) * 25. + pow(max(dot(rd, ld), 0.), 30.) * .8) : vec3(.004, .005, .01));
  col += T * bgc;
  if (uShot > 1.5) { // atmospheric haze toward the horizon + sun bloom
    float s = max(dot(rd, SUN), 0.);
    col += vec3(1., .5, .15) * pow(s, 14.) * .07;
  }
  if (uShot < .5) {   // the bolt itself
    vec2 a = vec2(.38, .62), b = vec2(.02, -.62);
    float db = bolt(uv, a, b, 3.);
    float db2 = bolt(uv, vec2(.31, .28), vec2(.62, -.25), 9.) * 1.7;
    float db3 = bolt(uv, vec2(.2, -.05), vec2(-.25, -.42), 21.) * 2.2;
    float m = min(db, min(db2, db3));
    col += vec3(.78, .82, 1.) * (exp(-m * 1400.) * 7. + exp(-m * 90.) * .45 + exp(-m * 10.) * .1);
  }
  float exposure = uShot > 1.5 ? .68 : (uShot > .5 ? 1.2 : 1.3);
  return finish(col * exposure, fc, .045, .7);
}
