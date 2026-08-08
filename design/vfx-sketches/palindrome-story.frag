#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;

// palindrome-story -- 2026-08-07. Four acts, one loop, with letters.
//
//   ACT 1  RACECAR   odd, a palindrome. The blade falls down the axis of
//                    symmetry, the cut is clean, the halves part level and hold
//                    their line. The middle E is cut THROUGH and survives,
//                    because it is its own mirror.
//   ACT 2  STONE     odd, not a palindrome. Cut badly: the pieces tumble and
//                    fall to the ground under a red X.
//   ACT 3  GAATTC    DNA, and a palindrome -- but NOT because it reads the same
//                    backwards. It does not. Because the DOUBLE STRAND has
//                    180-degree rotational symmetry: turn it upside down and it
//                    lands exactly on itself. Letters make the pairing plain:
//                    every A sits above a T, every C above a G.
//   ACT 4  GAATTA    one base off. The turn does NOT land on itself, and the
//                    picture localises the failure -- only the outermost pair
//                    goes red, because that is the only pair that disagrees.
//
//   THE THREAD: a palindrome is symmetry about a centre. In a word the middle
//   letter of an odd word is unpaired and needs no partner. In DNA the middle
//   base would have to be its OWN complement -- and A pairs with T, C with G,
//   so nothing does. Odd-length DNA palindromes are not rare, they are
//   impossible. Verified: 0 at lengths 1,3,5; 4 at length 2; 16 at length 4.

#define PI 3.14159265

// ------------------------------------------------------------------- 3x5 font
// bit index = row*3 + col, row 0 is the TOP row. Values computed, not hand-typed.
int glyphBits(int g){
  if(g== 0) return  23530;   // A
  if(g== 2) return  25166;   // C
  if(g== 4) return  29391;   // E
  if(g== 6) return  27470;   // G
  if(g== 7) return  23533;   // H
  if(g==13) return  24573;   // N
  if(g==14) return  11114;   // O
  if(g==17) return  23275;   // R
  if(g==18) return  14478;   // S
  if(g==19) return   9367;   // T
  return 0;
}
// p is local to the tile, in roughly [-TW,TW] x [-TH,TH]
float glyph(int g, vec2 p, float sx, float sy){
  vec2 q = vec2(p.x/sx*0.5+0.5, p.y/sy*0.5+0.5);      // -> [0,1]
  if(q.x<0.0||q.x>1.0||q.y<0.0||q.y>1.0) return 0.0;
  int cx = int(floor(q.x*3.0));
  int cy = int(floor((1.0-q.y)*5.0));
  cx = clamp(cx,0,2); cy = clamp(cy,0,4);
  return float((glyphBits(g) >> (cy*3+cx)) & 1);
}

float box(vec2 p, vec2 b){ vec2 d=abs(p)-b; return length(max(d,0.0))+min(max(d.x,d.y),0.0); }
mat2 rot(float a){ float s=sin(a),c=cos(a); return mat2(c,-s,s,c); }

// ------------------------------------------------------------------ act 1 / 2
int wordLen(int w){ return w==0 ? 7 : 5; }
int letterAt(int w,int i){
  if(w==0){ if(i==0)return 17; if(i==1)return 0; if(i==2)return 2; if(i==3)return 4;
            if(i==4)return 2;  if(i==5)return 0; return 17; }         // R A C E C A R
  if(i==0)return 18; if(i==1)return 19; if(i==2)return 14;
  if(i==3)return 13; return 4;                                         // S T O N E
}
vec3 tint(int c){ float h=fract(float(c)*0.125+0.06);
                  return 0.55+0.45*cos(6.28318*(h+vec3(0.0,0.33,0.67))); }

// ------------------------------------------------------------------ act 3 / 4
// A=0 C=1 G=2 T=3 ; complement swaps A<->T and C<->G. Nothing maps to itself.
int comp(int b){ return 3-b; }
int dnaGlyph(int b){ return b==0?0 : b==1?2 : b==2?6 : 19; }   // A C G T
vec3 dnaCol(int b){
  if(b==0) return vec3(0.30,0.82,0.42);
  if(b==1) return vec3(0.32,0.62,0.99);
  if(b==2) return vec3(0.99,0.76,0.26);
  return vec3(0.97,0.36,0.42);
}
int dnaAt(int s,int i){
  if(s==0){ if(i==0)return 2; if(i==1)return 0; if(i==2)return 0;
            if(i==3)return 3; if(i==4)return 3; return 1; }   // G A A T T C
  if(i==0)return 2; if(i==1)return 0; if(i==2)return 0;
  if(i==3)return 3; if(i==4)return 3; return 0;               // G A A T T A
}

const float TW=0.058, TH=0.080, GAP=0.010;   // bigger: the letters must be READABLE
float slotX(int i,int n){ float span=float(n)*(2.0*TW+GAP);
                          return -0.5*span+(2.0*TW+GAP)*(float(i)+0.5); }

// draw one lettered tile
void tile(inout vec3 col, vec2 p, vec3 c, int g, float alpha){
  float d=box(p, vec2(TW,TH));
  float a=smoothstep(0.005,0.0,d)*alpha;
  if(a<=0.001) return;
  col=mix(col,c,a);
  // sx/sy are the glyph box HALF-EXTENTS. They must be SMALLER than the tile or the
  // letter fills it edge to edge and reads as noise -- which is exactly what my first
  // value (TW*1.15, a box WIDER than the tile) produced.
  float gl=glyph(g, p, TW*0.56, TH*0.60);
  col=mix(col, vec3(0.04,0.04,0.06), gl*a);             // the letter, punched dark
  col+=c*0.30*smoothstep(0.028,0.0,abs(d))*alpha;
}

void mainImage(out vec4 O, in vec2 F){
  vec2 uv=(F-0.5*u_res.xy)/u_res.y;

  const float ACT=5.4;
  float t  = mod(u_time, ACT*4.0);
  int   act= int(floor(t/ACT));
  float lt = mod(t,ACT);

  vec3 col=vec3(0.05,0.055,0.07);
  bool pal;

  if(act<2){
    // ---------------------------------------------------------- WORDS
    int w=act, n=wordLen(w);
    pal = true;
    for(int i=0;i<3;i++){ if(i>=n/2) break;
      if(letterAt(w,i)!=letterAt(w,n-1-i)) pal=false; }

    float bladeY=mix(0.46,0.0,smoothstep(0.35,1.15,lt));
    float cut   =smoothstep(1.05,1.20,lt);
    float fall  =pal?0.0:smoothstep(1.20,3.10,lt);
    float part  =pal?0.022*smoothstep(1.15,1.60,lt):0.045*cut;

    float wash=smoothstep(1.10,1.30,lt)*(1.0-smoothstep(1.30,2.60,lt));
    col+=(pal?vec3(0.10,0.42,0.18):vec3(0.45,0.09,0.12))*wash
         *smoothstep(0.18,0.62,length(uv));
    col+=vec3(0.16,0.17,0.21)*smoothstep(0.004,0.0,abs(uv.y+0.375));

    for(int i=0;i<7;i++){
      if(i>=n) break;
      bool left=(float(i)<float(n)*0.5-0.001);
      bool mid =(n%2==1)&&(i==n/2);
      float dir=left?-1.0:1.0;
      vec2 o=vec2(dir*part,0.0); float ang=0.0;
      if(!pal){
        float FLOOR=0.30, land=sqrt(FLOOR/1.05), fl=min(fall,land);
        o+=vec2(dir*0.30*fl,-min(1.05*fall*fall,FLOOR)); ang=dir*1.9*fl;
        if(mid) o=vec2(dir*0.05*fall,-min(1.05*fall*fall,FLOOR));
      }
      vec2 p=rot(-ang)*(uv-vec2(slotX(i,n),0.0)-o);
      tile(col,p,tint(letterAt(w,i)),letterAt(w,i),1.0);
    }
    float bd=box(vec2(uv.x,uv.y-bladeY-0.20),vec2(0.0030,0.20));
    col=mix(col,vec3(0.85,0.92,1.0),smoothstep(0.004,0.0,bd));
    col+=vec3(0.35,0.55,0.9)*smoothstep(0.05,0.0,bd)*0.5;

  } else {
    // ---------------------------------------------------------- DNA
    int s=act-2, n=6;
    pal=true;
    for(int i=0;i<6;i++) if(dnaAt(s,i)!=comp(dnaAt(s,n-1-i))) pal=false;

    float turn  =smoothstep(1.0,3.2,lt);
    float landed=smoothstep(0.97,1.0,turn);
    float ROW=0.105;

    // the GHOST: the original, held still, so you see what it lands on
    for(int pass=0;pass<2;pass++){
      float a  = (pass==0)?0.32:1.0;
      vec2  base = (pass==0)? uv : rot(-turn*PI)*uv;
      for(int i=0;i<6;i++){
        float x=slotX(i,n); int b=dnaAt(s,i);
        tile(col, base-vec2(x, ROW), dnaCol(b)*a,       dnaGlyph(b),       a);
        tile(col, base-vec2(x,-ROW), dnaCol(comp(b))*a, dnaGlyph(comp(b)), a);
        float dR=box(base-vec2(x,0.0),vec2(0.005,0.043));
        col=mix(col,vec3(0.40,0.43,0.52)*a,smoothstep(0.004,0.0,dR));
        if(pass==1){
          bool ok=(dnaAt(s,i)==comp(dnaAt(s,n-1-i)));
          col += (ok?vec3(0.35,1.0,0.5):vec3(1.0,0.28,0.30))
                 *landed*smoothstep(0.024,0.0,abs(dR))*1.5;
        }
      }
    }
    float wash=landed*(1.0-smoothstep(4.4,5.2,lt));
    col+=(pal?vec3(0.10,0.42,0.18):vec3(0.45,0.09,0.12))*wash
         *smoothstep(0.18,0.62,length(uv));
    col+=vec3(0.7,0.75,0.9)*smoothstep(0.011,0.0,length(uv))*0.9;
  }

  // red X, top right, whenever the act failed
  if(!pal){
    float xa = (act<2)? smoothstep(1.15,1.45,lt) : smoothstep(3.15,3.35,lt);
    vec2 q=uv-vec2(0.37,0.37);
    float a1=box(rot( 0.7854)*q,vec2(0.052,0.008));
    float a2=box(rot(-0.7854)*q,vec2(0.052,0.008));
    col=mix(col,vec3(1.0,0.22,0.25),smoothstep(0.005,0.0,min(a1,a2))*xa);
    col+=vec3(1.0,0.2,0.2)*smoothstep(0.06,0.0,min(a1,a2))*0.35*xa;
  }

  col=pow(max(col,0.0),vec3(0.4545));
  O=vec4(col,1.0);
}

void main(){ mainImage(outColor, gl_FragCoord.xy); }
