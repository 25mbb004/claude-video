uniform float uRot, uGrow, uPulse;
// GOLD INK IN BLACK WATER — domain-warped fluid, metallic sheen from the field's gradient
// shot 0: build (plumes rising) · 1: silence (a single thread) · 2: DROP (ink blooms into a black sun)
float field(vec2 p){
  vec2 q = vec2(fbm2(p, 5), fbm2(p + vec2(5.2, 1.3), 5));
  vec2 r = vec2(fbm2(p + 3.6 * q + vec2(1.7, 9.2), 5), fbm2(p + 3.6 * q + vec2(8.3, 2.8), 5));
  return fbm2(p + 3.8 * r, 5);
}
vec2 domain(vec2 uv){
  if (uShot > 2.5) return uv * vec2(3.4, 1.6) + vec2(7.1, 2.3);
  if (uShot > 1.5) { float c = cos(uRot), sn = sin(uRot); vec2 w = mat2(c, -sn, sn, c) * uv / uGrow; float rr = length(w); float lr = log(rr + .02); return normalize(w) * 1.7 + vec2(lr * 2.3, lr * 1.2) + 4. + vec2(0., uTime * .12); }
  if (uShot < .5) return vec2(uv.x * 3.2 + sin(uv.y * 2. - uTime * .8) * .4, uv.y * 1.15 - uTime * .45) + vec2(2.1, .4);
  return uv * vec2(2.2, 2.2) + vec2(1.3 + uTime * .06, .4);
}
float mask(vec2 uv, float f){
  if (uShot > 2.5) return 1.;
  if (uShot < .5) {
    float w = .1 + (uv.y + .6) * .32;                      // plume widens as it rises
    float d = abs(uv.x + .12 - .08 * sin(uv.y * 3.) + (f - .5) * .5) / w;
    return smoothstep(1.1, .1, d) * smoothstep(-.62, -.35, uv.y) * smoothstep(uGrow + .15, uGrow - .35, uv.y);
  } else if (uShot < 1.5) {
    float y = .12 * sin(uv.x * 3.1 + 1.) + .05 * sin(uv.x * 7.3) - .04;
    float d = abs(uv.y - y + (f - .5) * .12);
    return exp(-d * d * 900.) * smoothstep(.95, .2, abs(uv.x + .05));
  } else {
    float rr = length(uv) / uGrow;
    float ring = exp(-pow((rr - .33 - (f - .5) * .3) / .12, 2.));
    float outer = smoothstep(.95, .3, rr + (f - .5) * .7) * .35;
    return max(ring, outer) * smoothstep(.19, .23, rr + (f - .5) * .03);
  }
}
vec3 inkAt(vec2 uv){
  vec2 p = domain(uv);
  float e = .004;
  float f = field(p);
  float fx = field(domain(uv + vec2(e, 0.))), fy = field(domain(uv + vec2(0., e)));
  float m = mask(uv, f);
  vec3 n = normalize(vec3((f - fx) * 22., (f - fy) * 22., 1.));
  float dens = smoothstep(uShot < .5 ? .55 : (uShot > 2.5 ? .3 : .5), .85, f) * m;
  float fil = pow(1. - abs(2. * fract(f * 3.) - 1.), 6.) * m;      // fine filaments
  vec3 L = normalize(vec3(-.5, .6, .7));
  float spec = pow(max(dot(reflect(-L, n), vec3(0, 0, 1)), 0.), 40.);
  float rim = pow(1. - n.z, 2.);
  vec3 deep = vec3(.16, .06, .01), gold = vec3(1., .62, .22), hi = vec3(1., .9, .7);
  vec3 c = deep * dens * 1.6 + gold * (dens * dens * .9 + fil * .35 * (.3 + dens) + rim * dens * 1.4) + hi * spec * dens * 3.;
  return c;
}
vec3 render(vec2 fc){
  vec2 uv = (fc - .5 * uRes) / uRes.y;
  vec3 col = vec3(.001, .003, .004) + vec3(0., .006, .008) * (1. - length(uv));   // black water, a hint of depth
  col += inkAt(uv);
  if (uShot > 1.5 && uShot < 2.5) { float rr = length(uv) / uGrow; col *= smoothstep(.17, .21, rr); col += vec3(1., .6, .25) * exp(-abs(rr - .2) * 60.) * .9 * (1. + uPulse); }
  if (uShot > .5 && uShot < 1.5) col *= 1.25;
  return finish(col * .95, fc, .04, .55);
}
