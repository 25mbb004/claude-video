// ---- shared helpers ----
#define PI 3.14159265
float hash12(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
float hash13(vec3 p3){ p3 = fract(p3 * .1031); p3 += dot(p3, p3.zyx + 31.32); return fract((p3.x + p3.y) * p3.z); }
vec2 hash22(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * vec3(.1031, .1030, .0973)); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.xx + p3.yz) * p3.zy); }
float noise2(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  return mix(mix(hash12(i), hash12(i + vec2(1, 0)), f.x), mix(hash12(i + vec2(0, 1)), hash12(i + vec2(1, 1)), f.x), f.y); }
float noise3(vec3 p){ vec3 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  float a = mix(mix(hash13(i), hash13(i + vec3(1,0,0)), f.x), mix(hash13(i + vec3(0,1,0)), hash13(i + vec3(1,1,0)), f.x), f.y);
  float b = mix(mix(hash13(i + vec3(0,0,1)), hash13(i + vec3(1,0,1)), f.x), mix(hash13(i + vec3(0,1,1)), hash13(i + vec3(1,1,1)), f.x), f.y);
  return mix(a, b, f.z); }
float fbm2(vec2 p, int o){ float s = 0., a = .5; mat2 m = mat2(1.6, 1.2, -1.2, 1.6); for (int i = 0; i < 8; i++){ if (i >= o) break; s += a * noise2(p); p = m * p; a *= .5; } return s; }
float fbm3(vec3 p, int o){ float s = 0., a = .5; for (int i = 0; i < 8; i++){ if (i >= o) break; s += a * noise3(p); p = p * 2.02 + vec3(1.7, 9.2, 3.1); a *= .5; } return s; }
vec3 aces(vec3 x){ return clamp((x * (2.51 * x + .03)) / (x * (2.43 * x + .59) + .14), 0., 1.); }
vec3 toSRGB(vec3 c){ return pow(clamp(c, 0., 1.), vec3(1. / 2.2)); }
vec3 finish(vec3 col, vec2 fc, float grain, float vig){
  vec2 uv = fc / uRes; vec2 d = uv - .5;
  col *= mix(1., smoothstep(1.1, .25, length(d * vec2(1.2, 1.))), vig);
  col = toSRGB(aces(col));
  col += (hash12(fc + 17.3) - .5) * grain;
  return col;
}
