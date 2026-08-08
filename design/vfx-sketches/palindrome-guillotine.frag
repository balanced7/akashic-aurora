#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;

// palindrome-guillotine -- 2026-08-07, Daniil's idea.
//
//   Words are drawn as coloured tiles, one per letter, same letter = same
//   colour. A palindrome therefore LOOKS like a palindrome before any test
//   runs: the colours mirror about the centre.
//
//   A blade falls down the axis of symmetry. If the word is a palindrome the
//   cut is clean -- the halves part a little, hold their line, and the screen
//   breathes green. If it is not, the halves are cut badly, tumble and fall
//   out of frame, and a red X strikes the top right.
//
//   The odd/even distinction is visible: an odd word has a middle tile the
//   blade passes THROUGH (it is its own mirror, so it survives a clean cut);
//   an even word has no middle and the blade falls between two tiles.

#define PI 3.14159265

// ---------------------------------------------------------------- the words
// 0 racecar (7, odd,  PAL)   1 noon  (4, even, PAL)
// 2 stone   (5, odd,  NOT)   3 shoe  (4, even, NOT)
int wordLen(int w){
  if(w==0) return 7; if(w==1) return 4; if(w==2) return 5; return 4;
}
int letterAt(int w, int i){
  if(w==0){ if(i==0)return 17; if(i==1)return 0; if(i==2)return 2; if(i==3)return 4;
            if(i==4)return 2;  if(i==5)return 0; return 17; }              // r a c e c a r
  if(w==1){ if(i==0)return 13; if(i==1)return 14; if(i==2)return 14; return 13; }  // n o o n
  if(w==2){ if(i==0)return 18; if(i==1)return 19; if(i==2)return 14;
            if(i==3)return 13; return 4; }                                  // s t o n e
  if(i==0)return 18; if(i==1)return 7; if(i==2)return 14; return 4;         // s h o e
}
bool isPal(int w){
  int n = wordLen(w);
  for(int i=0;i<4;i++){ if(i >= n/2) break;
    if(letterAt(w,i) != letterAt(w,n-1-i)) return false; }
  return true;
}

// letter code -> a distinct, pleasant colour
vec3 tint(int c){
  // 0.125 chosen by brute force: it maximises the WORST hue gap between two
  // different letters across all four words (0.125, against 0.008 for the
  // value I first guessed). My first objective only measured gaps between
  // DISTINCT HUES, and the optimiser gamed it -- 0.5 scored perfectly by
  // collapsing every letter onto two colours. Punishing collapse fixed it.
  float h = fract(float(c) * 0.125 + 0.06);
  return 0.55 + 0.45 * cos(6.28318 * (h + vec3(0.0, 0.33, 0.67)));
}

float box(vec2 p, vec2 b){ vec2 d = abs(p) - b; return length(max(d,0.0)) + min(max(d.x,d.y),0.0); }

mat2 rot(float a){ float s=sin(a), c=cos(a); return mat2(c,-s,s,c); }

void mainImage(out vec4 O, in vec2 F){
  vec2 uv = (F - 0.5*u_res.xy) / u_res.y;        // centred, y in [-0.5,0.5]

  const float CYCLE = 4.2;
  float t  = mod(u_time, CYCLE * 4.0);
  int   w  = int(floor(t / CYCLE));
  float lt = mod(t, CYCLE);                       // local time within this word

  int  n   = wordLen(w);
  bool pal = isPal(w);

  // ---- phases
  float bladeY = mix(0.46, 0.0, smoothstep(0.35, 1.15, lt));   // blade descends
  float cut    = smoothstep(1.05, 1.20, lt);                   // contact
  float fall   = pal ? 0.0 : smoothstep(1.20, 3.10, lt);       // only bad words fall
  float part   = pal ? 0.022 * smoothstep(1.15, 1.60, lt) : 0.045 * cut;

  vec3 col = vec3(0.055, 0.06, 0.075);

  // ---- verdict wash: green or red, a brief breath after the cut
  float wash = smoothstep(1.10, 1.30, lt) * (1.0 - smoothstep(1.30, 2.60, lt));
  float vig = smoothstep(0.18, 0.62, length(uv));           // edges only
  col += (pal ? vec3(0.10,0.42,0.18) : vec3(0.45,0.09,0.12)) * wash * vig;

  // ---- tiles
  float TW = 0.040, GAP = 0.010;                  // sized for a SQUARE cell: uv.x is +-0.5
  float span = float(n) * (2.0*TW + GAP);
  for(int i=0;i<7;i++){
    if(i >= n) break;
    bool left = (float(i) < float(n)*0.5 - 0.001);
    bool mid  = (n % 2 == 1) && (i == n/2);

    // home position
    float x0 = -0.5*span + (2.0*TW+GAP)*(float(i)+0.5);
    vec2  home = vec2(x0, 0.0);

    // per-half transform: part outward, then (if bad) tumble and fall
    float dir = left ? -1.0 : 1.0;
    vec2  p = uv;
    vec2  o = vec2(dir*part, 0.0);
    float ang = 0.0;
    if(!pal){
      // they fall to the GROUND and stay there: the drop is clamped at the floor and
      // the tumble freezes at the moment of landing, so nothing spins on the deck.
      float FLOOR = 0.30;
      float land  = sqrt(FLOOR / 1.05);                  // fall value at touchdown
      float fl    = min(fall, land);
      o += vec2(dir*0.30*fl, -min(1.05*fall*fall, FLOOR));
      ang = dir * 1.9 * fl;
    }
    // the middle tile drops STRAIGHT down rather than sideways. It must REPLACE the
    // half-drop above, not add to it -- adding sent it through the floor, which the
    // contact sheet caught: five tiles went down and four came to rest.
    if(mid && !pal){ o = vec2(dir*0.05*fall, -min(1.05*fall*fall, 0.30)); }

    p -= home + o;
    p  = rot(-ang) * p;

    float d = box(p, vec2(TW, 0.072));
    float a = smoothstep(0.006, 0.0, d);
    if(a > 0.001){
      vec3 c = tint(letterAt(w,i));
      // the blade's kerf: darken right at the cut line for the middle tile
      if(mid) c *= 1.0 - 0.45*smoothstep(0.012, 0.0, abs(p.x)) * cut;
      col = mix(col, c, a);
      col += c * 0.35 * smoothstep(0.030, 0.0, abs(d)) ;   // edge glow
    }
  }

  // ---- the ground the pieces land on
  col += vec3(0.16,0.17,0.21) * smoothstep(0.004, 0.0, abs(uv.y + 0.375));

  // ---- the blade: a thin bright line on the axis of symmetry
  float bd = box(vec2(uv.x, uv.y - bladeY - 0.20), vec2(0.0030, 0.20));
  float ba = smoothstep(0.004, 0.0, bd);
  col = mix(col, vec3(0.85,0.92,1.0), ba);
  col += vec3(0.35,0.55,0.9) * smoothstep(0.05, 0.0, bd) * 0.5;

  // ---- red X, top right, only when it failed
  if(!pal){
    float xa = smoothstep(1.15, 1.45, lt);
    vec2 q = uv - vec2(0.37, 0.37);
    float arm1 = box(rot( 0.7854)*q, vec2(0.052, 0.008));
    float arm2 = box(rot(-0.7854)*q, vec2(0.052, 0.008));
    float xm = smoothstep(0.005, 0.0, min(arm1, arm2));
    col = mix(col, vec3(1.0,0.22,0.25), xm * xa);
    col += vec3(1.0,0.2,0.2) * smoothstep(0.06,0.0,min(arm1,arm2)) * 0.35 * xa;
  }

  col = pow(max(col,0.0), vec3(0.4545));
  O = vec4(col, 1.0);
}

void main(){ mainImage(outColor, gl_FragCoord.xy); }
