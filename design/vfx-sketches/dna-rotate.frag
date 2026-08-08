#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;

// dna-rotate -- 2026-08-07. The intuition, not the definition.
//
//   WHY IT IS CALLED A PALINDROME. Not because it reads the same backwards --
//   it does not. Because the DOUBLE STRAND has 180-DEGREE ROTATIONAL SYMMETRY.
//   Turn the whole molecule upside down and it lands exactly on itself.
//
//       5'-G A A T T C-3'      turn it     5'-G A A T T C-3'
//       3'-C T T A A G-5'      upside      3'-C T T A A G-5'
//                              down
//
//   That is the same test as "equals its reverse complement", verified:
//   rotating 180 maps top[i] onto bottom[n-1-i], and bottom = complement(top),
//   so the condition is top[i] == comp(top[n-1-i]). Identical. One is the
//   algebra, the other is what your hands would do.
//
//   The GHOST is the original, held still. The SOLID rotates onto it. Where a
//   base lands on its own kind the rung lights green; where it lands on a
//   different base it flares red and the two versions visibly disagree.
//
//   AND THE ODD-LENGTH PROOF FALLS OUT: under a 180 turn the middle base of an
//   odd sequence maps onto ITSELF, so it would have to be its own complement.
//   A pairs with T, C with G -- nothing pairs with itself. Verified
//   exhaustively: 0 palindromes at lengths 1, 3, 5; 4 at length 2, 16 at 4.

#define PI 3.14159265

int comp(int b){ return 3 - b; }            // A0<->T3, C1<->G2. Never itself.

vec3 baseCol(int b){
  if(b==0) return vec3(0.30,0.82,0.42);     // A green
  if(b==1) return vec3(0.32,0.62,0.99);     // C blue
  if(b==2) return vec3(0.99,0.76,0.26);     // G amber
  return vec3(0.97,0.36,0.42);              // T red
}

const int N = 6;
int baseAt(int s, int i){
  if(s==0){ if(i==0)return 2; if(i==1)return 0; if(i==2)return 0;
            if(i==3)return 3; if(i==4)return 3; return 1; }   // GAATTC  EcoRI, a palindrome
  if(i==0)return 2; if(i==1)return 0; if(i==2)return 0;
  if(i==3)return 3; if(i==4)return 3; return 0;               // GAATTA  one base off
}

float box(vec2 p, vec2 b){ vec2 d=abs(p)-b; return length(max(d,0.0))+min(max(d.x,d.y),0.0); }

const float TW=0.048, GAP=0.014, ROW=0.10;
float slotX(int i){ float span=float(N)*(2.0*TW+GAP); return -0.5*span+(2.0*TW+GAP)*(float(i)+0.5); }

// draw the duplex into `col`; `gh` fades it to a ghost; returns nothing
void duplex(inout vec3 col, vec2 p, int s, float gh, float lit, bool showLit){
  for(int i=0;i<6;i++){
    float x=slotX(i);
    int b=baseAt(s,i), cb=comp(b);
    float dT=box(p-vec2(x, ROW), vec2(TW,0.042));
    float dB=box(p-vec2(x,-ROW), vec2(TW,0.042));
    float aT=smoothstep(0.005,0.0,dT), aB=smoothstep(0.005,0.0,dB);
    col=mix(col, baseCol(b)*gh,  aT);
    col=mix(col, baseCol(cb)*gh, aB);
    float dR=box(p-vec2(x,0.0), vec2(0.005,0.058));
    col=mix(col, vec3(0.40,0.43,0.52)*gh, smoothstep(0.004,0.0,dR));
    if(showLit){
      bool ok = (baseAt(s,i)==comp(baseAt(s,N-1-i)));
      vec3 c  = ok ? vec3(0.35,1.0,0.5) : vec3(1.0,0.28,0.30);
      col += c*lit*smoothstep(0.026,0.0,abs(dR))*1.5;
    }
  }
}

mat2 rot(float a){ float s=sin(a),c=cos(a); return mat2(c,-s,s,c); }

void mainImage(out vec4 O, in vec2 F){
  vec2 uv=(F-0.5*u_res.xy)/u_res.y;

  const float CYCLE=6.0;
  float t=mod(u_time,CYCLE*2.0);
  int   s=int(floor(t/CYCLE));
  float lt=mod(t,CYCLE);

  bool pal=true;
  for(int i=0;i<6;i++) if(baseAt(s,i)!=comp(baseAt(s,N-1-i))) pal=false;

  // the turn: hold, rotate a half-turn, hold, verdict
  float turn = smoothstep(1.0, 3.2, lt);                 // 0 -> 1
  float ang  = turn * PI;                                 // a full 180
  float landed = smoothstep(0.97, 1.0, turn);

  vec3 col=vec3(0.05,0.055,0.07);

  // GHOST: the original, held still, so you can see what it lands on
  duplex(col, uv, s, 0.30, 0.0, false);

  // SOLID: the same molecule, turned
  vec2 q = rot(-ang) * uv;
  duplex(col, q, s, 1.0, landed, true);

  // verdict wash once it has landed
  float wash = landed * (1.0 - smoothstep(4.6,5.6,lt));
  float vig  = smoothstep(0.18,0.62,length(uv));
  col += (pal?vec3(0.10,0.42,0.18):vec3(0.45,0.09,0.12)) * wash * vig;

  // the pivot it turns about
  col += vec3(0.7,0.75,0.9)*smoothstep(0.011,0.0,length(uv))*0.9;

  // red X, top right, only when the turn did NOT land on itself
  if(!pal){
    vec2 xq=uv-vec2(0.37,0.37);
    float a1=box(rot( 0.7854)*xq, vec2(0.052,0.008));
    float a2=box(rot(-0.7854)*xq, vec2(0.052,0.008));
    col=mix(col, vec3(1.0,0.22,0.25), smoothstep(0.005,0.0,min(a1,a2))*landed);
  }

  col=pow(max(col,0.0),vec3(0.4545));
  O=vec4(col,1.0);
}

void main(){ mainImage(outColor, gl_FragCoord.xy); }
