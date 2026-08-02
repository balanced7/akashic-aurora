#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;
uniform float u_sub;      // subdivision density: how finely the shell is tiled
uniform float u_gap;      // tile separation: openness
uniform float u_spin;     // rotation rate
uniform float u_pulse;    // breathing amplitude
uniform float u_sat;      // colour saturation (0 = greyscale, for dead/unsensed)
uniform vec3  u_tint;     // state hue
uniform float u_dim;      // overall brightness
uniform float u_wire;     // 0 = lit solid shell, 1 = dark wireframe (edges carry the light)
uniform vec3  u_id0;      // agent identity gradient, start (the BODY -- who this is)
uniform vec3  u_id1;      // agent identity gradient, end
uniform float u_round;    // tile shape: 0 = hexagon, 1 = disc
uniform float u_star;     // tile shape: >0 scallops the border, <0 pulls it into points
uniform float u_see;      // see-through: how strongly the FAR side shows through the near

#define PI 3.14159265359

void pR(inout vec2 p,float a){p=cos(a)*p+sin(a)*vec2(p.y,-p.x);}
float pReflect(inout vec3 p,vec3 n,float o){float t=dot(p,n)+o;if(t<0.){p=p-(2.*t)*n;}return sign(t);}
float smax(float a,float b,float r){float m=max(a,b);if((-a<r)&&(-b<r)){return max(m,-(r-sqrt((r+a)*(r+a)+(r+b)*(r+b))));}return m;}

vec3 facePlane,uPlane,vPlane,nc,pab,pbc,pca;
void initIco(){
  float cospin=cos(PI/5.),scospin=sqrt(0.75-cospin*cospin);
  nc=vec3(-0.5,-cospin,scospin);
  pbc=normalize(vec3(scospin,0.,0.5)); pca=normalize(vec3(0.,scospin,cospin)); pab=vec3(0,0,1);
  facePlane=pca; uPlane=cross(vec3(1,0,0),facePlane); vPlane=vec3(1,0,0);
}
void pModIco(inout vec3 p){
  p=abs(p); pReflect(p,nc,0.); p.xy=abs(p.xy); pReflect(p,nc,0.); p.xy=abs(p.xy); pReflect(p,nc,0.);
}

const float sqrt3=1.7320508075688772; const float i3=0.5773502691896258;
const mat2 cart2hex=mat2(1,0,i3,2.*i3); const mat2 hex2cart=mat2(1,0,-.5,.5*sqrt3);
const float faceRadius=0.3819660112501051;

vec3 isect(vec3 n,vec3 pn,float po){return n*((dot(vec3(0),pn)+po)/-dot(pn,n));}
vec2 icoFaceCoord(vec3 p){vec3 i=isect(normalize(p),facePlane,-1.);return vec2(dot(i,uPlane),dot(i,vPlane));}
vec3 faceToSphere(vec2 f){return normalize(facePlane+(uPlane*f.x)+(vPlane*f.y));}

struct TP{vec2 a;vec2 b;vec2 c;vec2 ctr;vec2 ab;vec2 bc;vec2 ca;};
TP closestTri(vec2 p){
  vec2 pt=cart2hex*p, pi=floor(pt), pf=fract(pt);
  float s1=step(pf.y,pf.x), s2=step(pf.x,pf.y);
  vec2 a=vec2(s1,1)+pi,b=vec2(1,s2)+pi,c=pi;
  a=hex2cart*a; b=hex2cart*b; c=hex2cart*c;
  return TP(a,b,c,(a+b+c)/3.,(a+b)/2.,(b+c)/2.,(c+a)/2.);
}
struct TP3{vec3 a;vec3 b;vec3 c;vec3 ctr;vec3 ab;vec3 bc;vec3 ca;};
TP3 geoTri(vec3 p,float sub){
  vec2 uv=icoFaceCoord(p); float s=sub/faceRadius/2.; TP t=closestTri(uv*s);
  return TP3(faceToSphere(t.a/s),faceToSphere(t.b/s),faceToSphere(t.c/s),faceToSphere(t.ctr/s),
             faceToSphere(t.ab/s),faceToSphere(t.bc/s),faceToSphere(t.ca/s));
}

vec3 pal(float t,vec3 a,vec3 b,vec3 c,vec3 d){return a+b*cos(6.28318*(c*t+d));}
vec3 spectrum(float n){return pal(n,vec3(.5),vec3(.5),vec3(1.),vec3(0.,.33,.67));}

struct Model{float d;vec3 col;float glow;};
Model hexModel(vec3 p,vec3 hc,vec3 eA,vec3 eB,float sub){
  float rTop=.05/sub, rCor=(.10+.62*u_round)/sub;
  // BREATHING: the shell height oscillates with u_pulse. At pulse 0 it is a still solid.
  float phase=dot(hc,pca)*22.+u_time*2.5;
  float h=2.-u_pulse*.16*(cos(phase)*.5+.5);
  float th=h;
  float eAd=dot(p,eA)+u_gap, eBd=dot(p,eB)-u_gap;
  float ed=smax(eAd,-eBd,rCor);
  float ang=atan(dot(p,eB),dot(p,eA));
  ed+=u_star*(.040/sub)*cos(6.*ang);
  float d=smax(ed,length(p)-h,rTop);
  d=smax(d,-(length(p)-h+th),rTop);
  float fb=clamp((h-length(p))/th,0.,1.);
  vec3 solidFace=mix(vec3(.9,.9,1.),vec3(.10,.10,.15),step(.5,fb));
  float gt=clamp(.5+.62*dot(normalize(hc),normalize(vec3(.7,.7,0.))),0.,1.);
  vec3 ident=mix(u_id0,u_id1,gt);
  ident=mix(vec3(dot(ident,vec3(.33))),ident,u_sat);   // a dead seat shows no vivid identity
  vec3 wireFace=ident*.062;                      // dim: a body to be read, not a lamp
  vec3 col=mix(solidFace,wireFace,u_wire);       // shell readable as a body, not a hole
  vec3 ec=spectrum(dot(hc,pca)*5.+length(p)+.8);
  ec=mix(vec3(dot(ec,vec3(.33))),ec,u_sat);      // desaturate for dead / unsensed
  ec=mix(ec,u_tint,mix(.45,.88,u_wire));         // wireframe leans hard on the state hue: with
                                                 // the faces dark, the lines ARE the signal
  float ew=mix(.120,.090,u_wire);
  float eb=smoothstep(-ew,-.004,ed);
  vec3 wd=normalize(vec3(sin(u_time*.083),cos(u_time*.061),sin(u_time*.047+1.7)));
  float wv=smoothstep(.72,1.,cos(dot(hc,wd)*3.4-u_time*.85));
  ec*=1.+1.5*wv;
  eb=min(1.,eb*(1.+.55*wv));
  return Model(d,mix(col,ec,eb),eb);
}
Model opU(Model a,Model b){if(a.d<b.d){return a;}return b;}

Model map(vec3 p){
  pR(p.xz,u_time*u_spin);
  pR(p.xy,.35);
  pModIco(p);
  float sub=u_sub;
  TP3 t=geoTri(p,sub);
  vec3 eAB=normalize(cross(t.ctr,t.ab)),eBC=normalize(cross(t.ctr,t.bc)),eCA=normalize(cross(t.ctr,t.ca));
  Model m=hexModel(p,t.b,eAB,eBC,sub);
  m=opU(m,hexModel(p,t.c,eBC,eCA,sub));
  m=opU(m,hexModel(p,t.a,eCA,eAB,sub));
  return m;
}

vec3 calcNormal(vec3 p){
  const vec2 k=vec2(1,-1); const float e=.0015;
  return normalize(k.xyy*map(p+k.xyy*e).d + k.yyx*map(p+k.yyx*e).d +
                   k.yxy*map(p+k.yxy*e).d + k.xxx*map(p+k.xxx*e).d);
}

void main(){
  initIco();
  vec2 uv=(-u_res.xy+2.*gl_FragCoord.xy)/u_res.y;
  vec3 ro=vec3(0,0,-5.5), rd=normalize(vec3(uv,2.));
  float t=0.; Model m; bool hit=false;
  // 48 steps, not the original 100: at avatar size the surface converges long before that,
  // and the step count is the single biggest lever on GPU cost.
  float cone=1e9;
  for(int i=0;i<48;i++){
    m=map(ro+rd*t);
    if(t>.001) cone=min(cone,m.d/t);
    if(m.d<.0015){hit=true;break;}
    t+=m.d*.9;
    if(t>9.)break;
  }
  vec3 col=vec3(0.);
  float alpha=0.;
  if(hit){
    vec3 pos=ro+rd*t, n=calcNormal(pos);
    vec3 lig=normalize(vec3(.5,.5,-1.)), bl=normalize(vec3(-.5,-.3,1.));
    float amb=clamp((dot(n,vec3(0,1,0))+1.)/2.,0.,1.);
    float dif=clamp(dot(n,lig),0.,1.);
    float bac=pow(clamp(dot(n,bl),0.,1.),1.5);
    float fre=pow(clamp(1.+dot(n,rd),0.,1.),2.);
    vec3 lin=1.20*dif*vec3(.9)+0.80*amb*vec3(.5,.7,.8)+0.30*bac*vec3(.25)+0.25*fre*u_tint;
    vec3 wlin=0.22*lin+1.05*fre*u_tint;
    lin=mix(lin,wlin,u_wire);
    col=mix(m.col*lin,m.col,m.glow)*u_dim;
    alpha=1.;
  }else{
    float px=1./u_res.y;
    float cov=1.-smoothstep(0.,px*1.6,cone);
    col=u_tint*mix(.42,.75,u_wire)*cov;
    alpha=cov*mix(.80,.95,u_wire);
  }
  if(u_see>.001){
    float bb=dot(ro,rd), cc=dot(ro,ro)-4.0;
    float dd=bb*bb-cc;
    if(dd>0.){
      Model mb=map(ro+rd*(-bb+sqrt(dd)));
      col+=mb.col*mb.glow*u_see*.55*u_dim;
      alpha=max(alpha,mb.glow*u_see*.9);
    }
  }
  col=pow(max(col,0.),vec3(1./2.2));
  outColor=vec4(col,alpha);   // transparent background: the avatar sits on the console glass
}