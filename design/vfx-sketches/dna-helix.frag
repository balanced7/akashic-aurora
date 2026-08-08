#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;

// dna-helix -- 2026-08-07. The palindrome as a cell would present it.
//
//   REAL B-DNA GEOMETRY, not a decorative spiral: 3.4 A rise per base pair,
//   34.3 degrees of twist per base pair (~10.5 bp per full turn), 20 A across.
//   Six base pairs is a little over half a turn, and about as tall as it is wide.
//
//   WHY A PALINDROME MATTERS IN 3D. GAATTC has a C2 SYMMETRY AXIS: turn the
//   whole duplex 180 degrees about a horizontal axis through its centre and it
//   lands on itself -- every base arrives where its partner was. That is the
//   symmetry, and it is a property of the OBJECT, not of a string.
//
//   AND IT IS WHY RESTRICTION ENZYMES CARE. EcoRI is a HOMODIMER: two identical
//   protein subunits. A site with 2-fold symmetry presents each subunit an
//   identical half. The symmetry of the sequence matches the symmetry of the
//   protein that reads it -- which is the actual reason palindromes are the
//   recognition sites and not a curiosity of notation.
//
//   Depth is resolved per pixel: every atom is tested and the NEAREST one wins,
//   so the back strand is genuinely occluded by the front rather than painted
//   over in a hopeful order.

#define PI 3.14159265

// A C G T -- saturated and maximally separated, so a pair is unmistakable
vec3 baseCol(int b){
  if(b==0) return vec3(0.15,1.00,0.25);   // A  green
  if(b==1) return vec3(0.10,0.55,1.00);   // C  blue
  if(b==2) return vec3(1.00,0.80,0.05);   // G  amber
  return vec3(1.00,0.12,0.20);            // T  red
}
int comp(int b){ return 3-b; }            // A<->T, C<->G. Never itself.

const int N = 6;
int baseAt(int s,int i){
  if(s==0){ if(i==0)return 2; if(i==1)return 0; if(i==2)return 0;
            if(i==3)return 3; if(i==4)return 3; return 1; }   // G A A T T C  EcoRI
  if(i==0)return 2; if(i==1)return 0; if(i==2)return 0;
  if(i==3)return 3; if(i==4)return 3; return 0;               // G A A T T A  one off
}

mat3 rotY(float a){ float s=sin(a),c=cos(a); return mat3(c,0,-s, 0,1,0, s,0,c); }
mat3 rotZ(float a){ float s=sin(a),c=cos(a); return mat3(c,-s,0, s,c,0, 0,0,1); }

const float RISE  = 0.125;                 // 3.4 A, scaled to fill the frame
const float TWIST = 34.3 * PI / 180.0;     // 34.3 degrees per base pair
const float RAD   = 0.34;                  // 20 A across

// world position of one atom: which base pair, which strand
vec3 atomPos(int i, int strand){
  float th = float(i) * TWIST + (strand==1 ? PI : 0.0);
  float y  = (float(i) - float(N-1)*0.5) * RISE;
  return vec3(RAD*cos(th), y, RAD*sin(th));
}

void mainImage(out vec4 O, in vec2 F){
  vec2 uv=(F-0.5*u_res.xy)/u_res.y;

  const float CYCLE=8.0;
  float t=mod(u_time,CYCLE*2.0);
  int   s=int(floor(t/CYCLE));
  float lt=mod(t,CYCLE);

  bool pal=true;
  for(int i=0;i<6;i++) if(baseAt(s,i)!=comp(baseAt(s,N-1-i))) pal=false;

  // slow spin, then the C2 half-turn about the HORIZONTAL axis through the centre
  float spin = lt*0.55;
  float c2   = smoothstep(3.0,5.4,lt) * PI;          // the symmetry operation itself
  mat3 M = rotY(spin) * rotZ(c2);

  vec3 col=vec3(0.035,0.04,0.055);

  // ---- per-pixel depth test over every atom and every rung sample
  float bestZ = 1e9;
  vec3  hit   = col;
  bool  got   = false;

  for(int i=0;i<6;i++){
    bool ok = (baseAt(s,i)==comp(baseAt(s,N-1-i)));

    // the two bases of this pair
    for(int st=0; st<2; st++){
      int b = (st==0) ? baseAt(s,i) : comp(baseAt(s,i));
      vec3 p = M * atomPos(i,st);
      float persp = 1.0/(1.0 + 0.55*p.z);            // nearer = larger
      vec2  sp = p.xy * persp;
      float r  = 0.062 * persp;
      float d  = length(uv-sp);
      if(d < r && p.z < bestZ){
        bestZ = p.z; got = true;
        // a sphere: lambert-ish shading from the silhouette distance
        float nz = sqrt(max(0.0, 1.0 - (d/r)*(d/r)));
        vec3  c  = baseCol(b);
        hit = c * (0.34 + 0.66*nz) + vec3(1.0)*pow(nz,18.0)*0.35;
      }
    }

    // THE BACKBONE: sugar-phosphate, joining consecutive bases ALONG each strand.
    // Without this the picture is a ladder; with it, it is a double helix -- the
    // two ribbons winding round each other are the thing everyone recognises.
    if(i < N-1){
      for(int st=0; st<2; st++){
        vec3 qa = M*atomPos(i,st), qb = M*atomPos(i+1,st);
        for(int k=0;k<=14;k++){
          vec3 p = mix(qa,qb,float(k)/14.0);
          float persp = 1.0/(1.0 + 0.55*p.z);
          vec2  sp = p.xy*persp;
          float r  = 0.030*persp;
          float d  = length(uv-sp);
          if(d < r && p.z < bestZ){
            bestZ = p.z; got = true;
            float nz = sqrt(max(0.0,1.0-(d/r)*(d/r)));
            vec3 c = (st==0) ? vec3(0.62,0.66,0.78) : vec3(0.45,0.49,0.62);
            hit = c*(0.35+0.65*nz) + vec3(1.0)*pow(nz,24.0)*0.25;
          }
        }
      }
    }

    // the base pair rung, sampled along its length so it can be occluded properly
    vec3 pa = M*atomPos(i,0), pb = M*atomPos(i,1);
    for(int k=1;k<34;k++){          // dense enough to read as a solid rung
      float f = float(k)/34.0;
      vec3 p = mix(pa,pb,f);
      float persp = 1.0/(1.0 + 0.55*p.z);
      vec2  sp = p.xy*persp;
      float r  = 0.024*persp;
      float d  = length(uv-sp);
      if(d < r && p.z < bestZ){
        bestZ = p.z; got = true;
        float nz = sqrt(max(0.0,1.0-(d/r)*(d/r)));
        // the rung carries the verdict for this pair
        vec3 c = ok ? vec3(0.75,0.95,0.80) : vec3(1.0,0.20,0.24);
        hit = c*(0.40+0.60*nz);
      }
    }
  }
  if(got) col = hit;

  // ---- the C2 axis it turns about, drawn as a faint horizontal line
  float axis = smoothstep(0.0025,0.0,abs(uv.y)) * smoothstep(0.60,0.30,abs(uv.x));
  col += vec3(0.30,0.36,0.50)*axis*(0.25+0.35*smoothstep(2.6,3.2,lt));

  // ---- verdict wash once the half-turn has completed
  float landed = smoothstep(5.2,5.5,lt);
  float wash   = landed*(1.0-smoothstep(7.0,7.9,lt));
  col += (pal?vec3(0.09,0.40,0.16):vec3(0.45,0.09,0.12))*wash
         *smoothstep(0.20,0.70,length(uv));

  col=pow(max(col,0.0),vec3(0.4545));
  O=vec4(col,1.0);
}

void main(){ mainImage(outColor, gl_FragCoord.xy); }
