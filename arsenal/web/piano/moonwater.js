import { Reflector } from 'three/addons/objects/Reflector.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { createHarmonicVoices, FIFTHS, packVoiceLabels } from './harmonic-voices.js';

const noiseGLSL=`
float hash31(vec3 p){p=fract(p*.1031);p+=dot(p,p.yzx+33.33);return fract((p.x+p.y)*p.z);}
float noise3(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
 return mix(mix(mix(hash31(i),hash31(i+vec3(1,0,0)),f.x),mix(hash31(i+vec3(0,1,0)),hash31(i+vec3(1,1,0)),f.x),f.y),
 mix(mix(hash31(i+vec3(0,0,1)),hash31(i+vec3(1,0,1)),f.x),mix(hash31(i+vec3(0,1,1)),hash31(i+1.),f.x),f.y),f.z);}
float mistNoise(vec3 p){return noise3(p)*.57+noise3(p*2.03+13.1)*.28+noise3(p*4.11+31.7)*.15;}
`;
const voiceGLSL=`
uniform sampler2D uVoices,uRipple;uniform vec4 uRippleBounds;
uniform float uFlow,uMotion,uPedal,uForce;uniform vec3 uNoteBounds;
vec4 voice(float i,float row){return texture2D(uVoices,vec2((i+.5)/88.,(row+.5)/3.));}
vec3 voicePath(float i,float t){vec4 a=voice(i,0.),b=voice(i,1.),c=voice(i,2.);
 float height=min(a.z,max(7.,uNoteBounds.z-2.));
 vec2 q=(vec2(a.y,-5.)-uRippleBounds.xy)/uRippleBounds.zw;
 float wind=texture2D(uRipple,q+vec2(.006,0)).r-texture2D(uRipple,q-vec2(.006,0)).r;
 float bend=(sin(t*3.+uFlow*.42+c.z*6.28)*.7+sin(t*7.-uFlow*.3)*.18+wind*2.5)*t*t;
 float dx=bend*(.8+a.w*2.5)*uMotion;
 float room=max(.1,dx>0.?uNoteBounds.y-a.x:a.x-uNoteBounds.x);
 dx=sign(dx)*room*(1.-exp(-abs(dx)/room));
 return vec3(mix(a.y,a.x,smoothstep(0.,.3,t))+dx,.8+t*height,-3.7-t*t*(5.+uPedal*5.));}
`;

// One coherent lake, with real planar scene reflection and a shared wave field.
// Fog is a stack of samples through a continuous 3D density field, depth tested
// against the landscape. It is deliberately bounded; this is not path tracing.
export function createMoonwater(THREE,parent,u,model,ctx){
 const group=new THREE.Group();group.name='Moonwater';parent.add(group);
 const resources=[],tracker=createHarmonicVoices(ctx.keyX),col=new THREE.Color();
 const data=new Float32Array(88*3*4),tex=new THREE.DataTexture(data,88,3,THREE.RGBAFormat,THREE.FloatType);
 tex.needsUpdate=true;resources.push(tex);
 const lights=Array.from({length:8},()=>new THREE.Vector4(0,-100,0,0));
 const colours=Array.from({length:8},()=>new THREE.Color());
 const fifths=Array.from({length:12},()=>new THREE.Vector4());
 const W={...u,uVoices:{value:tex},uLamps:{value:lights},uLampColours:{value:colours},
  uFifths:{value:fifths},uRoot:{value:-1},uConnections:{value:1},uRain:{value:0},uExpression:{value:1},uMood:{value:0},uLetters:{value:1}};
 let seed=1703;const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)|0;return(seed>>>0)/4294967296;};
 const uniforms=extra=>({...W,...extra});
 const worldVS=`varying vec3 vWorld,vNormal;varying vec2 vUv;void main(){vUv=uv;vNormal=normalize(mat3(modelMatrix)*normal);vec4 p=modelMatrix*vec4(position,1.);vWorld=p.xyz;gl_Position=projectionMatrix*viewMatrix*p;}`;
 function add(geometry,material){const mesh=new THREE.Mesh(geometry,material);group.add(mesh);resources.push(geometry,material);return mesh;}
 function shader(geo,fragment,extra={},vertex=worldVS){return add(geo,new THREE.ShaderMaterial({uniforms:uniforms(),vertexShader:vertex,fragmentShader:fragment,...extra}));}
 const litGLSL=`uniform vec4 uLamps[8];uniform vec3 uLampColours[8];
 vec3 noteLight(vec3 p){vec3 c=vec3(0);for(int i=0;i<8;i++){vec3 d=p-uLamps[i].xyz;c+=uLampColours[i]*uLamps[i].w/(2.+dot(d,d)*.035);}return c;}`;

 // A sky with shaped clouds, a textured moon and actual space above the valley.
 const sky=shader(new THREE.SphereGeometry(650,64,40),noiseGLSL+`
 uniform float uFlow,uMood;varying vec3 vWorld;void main(){vec3 rd=normalize(vWorld-cameraPosition);
 float horizon=pow(1.-abs(rd.y),4.);vec3 base=mix(vec3(.003,.009,.019),vec3(.022,.037,.054),horizon);
 vec3 moonDir=normalize(vec3(.04,-.035,-1.));float d=length(rd-moonDir);
 float disc=1.-smoothstep(.011,.012,d),halo=exp(-d*38.);
 float crater=mistNoise(rd*170.)*.65+.35;base+=vec3(.81,.89,.81)*disc*crater*1.45+vec3(.09,.12,.14)*halo;
 vec3 p=rd*vec3(6.,14.,6.)+vec3(uFlow*.021,0.,uFlow*.009);
 float cloud=smoothstep(.44,.77,mistNoise(p+mistNoise(p*.5)*2.));
 float rim=pow(max(0.,1.-abs(cloud-.24)*3.),4.)*halo;
 base=mix(base,vec3(.007,.012,.020)+rim*vec3(.15,.21,.22),cloud*.93);
 vec2 st=rd.xz/max(.15,rd.y+.25)*480.;vec2 cell=floor(st);float star=pow(hash31(vec3(cell,2.)),100.)*(1.-smoothstep(.0,.09,length(fract(st)-.5)));
 base+=star*(1.-cloud)*smoothstep(.03,.3,rd.y)*.7;
 base*=mix(vec3(1.),vec3(1.12,.92,1.17),uMood);
 gl_FragColor=vec4(base,1.);}`,{side:THREE.BackSide,depthWrite:false});
 sky.renderOrder=-30;

 // A central open valley, with ridges at three scales and banks at either side.
 function terrainHeight(x,z){
  const depth=Math.max(0,(-z-30)/260),bank=Math.max(0,Math.abs(x)-43-depth*45);
  const rough=Math.sin(x*.12+z*.073)*Math.sin(x*.046-z*.12)*3+Math.sin(x*.39+z*.24)*.8;
  const sides=Math.pow(Math.min(1,bank/58),1.8)*(12+depth*35)*(1+.2*Math.sin(z*.071+x*.041));
  const rear=Math.exp(-(((z+285)/43)**2))*(12+7*Math.sin(x*.031+.8)+5*Math.sin(x*.073+2));
  const islands=Math.exp(-((Math.abs(x)-40)**2)/190-((z+76)**2)/3500)*7;
  return -3.2+Math.max(sides,rear)*.57+rough*Math.min(1,(sides+rear)/8)*.55+islands;
 }
 const terrain=new THREE.PlaneGeometry(560,390,260,200);terrain.rotateX(-Math.PI/2);terrain.translate(0,-3,-205);
 const a=terrain.attributes.position;for(let i=0;i<a.count;i++)a.setY(i,terrainHeight(a.getX(i),a.getZ(i)));terrain.computeVertexNormals();
 shader(terrain,noiseGLSL+litGLSL+`
 uniform float uFlow;varying vec3 vWorld,vNormal;varying vec2 vUv;
 void main(){vec3 n=normalize(vNormal);float grain=mistNoise(vWorld*.53),vein=pow(abs(sin(vWorld.y*1.7+noise3(vWorld*.8)*5.)),12.);
 float moon=max(0.,dot(n,normalize(vec3(.3,.8,-.4))));
 vec3 rock=mix(vec3(.014,.025,.03),vec3(.069,.086,.084),grain)*( .35+moon*.75);
 float frost=smoothstep(26.,55.,vWorld.y+grain*8.)*smoothstep(.1,.65,n.y);rock=mix(rock,vec3(.22,.28,.29),frost*.8);
 float moss=smoothstep(.5,.83,n.y)*(1.-smoothstep(3.,19.,vWorld.y))*grain;rock=mix(rock,vec3(.035,.061,.041),moss*.65);
 rock+=vein*.004+noteLight(vWorld)*(.11+moon*.12);
 float haze=1.-exp(-length(vWorld-cameraPosition)*.0025);rock=mix(rock,vec3(.026,.034,.048),haze*.66);
 gl_FragColor=vec4(rock,1.);}`);

 // Branch silhouettes have gaps, varied crowns and finely tapered tips.
 const parts=[];
 const trunk=new THREE.CylinderGeometry(.045,.11,4.1,5);trunk.translate(0,2,0);parts.push(trunk);
 for(let j=0;j<9;j++){
  const h=.65+j*.35,r=.96*(1-j/10),tier=new THREE.ConeGeometry(r,1.1-j*.025,9,1,true);tier.translate(0,h,0);parts.push(tier);
 }
 const treeGeo=mergeGeometries(parts);parts.forEach(g=>g.dispose());
 const treeMat=new THREE.ShaderMaterial({uniforms:uniforms(),vertexShader:noiseGLSL+`
 uniform float uFlow,uForce;varying vec3 vWorld,vNormal;void main(){vec3 p=position;
 vec3 root=instanceMatrix[3].xyz;float wind=sin(uFlow*.32+root.x*.07+root.z*.035)*.025;
 p.x+=pow(max(0.,p.y)/4.,2.)*(wind+uForce*.055);vec4 wp=modelMatrix*instanceMatrix*vec4(p,1.);
 vWorld=wp.xyz;vNormal=normalize(mat3(instanceMatrix)*normal);gl_Position=projectionMatrix*viewMatrix*wp;}`,
 fragmentShader:noiseGLSL+litGLSL+`varying vec3 vWorld,vNormal;void main(){float facing=max(0.,dot(normalize(vNormal),normalize(vec3(.3,.8,-.4))));
 vec3 c=vec3(.008,.025,.024)+vec3(.015,.03,.025)*facing+noteLight(vWorld)*.1;
 float haze=1.-exp(-length(vWorld-cameraPosition)*.003);c=mix(c,vec3(.025,.043,.054),haze*.66);gl_FragColor=vec4(c,1.);}`,side:THREE.DoubleSide});
 const trees=new THREE.InstancedMesh(treeGeo,treeMat,390),dummy=new THREE.Object3D();
 for(let i=0;i<390;i++){const near=i<90,z=near?-35-random()*110:-22-random()*275,sign=random()<.5?-1:1,x=sign*(near?32+random()*19:46+Math.max(0,-z-35)*.16+random()*90);
  dummy.position.set(x,terrainHeight(x,z)-.6,z);const scale=1+random()*3.5;dummy.scale.set(scale*(.55+random()*.3),scale,scale*.8);dummy.rotation.y=random()*6.28;dummy.updateMatrix();trees.setMatrixAt(i,dummy.matrix);}
 trees.frustumCulled=false;group.add(trees);resources.push(treeGeo,treeMat);

 const fifthCanvas=document.createElement('canvas');fifthCanvas.width=1536;fifthCanvas.height=128;
 const fp=fifthCanvas.getContext('2d');fp.font='300 69px "Segoe UI", sans-serif';fp.textAlign='center';fp.textBaseline='middle';fp.fillStyle='white';
 ['C','G','D','A','E','B','F♯','C♯','A♭','E♭','B♭','F'].forEach((name,i)=>fp.fillText(name,i*128+64,64,116));
 const fifthGlyph=new THREE.CanvasTexture(fifthCanvas);resources.push(fifthGlyph);W.uFifthGlyph={value:fifthGlyph};
 const reflectionShader={name:'Moonwater reflected scene',uniforms:{tDiffuse:{value:null},color:{value:new THREE.Color()},textureMatrix:{value:new THREE.Matrix4()}},
 vertexShader:`uniform mat4 textureMatrix;varying vec4 vMirror;varying vec3 vWorld;void main(){vMirror=textureMatrix*vec4(position,1.);vWorld=(modelMatrix*vec4(position,1.)).xyz;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
 fragmentShader:noiseGLSL+litGLSL+`
 uniform sampler2D tDiffuse,uRipple,uFifthGlyph;uniform vec4 uRippleBounds,uFifths[12];uniform float uFlow,uRoot,uConnections,uForce,uLetters;
 varying vec4 vMirror;varying vec3 vWorld;
 float wave(vec2 p){vec2 q=(p-uRippleBounds.xy)/uRippleBounds.zw;float inside=step(0.,q.x)*step(q.x,1.)*step(0.,q.y)*step(q.y,1.);
 return texture2D(uRipple,clamp(q,0.,1.)).r*inside;}
 float segment(vec2 p,vec2 a,vec2 b){vec2 d=b-a;return length(p-a-d*clamp(dot(p-a,d)/max(dot(d,d),.001),0.,1.));}
 void main(){vec2 p=vWorld.xz;float dx=wave(p+vec2(.7,0))-wave(p-vec2(.7,0)),dz=wave(p+vec2(0,.7))-wave(p-vec2(0,.7));
 float fine=sin(p.x*.79+p.y*1.33+uFlow*.55+noise3(vec3(p*.13,uFlow*.07))*3.);
 vec2 slopes=vec2(dx,dz)*.055+vec2(sin(p.y*.81+uFlow*.5),fine)*.0025;
 vec2 uv=vMirror.xy/vMirror.w+slopes;vec3 reflected=texture2D(tDiffuse,clamp(uv,.002,.998)).rgb;
 vec3 eye=normalize(cameraPosition-vWorld),normal=normalize(vec3(-slopes.x*10.,1.,-slopes.y*10.));float fresnel=.13+.77*pow(1.-max(0.,dot(eye,normal)),3.);
 vec3 c=mix(vec3(.003,.012,.016),reflected,fresnel*.94);
 c+=noteLight(vec3(p.x,-1.,p.y))*.022*(.4+pow(max(0.,fine),12.)*2.);
 float caustic=exp(-abs(mistNoise(vec3(p*.24+slopes*3.,uFlow*.08))-.48)*90.);
 c+=vec3(.045,.095,.082)*caustic*exp(-length(p-vec2(0.,-13.))*.045)*(.025+uForce*.16);
 // Twelve submerged inlays in true fifth order; active pitches reveal a chord polygon.
 vec2 bed=p+slopes*13.;vec3 ritual=vec3(0);int first=-1,last=-1;
 for(int i=0;i<12;i++){vec4 mark=uFifths[i];float d=length(bed-mark.xy);float stone=1.-smoothstep(.35,.62,d);
  ritual+=vec3(.13,.21,.19)*stone*(.06+mark.z*.65);
  ritual+=mix(vec3(.40,.67,.65),vec3(.87,.71,.40),mark.w)*exp(-d*d*2.8)*mark.z*.55;
  ritual+=vec3(.65,.57,.32)*exp(-pow((d-1.1)*12.,2.))*mark.w*mark.z*.18;
  vec2 letter=(bed-mark.xy-vec2(0.,1.5))/2.+.5;
  if(letter.x>0.&&letter.x<1.&&letter.y>0.&&letter.y<1.)ritual+=vec3(.35,.50,.46)*texture2D(uFifthGlyph,vec2((float(i)+letter.x)/12.,1.-letter.y)).a*(.06+mark.z*.26)*uLetters;
  if(mark.z>.2){if(first<0)first=i;if(last>=0){float line=exp(-segment(bed,uFifths[last].xy,mark.xy)*38.);ritual+=vec3(.30,.53,.40)*line*min(mark.z,uFifths[last].z)*.34;}last=i;}}
 if(first>=0&&last!=first){float line=exp(-segment(bed,uFifths[first].xy,uFifths[last].xy)*38.);ritual+=vec3(.30,.53,.40)*line*.22;}
 c+=ritual*uConnections;
 gl_FragColor=vec4(c,1.);}`};
 const water=new Reflector(new THREE.PlaneGeometry(610,620),{textureWidth:1024,textureHeight:1024,clipBias:.004,multisample:0,shader:reflectionShader});
 Object.assign(water.material.uniforms,W);water.rotation.x=-Math.PI/2;water.position.set(0,-2.26,-190);water.name='Lake reflection';group.add(water);
 const reflect=water.onBeforeRender;let reflecting=false,reflectionFrames=0;
 water.onBeforeRender=function(renderer,scene,camera){if(reflecting)return;reflecting=true;const was=hud.visible,labelsWere=labels.visible,leadersWere=leaders.visible;
  const excluded=(ctx.reflectionExclusions||[]).map(o=>[o,o.visible]);for(const [o]of excluded)o.visible=false;
  hud.visible=false;labels.visible=false;leaders.visible=false;
  try{reflect.call(this,renderer,scene,camera);reflectionFrames++;}finally{hud.visible=was;labels.visible=labelsWere;leaders.visible=leadersWere;for(const [o,visible]of excluded)o.visible=visible;reflecting=false;}};

 // Continuous 3D fog, sampled on depth-tested sheets. The same note lamps light
 // the mist, stone, water and actual PBR keyboard lights.
 const fogGeo=new THREE.PlaneGeometry(430,38);
 const fogMat=new THREE.ShaderMaterial({uniforms:uniforms(),vertexShader:worldVS,transparent:true,depthWrite:false,side:THREE.DoubleSide,
 fragmentShader:noiseGLSL+litGLSL+`
 uniform sampler2D uRipple;uniform vec4 uRippleBounds;
 uniform float uFlow,uForce,uPedal,uRain;varying vec3 vWorld,vNormal;varying vec2 vUv;
 void main(){vec3 p=vWorld;float ground=exp(-max(0.,p.y+2.)*.18)*smoothstep(-2.3,0.,p.y),edge=smoothstep(0.,.15,vUv.y)*(1.-smoothstep(.72,1.,vUv.y));
 vec2 q=(p.xz-uRippleBounds.xy)/uRippleBounds.zw;
 float wave=texture2D(uRipple,clamp(q,0.,1.)).r;
 p.x+=wave*1.7*exp(-max(0.,p.y)*.12);
 vec3 drift=vec3(uFlow*.19,0.,uFlow*.065);float n=mistNoise(p*vec3(.055,.13,.055)-drift);
 float curl=noise3(p*.10+vec3(0.,uFlow*.11,0.));float density=smoothstep(.45,.80,n+curl*.15);
 float alpha=density*ground*edge*(.12+uRain*.045);
 vec3 lit=noteLight(p);vec3 c=vec3(.065,.092,.13)+min(lit,vec3(1.8))*.42;
 c+=vec3(.04,.07,.067)*pow(max(0.,density),3.);
 gl_FragColor=vec4(c,alpha);}`});resources.push(fogGeo,fogMat);
 for(let i=0;i<18;i++){const mesh=new THREE.Mesh(fogGeo,fogMat);mesh.position.set(0,10,-7-i*i*.82);mesh.renderOrder=1;group.add(mesh);}

 // One continuous geometry per musical part, with narrow luminous cores and
 // much softer shoulders. Changes of pitch move the same part through space.
 const base=new THREE.PlaneGeometry(1,1,1,100);base.translate(0,.5,0);
 const vgeo=new THREE.InstancedBufferGeometry();vgeo.setIndex(base.index);for(const [name,a]of Object.entries(base.attributes))vgeo.setAttribute(name,a);
 vgeo.setAttribute('aVoice',new THREE.InstancedBufferAttribute(Float32Array.from({length:88},(_,i)=>i),1));vgeo.instanceCount=88;
 const strands=shader(vgeo,`
 uniform float uFlow,uExpression;varying vec2 vUv;varying vec3 vColour;varying float vLevel,vPower,vPhase;
 void main(){float x=(vUv.x-.5)*2.,core=exp(-x*x*210.),shoulder=exp(-x*x*14.)*.10;
 float filament=exp(-pow((x-.18*sin(vUv.y*19.-uFlow*.4+vPhase))*42.,2.))*.25;
 float fade=smoothstep(0.,.035,vUv.y)*(1.-smoothstep(.75,1.,vUv.y));
 float pulse=.7+.3*sin(vUv.y*12.-uFlow*1.5+vPhase);
 gl_FragColor=vec4(vColour*(1.2+core*(.65+vPower*1.2)),(core+filament+shoulder)*fade*vLevel*(.72+vPower*.5)*pulse*uExpression);}`,
 {transparent:true,depthWrite:false,side:THREE.DoubleSide,blending:THREE.AdditiveBlending},voiceGLSL+`
 attribute float aVoice;varying vec2 vUv;varying vec3 vColour;varying float vLevel,vPower,vPhase;
 void main(){vec4 a=voice(aVoice,0.),b=voice(aVoice,1.),c=voice(aVoice,2.);vUv=uv;vColour=b.rgb;vLevel=b.a;vPower=a.w;vPhase=c.z*6.28;
 vec3 p=voicePath(aVoice,position.y);vec4 mv=modelViewMatrix*vec4(p,1.);mv.x+=position.x*(.45+a.w*.8);gl_Position=projectionMatrix*mv;}`);base.dispose();
 strands.renderOrder=3;

 // Fireflies inhabit a common wind field, including the existing water gradient.
 const fireGeo=new THREE.BufferGeometry(),motes=new Float32Array(1100*3);
 for(let i=0;i<motes.length;i++)motes[i]=random();fireGeo.setAttribute('position',new THREE.BufferAttribute(motes,3));
 const fireMat=new THREE.ShaderMaterial({uniforms:uniforms(),transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,
 vertexShader:noiseGLSL+litGLSL+`
 uniform sampler2D uRipple;uniform vec4 uRippleBounds;
 uniform float uFlow,uPx,uForce,uPresence,uRain;varying float vLight;varying vec3 vColour;void main(){vec3 s=position;
 vec3 p=vec3((s.x-.5)*125.,-.7+s.y*s.y*28.,-7.-s.z*165.);
 p.x+=sin(uFlow*.31+s.z*26.+p.y*.1)*(1.+uForce*2.);p.y+=sin(uFlow*.28+s.x*18.)*.8;
 vec2 q=clamp((p.xz-uRippleBounds.xy)/uRippleBounds.zw,0.,1.);
 vec2 gradient=vec2(texture2D(uRipple,q+vec2(.006,0)).r-texture2D(uRipple,q-vec2(.006,0)).r,texture2D(uRipple,q+vec2(0,.006)).r-texture2D(uRipple,q-vec2(0,.006)).r);
 p.xz-=gradient*4.*exp(-max(0.,p.y)*.10);
 float lantern=pow(.5+.5*sin(uFlow*.5+s.z*79.),5.);vec3 lit=noteLight(p);
 vLight=(.025+lantern*.28+length(lit)*.11)*smoothstep(-1.5,1.,p.y);vColour=mix(vec3(.71,.79,.37),vec3(.39,.71,.70),s.x);
 vec4 mv=modelViewMatrix*vec4(p,1.);gl_Position=projectionMatrix*mv;gl_PointSize=clamp((.027+s.z*.055)*uPx/max(3.,-mv.z),1.,9.);}`,
 fragmentShader:`varying float vLight;varying vec3 vColour;void main(){float d=length(gl_PointCoord-.5);if(d>.5)discard;gl_FragColor=vec4(vColour*1.6,exp(-d*d*38.)*vLight);}`});
 const fireflies=new THREE.Points(fireGeo,fireMat);fireflies.frustumCulled=false;group.add(fireflies);resources.push(fireGeo,fireMat);

 // Crisp, free letterforms. The texture is an atlas, not a cloud sprite.
 const atlas=document.createElement('canvas');atlas.width=1408;atlas.height=1024;const paint=atlas.getContext('2d');
 const glyph=new THREE.CanvasTexture(atlas);resources.push(glyph);const names=Array(88).fill('');
 const labelData=new Float32Array(88*4),labelTex=new THREE.DataTexture(labelData,88,1,THREE.RGBAFormat,THREE.FloatType);resources.push(labelTex);
 const labelGeo=new THREE.InstancedBufferGeometry(),labelBase=new THREE.PlaneGeometry(1,1);
 labelGeo.setIndex(labelBase.index);for(const [name,a]of Object.entries(labelBase.attributes))labelGeo.setAttribute(name,a);
 labelGeo.setAttribute('aVoice',vgeo.getAttribute('aVoice'));labelGeo.instanceCount=88;
 const labelMat=new THREE.ShaderMaterial({uniforms:uniforms({uGlyph:{value:glyph},uPlacement:{value:labelTex}}),transparent:true,depthWrite:false,depthTest:false,
 vertexShader:voiceGLSL+`uniform sampler2D uPlacement;attribute float aVoice;varying vec2 vUv;varying float vIndex,vLight;void main(){vUv=uv;vIndex=aVoice;vLight=voice(aVoice,1.).a;
 vec4 p=texture2D(uPlacement,vec2((aVoice+.5)/88.,.5));gl_Position=vec4(p.xy+position.xy*p.zw,0,1);}`,
 fragmentShader:`uniform sampler2D uGlyph;varying vec2 vUv;varying float vIndex,vLight;void main(){vec2 cell=vec2(mod(vIndex,11.),7.-floor(vIndex/11.));
 float a=texture2D(uGlyph,(cell+vUv)/vec2(11.,8.)).a;gl_FragColor=vec4(vec3(.88,.94,.84),a*smoothstep(0.,.13,vLight));}`});
 const labels=new THREE.Mesh(labelGeo,labelMat);labels.frustumCulled=false;labels.renderOrder=15;group.add(labels);resources.push(labelGeo,labelMat);labelBase.dispose();
 const leaderPoints=new Float32Array(88*6),leaderLevels=new Float32Array(88*2),leaderGeo=new THREE.BufferGeometry();
 leaderGeo.setAttribute('position',new THREE.BufferAttribute(leaderPoints,3));leaderGeo.setAttribute('aLevel',new THREE.BufferAttribute(leaderLevels,1));
 const leaderMat=new THREE.ShaderMaterial({transparent:true,depthTest:false,depthWrite:false,
  vertexShader:'attribute float aLevel;varying float vLevel;void main(){vLevel=aLevel;gl_Position=vec4(position,1.);}',
  fragmentShader:'varying float vLevel;void main(){gl_FragColor=vec4(.45,.62,.57,vLevel*.21);}'});
 const leaders=new THREE.LineSegments(leaderGeo,leaderMat);leaders.frustumCulled=false;leaders.renderOrder=14;group.add(leaders);resources.push(leaderGeo,leaderMat);

 const hudCanvas=document.createElement('canvas');hudCanvas.width=1536;hudCanvas.height=620;
 const hp=hudCanvas.getContext('2d'),hudTex=new THREE.CanvasTexture(hudCanvas);hudTex.colorSpace=THREE.SRGBColorSpace;resources.push(hudTex);
 const hudMat=new THREE.ShaderMaterial({uniforms:{uMap:{value:hudTex},uAspect:{value:1}},transparent:true,depthTest:false,depthWrite:false,toneMapped:false,
 vertexShader:`uniform float uAspect;varying vec2 vUv;void main(){vUv=uv;float w=uAspect<1.?.91:.44;float h=w*uAspect*620./1536.;vec2 origin=vec2(-.87,.82);gl_Position=vec4(origin+vec2(uv.x*w*2.,(uv.y-1.)*h*2.),0,1);}`,
 fragmentShader:`uniform sampler2D uMap;varying vec2 vUv;void main(){gl_FragColor=texture2D(uMap,vUv);}`});
 const hud=add(new THREE.PlaneGeometry(1,1),hudMat);hud.frustumCulled=false;hud.renderOrder=30;
 let hudSignature='',nextReading=0,reading=null,active=false,quality='',lastLabels='harmony',foreground=true;

 // Mineral grain is shared by the key materials, so their highlights describe
 // a physical surface. Existing key pivots and replay/ghost cues remain intact.
 const pixels=new Uint8Array(256*256*4);
 for(let y=0;y<256;y++)for(let x=0;x<256;x++){const i=(y*256+x)*4;
  const vein=Math.pow(.5+.5*Math.sin(x*.036+y*.014+Math.sin(y*.031)*2.8+Math.sin(x*.021+y*.018)*3),17);
  const value=Math.round(247-vein*3-random()*2);pixels.set([value,Math.min(255,value+1),value,255],i);}
 const mineral=new THREE.DataTexture(pixels,256,256);mineral.wrapS=mineral.wrapT=THREE.RepeatWrapping;mineral.colorSpace=THREE.SRGBColorSpace;mineral.needsUpdate=true;resources.push(mineral);
 const saved=new Map();for(const mat of [ctx.lacquer,...[...ctx.keys.values()].map(k=>k.material)])saved.set(mat,{map:mat.map,transmission:mat.transmission,thickness:mat.thickness,ior:mat.ior,iridescence:mat.iridescence,clearcoat:mat.clearcoat,clearcoatRoughness:mat.clearcoatRoughness});
 const pointLights=Array.from({length:4},()=>{const light=new THREE.PointLight(0xcbe6cc,0,25,2);group.add(light);return light;});
 // A thick optical-glass lip carries an inner metal filament. Transmission
 // refracts the scene behind it; the lake also reflects the whole instrument.
 const glassMat=new THREE.MeshPhysicalMaterial({color:0xaccbc5,roughness:.11,metalness:0,transmission:.86,thickness:.65,ior:1.46,
  attenuationColor:new THREE.Color(0x527d79),attenuationDistance:2.5,clearcoat:1,iridescence:.22,envMap:ctx.lacquer.envMap,envMapIntensity:1.1});
 const glassLip=add(new RoundedBoxGeometry(55.7,.75,.78,4,.16),glassMat);glassLip.position.set(0,-1.32,2.92);
 const silverMat=new THREE.MeshStandardMaterial({color:0x899f9c,metalness:.93,roughness:.2,envMap:ctx.lacquer.envMap});
 const silver=add(new RoundedBoxGeometry(55.5,.035,.035,2,.012),silverMat);silver.position.set(0,-1.08,3.32);
 const projection=new THREE.Vector3();let signature='';
 function setActive(on){if(active===on)return;active=on;group.visible=on;
  for(const [mat,base] of saved){if(on){mat.map=mineral;mat.iridescence=.12;mat.ior=1.46;mat.clearcoat=1;mat.clearcoatRoughness=.09;}
   else Object.assign(mat,base);mat.needsUpdate=true;}}
 function pathCPU(v,t){const height=Math.min(v.height,Math.max(7,u.uNoteBounds.value.z-2));
  const bend=(Math.sin(t*3+u.uFlow.value*.42+v.phase*6.28)*.7+Math.sin(t*7-u.uFlow.value*.3)*.18)*t*t;
  return [v.x+bend*(.8+v.velocity*v.velocity*2.5)*u.uMotion.value,.8+t*height,-3.7-t*t*(5+u.uPedal.value*5)];}
 const pitchNames=['C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B'];
 function update(dt,time,info,settings){
  const voices=tracker.update(model.notes,dt,time);
  setActive(settings.enabled&&(settings.theme==='moon'||settings.theme==='rain'));if(!active)return;
  foreground=!settings.harmonyMode||settings.harmonyMode==='atmosphere';strands.visible=foreground;
  W.uExpression.value=settings.intensity;W.uLetters.value=foreground&&settings.labels!=='off'?1:0;lastLabels=settings.labels;data.fill(0);
  W.uMood.value+=( (settings.harmony?model.state.minor*.55+model.state.tension*.45:0)-W.uMood.value)*(1-Math.exp(-dt/3));
  const spellings=new Map((info?.notes||[]).map(n=>[n.midi,n.name]));
   const anchors=[];let atlasDirty=false;
  for(let i=0;i<voices.length;i++){const v=voices[i],power=v.velocity*v.velocity;
   // Restrained pigment, preserved for the life of a part, including pitch motion.
   col.setHSL((.12+v.hue)%1,.50,.57).lerp(new THREE.Color(0xe7e2c3),.24);
   data.set([v.x,v.targetX,v.height,power],i*4);data.set([col.r,col.g,col.b,v.level],352+i*4);data.set([v.midi,time-v.born,v.phase,v.active?1:0],704+i*4);
   const name=(spellings.get(v.midi)||pitchNames[v.midi%12]).replace(/#/g,'♯').replace(/b/g,'♭'),octave=Math.floor(v.midi/12)-1,full=name+octave;
   if(names[i]!==full){names[i]=full;const ax=i%11*128,ay=Math.floor(i/11)*128;paint.clearRect(ax,ay,128,128);
    paint.textAlign='center';paint.textBaseline='middle';paint.fillStyle='#f0f3dc';paint.font='300 67px "Segoe UI Variable", "Segoe UI", sans-serif';paint.fillText(name,ax+61,ay+58,102);
    paint.fillStyle='#a8bdb5';paint.font='400 20px "Segoe UI", sans-serif';paint.fillText(String(octave),ax+96,ay+92);atlasDirty=true;}
   const p=pathCPU(v,.76);projection.set(...p).project(ctx.camera);
   const actual={x:projection.x,y:projection.y};projection.set(v.x,p[1],p[2]).project(ctx.camera);
   anchors.push({x:projection.x,y:projection.y,actual});
  }
  const placement=packVoiceLabels(anchors,ctx.camera.aspect);
  for(let i=0;i<placement.length;i++){const p=placement[i];
   labelData.set([p.x,p.y,p.width,p.height],i*4);
   const a=anchors[i].actual;leaderPoints.set([a.x,a.y,0,p.x,p.y-p.height*.34,0],i*6);
   const opacity=Math.hypot(p.x-a.x,(p.y-a.y)/ctx.camera.aspect)>p.width*.42?voices[i].level:0;leaderLevels.set([opacity,opacity],i*2);
  }
  leaderGeo.setDrawRange(0,voices.length*2);leaderGeo.attributes.position.needsUpdate=true;leaderGeo.attributes.aLevel.needsUpdate=true;
  if(atlasDirty)glyph.needsUpdate=true;tex.needsUpdate=true;labelTex.needsUpdate=true;
  labelGeo.instanceCount=voices.length;labels.visible=leaders.visible=foreground&&settings.labels!=='off'&&settings.labels!=='full';
  const brightest=[...voices].sort((a,b)=>b.level*b.velocity-a.level*a.velocity).slice(0,8);
  for(let i=0;i<8;i++){const v=brightest[i];if(!v){lights[i].set(0,-100,0,0);continue;}
   const p=pathCPU(v,.30);lights[i].set(p[0],p[1],p[2],v.level*(.10+v.velocity*v.velocity*1.6)*settings.intensity);
   colours[i].setHSL((.12+v.hue)%1,.42,.63);if(i<4){pointLights[i].position.set(v.x,2.,-2.7);pointLights[i].color.copy(colours[i]);pointLights[i].intensity=v.level*(.5+v.velocity*v.velocity*4.5);}}
  for(let i=brightest.length;i<4;i++)pointLights[i].intensity=0;
  const root=info?.root?(([0,2,4,5,7,9,11][info.root.letter]+info.root.acc+12)%12):-1;
  W.uRoot.value=root;W.uConnections.value=foreground&&settings.harmony?1:0;W.uRain.value=settings.theme==='rain'?1:0;
  for(let i=0;i<12;i++){const angle=i*Math.PI/6;const level=voices.filter(v=>v.midi%12===FIFTHS[i]).reduce((m,v)=>Math.max(m,v.level),0);
   fifths[i].set(ctx.lookTarget.x+Math.sin(angle)*9,-30+Math.cos(angle)*8,level,FIFTHS[i]===root?1:0);}
  for(const k of ctx.keys.values()){
   if(k.cueGlow>.015||k.ghostLevel>.015)continue;
   const v=voices.find(v=>v.midi===k.m&&v.active),level=v?v.level:0;
   k.material.color.setHex(k.black?0x10272b:0xd7d9cb);if(v)k.material.color.lerp(col.setHSL((.12+v.hue)%1,.34,.62),level*.23);
   k.material.emissive.copy(col.setHex(0xc7e3bd));k.material.emissiveIntensity=level*(.018+(v?.velocity||0)**2*.13);
   k.material.roughness=k.black?.16:.27;k.material.metalness=k.black?.32:.04;
   k.material.clearcoat=1;k.material.clearcoatRoughness=.085;
  }
  ctx.lacquer.color.setHex(0x081b20);ctx.lacquer.metalness=.34;ctx.lacquer.roughness=.22;ctx.lacquer.clearcoat=1;
  ctx.bloom.strength=.36+model.state.force*.14;ctx.bloom.radius=.24;ctx.bloom.threshold=1.03;
  const resolution=settings.quality==='cinema'?1536:settings.quality==='ultra'?1024:768;
  if(quality!==settings.quality){water.getRenderTarget().setSize(resolution,resolution);quality=settings.quality;}
  if(time>=nextReading || time<nextReading-.2){nextReading=time+.1;const stats=window.__piano?.stats?.();
   if(stats)reading={number:stats.nns,key:stats.key?.name,dim:stats.key?.dim,mode:stats.nnsMode,fps:stats.fps};}
  const numbersOnly=reading?.mode==='numbers',unclassified=info&&!info.root&&info.notes?.length>5&&info.name?.includes(' ');
  const shown=info?(unclassified?`${info.notes.length} notes`:numbersOnly&&reading?.number?reading.number:info.name||''):'';
  const sub=shown&&settings.labels==='harmony'&&reading?.mode!=='off'?[numbersOnly?null:reading?.number,reading?.key].filter(Boolean).join('  ·  '):'';
  signature=shown+'|'+sub+'|'+reading?.dim;
  if(signature!==hudSignature){hudSignature=signature;hp.clearRect(0,0,1536,620);hp.textAlign='left';hp.textBaseline='alphabetic';
   const title=shown.replace(/#/g,'♯').replace(/b/g,'♭').replace(/\^/g,''),parts=unclassified?null:/^([A-G][♯♭]?|[♯♭]?[1-7])([^/]*)(.*)$/.exec(title);
   const runs=parts?[{text:parts[1],scale:1,dy:0},{text:parts[2],scale:.48,dy:-102},{text:parts[3],scale:.63,dy:0}]:[{text:title,scale:1,dy:0}];
   const font=(s)=>`200 ${s}px "Segoe UI Variable", "Segoe UI", sans-serif`;
   let size=260,total=0;do{total=runs.reduce((sum,r)=>{hp.font=font(size*r.scale);return sum+hp.measureText(r.text).width+12},0);if(total>1400)size-=4;}while(total>1400&&size>74);
   hp.fillStyle='#e6ece0';let x=12;for(const r of runs){hp.font=font(size*r.scale);hp.fillText(r.text,x,270+r.dy*size/260);x+=hp.measureText(r.text).width+12;}
   hp.font='300 62px "Segoe UI Variable", "Segoe UI", sans-serif';hp.fillStyle=reading?.dim?'#6e8b87':'#a0b8b1';hp.fillText(sub.replace(/#/g,'♯').replace(/b(?=\d)/g,'♭').replace(/\^/g,''),16,390,1400);hudTex.needsUpdate=true;}
  hudMat.uniforms.uAspect.value=ctx.camera.aspect;hud.visible=foreground&&settings.labels!=='off'&&settings.labels!=='full';
 }
 group.visible=false;
 return {update,setActive,ownsTheory:()=>active&&foreground&&lastLabels!=='full',
  stats:()=>({active,reflectionFrames,reflectionSize:water.getRenderTarget().width,fogLayers:18,
   voices:tracker.voices.map(v=>({id:v.id,midi:v.midi,previousMidi:v.previousMidi,x:v.x,targetX:v.targetX,level:v.level,height:v.height,phase:v.phase,born:v.born,velocity:v.velocity,style:v.style,moves:v.moves,active:v.active})),
   fifths:FIFTHS.map((pc,i)=>({pc,level:fifths[i].z})),reading,heading:signature}),
  dispose(){setActive(false);water.dispose();water.geometry.dispose();for(const r of resources)r.dispose();parent.remove(group);}};
}
