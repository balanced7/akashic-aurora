#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;

// ingested: aurora-bus
#define iTime (u_time)
#define iResolution vec3(u_res, 1.0)
#define iMouse vec4(0.0)
#define iTimeDelta (1.0 / 60.0)
#define iFrameRate (60.0)
#define iFrame (int(u_time * 60.0))
#define iSampleRate (44100.0)
#define iDate vec4(2026.0, 1.0, 1.0, u_time)

// aurora-bus v4 -- "the confluence". Three ancestries, one sky. 2026-08-05 night.
//
//   CURTAINS  from the domain-warped fbm lights engine Daniil brought (shader 2):
//             pnoise -> fbm -> fbm2 warp, three bands, adapted to our palette.
//   ATMOSPHERE from the ray-marched snowfield aurora he brought (shader 1): the
//             pre-dawn horizon glow, glow-falloff star flicker, ACES tonemap.
//             Its volumetric AABB march needs texture LUTs (blue noise, 3D noise
//             channels) the bench has no channels for -- so noise is COMPUTED here,
//             not fetched, and the march is traded for screen-space curtains.
//   PROTAGONISTS from tonight's ledger (friction reader, window 168h):
//             six DEAD embers -- 1785557712632-0 opus-engineer,
//             1785608643316-0 cursor_grok, 1785807236486-0 + 1785807344131-0
//             deepseek-review, 1785818090897-0 t147probe, 1785818587838-0 codex_root
//             one ECHO -- 1785818229175-0 (settled from the ledger; no message existed)
//             one OPEN -- 1785985931818-0 claude -> deepseek, breathing, overdue.
//
//   THE HONEST PHYSICS: DEAD_RATE gates the rose crown -- real auroras only wear
//   red on violent nights, and tonight was 6 dead of 7 closed. The sky is pre-dawn
//   ON PURPOSE: the first ANSWERED star hasn't risen yet. Both facts re-render.

#define PI 3.14159265
const float DEAD_RATE = 0.857;      // 6/7, 2026-08-05 -- thin the crown by re-rendering

// ---------------- noise, all computed (no LUT channels on the bench) ----------------
float hash(vec2 co){ return fract(sin(dot(co, vec2(12.9898,78.233)))*43758.5453); }

float shash(vec2 co){
  float x=co.x, y=co.y;
  float corners=(hash(vec2(x-1.,y-1.))+hash(vec2(x+1.,y-1.))
                +hash(vec2(x-1.,y+1.))+hash(vec2(x+1.,y+1.)))/16.;
  float sides=(hash(vec2(x-1.,y))+hash(vec2(x+1.,y))
              +hash(vec2(x,y-1.))+hash(vec2(x,y+1.)))/8.;
  return corners+sides+hash(co)/4.;
}

float noise2(vec2 co){
  vec2 pos=floor(co), fpos=co-pos;
  fpos=(3.0-2.0*fpos)*fpos*fpos;
  float c1=shash(pos), c2=shash(pos+vec2(0,1));
  float c3=shash(pos+vec2(1,0)), c4=shash(pos+vec2(1,1));
  return mix(mix(c1,c3,fpos.x), mix(c2,c4,fpos.x), fpos.y);
}

float pnoise(vec2 co, int oct){
  float total=0.0, m=0.0;
  for(int i=0;i<4;i++){
    if(i>=oct) break;
    float freq=pow(2.0,float(i)), amp=pow(0.5,float(i));
    total+=noise2(freq*co)*amp; m+=amp;
  }
  return total/m;
}

vec2 fbmv(vec2 p, int oct, float t){
  return vec2(pnoise(p+vec2(t,0.),oct), pnoise(p+vec2(-t,0.),oct));
}
float fbm2(vec2 p, int oct, float t){
  return pnoise(p + 10.*fbmv(p,oct,t) + vec2(0.,t), oct);
}

float getGlow(float d, float r, float i){ d=max(d,1e-6); return pow(r/d,i); }
vec3 ACESFilm(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.,1.); }
float star(vec2 p, vec2 pos, float size){ float d=length(p-pos); return exp(-d*d/(size*size)); }

// -------- the curtain engine (shader 2's lights, in our palette + our meaning) --------
// crownGain arrives from mainImage: DEAD_RATE lives where the meaning lives, and the
// reference render taught that the red band is a HEAVYWEIGHT -- ungated it eats the
// sky (v4's strawberry ceiling). Even a 100% dead-rate night wears a fringe, never a lid.
vec3 lights(vec2 co, float t, float crownGain){
  float d=pnoise(2.*co+vec2(0.3*t),1);

  // the rose crown: their red band, now a thin high wound
  float r=fbm2(co*vec2(1.0,0.5),1,t);
  vec3 rc=crownGain*vec3(0.85,0.10,0.22)*r
        *smoothstep(0.0,2.5+d*r,co.y)*smoothstep(-5.,1.,5.-co.y-2.*d);

  // teal-green heart, two warp layers
  float g=fbm2(co*vec2(2.,0.5),4,t);
  vec3 gc=0.8*vec3(0.20,1.0,0.55)*clamp(2.*pow((3.-2.*g)*g*g,2.5)-0.5*co.y,0.,1.)
        *smoothstep(-2.*d,0.,co.y)*smoothstep(0.,0.3,1.1+d-co.y);
  float g2=fbm2(co*vec2(1.0,0.2),2,t);
  gc+=0.5*vec3(0.30,0.90,0.75)*clamp(2.*pow((3.-2.*g2)*g2*g2,2.5)-0.5*co.y,0.,1.)
        *smoothstep(-2.*d,0.,co.y)*smoothstep(0.,0.3,1.1+d-co.y);

  // icy fringe along the underside
  float h=pnoise(vec2(5.*co.x,2.0*t),1);
  vec3 hc=vec3(0.0,0.65,1.0)*pow(h+0.1,2.0)
        *smoothstep(-2.*d,0.,co.y+0.2)*smoothstep(-h,0.,-co.y-0.4);

  return rc+gc+hc;
}

void mainImage(out vec4 O, in vec2 fragCoord){
  vec2 R=iResolution.xy;
  vec2 uv=fragCoord/R;
  vec2 co=fragCoord/R.y;                   // aspect-true space
  float aspect=R.x/R.y;
  float t=iTime*0.5;                       // contemplative tempo

  // pre-dawn sky: deep indigo, and low on the right a rose-amber promise
  vec3 col=mix(vec3(0.008,0.012,0.030), vec3(0.016,0.038,0.052), pow(1.0-uv.y,2.0));
  float dawn=getGlow(distance(co,vec2(aspect*0.88,-0.10)),0.40,1.6);
  col+=vec3(1.0,0.28,0.06)*0.030*dawn;

  // stars: hashed cells with glow-falloff flicker (shader 1's technique, 2D)
  vec2 g=fragCoord/5.0;
  float hs=hash(floor(g));
  if(hs>0.982){
    float fl=2.5-2.0*sin(hs*97.0+iTime*(1.5+2.0*fract(hs*13.0)));
    col+=vec3(0.75,0.82,1.0)*0.045*getGlow(length(fract(g)-0.5),0.11,max(fl,0.4));
  }

  // curtains: bend the base line with slow noise (their aco transform, kept).
  // The crown only exists high in the FRAME and only as DEAD_RATE allows -- rose
  // fringe above the green, thinning on re-render as the verb earns answers.
  float crownGain=DEAD_RATE*0.30*smoothstep(0.42,0.88,uv.y);
  float f=0.30+0.40*pnoise(vec2(5.*uv.x,0.3*t),1);
  vec2 aco=co; aco.y-=f; aco*=10.*uv.x+5.0;
  vec3 cur=0.5*lights(aco,t,crownGain)
      *(smoothstep(0.3,0.6,pnoise(vec2(10.*uv.x,0.3*t),1))
      +0.5*smoothstep(0.5,0.7,pnoise(vec2(10.*uv.x,t),1)));
  col+=cur;

  // the ridge: slow-dreaming perlin mountains occlude sky and curtains
  float ridge=pnoise(vec2(20.*co.x,0.02*iTime),2);
  float ridgeY=ridge*0.2+0.10;
  if(co.y<ridgeY){
    vec3 rock=vec3(0.010,0.012,0.020);
    rock+=cur*0.16;                        // aurora light resting on the snow crest
    rock+=vec3(1.0,0.28,0.06)*0.012*dawn;  // dawn touches the ground too
    vec2 sco=co*500.0;                     // snow sparkle, truly on the ground now
    if(hash(floor(sco))<0.004){
      float s1=hash(floor(sco)*1.7);
      float s2=max(1.-2.*distance(vec2(0.5),fract(sco)),0.0);
      rock+=vec3(s1*s2)*0.55;
    }
    col=rock;
  }

  // ---------------- the protagonists ----------------
  // six embers: watchfires just beyond the ridge, halos bleeding over the crest
  for(int i=0;i<6;i++){
    float fi=float(i);
    float px=(0.09+0.150*fi+0.012*sin(fi*7.0))*aspect;
    float ry=pnoise(vec2(20.*px,0.02*iTime),2)*0.2+0.10;
    vec2 p=vec2(px,ry-0.018);
    float gutter=0.40+0.26*sin(iTime*0.7+fi*2.2)+0.20*noise2(vec2(iTime*0.9,fi*5.0));
    col+=vec3(0.90,0.30,0.09)*gutter*star(co,p,0.010);
    col+=vec3(0.50,0.11,0.03)*gutter*0.5*star(co,p,0.026);
  }

  // the echo: calm green, in the quiet air below the curtains
  vec2 pe=vec2(0.26*aspect,0.30);
  float calm=0.60+0.08*sin(iTime*0.8);
  col+=vec3(0.25,0.95,0.45)*calm*star(co,pe,0.012);
  col+=vec3(0.10,0.55,0.25)*calm*0.40*star(co,pe,0.030);

  // the open ask: high above everything, breathing on a warm floor, overdue
  float breath=0.38+0.42*(0.5+0.5*sin(iTime*2.6));
  vec2 po=vec2(0.55*aspect,0.86-0.012*(0.5+0.5*sin(iTime*1.3)));
  col+=vec3(0.78,0.95,1.00)*breath*star(co,po,0.017);
  col+=vec3(0.30,0.75,1.00)*breath*0.38*star(co,po,0.050);

  // shader 1's finishing discipline: filmic first, then gamma
  col=ACESFilm(col);
  O=vec4(pow(col,vec3(0.4545)),1.0);
}

void main(){ mainImage(outColor, gl_FragCoord.xy); }
