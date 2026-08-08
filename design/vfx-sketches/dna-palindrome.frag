#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;

// dna-palindrome -- 2026-08-07. The conceptual demo: why the word test is the
// WRONG test for DNA, and why odd length is not merely rare there but IMPOSSIBLE.
//
//   A DNA "palindrome" is not "reads the same backwards". It is a sequence that
//   equals its REVERSE COMPLEMENT -- what the opposite strand reads, in the same
//   direction. A pairs with T, C pairs with G.
//
//   GAATTC is a palindrome. String-reversed it is CTTAAG, which the word test
//   rejects -- and GAATTC is EcoRI's cut site, so the word test misses a real
//   restriction site.
//
//   THE ODD-LENGTH PROOF, drawn: the middle base of an odd sequence has no
//   partner but itself, so it would have to be its own complement. No base is.
//   Verified exhaustively: 0 palindromes at lengths 1, 3 and 5; 4 at length 2
//   and 16 at length 4.
//
//   Top strand runs 5'->3'. Bottom strand is its complement, and is READ in the
//   opposite direction. When the two readings agree, the rungs light.

#define PI 3.14159265

// A=0 C=1 G=2 T=3 ; complement swaps A<->T and C<->G
int comp(int b){ return 3 - b; }             // 0<->3, 1<->2. No base maps to itself.

vec3 baseCol(int b){
  if(b==0) return vec3(0.30,0.80,0.42);      // A green
  if(b==1) return vec3(0.30,0.62,0.98);      // C blue
  if(b==2) return vec3(0.98,0.75,0.25);      // G amber
  return vec3(0.96,0.36,0.40);               // T red
}

// two sequences, alternating: GAATTC (a real EcoRI site) and GAATTA (one base off)
int seqLen(int s){ return 6; }
int baseAt(int s, int i){
  if(s==0){ if(i==0)return 2; if(i==1)return 0; if(i==2)return 0;
            if(i==3)return 3; if(i==4)return 3; return 1; }        // G A A T T C
  if(i==0)return 2; if(i==1)return 0; if(i==2)return 0;
  if(i==3)return 3; if(i==4)return 3; return 0;                     // G A A T T A
}

float box(vec2 p, vec2 b){ vec2 d=abs(p)-b; return length(max(d,0.0))+min(max(d.x,d.y),0.0); }

void mainImage(out vec4 O, in vec2 F){
  vec2 uv = (F - 0.5*u_res.xy) / u_res.y;

  const float CYCLE = 5.0;
  float t  = mod(u_time, CYCLE*2.0);
  int   s  = int(floor(t / CYCLE));
  float lt = mod(t, CYCLE);

  int n = seqLen(s);

  // is it a reverse-complement palindrome?
  bool pal = true;
  for(int i=0;i<6;i++){ if(i>=n) break;
    if(baseAt(s,i) != comp(baseAt(s,n-1-i))) pal = false; }

  vec3 col = vec3(0.05,0.055,0.07);

  float TW=0.045, GAP=0.012;
  float span = float(n)*(2.0*TW+GAP);
  float TOP=0.13, BOT=-0.13;

  // the pair currently under test, sweeping in from the ends
  float k = mod(lt*1.15, float(n)+2.0);

  for(int i=0;i<6;i++){
    if(i>=n) break;
    float x0 = -0.5*span + (2.0*TW+GAP)*(float(i)+0.5);
    int   b  = baseAt(s,i);
    int   cb = comp(b);                       // what sits opposite it on the bottom strand

    // top strand
    float dT = box(uv - vec2(x0, TOP), vec2(TW, 0.055));
    col = mix(col, baseCol(b),  smoothstep(0.005,0.0,dT));
    // bottom strand: the COMPLEMENT
    float dB = box(uv - vec2(x0, BOT), vec2(TW, 0.055));
    col = mix(col, baseCol(cb), smoothstep(0.005,0.0,dB));

    // the rung joining a base to its partner
    float dR = box(uv - vec2(x0, 0.0), vec2(0.006, 0.075));
    col = mix(col, vec3(0.42,0.45,0.55), smoothstep(0.004,0.0,dR));

    // THE TEST: does base i equal the complement of base n-1-i?
    bool ok  = (baseAt(s,i) == comp(baseAt(s,n-1-i)));
    float on = 1.0 - smoothstep(0.0, 1.1, abs(float(min(i,n-1-i)) - k));
    vec3 lit = ok ? vec3(0.35,1.0,0.5) : vec3(1.0,0.30,0.32);
    col += lit * on * smoothstep(0.030,0.0,abs(dR)) * 1.4;

    // link line from i to its mirror partner, drawn along the top
    if(float(i) < float(n)*0.5){
      float xm = -0.5*span + (2.0*TW+GAP)*(float(n-1-i)+0.5);
      float y  = TOP + 0.085 + 0.028*float(i);
      float seg = box(vec2(uv.x-0.5*(x0+xm), uv.y-y), vec2(0.5*abs(xm-x0), 0.0035));
      col += lit * on * smoothstep(0.005,0.0,seg) * 0.9;
    }
  }

  // verdict wash from the edges
  float wash = smoothstep(3.2,3.6,lt) * (1.0-smoothstep(4.2,4.9,lt));
  float vig  = smoothstep(0.18,0.62,length(uv));
  col += (pal ? vec3(0.10,0.42,0.18) : vec3(0.45,0.09,0.12)) * wash * vig;

  // 5' and 3' direction ticks: the strands are READ in opposite directions
  float arrowT = box(uv - vec2( 0.5*span+0.045, TOP), vec2(0.022,0.004));
  float arrowB = box(uv - vec2(-0.5*span-0.045, BOT), vec2(0.022,0.004));
  col += vec3(0.65,0.70,0.85) * smoothstep(0.004,0.0,min(arrowT,arrowB));

  // the impossibility mark: an odd sequence would need a base opposite ITSELF.
  // Drawn as a struck-through slot on the axis, permanently unlit.
  float pulse = 0.5+0.5*sin(u_time*1.6);
  vec2 q = uv - vec2(0.0, -0.34);
  float slot = box(q, vec2(TW, 0.030));
  col = mix(col, vec3(0.16,0.16,0.19), smoothstep(0.005,0.0,slot));
  float bar1 = box(q, vec2(TW*1.25, 0.0035));
  col += vec3(0.85,0.25,0.28) * smoothstep(0.004,0.0,bar1) * (0.55+0.45*pulse);

  col = pow(max(col,0.0), vec3(0.4545));
  O = vec4(col,1.0);
}

void main(){ mainImage(outColor, gl_FragCoord.xy); }
