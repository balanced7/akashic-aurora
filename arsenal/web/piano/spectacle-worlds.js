import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { GPUComputationRenderer } from 'three/addons/misc/GPUComputationRenderer.js';
import { approach } from './spectacle-motion.js';

// Procedural scenery, with geometry in depth and no image assets or downloaded shaders.
export function createWorlds(THREE, parent, u, ctx) {
  const disposables=[], objects=[], weights={forest:0,mountain:0,city:0,cosmos:0};
  const W={...u,uForest:{value:0},uMountain:{value:0},uCity:{value:0},uCosmos:{value:0},uAudio:{value:0}};
  // Shared height/velocity field: every hit adds an impulse to water already moving.
  // 24 world units/s, a 256-square grid and 1/120 s steps keep the wave CFL below .4.
  const rippleGPU=new GPUComputationRenderer(256,256,ctx.renderer),rippleInitial=rippleGPU.createTexture();
  const rippleBounds=new THREE.Vector4(-110,-165,220,177),drops=Array.from({length:8},()=>new THREE.Vector4());
  const ripple=rippleGPU.addVariable('waveState',`
    uniform float uStep,uDropCount;uniform vec4 uDrops[8],uBounds;
    void main(){vec2 uv=gl_FragCoord.xy/resolution.xy,texel=1.0/resolution.xy;
      vec4 s=texture2D(waveState,uv);vec2 cell=uBounds.zw/resolution.xy;
      float lap=(texture2D(waveState,uv-vec2(texel.x,0)).r+texture2D(waveState,uv+vec2(texel.x,0)).r-2.0*s.r)/(cell.x*cell.x);
      lap+=(texture2D(waveState,uv-vec2(0,texel.y)).r+texture2D(waveState,uv+vec2(0,texel.y)).r-2.0*s.r)/(cell.y*cell.y);
      float velocity=(s.g+(576.0*lap-s.r*.3)*uStep)*exp(-uStep*.75);
      vec2 p=uBounds.xy+uv*uBounds.zw;
      for(int i=0;i<8;i++){if(float(i)>=uDropCount)break;vec2 d=(p-uDrops[i].xy)/uDrops[i].w;velocity+=exp(-dot(d,d)*2.0)*uDrops[i].z;}
      float edge=smoothstep(0.0,.045,min(min(uv.x,uv.y),min(1.0-uv.x,1.0-uv.y)));
      float absorb=exp(-(1.0-edge)*uStep*14.0);
      gl_FragColor=vec4(clamp((s.r+velocity*uStep)*absorb,-4.0,4.0),clamp(velocity*absorb,-60.0,60.0),0,1);
    }`,rippleInitial);
  Object.assign(ripple.material.uniforms,{uStep:{value:1/120},uDropCount:{value:0},uDrops:{value:drops},uBounds:{value:rippleBounds}});
  rippleGPU.setVariableDependencies(ripple,[ripple]);
  const rippleError=rippleGPU.init();
  if(rippleError)ctx.toast('Water simulation unavailable: '+rippleError,true);
  const smoothRipples=!rippleError && ctx.renderer.extensions.has('OES_texture_float_linear');
  if(smoothRipples)for(const rt of [rippleGPU.getCurrentRenderTarget(ripple),rippleGPU.getAlternateRenderTarget(ripple)]){
    rt.texture.minFilter=rt.texture.magFilter=THREE.LinearFilter;rt.texture.needsUpdate=true;
  }
  W.uRipple={value:rippleError?rippleInitial:rippleGPU.getCurrentRenderTarget(ripple).texture};W.uRippleBounds={value:rippleBounds};
  u.uRipple=W.uRipple;u.uRippleBounds=W.uRippleBounds;
  let rippleTime=0,lastDrop=-Infinity,rippleSteps=0;const pendingDrops=[];
  function updateRipples(dt,hits){
    if(rippleError)return;
    for(const hit of hits)if(hit.time>lastDrop){lastDrop=hit.time;pendingDrops.push(hit);}
    rippleTime+=Math.min(Math.max(dt,0),1/30);
    while(rippleTime>=1/120){
      const batch=pendingDrops.splice(0,8);
      batch.forEach((hit,i)=>{const x=hit.notes.reduce((sum,m)=>sum+ctx.keyX(m),0)/hit.notes.length;
        drops[i].set(x,-5,3+hit.strength*18,2.5+(hit.chord?2.5:0)+hit.strength*1.6);});
      ripple.material.uniforms.uDropCount.value=batch.length;
      rippleGPU.compute();rippleTime-=1/120;rippleSteps++;
    }
    W.uRipple.value=rippleGPU.getCurrentRenderTarget(ripple).texture;
  }
  const common=`uniform float uFlow,uEnergy,uCalm,uImpact,uTension,uOpacity,uForest,uMountain,uCity,uCosmos; uniform vec3 uA,uB,uC;
    float hash2(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
    float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(hash2(i),hash2(i+vec2(1,0)),f.x),mix(hash2(i+vec2(0,1)),hash2(i+1.0),f.x),f.y);}
    float fbm(vec2 p){float n=0.0,a=.5;for(int i=0;i<4;i++){n+=noise(p)*a;p=mat2(1.6,-1.2,1.2,1.6)*p+7.1;a*=.5;}return n;}`;
  const vertex=`varying vec3 vWorld;varying vec2 vUv;void main(){vUv=uv;vec4 p=modelMatrix*vec4(position,1.0);vWorld=p.xyz;gl_Position=projectionMatrix*viewMatrix*p;}`;
  function add(geo,vs,fs,options={}){
    const mat=new THREE.ShaderMaterial({uniforms:W,vertexShader:vs,fragmentShader:fs,transparent:true,depthWrite:false,side:THREE.DoubleSide,...options});
    const mesh=new THREE.Mesh(geo,mat);mesh.frustumCulled=false;parent.add(mesh);disposables.push(geo,mat);objects.push(mesh);return mesh;
  }
  // A deep sky rather than a flat black void. Its galaxy is a layered spiral dust field.
  const sky=add(new THREE.PlaneGeometry(680,540),vertex,common+`
    varying vec2 vUv;void main(){vec2 p=(vUv-.5)*vec2(2.0,1.0);float n=fbm(p*5.0+vec2(uFlow*.018,0));
      vec3 c=mix(uB*.018,uA*.08,pow(max(0.0,1.0-abs(p.y+.2)),3.0))*(.7+n*.6);
      vec2 g=(p-vec2(-.16,-.01))*vec2(1.0,2.1);float r=length(g),a=atan(g.y,g.x);
      float arms=pow(.5+.5*sin(a*3.0-r*16.0+uFlow*.035+fbm(g*9.0)*3.0),3.0);
      float dust=fbm(g*22.0+uFlow*.007);float neb=exp(-r*3.0)*(arms*.5+dust*.7);
      c+=uCosmos*(mix(uA,uB,dust)*neb*.9+uC*exp(-r*18.0)*.7);
      c+=mix(uA,uC,.3)*pow(max(0.0,1.0-abs(p.y+.19)*8.0),3.0)*.03;
      gl_FragColor=vec4(c*uOpacity,1.0);
    }`);
  sky.position.set(0,-15,-370);sky.renderOrder=-20;

  // Stars occupy a bowl of space. The same restrained stars remain above the lake.
  let seed=851;const rand=()=>{seed=(Math.imul(seed,1664525)+1013904223)|0;return(seed>>>0)/4294967296;};
  const starsGeo=new THREE.BufferGeometry(),stars=new Float32Array(5500*3);
  for(let i=0;i<5500;i++){stars[i*3]=(rand()-.5)*640;stars[i*3+1]=-50+rand()*125;stars[i*3+2]=-140-rand()*270;}
  starsGeo.setAttribute('position',new THREE.BufferAttribute(stars,3));
  const starsMat=new THREE.ShaderMaterial({uniforms:W,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,
    vertexShader:common+`uniform float uPx;varying float vLight;void main(){vec3 p=position;
      p.x+=sin(uFlow*.027)*5.0*uCosmos;p.y+=cos(uFlow*.022)*3.0*uCosmos;
      vec4 mv=modelViewMatrix*vec4(p,1.0);gl_Position=projectionMatrix*mv;
      float h=hash2(position.xy);gl_PointSize=clamp((.035+h*h*.34)*uPx/max(10.0,-mv.z),1.0,9.0);
      vLight=(.04+uCosmos*.45)*(1.0-uForest*.85)*(0.7+.3*sin(uFlow*.4+h*40.0))*uOpacity;
    }`,fragmentShader:`uniform vec3 uA,uC;varying float vLight;void main(){float r=length(gl_PointCoord-.5);if(r>.5)discard;gl_FragColor=vec4(mix(uA,uC,.6),exp(-r*r*35.0)*vLight);}`});
  const starfield=new THREE.Points(starsGeo,starsMat);starfield.frustumCulled=false;parent.add(starfield);disposables.push(starsGeo,starsMat);

  // Moon / distant planet: a shaded sphere with a faint atmospheric limb.
  const moon=add(new THREE.SphereGeometry(9,48,32),
    `varying vec3 vN;varying vec3 vP;void main(){vN=normal;vP=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    common+`varying vec3 vN,vP;void main(){float light=pow(max(0.0,dot(normalize(vN),normalize(vec3(-.6,.7,.5)))),.7);
      float grain=fbm(vP.xy*1.5);vec3 c=mix(uB*.06,uC*.75,light)*(.75+grain*.25);
      gl_FragColor=vec4(c,(1.0-uForest*.65)*(1.0-uCity*.8)*uOpacity);}`);
  moon.position.set(64,15,-235);

  // Water is displaced geometry; a procedural sky reflection and grazing glints make it legible.
  const water=add(new THREE.PlaneGeometry(480,520,240,240),common+`
    uniform sampler2D uRipple;uniform vec4 uRippleBounds;
    varying vec3 vWorld;varying vec2 vUv;varying float vWave;void main(){vUv=uv;vec3 p=position;
      float w=sin(p.x*.11+uFlow*.7)*cos(p.y*.085-uFlow*.45)+sin(p.x*.24+p.y*.12-uFlow*.6)*.3;
      p.z+=w*(.16+uEnergy*.20)*(1.0-uCity);vWave=w;vec4 wp=modelMatrix*vec4(p,1.0);
      vec2 q=(wp.xz-uRippleBounds.xy)/uRippleBounds.zw;float inside=step(0.0,q.x)*step(q.x,1.0)*step(0.0,q.y)*step(q.y,1.0);
      wp.y+=texture2D(uRipple,clamp(q,0.0,1.0)).r*inside;vWorld=wp.xyz;gl_Position=projectionMatrix*viewMatrix*wp;
    }`,common+`uniform sampler2D uRipple;uniform vec4 uRippleBounds;varying vec3 vWorld;varying vec2 vUv;varying float vWave;void main(){
      vec2 p=vWorld.xz;float wave=sin(p.x*.22+p.y*.39+uFlow*.6+sin(p.y*.11-uFlow*.35)*2.0);
      float fine=sin(p.y*2.9+sin(p.x*.15+uFlow*.5)*4.0+uFlow*.6);
      float d=(p.x-25.0-sin(p.y*.07)*6.0)/24.0;float refl=exp(-d*d);
      float broken=smoothstep(.25,.67,fbm(p*vec2(.17,.8)+uFlow*.06));
      vec3 c=uB*.021+uA*(.009+pow(max(0.0,wave),18.0)*.016*broken+pow(max(0.0,fine),16.0)*refl*.12*broken);
      c+=uC*refl*(.008+pow(max(0.0,fine),25.0)*.13*broken);
      vec2 q=(p-uRippleBounds.xy)/uRippleBounds.zw;float inside=step(0.0,q.x)*step(q.x,1.0)*step(0.0,q.y)*step(q.y,1.0);
      vec2 texel=vec2(1.0/256.0),slope=vec2(texture2D(uRipple,q+vec2(texel.x,0)).r-texture2D(uRipple,q-vec2(texel.x,0)).r,
        texture2D(uRipple,q+vec2(0,texel.y)).r-texture2D(uRipple,q-vec2(0,texel.y)).r);
      float glint=clamp(length(slope)*1.4,0.0,1.0);c+=mix(uA,uC,glint*.8)*glint*.85*inside;
      float grid=(1.0-smoothstep(.0,.035,abs(fract(p.x*.18)-.5)))+(1.0-smoothstep(.0,.035,abs(fract(p.y*.18)-.5)));
      c=mix(c,uB*.009+uA*grid*.09,uCity);
      float distanceFade=1.0-smoothstep(100.0,270.0,length(p));
      gl_FragColor=vec4(c*uOpacity,distanceFade*(1.0-uCosmos*.75));
    }`);
  water.rotation.x=-Math.PI/2;water.position.set(0,-2.26,-145);water.renderOrder=-8;

  // Ridged terrain has actual parallax and changing facet light, not a panorama.
  const terrainGeo=new THREE.PlaneGeometry(470,180,190,88);terrainGeo.rotateX(-Math.PI/2);terrainGeo.translate(0,-4,-225);
  const pa=terrainGeo.attributes.position;
  for(let i=0;i<pa.count;i++){
    const x=pa.getX(i),z=pa.getZ(i),ridge=32+21*Math.sin(x*.023+.8)+10*Math.sin(x*.061)+5*Math.sin(x*.133+1.8);
    const centre=-217+Math.sin(x*.032)*18;
    const h=Math.max(0,ridge)*Math.exp(-Math.pow((z-centre)/47,2));
    pa.setY(i,-4+h*.48*(.84+.16*Math.sin(x*.41+z*.29))+Math.sin(x*.28-z*.2)*.8);
  }
  terrainGeo.computeVertexNormals();
  const mountains=add(terrainGeo,`varying vec3 vN,vWorld;void main(){vN=normal;vWorld=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    common+`varying vec3 vN,vWorld;void main(){float lighting=.18+max(0.0,dot(normalize(vN),normalize(vec3(-.4,.65,.5))));
      float frost=smoothstep(7.0,18.0,vWorld.y+fbm(vWorld.xz*.14)*6.0)*uMountain;
      vec3 c=mix(uB*.075,uC*.30,frost)*lighting;
      float haze=exp(-max(0.0,vWorld.y+1.0)*.10);c=mix(c,uA*.06,haze*.6);
      gl_FragColor=vec4(c*uOpacity,(.75+uMountain*.25)*(1.0-uCity)*(1.0-uCosmos));}`);
  mountains.renderOrder=-12;

  // Four tapered branch tiers per pine, instanced hundreds of times into the mist.
  const parts=[];
  for(let tier=0;tier<4;tier++){const g=new THREE.ConeGeometry(.94-tier*.17,1.9-tier*.2,7);g.translate(0,.8+tier*.66,0);parts.push(g);}
  const treeBase=mergeGeometries(parts);parts.forEach(g=>g.dispose());
  const treesGeo=new THREE.InstancedBufferGeometry();treesGeo.setIndex(treeBase.index);for(const [name,a] of Object.entries(treeBase.attributes))treesGeo.setAttribute(name,a);
  const positions=new Float32Array(260*4);
  for(let i=0;i<260;i++){let x=(rand()-.5)*370;const z=-42-rand()*200;
    if(Math.abs(x)<19 && z>-100)x+=(x<0?-1:1)*23;
    positions.set([x,-2.6,z,2.8+rand()*6],i*4);
  }
  treesGeo.setAttribute('aTree',new THREE.InstancedBufferAttribute(positions,4));treesGeo.instanceCount=260;
  const trees=add(treesGeo,common+`attribute vec4 aTree;varying vec3 vN,vWorld;void main(){vec3 p=position*aTree.w+aTree.xyz;
      p.x+=sin(uFlow*.3+aTree.x*.11)*pow(max(0.0,position.y)/4.0,2.0)*.6;vN=normal;vWorld=p;
      gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);}`,
    common+`varying vec3 vN,vWorld;void main(){float light=.15+pow(max(0.0,dot(normalize(vN),normalize(vec3(.3,.8,-.5)))),2.0)*.6;
      vec3 c=uA*light*.085;float mist=smoothstep(-3.0,28.0,vWorld.y);float depth=clamp((-vWorld.z-50.0)/230.0,0.0,1.0);
      c=mix(uA*.055,c,mist);c=mix(c,uB*.035,depth);
      gl_FragColor=vec4(c*uOpacity,uForest*(.8-depth*.2));}`);
  trees.renderOrder=-7;

  // Fog banks cross the scene at several depths. Soft noise leaves recognisable silhouettes.
  for(let i=0;i<4;i++){
    const fog=add(new THREE.PlaneGeometry(420,34),vertex,common+`varying vec2 vUv;varying vec3 vWorld;void main(){
      float n=fbm(vec2(vWorld.x*.025+uFlow*.09,vWorld.y*.10+vWorld.z*.01));
      float shape=pow(max(0.0,1.0-abs(vUv.y-.38)*2.0),2.0)*smoothstep(0.0,.18,vUv.x)*(1.0-smoothstep(.82,1.0,vUv.x));
      gl_FragColor=vec4(mix(uA,uB,.6)*.19,shape*(.06+uForest*.26+uCalm*.09)*n*uOpacity*(1.0-uCosmos));}`);
    fog.position.set(0,5+i*1.8,-48-i*46);fog.renderOrder=-6+i;
  }

  // Every MIDI key owns one architectural column. Attacks raise it; release lets it settle.
  const cityBase=new THREE.BoxGeometry(.48,1,.7,1,12,1);cityBase.translate(0,.5,0);
  const cityGeo=new THREE.InstancedBufferGeometry();cityGeo.setIndex(cityBase.index);for(const [name,a]of Object.entries(cityBase.attributes))cityGeo.setAttribute(name,a);
  cityGeo.setAttribute('aNote',new THREE.InstancedBufferAttribute(Float32Array.from({length:88},(_,i)=>i),1));cityGeo.instanceCount=88;
  const city=add(cityGeo,common+`uniform sampler2D uNotes,uKeyMotion;uniform float uTime;attribute float aNote;varying vec3 vLocal,vN;varying float vLight,vHeight;
    void main(){vec4 n=texture2D(uNotes,vec2((aNote+.5)/88.0,.25));vec4 meta=texture2D(uNotes,vec2((aNote+.5)/88.0,.75));
      vec4 movement=texture2D(uKeyMotion,vec2((aNote+.5)/88.0,.5));float envelope=movement.z;
      float height=.3+movement.x;vec3 p=position;
      p.y*=height;p.x+=n.x;p.z-=7.5+mod(aNote,3.0)*1.1;
      vLocal=vec3(position.x,position.y*height,position.z);vN=normal;vLight=envelope;vHeight=height;
      gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);}`,
    common+`varying vec3 vLocal,vN;varying float vLight,vHeight;void main(){
      // MSAA can extrapolate varyings outside a thin face at its covered edge.
      // Clamp its normalised coordinates before high powers amplify that overshoot.
      float edge=pow(clamp(abs(vLocal.x)/.24,0.0,1.0),18.0)+pow(clamp(abs(vLocal.z)/.35,0.0,1.0),18.0);
      float windows=pow(max(0.0,cos(vLocal.y*9.0)),18.0)*(.6+.4*sin(vLocal.y*.2-uFlow*2.0));
      float pulse=.7+.3*sin(vLocal.y*.8-uFlow*3.0+uImpact*2.0);
      vec3 c=uB*.035+mix(uA,uC,clamp(vLocal.y/28.0,0.0,1.0))*(edge*.14+windows*.27)*(.15+vLight*.9)*pulse;
      c+=uC*pow(clamp(vLocal.y/max(vHeight,.01),0.0,1.0),35.0)*vLight*.6;
      gl_FragColor=vec4(c*uOpacity,uCity);}`);
  city.renderOrder=1;

  // The waveform samples only the audio analyser supplied by the piano's selected input.
  const waveData=new Float32Array(512),waveTex=new THREE.DataTexture(waveData,512,1,THREE.RedFormat,THREE.FloatType);
  waveTex.needsUpdate=true;W.uWave={value:waveTex};disposables.push(waveTex);
  const wave=add(new THREE.PlaneGeometry(56,.35,511,1),`
    uniform sampler2D uWave;uniform float uAudio;varying vec2 vUv;void main(){vUv=uv;vec3 p=position;
      float amp=texture2D(uWave,vec2(uv.x,.5)).r;p.y+=amp*8.0;
      gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);}`,
    `uniform vec3 uA,uC;uniform float uAudio,uOpacity;varying vec2 vUv;void main(){float edge=pow(1.0-abs(vUv.y-.5)*2.0,2.0);float ends=smoothstep(0.0,.06,vUv.x)*(1.0-smoothstep(.94,1.0,vUv.x));gl_FragColor=vec4(mix(uA,uC,.6)*1.2,edge*ends*min(1.0,uAudio*6.0+.12)*uOpacity);}`,
    {blending:THREE.AdditiveBlending});
  wave.position.set(0,3.2,-12);wave.visible=false;

  return {
    waveform:wave,
    update(dt,settings,state,audioLevel,hits=[]){
      updateRipples(dt,hits);
      const theme=settings.theme;
      for(const id of Object.keys(weights)){const target=id==='forest'?theme==='rain':id==='mountain'?theme==='winter':id==='city'?theme==='city':theme==='nebula';
        weights[id]=approach(weights[id],target?1:0,1.7,dt);W['u'+id[0].toUpperCase()+id.slice(1)].value=weights[id];}
      trees.visible=weights.forest>.001;city.visible=weights.city>.001;
      W.uAudio.value=audioLevel;
      const data=settings.waveform?ctx.audio():null;wave.visible=!!data;
      if(data){for(let i=0;i<512;i++)waveData[i]=data[Math.floor(i*data.length/512)]||0;waveTex.needsUpdate=true;}
    },
    dispose(){rippleGPU.dispose();rippleInitial.dispose();for(const d of disposables)d.dispose();},
    stats:()=>({...weights,waveform:wave.visible,rippleError,rippleSteps,smoothRipples}),
  };
}
