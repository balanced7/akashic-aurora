import { GPUComputationRenderer } from 'three/addons/misc/GPUComputationRenderer.js';
import { createGestureModel, createWorldJourney, clamp, approach } from './spectacle-motion.js';
import { createWorlds } from './spectacle-worlds.js';
import { createVoicings, notePathGLSL } from './spectacle-voicing.js';
import { createMoonwater } from './moonwater.js';
import { MODES } from './harmony-model.js';
import { createHarmonyRenderer } from './harmony-renderer.js';

// Original shaders, informed by the house's aurora, curtains, snowfield and
// highlight-shoulder studies. All layers render into the piano's own HDR canvas.
const THEMES = {
  moon: { name:'Moonlit lake', a:0x74dfd0, b:0x577bdb, c:0xd4c396, body:0x08191f, ivory:0xbacdd0, weather:0, metal:.42 },
  ember: { name:'Ember sanctuary', a:0xffa65f, b:0x9b415b, c:0xffdda3, body:0x24100d, ivory:0xceae89, weather:3, metal:.66 },
  nebula: { name:'Velvet nebula', a:0xae8bef, b:0x386db0, c:0xeeb5de, body:0x150b26, ivory:0xc1b6cf, weather:0, metal:.5 },
  winter: { name:'Winter mountains', a:0xa3d4ee, b:0x6d79b4, c:0xe5f5fc, body:0x102334, ivory:0xd5e1e5, weather:2, metal:.22 },
  rain: { name:'Rainforest at midnight', a:0x5ba8a0, b:0x435c78, c:0xc4d3ac, body:0x080e1b, ivory:0xa8b6be, weather:1, metal:.78 },
  city: { name:'City of light', a:0x54d5e4, b:0x704ac2, c:0xffabdc, body:0x080b20, ivory:0xc0c4d4, weather:0, metal:.82 },
};
const QUALITY = { studio:{name:'Studio · 1080p',scale:1,count:32768}, ultra:{name:'Ultra · 1440p',scale:4/3,count:65536}, cinema:{name:'Cinema · 4K',scale:2,count:131072} };
const read = () => { try { return JSON.parse(localStorage.getItem('arsenal.piano.spectacle') || '{}'); } catch { return {}; } };
const hashGLSL = `float hash(float p){p=fract(p*.1031);p*=p+33.33;p*=p+p;return fract(p);}
vec3 random3(float n){return vec3(hash(n+1.7),hash(n+8.1),hash(n+21.3));}`;
const computeCommon = `
uniform sampler2D uNotes,uKeyMotion,uRipple;
uniform vec4 uRippleBounds;
uniform float uTime,uDt,uPedal,uEnergy,uCalm,uTension,uImpact,uHitX,uMotion,uTheme,uFlow;
${hashGLSL}
void source(out float id,out vec4 note,out vec4 meta,out vec3 seed){
 vec2 uv=gl_FragCoord.xy/resolution.xy;
 id=floor(gl_FragCoord.y)*resolution.x+floor(gl_FragCoord.x);
 float key=mod(id,88.0);
 note=texture2D(uNotes,vec2((key+.5)/88.0,.25));
 meta=texture2D(uNotes,vec2((key+.5)/88.0,.75));seed=random3(id);
}
float lifeFor(vec3 seed,vec4 meta){return 3.4+seed.y*4.0;}
bool emit(float id,vec4 note,vec3 seed){float key=mod(id,88.0);float phase=texture2D(uKeyMotion,vec2((key+.5)/88.0,.5)).w;
 return note.z>.5 && fract(phase+seed.z)<uDt*(.6+note.y*note.y*1.8);}
vec3 spawn(vec4 note,vec3 seed){float y=1.15+seed.z*seed.z*(1.5+note.y*5.0);
 return vec3(note.x+(seed.x-.5)*1.0+sin(y*.18+uFlow*.6)*.6,y,-3.7+(seed.y-.5)*2.0);}
vec3 launch(vec4 note,vec4 meta,vec3 seed){
 float power=note.y*note.y;float bright=step(.58,meta.w);
 float angle=seed.x*6.2831853,spread=seed.y*seed.y*(.7+power*12.0);
 return vec3(cos(angle)*spread,2.8+power*(9.0+seed.z*27.0)+bright*1.5,sin(angle)*spread*.7);
}`;

export function createSpectacle(ctx) {
  const { THREE, scene, renderer, camera, keys, lacquer, floor, railLine, bloom } = ctx;
  const stored = read();
  const settings = { theme:THEMES[stored.theme] ? stored.theme : 'moon', enabled:stored.enabled !== false,
    quality:QUALITY[stored.quality] ? stored.quality : 'ultra', weather:['world','none','rain','snow','embers'].includes(stored.weather) ? stored.weather : 'world',
    intensity:clamp(Number(stored.intensity) || .85,.25,1.4), harmony:stored.harmony !== false, waveform:stored.waveform !== false, autoWorld:stored.autoWorld===true,
    journey:clamp(Number(stored.journey)||0,0,1),
    harmonyMode:MODES[stored.harmonyMode] ? stored.harmonyMode : 'tonnetz',
    labels:stored.theoryVersion===3 && ['harmony','full','chord','off'].includes(stored.labels) ? stored.labels : 'harmony',theoryVersion:3,
    motion:matchMedia('(prefers-reduced-motion: reduce)').matches ? .25 : clamp(Number(stored.motion)||1,.15,1) };
  const model = createGestureModel(), journey=createWorldJourney(), group = new THREE.Group(); group.name = 'Piano atmosphere'; scene.add(group);
  const resources = [], original = new Map();
  for (const material of [lacquer,floor.material,...[...keys.values()].map(k=>k.material)]) {
    original.set(material,{color:material.color.clone(),roughness:material.roughness,metalness:material.metalness});
  }
  const baseBloom = {strength:bloom.strength,radius:bloom.radius,threshold:bloom.threshold};
  const baseRail = railLine.material.color.clone();
  const cA=new THREE.Color(), cB=new THREE.Color(), cC=new THREE.Color(), body=new THREE.Color(), ivory=new THREE.Color(), temp=new THREE.Color();
  const targetA=new THREE.Color(),targetB=new THREE.Color(),targetC=new THREE.Color();
  const noteData=new Float32Array(88*2*4), noteTex=new THREE.DataTexture(noteData,88,2,THREE.RGBAFormat,THREE.FloatType);
  noteTex.minFilter=noteTex.magFilter=THREE.NearestFilter; noteTex.needsUpdate=true; resources.push(noteTex);
  for(let i=0;i<88;i++){noteData[i*4]=ctx.keyX(i+21);noteData[352+i*4]=-9999;noteData[352+i*4+1]=-9999;noteData[352+i*4+3]=(i+21)/127;}
  const keyTex=new THREE.DataTexture(model.keyMotion,88,1,THREE.RGBAFormat,THREE.FloatType);resources.push(keyTex);
  const uniforms={uNotes:{value:noteTex},uTime:{value:0},uDt:{value:.016},uPedal:{value:0},uEnergy:{value:0},uCalm:{value:0},
    uTension:{value:0},uImpact:{value:0},uHitX:{value:0},uMotion:{value:1},uA:{value:cA},uB:{value:cB},uC:{value:cC},
    uOpacity:{value:1},uPx:{value:1080},uWeather:{value:0},uWeatherTime:{value:0},uFlow:{value:0},
    uKeyMotion:{value:keyTex},uTheme:{value:0},uForce:{value:0},uPresence:{value:0},uFocusX:{value:0},
    uStageCentre:{value:new THREE.Vector3()},uStageSize:{value:new THREE.Vector2(30,20)},uNoteBounds:{value:new THREE.Vector3(-50,50,28)}};
  const stageOrigin=new THREE.Vector3(),stageCorner=new THREE.Vector3();
  function stageAt(x,y,out,z=-30){out.set(x,y,.5).unproject(camera);out.sub(camera.position).multiplyScalar((z-camera.position.z)/out.z).add(camera.position);return out;}
  let gpu=null,posVar=null,velVar=null,particles=null,particleCount=0,gpuError=null,disposed=false;
  let flow=0,weatherTime=0,lastImpact=-1,lastMaterialTheme='',smoothedWeather=0;
  const cloneUniforms = extra => ({...uniforms,...extra});
  const worldGroup=new THREE.Group(),voicingGroup=new THREE.Group(),legacyObjects=[];
  group.add(worldGroup,voicingGroup);
  const worlds=createWorlds(THREE,worldGroup,uniforms,ctx);
  group.add(worlds.waveform);
  const voicings=createVoicings(THREE,voicingGroup,uniforms,model,ctx);
  const moonwater=createMoonwater(THREE,group,uniforms,model,ctx);
  const harmonyView=createHarmonyRenderer(THREE,group,model,ctx);
  function material(geometry,options,points=false){
    const mat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,...options});
    const mesh=points?new THREE.Points(geometry,mat):new THREE.Mesh(geometry,mat);
    mesh.frustumCulled=false; group.add(mesh);legacyObjects.push(mesh); resources.push(geometry,mat); return mesh;
  }

  function buildParticles(count){
    if(gpu){gpu.dispose();gpu=null;}
    if(particles){group.remove(particles);particles.geometry.dispose();particles.material.dispose();particles=null;}
    particleCount=count;
    const width=256,height=count/256;
    gpu=new GPUComputationRenderer(width,height,renderer);
    const p0=gpu.createTexture(),v0=gpu.createTexture();
    for(let i=0;i<count;i++){p0.image.data[i*4+1]=-100;p0.image.data[i*4+3]=100;v0.image.data[i*4+3]=-9999;}
    velVar=gpu.addVariable('textureVelocity',computeCommon+`
      void main(){
       vec2 uv=gl_FragCoord.xy/resolution.xy;vec4 pos=texture2D(texturePosition,uv),vel=texture2D(textureVelocity,uv);
       float id;vec4 note,meta;vec3 seed;source(id,note,meta,seed);
       bool respawn=pos.w>lifeFor(seed,meta) && emit(id,note,seed);
       if(respawn){gl_FragColor=vec4(launch(note,meta,seed),note.y);return;}
       vec3 p=pos.xyz*.22;
       vec3 curl=vec3(cos(p.y+uTime*.19)-sin(p.z-uTime*.13),cos(p.z+uTime*.17)-sin(p.x+uTime*.12),cos(p.x-uTime*.11)-sin(p.y+uTime*.15));
       float suspended=step(1.5,meta.z)*uPedal;
       float dry=step(.5,meta.z)*(1.0-step(1.5,meta.z));
       vec3 force=curl*(.65+uCalm*1.7+uTension*2.2)*uMotion;
       vec2 q=(pos.xz-uRippleBounds.xy)/uRippleBounds.zw,texel=vec2(1.0/256.0);
       vec2 gradient=vec2(texture2D(uRipple,q+vec2(texel.x,0)).r-texture2D(uRipple,q-vec2(texel.x,0)).r,
         texture2D(uRipple,q+vec2(0,texel.y)).r-texture2D(uRipple,q-vec2(0,texel.y)).r);
       float wave=texture2D(uRipple,q).g;
       force+=vec3(-gradient.x*12.0,wave*.3,-gradient.y*12.0)*exp(-max(0.0,pos.y)*.045)*uMotion;
       force.x+=sin(pos.y*.18+uFlow*.6)*.6*uMotion;
       float ember=1.0-smoothstep(0.0,.6,abs(uTheme-1.0)),nebula=1.0-smoothstep(0.0,.6,abs(uTheme-2.0));
       float winter=1.0-smoothstep(0.0,.6,abs(uTheme-3.0));
       force.y+=mix(-1.8,.8,uPedal)+suspended*.9-dry*8.0+ember*2.2+winter*.6;
       force.xz+=vec2(-vel.z,vel.x)*nebula*.85;
       force.x+=(note.x-pos.x)*(.1+uCalm*.22);
       vec3 delta=pos.xyz-vec3(uHitX,2.0,-4.0);float dist=length(delta);
       force+=delta/max(dist,.5)*uImpact*9.0*exp(-dist*.035);
       vel.xyz=(vel.xyz+force*uDt)*exp(-uDt*(.3+uCalm*.5+suspended*.3));
       if(pos.y<-.7 && vel.y<0.0)vel.y=abs(vel.y)*.35;
       vel.xyz=clamp(vel.xyz,vec3(-40),vec3(40));gl_FragColor=vec4(vel.xyz,vel.w);
      }`,v0);
    posVar=gpu.addVariable('texturePosition',computeCommon+`
      void main(){
       vec2 uv=gl_FragCoord.xy/resolution.xy;vec4 pos=texture2D(texturePosition,uv),vel=texture2D(textureVelocity,uv);
       float id;vec4 note,meta;vec3 seed;source(id,note,meta,seed);
       bool respawn=pos.w>lifeFor(seed,meta) && emit(id,note,seed);
       if(respawn){gl_FragColor=vec4(spawn(note,seed),0.0);return;}
       pos.xyz+=vel.xyz*uDt*uMotion;pos.w+=uDt;gl_FragColor=pos;
      }`,p0);
    gpu.setVariableDependencies(velVar,[posVar,velVar]);gpu.setVariableDependencies(posVar,[posVar,velVar]);
    Object.assign(velVar.material.uniforms,uniforms);Object.assign(posVar.material.uniforms,uniforms);
    gpuError=gpu.init();
    if(gpuError){gpu.dispose();gpu=null;ctx.toast('Particle simulation unavailable: '+gpuError,true);return;}
    const geometry=new THREE.BufferGeometry(),uv=new Float32Array(count*2),ids=new Float32Array(count);
    for(let i=0;i<count;i++){uv[i*2]=(i%width+.5)/width;uv[i*2+1]=(Math.floor(i/width)+.5)/height;ids[i]=i;}
    geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(count*3),3));
    geometry.setAttribute('aUv',new THREE.BufferAttribute(uv,2));geometry.setAttribute('aId',new THREE.BufferAttribute(ids,1));
    const mat=new THREE.ShaderMaterial({uniforms:cloneUniforms({uPosition:{value:null},uVelocity:{value:null}}),transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,
      vertexShader:`uniform sampler2D uPosition,uVelocity,uNotes,uKeyMotion;uniform float uPx,uOpacity,uTime;attribute vec2 aUv;attribute float aId;
      varying float vAlpha,vShape,vPower,vAngle;varying vec3 vColor;uniform vec3 uA,uB,uC;${hashGLSL}
      void main(){vec4 p=texture2D(uPosition,aUv);float k=mod(aId,88.0);vec4 n=texture2D(uNotes,vec2((k+.5)/88.0,.25));vec4 meta=texture2D(uNotes,vec2((k+.5)/88.0,.75));
       vec4 velocity=texture2D(uVelocity,aUv);float level=texture2D(uKeyMotion,vec2((k+.5)/88.0,.5)).z;
       float seed=hash(aId+3.8);float life=3.4+hash(aId+8.1)*4.0;
       float tail=(1.0-smoothstep(life*.45,life,p.w))*smoothstep(0.0,.12,p.w);float audible=.25+level*.75;
       vPower=max(0.0,velocity.w)*max(0.0,velocity.w);vAlpha=tail*audible*(.3+vPower*.65)*(.35+seed*.65)*uOpacity;vShape=meta.z;
       vColor=mix(uA,uC,.3+vPower*.55);vColor=mix(vColor,uB,seed*.25);
       vec4 mv=modelViewMatrix*vec4(p.xyz,1.0);gl_Position=projectionMatrix*mv;
       vec3 direction=(modelViewMatrix*vec4(velocity.xyz,0.0)).xyz;vAngle=atan(direction.y,direction.x);
       gl_PointSize=clamp((.10+seed*.13+vPower*.3)*uPx/max(2.0,-mv.z),1.0,30.0);
       if(vAlpha<.002||p.w>life||meta.x< -9000.0)gl_PointSize=0.0;
      }`,
      fragmentShader:`uniform float uTheme;varying float vAlpha,vShape,vPower,vAngle;varying vec3 vColor;void main(){vec2 p=gl_PointCoord-.5;float r=length(p);if(r>.5)discard;
       float core=exp(-r*r*38.0);float halo=exp(-r*r*10.0)*.14;
       vec2 q=mat2(cos(vAngle),-sin(vAngle),sin(vAngle),cos(vAngle))*p;
       float shard=exp(-q.y*q.y*220.0)*exp(-q.x*q.x*13.0);
       float shape=mix(core+halo,shard,vPower*.8);
       shape=mix(shape,shard,step(.5,vShape)*(1.0-step(1.5,vShape)));
       float winter=1.0-smoothstep(0.0,.6,abs(uTheme-3.0)),city=1.0-smoothstep(0.0,.6,abs(uTheme-5.0));
       float crystal=pow(max(0.0,cos(atan(p.y,p.x)*3.0)),10.0)*exp(-r*5.0)+core*.4;
       shape=mix(shape,crystal,winter);shape=mix(shape,exp(-max(abs(p.x),abs(p.y))*14.0),city);
       gl_FragColor=vec4(vColor*(1.0+core*.6),shape*vAlpha);
      }`});
    particles=new THREE.Points(geometry,mat);particles.frustumCulled=false;group.add(particles);
  }

  // Luminous threads retain note identity while their upper ends gather into mist.
  const threadGeo=new THREE.InstancedBufferGeometry(),threadBase=new THREE.PlaneGeometry(2.2,1,1,96);
  threadBase.translate(0,.5,0);threadGeo.setIndex(threadBase.getIndex());
  threadGeo.setAttribute('position',threadBase.getAttribute('position'));threadGeo.setAttribute('uv',threadBase.getAttribute('uv'));
  threadGeo.setAttribute('aNote',new THREE.InstancedBufferAttribute(Float32Array.from({length:88},(_,i)=>i),1));threadGeo.instanceCount=88;
  threadBase.dispose();
  const threads=material(threadGeo,{uniforms,side:THREE.DoubleSide,
    vertexShader:notePathGLSL+`attribute float aNote;varying vec2 vUv;varying float vAlpha,vTone;
    void main(){vec4 n=texture2D(uNotes,vec2((aNote+.5)/88.0,.25));vec4 meta=texture2D(uNotes,vec2((aNote+.5)/88.0,.75));
     vec4 movement=texture2D(uKeyMotion,vec2((aNote+.5)/88.0,.5));float power=movement.z*movement.z;
     vAlpha=movement.z*(.45+power*.65);vTone=fract(meta.w*127.0/12.0);vUv=uv;
     vec3 p=notePath(aNote,position.y);p.x+=position.x*(.55+power*1.1+uCalm*.25);
     gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);
    }`,fragmentShader:`uniform vec3 uA,uB,uC;uniform float uOpacity,uCalm,uFlow;varying vec2 vUv;varying float vAlpha,vTone;
    void main(){float edge=pow(max(0.0,1.0-abs(vUv.x-.5)*2.0),2.0);float d=(vUv.x-.5-sin(vUv.y*12.0-uFlow*.4)*.13)*24.0;float line=exp(-d*d);
     float fade=pow(max(0.0,1.0-vUv.y),1.7)*smoothstep(0.0,.025,vUv.y);vec3 c=mix(uA,uB,vTone*.6);
     gl_FragColor=vec4(mix(c,uC,line*.42)*(1.0+line*.6),fade*(edge*.24+line*.32)*vAlpha*uOpacity);
    }`});

  // A middle-distance focal form: three twisting silk surfaces open with the phrase.
  // The phase is continuous. Dynamics change its reach, not the animation's clock.
  for(let layer=0;layer<3;layer++){
    const veil=material(new THREE.PlaneGeometry(1,1,256,10),{uniforms:cloneUniforms({uLayer:{value:layer}}),side:THREE.DoubleSide,
      vertexShader:`uniform float uFlow,uForce,uPresence,uImpact,uCalm,uMotion,uLayer,uFocusX,uTheme;uniform vec3 uStageCentre;uniform vec2 uStageSize;
        varying vec2 vUv;varying float vFold;
        void main(){vUv=uv;float a=uv.x*6.2831853,across=uv.y-.5;
          float phase=uFlow*.18+uLayer*2.0944,radius=(.74+uLayer*.12);
          float winter=1.0-smoothstep(0.0,.6,abs(uTheme-3.0)),ember=1.0-smoothstep(0.0,.6,abs(uTheme-1.0));
          float nebula=1.0-smoothstep(0.0,.6,abs(uTheme-2.0)),rain=1.0-smoothstep(0.0,.6,abs(uTheme-4.0)),city=1.0-smoothstep(0.0,.6,abs(uTheme-5.0));
          float petal=sin(a*(3.0+winter*3.0)+phase)*(.035+uForce*.08)+sin(a*5.0-phase*.7)*uCalm*.03;
          float twist=sin(a*2.0+phase),width=(.035+uForce*.055+uCalm*.02)*uStageSize.y;
          float r=radius+petal;
          vec2 shape=vec2(cos(a),sin(a));
          shape=mix(shape,vec2(cos(a)*(.66-.3*sin(a)),sin(a)*1.05),ember);
          float orbit=uLayer*.65+uFlow*.025;vec2 orbital=vec2(cos(a),sin(a)*.53);
          orbital=mat2(cos(orbit),-sin(orbit),sin(orbit),cos(orbit))*orbital;
          shape=mix(shape,orbital,nebula);
          float hex=.8660254/cos(mod(a+3.14159265/6.0,6.2831853/6.0)-3.14159265/6.0);
          shape=mix(shape,vec2(cos(a),sin(a))*hex,winter);
          shape=mix(shape,vec2(cos(a),sin(a)*.25+sin(a*2.0+phase)*.23+(uLayer-1.0)*.36),rain);
          shape=mix(shape,sign(vec2(cos(a),sin(a)))*sqrt(abs(vec2(cos(a),sin(a)))),city);
          vec3 p=uStageCentre+vec3(shape.x*r*uStageSize.x*(.34+uForce*.12),shape.y*r*uStageSize.y*(.22+uForce*.12),0);
          p.x+=across*width*twist;p.y+=across*width*cos(a*2.0+phase)+sin(a*2.0-phase)*uStageSize.y*.025*uMotion;
          p.y+=ember*pow(max(0.0,sin(a)),3.0)*uStageSize.y*.07;
          p.z+=sin(a)*2.0+cos(a*3.0+phase)*1.5*uMotion+across*width*twist;
          vFold=twist;gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);
        }`,
      fragmentShader:`uniform vec3 uA,uB,uC;uniform float uFlow,uForce,uPresence,uCalm,uOpacity,uLayer,uTheme;
        varying vec2 vUv;varying float vFold;
        void main(){float edge=pow(max(0.0,sin(vUv.y*3.14159265)),1.5);
          float d=(vUv.y-.5-sin(vUv.x*24.0+uFlow*.2+uLayer)*.18)*22.0;
          float filament=exp(-d*d),weave=.65+.35*sin(vUv.x*240.0+vUv.y*12.0-uFlow*.6);
          float city=1.0-smoothstep(0.0,.6,abs(uTheme-5.0));
          weave=mix(weave,.25+.75*pow(max(0.0,cos(vUv.x*80.0-uFlow*2.0)),6.0),city);
          float arc=.2+.8*pow(.5+.5*sin(vUv.x*6.2831853+uLayer*2.0944+uFlow*.12),2.0);
          vec3 c=mix(uA,uB,.5+.4*vFold);c=mix(c,uC,filament*(.35+uForce*.35));
          float alpha=edge*arc*(.13+filament*.26+uForce*.18)*uPresence*uOpacity*weave;
          gl_FragColor=vec4(c*(1.3+filament*.85),alpha);
        }`});
    veil.renderOrder=2;
  }

  // Broad translucent curtains: multiple depths, no time*velocity phase jumps.
  for(let layer=0;layer<3;layer++){
    const curtain=material(new THREE.PlaneGeometry(280,72,160,40),{uniforms:cloneUniforms({uLayer:{value:layer}}),side:THREE.DoubleSide,
      vertexShader:`uniform float uFlow,uEnergy,uCalm,uLayer,uMotion;varying vec2 vUv;varying float vFold;
      void main(){vUv=uv;vec3 p=position;float wave=sin(p.x*.08+uFlow*.16+uLayer*2.0)+sin(p.x*.17-uFlow*.11+p.y*.035)*.45;
       p.z+=wave*(3.0+uCalm*3.0)*uMotion;p.y+=sin(p.x*.045+uLayer+uFlow*.09)*(3.0+uEnergy*2.0);vFold=wave;
       gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);}`,
      fragmentShader:`uniform float uFlow,uEnergy,uCalm,uLayer,uOpacity,uTension;uniform vec3 uA,uB,uC;varying vec2 vUv;varying float vFold;
      void main(){vec2 p=vUv;float centre=.45+sin(p.x*8.0+uFlow*.09+uLayer*1.4)*.12+sin(p.x*19.0-uFlow*.06)*.045;
       float d=(p.y-centre)*27.0;float band=exp(-d*d);float veil=exp(-max(0.0,p.y-centre)*12.0)*smoothstep(centre-.005,centre+.04,p.y);
       float filament=pow(max(0.0,.5+.5*sin(p.x*315.0+vFold*3.0)),5.0);
       float fine=.5+.5*sin(p.x*19.0+p.y*8.0+uFlow*.06);float edge=smoothstep(0.0,.16,p.x)*(1.0-smoothstep(.82,1.0,p.x));
       vec3 c=mix(uB,uA,fine);c=mix(c,uC,uTension*.22);
       float alpha=(band*.7+veil*.22)*edge*(.07+uEnergy*.045+uCalm*.09)*(.4+filament*.6)*uOpacity;
       gl_FragColor=vec4(c,alpha);
      }`});
    curtain.position.set(0,8+layer*10,-170-layer*40);curtain.renderOrder=-11+layer;
  }

  // Weather exists in depth, so rain streaks and snowflakes pass behind the keys.
  const weatherCount=9000,weatherGeo=new THREE.BufferGeometry(),seeds=new Float32Array(weatherCount*3);
  let rng=7391;const random=()=>{rng=(Math.imul(rng,1664525)+1013904223)|0;return(rng>>>0)/4294967296;};
  for(let i=0;i<seeds.length;i++)seeds[i]=random();
  weatherGeo.setAttribute('position',new THREE.BufferAttribute(seeds,3));
  const weatherField=material(weatherGeo,{uniforms,
    vertexShader:`uniform float uWeather,uWeatherTime,uFlow,uEnergy,uPedal,uImpact,uPx,uMotion,uOpacity,uHitX;uniform vec3 uA,uB,uC;
    varying float vAlpha,vKind,vSeed;varying vec3 vColor;
    void main(){vec3 s=position;vSeed=s.x;vKind=uWeather;
     float rain=1.0-smoothstep(.0,.2,abs(uWeather-1.0));float snow=1.0-smoothstep(.0,.2,abs(uWeather-2.0));float ember=1.0-smoothstep(.0,.2,abs(uWeather-3.0));
     float fall=uWeatherTime*(.04+rain*.2+ember*.015)*(0.7+s.z);
     vec3 p=vec3((s.x-.5)*145.0,mod(s.y*70.0-fall*70.0,70.0)-3.0,-8.0-s.z*100.0);
     if(ember>.5)p.y=mod(s.y*55.0+fall*35.0,55.0)-3.0;
     float sway=sin(uFlow*.4+s.z*35.0+p.y*.08)*(1.0+snow*2.5);p.x+=sway*uMotion;
     p.x+=sin(uFlow*.21)*p.y*.045*(1.0+uEnergy*3.0)*uMotion;
     vec2 delta=p.xy-vec2(uHitX,3.0);p.xy+=normalize(delta+vec2(.01))*uImpact*3.0*exp(-length(delta)*.03)*uMotion;
     vec4 mv=modelViewMatrix*vec4(p,1.0);gl_Position=projectionMatrix*mv;
     gl_PointSize=clamp((.10+rain*.6+snow*.18+ember*.10)*uPx/max(3.0,-mv.z),1.0,22.0);
     vAlpha=(rain+snow+ember)*(.12+s.z*.25)*uOpacity*smoothstep(-3.0,2.0,p.y)*(1.0-smoothstep(48.0,67.0,p.y));
     vColor=mix(uA,uC,ember*.7+snow*.35);
    }`,fragmentShader:`varying float vAlpha,vKind,vSeed;varying vec3 vColor;
    void main(){vec2 p=gl_PointCoord-.5;float r=length(p);if(r>.5)discard;float a=exp(-r*r*22.0);
     if(vKind>.7&&vKind<1.3)a=exp(-p.x*p.x*650.0)*(1.0-smoothstep(0.0,.5,abs(p.y)));
     if(vKind>1.7&&vKind<2.3){float angle=atan(p.y,p.x);a*=.5+.5*pow(abs(cos(angle*3.0)),8.0);}
     gl_FragColor=vec4(vColor,a*vAlpha);
    }`},true);

  // Bounded ring pool: strong chords arrive as waves through the floor and air.
  const ringData=[];
  for(let i=0;i<12;i++){
    const u=cloneUniforms({uAge:{value:100},uStrength:{value:0}});
    const ring=material(new THREE.PlaneGeometry(2,2),{uniforms:u,side:THREE.DoubleSide,
      vertexShader:`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
      fragmentShader:`uniform float uAge,uStrength,uOpacity;uniform vec3 uA,uC;varying vec2 vUv;
      void main(){vec2 p=vUv-.5;float r=length(p)*2.0;float d=(r-.72)*80.0,e=(r-.54)*120.0;float band=exp(-d*d);float echo=exp(-e*e)*.2;
       float arc=.65+.35*sin(atan(p.y,p.x)*18.0+uAge);float a=(band+echo)*arc*exp(-uAge*.9)*uStrength*uOpacity;
       gl_FragColor=vec4(mix(uA,uC,.55)*1.2,a);
      }`});
    ring.rotation.x=-Math.PI/2;ring.position.y=-2.22;ring.visible=false;ringData.push({mesh:ring,u,born:-100,strength:0});
  }

  // A quiet harmonic constellation, with one point per pitch class.
  const haloGeo=new THREE.BufferGeometry(),haloPositions=new Float32Array(12*3),haloColors=new Float32Array(12*3);
  haloGeo.setAttribute('position',new THREE.BufferAttribute(haloPositions,3));haloGeo.setAttribute('color',new THREE.BufferAttribute(haloColors,3));
  const halo=material(haloGeo,{uniforms,vertexColors:true,
    vertexShader:`uniform float uPx;varying vec3 vColor;void main(){vColor=color;vec4 mv=modelViewMatrix*vec4(position,1.0);gl_Position=projectionMatrix*mv;gl_PointSize=clamp(.75*uPx/max(3.0,-mv.z),2.0,36.0);}`,
    fragmentShader:`varying vec3 vColor;void main(){vec2 p=gl_PointCoord-.5;float r=length(p);if(r>.5)discard;gl_FragColor=vec4(vColor,exp(-r*r*26.0));}`},true);
  const haloLines=new THREE.LineLoop(haloGeo,new THREE.LineBasicMaterial({color:0x608080,transparent:true,opacity:.07,depthWrite:false,blending:THREE.AdditiveBlending}));
  group.add(haloLines);resources.push(haloLines.material);
  const haloLevel=new Float32Array(12);

  function restore(){
    floor.visible=true;
    for(const [mat,base] of original){mat.color.copy(base.color);mat.roughness=base.roughness;mat.metalness=base.metalness;}
    Object.assign(bloom,baseBloom);railLine.material.color.copy(baseRail);
  }
  function save(){try{localStorage.setItem('arsenal.piano.spectacle',JSON.stringify(settings));}catch{}}
  function configure(patch={}){
    const oldQuality=settings.quality;
    if(patch.quality && ctx.recording()) {ctx.toast('Stop recording before changing render quality.',true);return false;}
    if(patch.theme && THEMES[patch.theme])settings.theme=patch.theme;
    if(patch.harmonyMode && MODES[patch.harmonyMode])settings.harmonyMode=patch.harmonyMode;
    if(patch.quality && QUALITY[patch.quality])settings.quality=patch.quality;
    if(['world','none','rain','snow','embers'].includes(patch.weather))settings.weather=patch.weather;
    if(['harmony','full','chord','off'].includes(patch.labels))settings.labels=patch.labels;
    for(const key of ['enabled','harmony','waveform','autoWorld'])if(typeof patch[key]==='boolean')settings[key]=patch[key];
    if(Number.isFinite(patch.intensity))settings.intensity=clamp(patch.intensity,.25,1.4);
    if(Number.isFinite(patch.motion))settings.motion=clamp(patch.motion,.15,1);
    if(Number.isFinite(patch.journey))settings.journey=clamp(patch.journey);
    if(settings.enabled && (!gpu||oldQuality!==settings.quality))buildParticles(QUALITY[settings.quality].count);
    if(oldQuality!==settings.quality)ctx.quality(QUALITY[settings.quality].scale);
    group.visible=settings.enabled;floor.visible=!settings.enabled;ctx.classic(!settings.enabled);
    if(!settings.enabled){moonwater.setActive(false);restore();}
    save();syncControls();return true;
  }
  let panel=null,button=null,readout=null;
  function mount(){
    const link=document.createElement('link');link.rel='stylesheet';link.href='/web/piano/spectacle.css';document.head.append(link);
    button=document.createElement('button');button.className='btn';button.type='button';button.textContent='Atmosphere';button.id='btn-atmosphere';button.setAttribute('aria-expanded','false');
    document.querySelector('.topbar-actions').append(button);
    panel=document.createElement('section');panel.id='atmosphere-panel';panel.hidden=true;panel.setAttribute('aria-label','Piano atmosphere');
    panel.innerHTML=`<div class="atmos-head"><span>Atmosphere</span><button type="button" aria-label="Close atmosphere">×</button></div>
      <label class="atmos-check"><input type="checkbox" data-setting="enabled"> Cinematic atmosphere</label>
      <label>Chord visualization<select data-setting="harmonyMode">${Object.entries(MODES).map(([id,m])=>`<option value="${id}">${m.name}</option>`).join('')}</select></label>
      <p data-harmony-hint></p>
      <label>Environment<select data-setting="theme">${Object.entries(THEMES).map(([id,t])=>`<option value="${id}">${t.name}</option>`).join('')}</select></label>
      <label class="atmos-check"><input type="checkbox" data-setting="autoWorld"> Travel with the music</label>
      <label>Weather<select data-setting="weather"><option value="world">Environment default</option><option value="none">Clear air</option><option value="rain">Rain</option><option value="snow">Snow</option><option value="embers">Embers</option></select></label>
      <label>Render quality<select data-setting="quality">${Object.entries(QUALITY).map(([id,q])=>`<option value="${id}">${q.name}</option>`).join('')}</select></label>
      <label>Light & impact<input type="range" min=".25" max="1.4" step=".05" data-setting="intensity"></label>
      <label>Motion<input type="range" min=".15" max="1" step=".05" data-setting="motion"></label>
      <label>Camera drift<input type="range" min="0" max="1" step=".05" data-setting="journey"></label>
      <label class="atmos-check"><input type="checkbox" data-setting="harmony"> Let harmony colour the world</label>
      <label class="atmos-check"><input type="checkbox" data-setting="waveform"> Waveform from connected audio</label>
      <label>Theory display<select data-setting="labels"><option value="harmony">Chord + Nashville + note glass</option><option value="full">Harmony + staff</option><option value="chord">Chord + note glass</option><option value="off">Pure performance</option></select></label>
      <p>Held notes gather light. Pedal lets it drift. Dry high notes scatter; strong chords send waves through the scene.</p><output id="atmosphere-status"></output>`;
    document.getElementById('app').append(panel);readout=panel.querySelector('output');
    const close=()=>{panel.hidden=true;button.setAttribute('aria-expanded','false');};
    button.addEventListener('click',()=>{panel.hidden=!panel.hidden;button.setAttribute('aria-expanded',String(!panel.hidden));});
    panel.querySelector('.atmos-head button').addEventListener('click',close);
    panel.addEventListener('keydown',e=>{if(e.key==='Escape'){e.stopPropagation();close();button.focus();}});
    for(const input of panel.querySelectorAll('[data-setting]'))input.addEventListener(input.type==='range'?'input':'change',()=>{
      configure({[input.dataset.setting]:input.type==='checkbox'?input.checked:input.type==='range'?Number(input.value):input.value});syncControls();
    });
    syncControls();
  }
  function syncControls(){if(!panel)return;for(const input of panel.querySelectorAll('[data-setting]')){if(input.type==='checkbox')input.checked=settings[input.dataset.setting];else input.value=settings[input.dataset.setting];}panel.querySelector('[data-harmony-hint]').textContent=settings.labels==='full'&&settings.harmonyMode!=='atmosphere'?'Staff view takes the centre. Choose Chord + Nashville + note glass below to return to your selected diagram.':MODES[settings.harmonyMode].hint;}
  function update(dt,t,info,audioLevel=0){
    if(disposed)return;
    const s=model.update(dt,t,info);
    if(!settings.enabled){harmonyView.update(dt,t,info,settings);return;}
    if(settings.autoWorld){const next=journey(s,t,settings.theme);if(next!==settings.theme){settings.theme=next;syncControls();save();}}
    const theme=THEMES[settings.theme];
    targetA.setHex(theme.a);targetB.setHex(theme.b);targetC.setHex(theme.c);
    if(settings.harmony){targetA.lerp(temp.setHex(0x9e88e4),s.minor*.32);targetB.lerp(temp.setHex(0x61498f),s.tension*.4);targetC.lerp(temp.setHex(0xe3cf8e),s.cadence*.5);}
    const blend=1-Math.exp(-dt/2.6);cA.lerp(targetA,blend);cB.lerp(targetB,blend);cC.lerp(targetC,blend);
    if(!lastMaterialTheme){cA.copy(targetA);cB.copy(targetB);cC.copy(targetC);}lastMaterialTheme=settings.theme;
    const intensity=settings.intensity,energy=clamp(s.energy+audioLevel*.1);
    flow+=dt*(.4+energy*.45)*settings.motion;
    weatherTime+=dt*(s.pedal?.3:1)*(1+energy*.5)*settings.motion;
    const weather=settings.weather==='world'?theme.weather:{none:0,rain:1,snow:2,embers:3}[settings.weather];
    smoothedWeather=approach(smoothedWeather,weather,.9,dt);
    uniforms.uTime.value=t;uniforms.uDt.value=Math.min(dt,1/30);uniforms.uFlow.value=flow;uniforms.uWeatherTime.value=weatherTime;
    uniforms.uWeather.value=smoothedWeather;uniforms.uMotion.value=settings.motion;uniforms.uEnergy.value=energy;uniforms.uCalm.value=s.calm;
    uniforms.uTheme.value=approach(uniforms.uTheme.value,Object.keys(THEMES).indexOf(settings.theme),.8,dt);
    uniforms.uForce.value=s.force;uniforms.uPresence.value=s.presence;
    uniforms.uFocusX.value=approach(uniforms.uFocusX.value,ctx.keyX(Math.round(s.centroid)),.8,dt);
    camera.updateMatrixWorld();
    stageAt(0,.16,uniforms.uStageCentre.value);stageAt(-1,-1,stageOrigin);stageAt(1,1,stageCorner);
    uniforms.uStageSize.value.set(stageCorner.x-stageOrigin.x,stageCorner.y-stageOrigin.y);
    stageAt(-.9,0,stageOrigin,-8);stageAt(.9,.68,stageCorner,-8);
    uniforms.uNoteBounds.value.set(stageOrigin.x,stageCorner.x,stageCorner.y);
    uniforms.uPedal.value=approach(uniforms.uPedal.value,s.pedal?1:0,.4,dt);uniforms.uTension.value=s.tension;
    uniforms.uImpact.value=(s.impact+s.cadence*.22)*intensity;
    uniforms.uOpacity.value=approach(uniforms.uOpacity.value,intensity/Math.sqrt(1+s.density*.06+s.visualDensity*.045),.4,dt);uniforms.uPx.value=renderer.domElement.height/(2*Math.tan(camera.fov*Math.PI/360));
    worlds.update(dt,settings,s,audioLevel,model.impacts);
    if(settings.journey){camera.position.x+=Math.sin(flow*.08)*3*settings.journey;camera.position.y+=Math.sin(flow*.065)*1.5*settings.journey;camera.lookAt(ctx.lookTarget);}
    for(let i=0;i<88;i++){noteData[i*4+2]=0;noteData[i*4+3]=0;}
    for(const [m,n] of model.notes){const i=m-21,a=i*4,b=352+a;
      noteData[a+1]=n.velocity/127;noteData[a+2]=n.end===null?1:0;noteData[a+3]=n.held?1:0;
      noteData[b]=n.at;noteData[b+1]=n.end===null?-1:n.end;noteData[b+2]=n.style;
    }
    noteTex.needsUpdate=true;
    keyTex.needsUpdate=true;voicings.update(info,settings.labels);
    if(gpu&&dt>0&&settings.harmonyMode==='atmosphere'&&settings.theme!=='moon'&&settings.theme!=='rain'){gpu.compute();particles.material.uniforms.uPosition.value=gpu.getCurrentRenderTarget(posVar).texture;particles.material.uniforms.uVelocity.value=gpu.getCurrentRenderTarget(velVar).texture;}
    for(const hit of model.impacts)if(hit.time>lastImpact){
      lastImpact=hit.time;const x=hit.notes.reduce((sum,m)=>sum+ctx.keyX(m),0)/hit.notes.length;uniforms.uHitX.value=x;
      if(hit.chord||hit.strength>.5){const r=ringData.find(r=>t-r.born>=5);if(!r)continue;r.born=hit.time;r.strength=hit.strength;
        r.mesh.position.set(x,-2.22,-5);r.mesh.rotation.set(-Math.PI/2,0,0);}
    }
    for(const r of ringData){const age=t-r.born;r.mesh.visible=age>=0&&age<5;
      if(r.mesh.visible){r.u.uAge.value=age;r.u.uStrength.value=r.strength;const size=2+age*(9+r.strength*8);r.mesh.scale.set(size,size,1);}}
    const pcs=new Set([...model.notes.values()].filter(n=>n.end===null).map(n=>n.midi%12));
    for(let pc=0;pc<12;pc++){
      haloLevel[pc]=approach(haloLevel[pc],pcs.has(pc)?1:0,.6,dt);
      const angle=pc/12*Math.PI*2+flow*.018,radius=12+s.air*2+s.tension*2;
      haloPositions[pc*3]=Math.sin(angle)*radius;haloPositions[pc*3+1]=14+Math.cos(angle)*radius*.65;haloPositions[pc*3+2]=-27;
      temp.copy(cA).lerp(cC,pc/12).multiplyScalar((.015+haloLevel[pc]*.8)*intensity);
      temp.toArray(haloColors,pc*3);
    }
    haloGeo.attributes.position.needsUpdate=true;haloGeo.attributes.color.needsUpdate=true;
    haloLines.material.color.copy(cB);haloLines.material.opacity=(.015+energy*.025)*intensity;
    body.setHex(theme.body);ivory.setHex(theme.ivory);lacquer.color.lerp(body,blend);lacquer.metalness=approach(lacquer.metalness,theme.metal,1.5,dt);
    lacquer.roughness=approach(lacquer.roughness,settings.theme==='rain'?.12:.24,1.5,dt);
    for(const k of keys.values()){
      if(k.glow<.015&&k.cueGlow<.015&&k.ghostLevel<.015)k.material.color.lerp(k.black?body:ivory,.88);
      k.material.roughness=approach(k.material.roughness,settings.theme==='winter'?.42:settings.theme==='rain'?.18:.29,1.8,dt);
      k.material.metalness=approach(k.material.metalness,k.black?theme.metal*.6:theme.metal*.13,1.8,dt);
    }
    railLine.material.color.copy(cA).multiplyScalar(.3+energy*.4);
    floor.material.color.lerp(body,.05);floor.material.roughness=approach(floor.material.roughness,.35,2,dt);
    bloom.strength=.42+s.force*.25+s.impact*.06*intensity;bloom.radius=.22+s.calm*.13;bloom.threshold=.94;
    scene.background.lerp(temp.copy(cB).multiplyScalar(.006+energy*.009),.12);scene.fog.color.copy(scene.background);
    const inLake=settings.theme==='moon'||settings.theme==='rain';
    const originalForeground=settings.harmonyMode==='atmosphere';
    worldGroup.visible=!inLake;voicingGroup.visible=!inLake&&originalForeground;
    for(const object of legacyObjects)if(!ringData.some(r=>r.mesh===object))object.visible=!inLake&&originalForeground;
    weatherField.visible=true;
    if(inLake)for(const r of ringData)r.mesh.visible=false;
    haloLines.visible=!inLake&&originalForeground;if(particles)particles.visible=!inLake&&originalForeground;
    moonwater.update(dt,t,info,settings);
    harmonyView.update(dt,t,info,settings);
    if(readout&&!panel.hidden)readout.textContent=`${Math.round(renderer.domElement.width)} × ${Math.round(renderer.domElement.height)} · ${inLake?'Moonwater':particleCount.toLocaleString()+' simulated motes'}${gpuError?' · GPU unavailable':''}${settings.quality==='cinema'?' · 4K WebM capture can be slower. Ultra is best for smooth browser recordings.':''}`;
  }
  cA.setHex(THEMES[settings.theme].a);cB.setHex(THEMES[settings.theme].b);cC.setHex(THEMES[settings.theme].c);
  mount();configure();ctx.quality(QUALITY[settings.quality].scale);
  return {settings,model,configure,update,ownsTheory:()=>harmonyView.ownsTheory()||moonwater.ownsTheory(),
    noteOn:(...args)=>model.noteOn(...args),noteOff:(...args)=>model.noteOff(...args),pedal:(...args)=>model.pedal(...args),clear:(...args)=>model.clear(...args),
    stats:()=>({enabled:settings.enabled,theme:settings.theme,weather:settings.weather,quality:settings.quality,particles:particleCount,gpuError,
      render:[renderer.domElement.width,renderer.domElement.height],worlds:worlds.stats(),voicings:voicings.stats(),moonwater:moonwater.stats(),harmonyView:harmonyView.stats(),...model.state}),
    dispose(){disposed=true;harmonyView.dispose();moonwater.dispose();worlds.dispose();voicings.dispose();gpu?.dispose();if(particles){particles.geometry.dispose();particles.material.dispose();}for(const r of resources)r.dispose();scene.remove(group);panel?.remove();button?.remove();restore();},
  };
}
