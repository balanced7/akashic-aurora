#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;

// palindrome-axis -- 2026-08-07, for Daniil's assessment detour.
//
//   A palindrome is symmetry about a centre, not a reversed copy. This shader
//   tests the definition directly: it pairs index i with index n-1-i and walks
//   inward until the two meet. A word of odd length leaves one element in the
//   middle with no partner, and it needs none -- it is already its own mirror.
//
//   THE PICTURE IS ALWAYS LEFT-RIGHT SYMMETRIC, whatever word you give it,
//   because pairing i with n-1-i is a relation that is its own mirror. The
//   WORD's symmetry shows in the COLOUR, not the shape: green means the pair
//   agreed, red means it did not. The method is symmetric; whether the data is
//   symmetric is the question it answers. I claimed the opposite first and a
//   CPU simulation of this exact math caught it.
//
//   Every identifier below is itself a palindrome: level, sees, deed, civic,
//   stats, radar, tenet, noon, rotor, refer.

#define PI 3.14159265

const int  n     = 7;                        // "racecar" -- odd, so a middle shows
const int  level = n / 2;                    // floor(n/2): the pair count. The floor
                                             // is what excludes the unpaired middle.
const vec3 sees  = vec3(0.24, 0.86, 0.46);   // pair agrees
const vec3 deed  = vec3(0.95, 0.26, 0.30);   // pair differs
const vec3 civic = vec3(1.00, 0.82, 0.22);   // the unpaired middle

// r a c e c a r   as a=0 .. z=25
int radar(int i){
  if(i==0) return 17; if(i==1) return  0; if(i==2) return  2;
  if(i==3) return  4;
  if(i==4) return  2; if(i==5) return  0; if(i==6) return 17;
  return -1;
}

// one soft band edge, so the nesting reads as depth rather than as steps
float refer(float y, float b){ return smoothstep(b + 0.012, b - 0.012, y); }

void mainImage(out vec4 O, in vec2 F){
  vec2  uv = F / u_res.xy;
  float aspect = u_res.x / u_res.y;

  int   i     = int(uv.x * float(n));         // which element this column is
  i           = clamp(i, 0, n - 1);
  int   tenet = n - 1 - i;                    // its mirror partner
  bool  noon  = (i == tenet);                 // the unpaired middle?
  bool  rotor = (radar(i) == radar(tenet));   // does the pair agree?

  vec3 col = noon ? civic : (rotor ? sees : deed);

  // outermost pair tallest, innermost shortest: the drawing nests inward
  // exactly the way the comparison does.
  int   pair = min(i, tenet);                 // 0,1,2,3,2,1,0
  float band = 1.0 - float(pair) / float(level + 1);
  float y    = abs(uv.y - 0.5) * 2.0;
  col       *= refer(y, band);

  // the pair being compared right now, sweeping outward-in with time
  float k    = mod(u_time * 0.6, float(level) + 1.0);
  float live = 1.0 - smoothstep(0.0, 0.55, abs(float(pair) - k));
  col       += col * live * 0.85;

  // the axis of symmetry: the line every pair is reflected through
  float ax = smoothstep(0.0035, 0.0, abs(uv.x - 0.5));
  col += vec3(0.55, 0.62, 0.78) * ax * (0.35 + 0.25 * sin(u_time * 1.7));

  // ticks on the axis where each pair meets it
  for(int p = 0; p <= 3; p++){
    if(p > level) break;
    float ty = 1.0 - float(p) / float(level + 1);
    float d  = length(vec2((uv.x - 0.5) * aspect, y - ty));
    col += vec3(0.9, 0.95, 1.0) * smoothstep(0.010, 0.0, d) * 0.7;
  }

  col = pow(max(col, 0.0), vec3(0.4545));     // gamma last
  O = vec4(col, 1.0);
}

void main(){ mainImage(outColor, gl_FragCoord.xy); }
