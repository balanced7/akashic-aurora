// One path definition serves the strands, note glass and connections between voices.
export const notePathGLSL = `
uniform sampler2D uNotes,uKeyMotion,uRipple;uniform vec4 uRippleBounds;
uniform float uFlow,uCalm,uMotion,uTheme;
uniform vec3 uNoteBounds;
float lanternAt(float key){return .29+mod(key,3.0)*.105;}
vec3 notePath(float key,float y){
 vec4 n=texture2D(uNotes,vec2((key+.5)/88.0,.25));
 vec4 movement=texture2D(uKeyMotion,vec2((key+.5)/88.0,.5));
 float power=movement.z*movement.z,top=7.0+movement.x*1.4;
 vec2 q=(vec2(n.x,-5.0)-uRippleBounds.xy)/uRippleBounds.zw;
 float wave=texture2D(uRipple,q+vec2(1.0/256.0,0)).r-texture2D(uRipple,q-vec2(1.0/256.0,0)).r;
 float city=1.0-smoothstep(0.0,.6,abs(uTheme-5.0)),rain=1.0-smoothstep(0.0,.6,abs(uTheme-4.0));
 float bend=sin(y*4.0+uFlow*.65+(key+21.0)/127.0*20.0)+wave*2.0;
 float dx=bend*sin(y*3.14159)*(2.0+power*7.0+uCalm*3.0)*uMotion*(1.0-city*.94);
 float room=max(.01,dx>0.0?uNoteBounds.y-n.x:n.x-uNoteBounds.x);
 dx=sign(dx)*room*(1.0-exp(-abs(dx)/room));
 float ceiling=max(7.0,uNoteBounds.z-1.15),height=y*top*(1.0-rain*.55);
 return vec3(n.x+dx,
  1.15+ceiling*(1.0-exp(-height/ceiling)),
  -3.9-sin(y*5.0+(key+21.0)/127.0*40.0+uFlow*.3)*y*(3.0+power*4.0)*(1.0-city)-y*y*rain*42.0);
}`;

export function createVoicings(THREE,parent,u,model,ctx){
 const resources=[],objects=[];
 const layoutData=new Float32Array(88*4),layoutTexture=new THREE.DataTexture(layoutData,88,1,THREE.RGBAFormat,THREE.FloatType);
 layoutTexture.needsUpdate=true;resources.push(layoutTexture);u.uLabelLayout={value:layoutTexture};
 const positioned=new Set(),projected=new THREE.Vector3();
 function labelLayout(active){
  const portrait=ctx.camera.aspect<1,w=portrait?.16:.07,h=w*ctx.camera.aspect/1.535,boxes=[];
  // Pitch-ordered packing gives dense chords room; leaders retain the physical attachment.
  for(const key of active){const o=key*4,m=model.keyMotion;
   const y=.29+key%3*.105,power=m[o+2]**2,top=7+m[o]*1.4;
   const theme=u.uTheme.value,weight=id=>Math.max(0,1-Math.min(1,Math.abs(theme-id)/.6)**2*(3-2*Math.min(1,Math.abs(theme-id)/.6)));
   const city=weight(5),rain=weight(4),x=ctx.keyX(key+21);
   let dx=Math.sin(y*4+u.uFlow.value*.65+(key+21)/127*20)*Math.sin(y*Math.PI)*(2+power*7+u.uCalm.value*3)*u.uMotion.value*(1-city*.94);
   const room=Math.max(.01,dx>0?u.uNoteBounds.value.y-x:x-u.uNoteBounds.value.x);dx=Math.sign(dx)*room*(1-Math.exp(-Math.abs(dx)/room));
   const ceiling=Math.max(7,u.uNoteBounds.value.z-1.15),height=y*top*(1-rain*.55);
   projected.set(x+dx,1.15+ceiling*(1-Math.exp(-height/ceiling)),-3.9-Math.sin(y*5+(key+21)/127*40+u.uFlow.value*.3)*y*(3+power*4)*(1-city)-y*y*rain*42).project(ctx.camera);
   const baseX=Math.max(-.94+w/2,Math.min(.94-w/2,projected.x)),baseY=Math.max(-.43+h/2,Math.min(.22-h/2,projected.y));
   let best=null;
   for(let row=0;row<18;row++)for(const col of [0,-1,1,-2,2]){
    const sign=row%2===0?1:-1,offset=Math.ceil(row/2)*sign;
    const px=Math.max(-.94+w/2,Math.min(.94-w/2,baseX+col*w*1.08)),py=baseY+offset*h*1.16;
    if(py<-.43+h/2||py>.25-h/2||boxes.some(b=>Math.abs(px-b.x)<w*1.04&&Math.abs(py-b.y)<h*1.07))continue;
    const cost=(px-baseX)**2+(py-baseY)**2+(positioned.has(key)?((px-layoutData[o])**2+(py-layoutData[o+1])**2)*.4:0);
    if(!best||cost<best.cost)best={x:px,y:py,cost};
   }
   best ||= {x:baseX,y:baseY};boxes.push(best);
   // Packing itself must not interpolate through another label. The common flow still
   // moves continuously underneath, and the leader carries that movement to the label.
   layoutData[o]=best.x;layoutData[o+1]=best.y;layoutData[o+2]=w;layoutData[o+3]=h;positioned.add(key);
  }
  for(const key of positioned)if(!active.includes(key))positioned.delete(key);
  layoutTexture.needsUpdate=true;
 }
 const atlas=document.createElement('canvas');atlas.width=1408;atlas.height=1024;
 const paint=atlas.getContext('2d'),names=Array(88).fill('');
 const glyphs=new THREE.CanvasTexture(atlas);glyphs.minFilter=THREE.LinearMipmapLinearFilter;resources.push(glyphs);
 const canonical=['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'];
 function writeName(key,name){if(names[key]===name)return false;names[key]=name;
  const x=key%11*128,y=Math.floor(key/11)*128;paint.clearRect(x,y,128,128);
  paint.fillStyle='#fff';paint.textAlign='center';paint.textBaseline='middle';
  paint.font='600 48px "Segoe UI", sans-serif';paint.fillText(name,x+64,y+65,116);return true;}
 for(let key=0;key<88;key++){const midi=key+21;writeName(key,canonical[midi%12]+(Math.floor(midi/12)-1));}
 function instanced(base,attributes,count,vs,fs,options={}){
  const g=new THREE.InstancedBufferGeometry();g.setIndex(base.index);
  for(const [name,a]of Object.entries(base.attributes))g.setAttribute(name,a);
  for(const [name,a]of Object.entries(attributes))g.setAttribute(name,a);g.instanceCount=count;
  const mat=new THREE.ShaderMaterial({uniforms:{...u,uGlyphs:{value:glyphs}},vertexShader:vs,fragmentShader:fs,
   transparent:true,depthWrite:false,side:THREE.DoubleSide,...options});
  const mesh=new THREE.Mesh(g,mat);mesh.frustumCulled=false;parent.add(mesh);objects.push(mesh);resources.push(g,mat);base.dispose();return mesh;
 }
 const keys=new THREE.InstancedBufferAttribute(Float32Array.from({length:88},(_,i)=>i),1);
 const glass=instanced(new THREE.PlaneGeometry(2.15,1.4),{aNote:keys},88,notePathGLSL+`
  uniform sampler2D uLabelLayout;attribute float aNote;varying vec2 vUv;varying float vKey,vLight;
  void main(){vUv=uv;vKey=aNote;vLight=texture2D(uKeyMotion,vec2((aNote+.5)/88.0,.5)).z;
   vec4 placement=texture2D(uLabelLayout,vec2((aNote+.5)/88.0,.5));gl_Position=vec4(placement.xy+(uv-.5)*placement.zw,0,1);}`,
  `uniform sampler2D uGlyphs;uniform vec3 uA,uB,uC;uniform float uFlow;
   varying vec2 vUv;varying float vKey,vLight;
   void main(){if(vLight<.012)discard;vec2 q=abs(vUv-.5)-vec2(.39,.32);
    float d=length(max(q,0.0))+min(max(q.x,q.y),0.0)-.07;
    float aa=max(fwidth(d),.002),inside=1.0-smoothstep(-aa,aa,d);
    float rim=exp(-abs(d)*120.0),halo=exp(-max(d,0.0)*24.0)*.1;
    vec2 cell=vec2(mod(vKey,11.0),7.0-floor(vKey/11.0));
    float letter=texture2D(uGlyphs,(cell+vUv)/vec2(11.0,8.0)).a;
    vec3 spectral=.5+.5*cos(vec3(0,2.094,4.188)+(vUv.x+vUv.y)*4.0+vKey*.25+uFlow*.12);
    vec3 edge=mix(mix(uA,uC,.4),spectral,.5);
    float shine=pow(max(0.0,1.0-abs(vUv.y-.78+vUv.x*.2)*18.0),3.0)*inside*.11;
    vec3 colour=mix(uB*.035,edge*(.65+vLight*.6),rim)+edge*shine;
    colour=mix(colour,mix(vec3(1.1),uC,.12),letter);
    gl_FragColor=vec4(colour,(inside*.76+halo+letter*.18)*smoothstep(0.0,.1,vLight));}`);
 glass.renderOrder=7;glass.material.depthTest=false;
 const leaders=instanced(new THREE.PlaneGeometry(1,1),{aNote:keys},88,notePathGLSL+`
  uniform sampler2D uLabelLayout;attribute float aNote;varying vec2 vUv;varying float vLight;
  void main(){vUv=uv;vLight=texture2D(uKeyMotion,vec2((aNote+.5)/88.0,.5)).z;
   vec4 point=projectionMatrix*modelViewMatrix*vec4(notePath(aNote,lanternAt(aNote)),1.0);
   vec2 end=texture2D(uLabelLayout,vec2((aNote+.5)/88.0,.5)).xy;
   gl_Position=vec4(mix(point.xy/point.w,end,uv.x)+vec2(0,position.y*.0015),0,1);}`,
  `uniform vec3 uA;varying vec2 vUv;varying float vLight;void main(){gl_FragColor=vec4(uA,sin(vUv.y*3.14159)*vLight*.32);}`,
  {depthTest:false,blending:THREE.AdditiveBlending});leaders.renderOrder=6;
 const pairData=new Float32Array(87*2),pairs=new THREE.InstancedBufferAttribute(pairData,2);
 const links=instanced(new THREE.PlaneGeometry(1,1,48,1),{aPair:pairs},0,notePathGLSL+`
  attribute vec2 aPair;varying vec2 vUv;varying float vLight,vPhase;
  void main(){vUv=uv;vec3 a=notePath(aPair.x,lanternAt(aPair.x)),b=notePath(aPair.y,lanternAt(aPair.y));
   vLight=min(texture2D(uKeyMotion,vec2((aPair.x+.5)/88.0,.5)).z,texture2D(uKeyMotion,vec2((aPair.y+.5)/88.0,.5)).z);
   float city=1.0-smoothstep(0.0,.6,abs(uTheme-5.0));
   vec3 p=mix(a,b,uv.x);p.y+=sin(uv.x*3.14159)*min(length(b-a)*.18,3.0)*(1.0-city);
   vec3 corner=vec3(b.x,a.y,(a.z+b.z)*.5);
   vec3 circuit=uv.x<.5?mix(a,corner,uv.x*2.0):mix(corner,b,(uv.x-.5)*2.0);
   p=mix(p,circuit,city);vec4 view=modelViewMatrix*vec4(p,1.0);
   view.y+=position.y*(.075+vLight*.075);gl_Position=projectionMatrix*view;
   vPhase=aPair.x*.61803398875;}`,
  `uniform vec3 uA,uB,uC;uniform float uFlow;varying vec2 vUv;varying float vLight,vPhase;
   void main(){float pulse=.5+.5*sin(uFlow*1.7+vPhase);float d=(vUv.x-pulse)*24.0;
    float light=exp(-d*d),edge=pow(max(0.0,sin(vUv.y*3.14159)),1.8);
    gl_FragColor=vec4(mix(uA,uC,light)*(.4+light*1.6),edge*(.2+light*.7)*vLight);}`,
  {blending:THREE.AdditiveBlending});links.renderOrder=6;
 // Light scattered through low mist. Its positions are the same note paths, on the GPU.
 const mistData=new Float32Array(16*2),mistKeys=new THREE.InstancedBufferAttribute(mistData,2);
 const mist=instanced(new THREE.PlaneGeometry(18,14),{aSource:mistKeys},0,notePathGLSL+`
  attribute vec2 aSource;varying vec3 vWorld;varying vec2 vUv;varying float vLight;
  void main(){vec3 source=notePath(aSource.x,lanternAt(aSource.x));vUv=uv;vLight=aSource.y;
   vec3 p=source+position+vec3(0,0,-8);vWorld=p;gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);}`,
  `uniform float uFlow,uOpacity;uniform vec3 uA,uC;varying vec3 vWorld;varying vec2 vUv;varying float vLight;
   void main(){vec2 delta=(vUv-.5)*vec2(5.8,4.9);
    float density=.55+.25*sin(vWorld.x*.38+sin(vWorld.y*.6)+uFlow*.6)+.2*sin(vWorld.y*.8-vWorld.x*.15-uFlow*.3);
    float scatter=exp(-dot(delta,delta))*(.06+vLight*.26);
    float boundary=pow(max(0.0,sin(vUv.y*3.14159)),2.0)*smoothstep(0.0,.08,vUv.x)*(1.0-smoothstep(.92,1.0,vUv.x));
    gl_FragColor=vec4(mix(uA,uC,vLight),scatter*density*boundary*uOpacity);}`,
  {blending:THREE.AdditiveBlending});mist.renderOrder=3;
 // Consume the piano's published Nashville/key reading; never infer a second key.
 const numberCanvas=document.createElement('canvas');numberCanvas.width=768;numberCanvas.height=256;
 const numberPaint=numberCanvas.getContext('2d'),numberTexture=new THREE.CanvasTexture(numberCanvas);
 const numberUniforms={...u,uNumber:{value:numberTexture},uPortrait:{value:0},uDim:{value:0}};
 const numberGeometry=new THREE.PlaneGeometry(1,1);
 const numberMaterial=new THREE.ShaderMaterial({uniforms:numberUniforms,transparent:true,depthTest:false,depthWrite:false,
  vertexShader:`uniform float uPortrait;varying vec2 vUv;void main(){vUv=uv;
   vec2 centre=mix(vec2(-.70,.34),vec2(0,.45),uPortrait),size=mix(vec2(.43,.19),vec2(.60,.135),uPortrait);
   gl_Position=vec4(centre+position.xy*size,0,1);}`,
  fragmentShader:`uniform sampler2D uNumber;uniform vec3 uA,uB,uC;uniform float uFlow,uDim;varying vec2 vUv;
   void main(){vec2 p=abs(vUv-.5)-vec2(.45,.31);float d=length(max(p,0.0))+min(max(p.x,p.y),0.0)-.055;
    float inside=1.0-smoothstep(-.003,.003,d),rim=exp(-abs(d)*170.0);
    vec4 text=texture2D(uNumber,vUv);vec3 edge=mix(uA,uC,.5+.5*sin(vUv.x*4.0+uFlow*.12));
    vec3 colour=mix(uB*.025+rim*edge*.75,text.rgb,text.a);
    gl_FragColor=vec4(colour,(inside*.7+text.a*.25)*(1.0-uDim*.55));}`});
 const numberGlass=new THREE.Mesh(numberGeometry,numberMaterial);numberGlass.frustumCulled=false;numberGlass.renderOrder=20;
 parent.add(numberGlass);objects.push(numberGlass);resources.push(numberTexture,numberGeometry,numberMaterial);
 let lastReading='',reading=null,nextReading=0;
 let activeCount=0;
 return {update(info,labels){
  let changed=false;for(const n of info?.notes||[]){if(n.midi>=21&&n.midi<=108&&n.name)changed=writeName(n.midi-21,n.name+(n.octave??Math.floor(n.midi/12)-1))||changed;}
  if(changed)glyphs.needsUpdate=true;
  const active=[];for(let k=0;k<88;k++)if(model.keyMotion[k*4+2]>.035)active.push(k);
  activeCount=active.length;for(let i=1;i<active.length;i++){pairData[(i-1)*2]=active[i-1];pairData[(i-1)*2+1]=active[i];}
  labelLayout(active);leaders.visible=labels!=='off';
  pairs.needsUpdate=true;links.geometry.instanceCount=Math.max(0,active.length-1);glass.visible=labels!=='off';
  const brightest=[...active].sort((a,b)=>model.keyMotion[b*4+2]-model.keyMotion[a*4+2]).slice(0,16);
  brightest.forEach((k,i)=>{mistData[i*2]=k;mistData[i*2+1]=model.keyMotion[k*4+2];});
  mistKeys.needsUpdate=true;mist.geometry.instanceCount=brightest.length;
  numberUniforms.uPortrait.value=ctx.camera.aspect<1?1:0;
  if(u.uTime.value>=nextReading){nextReading=u.uTime.value+.1;const current=window.__piano?.stats?.();
   if(current){reading={number:current.nns,key:current.key.name,dim:current.key.dim,mode:current.nnsMode};
    numberUniforms.uDim.value=current.key.dim?1:0;
    const signature=JSON.stringify(reading);if(signature!==lastReading){lastReading=signature;numberPaint.clearRect(0,0,768,256);
     numberPaint.fillStyle='#eff5ee';numberPaint.textAlign='center';numberPaint.textBaseline='middle';
     numberPaint.font='600 94px "Segoe UI", sans-serif';numberPaint.fillText(reading.number||'·',384,106,680);
     numberPaint.fillStyle='#a4ccc9';numberPaint.font='500 27px "Segoe UI", sans-serif';
     numberPaint.fillText(reading.key?reading.key.toUpperCase():'LISTENING FOR THE KEY',384,179,680);numberTexture.needsUpdate=true;}
   }
  }
  numberGlass.visible=labels==='harmony'&&reading?.mode!=='off';
 },stats:()=>({voices:activeCount,links:links.geometry.instanceCount,labels:glass.visible,nashville:numberGlass.visible?reading:null,names:names.filter((_,k)=>model.keyMotion[k*4+2]>.035)}),
 dispose(){for(const object of objects)parent.remove(object);for(const resource of resources)resource.dispose();}};
}
