import { MODES, TONNETZ, TRIANGLES, pc, pitchClass, NOTE_NAMES, FIFTHS,
  fifthIndex, foldPosition, spiralPosition, weightedCells, createHarmonyState, intervalFamily } from './harmony-model.js';

// Original visual studies. All eight views share one performance clock and
// one part tracker; changing the view never creates a fresh note attack.
export function createHarmonyRenderer(THREE, parent, model, ctx) {
  const state=createHarmonyState(), root=new THREE.Group(), art=new THREE.Group();
  root.name='Live harmony instruments';root.add(art);parent.add(root);
  const resources=[],keep=r=>(resources.push(r),r),camera=ctx.camera;
  const palette=FIFTHS.map((_,i)=>new THREE.Color().setHSL((.48+i*.071)%1,.48,.65));
  const colour=m=>palette[fifthIndex(m)], voiceColour=v=>palette[Math.round(v.hue*12)%12], bone=new THREE.Color(0xe6eddb);
  const sphere=keep(new THREE.IcosahedronGeometry(1,3)), torus=keep(new THREE.TorusGeometry(1,.026,8,80));
  function glass(c){return keep(new THREE.MeshPhysicalMaterial({color:c,metalness:.38,roughness:.27,
    clearcoat:.32,clearcoatRoughness:.32,transmission:.12,thickness:.22,ior:1.46,
    iridescence:.10,envMap:ctx.lacquer.envMap,envMapIntensity:.32,emissive:c,emissiveIntensity:.04,side:THREE.DoubleSide}));}
  function ink(c,opacity=1){return keep(new THREE.MeshBasicMaterial({color:c,transparent:true,opacity,depthWrite:false}));}
  function mesh(g,m,where=art){const o=new THREE.Mesh(g,m);where.add(o);o.frustumCulled=false;return o;}
  function wire(count=96,c=0x658a96,opacity=.3){
    const g=keep(new THREE.BufferGeometry()),p=new Float32Array(count*3);g.setAttribute('position',new THREE.BufferAttribute(p,3));g.setDrawRange(0,0);
    const mat=keep(new THREE.LineBasicMaterial({color:c,transparent:true,opacity,depthWrite:false})),o=new THREE.Line(g,mat);art.add(o);o.frustumCulled=false;
    return{o,p,set(points){const n=Math.min(count,points.length);for(let i=0;i<n;i++)p.set([points[i].x,points[i].y,points[i].z||0],i*3);g.setDrawRange(0,n);g.attributes.position.needsUpdate=true;o.visible=n>1;}};
  }
  function facet(){const g=keep(new THREE.BufferGeometry());g.setAttribute('position',new THREE.BufferAttribute(new Float32Array(64*9),3));g.setAttribute('normal',new THREE.BufferAttribute(new Float32Array(64*9),3));g.setDrawRange(0,0);
    const o=mesh(g,glass(0x2c6975));o.visible=false;
    return{o,set(points,centre,depth=.035){let n=0;const a=g.attributes.position.array;
      for(let i=0;i<points.length;i++){const p=points[i],q=points[(i+1)%points.length];a.set([centre.x,centre.y,depth,p.x,p.y,p.z||0,q.x,q.y,q.z||0],n);n+=9;}
      g.setDrawRange(0,n/3);g.attributes.position.needsUpdate=true;g.computeVertexNormals();o.visible=n>0;}};
  }
  const nodes=Array.from({length:25},()=>{const o=mesh(sphere,glass(0xb3d3ce)),rim=mesh(torus,ink(0xcbded3,.5));return{o,rim};});
  const faces=Array.from({length:32},facet), lines=Array.from({length:100},()=>wire()), accents=Array.from({length:52},()=>mesh(torus,ink(0xaadbd6,.4)));
  // Petals have a curved, faceted surface, rather than a billboard texture.
  const petalGeo=keep(new THREE.BufferGeometry()),petalVertices=[];
  function pp(t,s){return [Math.sin(Math.PI*t)**.75*s*.19,t,Math.sin(Math.PI*t)*(.09+.09*(1-s*s))];}
  for(let i=0;i<22;i++)for(let j=0;j<8;j++){const t=i/22,u=(i+1)/22,s=j/4-1,v=(j+1)/4-1;petalVertices.push(...pp(t,s),...pp(u,s),...pp(u,v),...pp(t,s),...pp(u,v),...pp(t,v));}
  petalGeo.setAttribute('position',new THREE.Float32BufferAttribute(petalVertices,3));petalGeo.computeVertexNormals();
  const parts=Array.from({length:88},()=>({ring:mesh(torus,ink(0xcad6be)),petal:mesh(petalGeo,glass(0x91c7ba)),core:mesh(sphere,glass(0x95d4d0))}));
  const canvas=document.createElement('canvas'),paint=canvas.getContext('2d');let texture=keep(new THREE.CanvasTexture(canvas));texture.colorSpace=THREE.SRGBColorSpace;
  texture.minFilter=THREE.LinearFilter;texture.generateMipmaps=false;
  const hudMat=keep(new THREE.ShaderMaterial({uniforms:{uMap:{value:texture}},transparent:true,depthTest:false,depthWrite:false,toneMapped:false,
    vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy*2.,0.,1.);}',
    fragmentShader:'uniform sampler2D uMap;varying vec2 vUv;void main(){gl_FragColor=texture2D(uMap,vUv);}'}));
  const hud=mesh(keep(new THREE.PlaneGeometry(1,1)),hudMat,root);hud.renderOrder=36;
  (ctx.reflectionExclusions??=[]).push(hud);
  const projection=new THREE.Vector3(),aim=new THREE.Vector3(),mainPoints=[],voicePoints=[];
  const cellSites=FIFTHS.map((pitch,i)=>{const a=i*2.399963229728653,r=.20+Math.sqrt(i/11)*.62;return{pc:pitch,x:Math.cos(a)*r,y:Math.sin(a)*r*.78,weight:0};});
  let active=false,lastMode='',labels='harmony',time=0,nextPaint=0,reading={},rootPc=null,modeAge=0,span=.7,fade=1,expression=1,railLow=36,railHigh=84;
  let lastCells=-Infinity,cells=[],frameCount=0;const centre=new THREE.Vector3();
  const point=(x,y,z=0)=>({x,y,z});
  function node(i,p,pitch,level,power){const n=nodes[i];n.o.visible=n.rim.visible=true;n.o.position.set(p.x,p.y,p.z||0);
    power*=expression;const radius=.017+level*.012+Math.sqrt(Math.max(0,power))*.023;n.o.scale.setScalar(radius);
    n.o.material.color.copy(colour(pitch)).lerp(bone,.18);n.o.material.emissive.copy(colour(pitch));n.o.material.emissiveIntensity=(.015+power*.38)*fade;
    n.rim.position.copy(n.o.position);n.rim.position.z+=.005;n.rim.scale.setScalar(radius*1.62);n.rim.material.color.copy(colour(pitch));n.rim.material.opacity=(.12+level*.5)*fade;
    mainPoints.push({...p,pc:pitch,level,root:pitch===rootPc});
  }
  function line(i,points,c,opacity){lines[i].set(points);lines[i].o.material.color.set(c);lines[i].o.material.opacity=opacity*fade;}
  function circle(i,p,r,c,alpha,squash=1){const o=accents[i];if(!o)return;o.visible=true;o.position.set(p.x,p.y,(p.z||0)+.006);o.scale.set(r,r*squash,r);o.rotation.set(0,0,0);o.material.color.set(c);o.material.opacity=alpha*fade;}
  function screenPoint(p){projection.set(p.x,p.y,p.z||0);art.localToWorld(projection);projection.project(camera);return{x:(projection.x+1)*canvas.width/2,y:(1-projection.y)*canvas.height/2};}
  function update(dt,t,info,settings){
    state.update(model.notes,dt,t);time=t;active=settings.enabled&&settings.harmonyMode!=='atmosphere';root.visible=active;labels=settings.labels;art.visible=labels!=='full';if(!active)return;
    const mode=MODES[settings.harmonyMode]?settings.harmonyMode:'tonnetz';if(lastMode!==mode){lastMode=mode;modeAge=0;lastCells=-Infinity;}modeAge+=dt;fade=Math.min(1,.35+modeAge*3);
    rootPc=pitchClass(info?.root);camera.updateMatrixWorld();const distance=18,half=distance*Math.tan(camera.fov*Math.PI/360);
    // Unproject the centre: the piano uses setViewOffset to lower the keyboard.
    // A point straight along camera.forward is therefore not screen-centred.
    camera.getWorldDirection(aim);projection.set(0,0,.5).unproject(camera).sub(camera.position);
    root.position.copy(camera.position).addScaledVector(projection,distance/projection.dot(aim));root.quaternion.copy(camera.quaternion);root.scale.setScalar(half);
    span=Math.min(camera.aspect*.80,camera.aspect>1?.62:.78);art.position.set(0,.16,0);art.scale.setScalar(span);art.rotation.set(0,0,0);
    mainPoints.length=voicePoints.length=0;for(const n of nodes)n.o.visible=n.rim.visible=false;for(const f of faces)f.o.visible=false;for(const l of lines)l.o.visible=false;for(const a of accents)a.visible=false;
    for(const p of parts)p.core.visible=p.ring.visible=p.petal.visible=false;
    expression=settings.intensity;const level=state.levels,power=state.power,motion=settings.motion;
    const extents=state.voices.filter(v=>v.level>.02).map(v=>v.x);
    if(extents.length){const lo=Math.min(...extents),hi=Math.max(...extents),width=Math.max(36,hi-lo+12),mid=(hi+lo)/2;
      railLow+=(mid-width/2-railLow)*(1-Math.exp(-dt/.7));railHigh+=(mid+width/2-railHigh)*(1-Math.exp(-dt/.7));}
    if(mode==='tonnetz'){
      // Constant pitch positions make the overlap between successive chords visible.
      for(let i=0;i<TONNETZ.length;i++){const p=TONNETZ[i];node(i,p,p.pc,level[p.pc],power[p.pc]);}
      const edges=new Set();let edge=0;
      for(let i=0;i<TRIANGLES.length;i++){const tr=TRIANGLES[i],points=tr.ids.map(j=>TONNETZ[j]),energy=Math.min(...points.map(p=>level[p.pc]));
        if(energy>.025){const c=point(points.reduce((s,p)=>s+p.x,0)/3,points.reduce((s,p)=>s+p.y,0)/3);faces[i].set(points,c,-.025);faces[i].o.material.color.copy(colour(tr.root)).multiplyScalar(.28+energy*.6);faces[i].o.material.emissive.copy(colour(tr.root));faces[i].o.material.emissiveIntensity=.035+Math.min(...points.map(p=>power[p.pc]))*.24;}
        for(let j=0;j<3;j++){const a=tr.ids[j],b=tr.ids[(j+1)%3],id=[a,b].sort((x,y)=>x-y).join(':');if(edges.has(id))continue;edges.add(id);line(edge++,[TONNETZ[a],TONNETZ[b]],0x9cb9ba,.13+Math.min(level[TONNETZ[a].pc],level[TONNETZ[b].pc])*.35);}}
    }else if(mode==='folds'){
      art.rotation.set(.25,-.27,0);const names=new Map((info?.notes||[]).map(n=>[pc(n.midi),n.name]));
      const positions=NOTE_NAMES.map((name,pitch)=>foldPosition(names.get(pitch)||name));
      for(let i=0;i<12;i++){const p=positions[i];node(i,p,i,level[i],power[i]);if(p.z)line(i,[point(p.x,p.y,-.01),p],colour(i),.15+level[i]*.6);}
      let index=12;for(let i=0;i<12;i++)for(let j=i+1;j<12;j++)if(level[i]>.08&&level[j]>.08)line(index++,[positions[i],positions[j]],colour(rootPc??i),.22+Math.min(level[i],level[j])*.22);
      const plane=[point(-1,-.67,-.02),point(1,-.67,-.02),point(1,.73,-.02),point(-1,.73,-.02),point(-1,-.67,-.02)];line(95,plane,0x587d89,.28);
    }else if(mode==='spiral'){
      art.rotation.set(.12,-.62+Math.sin(t*.07)*.07*motion,0);
      const helix=Array.from({length:96},(_,i)=>{const n=i/95*11,a=n*Math.PI/2;return point(Math.cos(a)*.64,(n-5.5)*.137,Math.sin(a)*.64);});line(0,helix,0x8daebc,.38);
      let sum=0;aim.set(0,0,0);for(let i=0;i<12;i++){const p=spiralPosition(i);node(i,p,i,level[i],power[i]);sum+=level[i];aim.addScaledVector(new THREE.Vector3(p.x,p.y,p.z),level[i]);}
      if(sum>.01)aim.divideScalar(sum);centre.lerp(aim,1-Math.exp(-dt/.7));
      circle(0,centre,.08+Math.min(sum,6)*.009,0xf0dab0,Math.min(1,sum)*.6);
      for(let i=0;i<12;i++)if(level[i]>.025)line(i+1,[spiralPosition(i),centre],colour(i),level[i]*.48);
    }else if(mode==='glass'){
      for(let i=0;i<12;i++){const s=cellSites[i],target=power[s.pc]*.15+(state.bass!==null&&pc(state.bass)===s.pc?.025:0);s.weight+=(target-s.weight)*(1-Math.exp(-dt/.24));}
      if(t-lastCells>1/30||t<lastCells){cells=weightedCells(cellSites,[-1,-.76,1,.76]);lastCells=t;}
      for(let i=0;i<12;i++){const s=cellSites[i],poly=cells[i];if(!poly?.length)continue;
        const c=point(poly.reduce((a,p)=>a+p[0],0)/poly.length,poly.reduce((a,p)=>a+p[1],0)/poly.length);
        const pts=poly.map(p=>point(c.x+(p[0]-c.x)*.98,c.y+(p[1]-c.y)*.98,-.015));
        faces[i].set(pts,c,.035+power[s.pc]*.07);faces[i].o.material.color.copy(colour(s.pc)).multiplyScalar(.10+level[s.pc]*.62);faces[i].o.material.emissive.copy(colour(s.pc));faces[i].o.material.emissiveIntensity=.014+power[s.pc]*.24;
        line(i,[...pts,pts[0]],colour(s.pc),.10+level[s.pc]*.6);node(i,{...c,z:.08+power[s.pc]*.07},s.pc,level[s.pc],power[s.pc]);}
    }else if(mode==='compass'){
      const positions=FIFTHS.map((p,i)=>point(Math.sin(i*Math.PI/6)*.76,Math.cos(i*Math.PI/6)*.76));
      circle(0,point(0,0,-.015),.76,0x8aaeb0,.23);circle(1,point(0,0,-.015),.67,0x65858f,.16);
      for(let i=0;i<12;i++){const pitch=FIFTHS[i],p=positions[i];node(i,p,pitch,level[pitch],power[pitch]);line(i,[point(p.x*.86,p.y*.86),point(p.x*.92,p.y*.92)],0xb3c8bf,.30);}
      const selected=positions.filter((_,i)=>level[FIFTHS[i]]>.06);if(selected.length>1)line(20,[...selected,selected[0]],colour(rootPc??0),.6);
      if(rootPc!==null){const p=positions[fifthIndex(rootPc)];circle(2,p,.092,0xe8d19b,.8);line(21,[point(0,0),p],0xe8d19b,.42);}
      if(state.bass!==null){const p=positions[fifthIndex(state.bass)],r=.055;line(22,[point(p.x,p.y+r,.02),point(p.x+r,p.y,.02),point(p.x,p.y-r,.02),point(p.x-r,p.y,.02),point(p.x,p.y+r,.02)],0xf5f2d8,.95);}
    }else{
      const voices=[...state.voices].sort((a,b)=>a.x-b.x),dense=voices.length>18;let pulseIndex=0;
      for(let i=0;i<voices.length;i++){const v=voices[i],p=parts[i],strength=v.velocity*v.velocity,theta=fifthIndex(v.midi)*Math.PI/6;
        let x,y,z=.05,angle=0;
        if(mode==='petals'){const octave=Math.floor(v.midi/12)-4,r=.10+Math.max(0,octave+2)*.042;angle=-theta+octave*.16;const a=-angle;x=Math.sin(a)*r;y=Math.cos(a)*r;z=octave*.012;
          p.petal.visible=true;p.petal.position.set(x,y,z);p.petal.rotation.set(Math.sin(v.phase*6.28)*.07*motion,0,angle);
          const size=(.32+v.level*.30+strength*.18)*(dense?.68:1);p.petal.scale.set(.44+strength*.38,size,size);
          p.petal.material.color.copy(voiceColour(v)).multiplyScalar(.25+v.level*.68);p.petal.material.emissive.copy(voiceColour(v));p.petal.material.emissiveIntensity=(v.level*(.02+strength*.25)+v.heat*.2)*expression;
          x+=Math.sin(a)*size*.82;y+=Math.cos(a)*size*.82;
        }else{ x=Math.max(-.93,Math.min(.93,-1+2*(v.x-railLow)/(railHigh-railLow)));y=(mode==='rings'?Math.sin(v.phase*6.28)*.055*motion:Math.sin((v.x-36)*.105)*.26)+(Math.floor(v.midi/12)%2)*.025;
          if(mode==='rings'){p.ring.visible=true;p.ring.position.set(x,y,z);p.ring.rotation.set(.32+Math.sin(v.phase*6.28)*.16*motion,.1,Math.sin(v.phase*6.28)*.15*motion);
            const radius=(.09+strength*.11+v.level*.08)*(dense?.6:1);p.ring.scale.set(radius,radius*(1.3+v.velocity*.4),radius);p.ring.material.color.copy(voiceColour(v));p.ring.material.opacity=Math.min(1,v.level*(.28+strength*.7)*expression)*fade;}
        }
        p.core.visible=true;p.core.position.set(x,y,z);p.core.scale.setScalar((.013+strength*.022)*Math.min(1,v.level*5));p.core.material.color.copy(voiceColour(v));p.core.material.emissive.copy(voiceColour(v));p.core.material.emissiveIntensity=(.04+strength*.4+v.heat*.3)*v.level*expression;
        voicePoints.push({x,y,z,v});
        if(mode!=='yarn')for(const pulse of v.pulses){if(pulseIndex>=48)break;const age=t-pulse.at,life=Math.max(0,1-age/2.6);circle(pulseIndex++,point(x,y,z),.025+age*(.06+pulse.power*.15),voiceColour(v),life*life*(.2+pulse.power*.7)*v.level*expression,mode==='petals'?.5:1.25);}
      }
      for(let i=1;i<voicePoints.length;i++){const a=voicePoints[i-1],b=voicePoints[i],family=intervalFamily(b.v.midi-a.v.midi),c={third:0xe3bb77,fifth:0x70bed8,tension:0xcc83a7,octave:0xc0d9c8}[family];
        const pts=Array.from({length:36},(_,j)=>{const f=j/35,arch=Math.sin(f*Math.PI);return point(a.x+(b.x-a.x)*f,a.y+(b.y-a.y)*f+arch*(mode==='yarn'?.20+Math.abs(b.v.x-a.v.x)*.008:.05)*motion, .045+arch*.08);});
        line(i-1,pts,c,Math.min(a.v.level,b.v.level)*(mode==='yarn'?.8:.22));
        if(mode==='yarn'&&pulseIndex<52){const f=(t*.27+a.v.phase)%1,j=Math.round(f*35);circle(pulseIndex++,pts[j],.013+a.v.heat*.011,c,Math.min(a.v.level,b.v.level)*.75);}}
    }
    root.updateMatrixWorld(true);
    if(t>=nextPaint||t<nextPaint-.2){nextPaint=t+1/30;reading=window.__piano?.stats?.()||reading;draw(info,settings,mode);}
    frameCount++;
  }
  function draw(info,settings,mode){
    const aspect=camera.aspect,w=Math.round(Math.min(2400,Math.max(1000,ctx.renderer.domElement.width))),h=Math.round(w/aspect);
    // Bound the label texture independently from the selected render resolution.
    const scale=Math.min(1,2600/h),width=Math.round(w*scale),height=Math.round(h*scale);
    if(canvas.width!==width||canvas.height!==height){
      canvas.width=width;canvas.height=height;
      // Canvas dimensions are also GPU storage dimensions. Reusing an uploaded
      // texture after a framing change left the previous portrait labels frozen.
      const previous=texture;texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;
      texture.minFilter=THREE.LinearFilter;texture.generateMipmaps=false;
      resources[resources.indexOf(previous)]=texture;hudMat.uniforms.uMap.value=texture;previous.dispose();
    }
    const W=canvas.width,H=canvas.height,mobile=aspect<1,unit=Math.min(W,H),font=(size,weight=350)=>`${weight} ${size}px "Segoe UI Variable", "Segoe UI", sans-serif`;
    paint.clearRect(0,0,W,H);hud.visible=labels!=='off';if(labels==='off'){texture.needsUpdate=true;return;}
    const natural=s=>String(s||'').replace(/#/g,'♯').replace(/([A-G])b/g,'$1♭').replace(/b(?=[0-9]|$)/g,'♭').replace(/\^/g,'');
    const gradient=paint.createLinearGradient(0,H*.02,0,H*.34);gradient.addColorStop(0,'rgba(2,12,20,.62)');gradient.addColorStop(1,'rgba(2,12,20,0)');paint.fillStyle=gradient;paint.fillRect(0,0,W,H*.34);
    const left=W*.07,top=H*.105;paint.textAlign='left';paint.textBaseline='alphabetic';paint.fillStyle='#8aa9ad';paint.font=font(unit*.015,500);paint.letterSpacing=`${unit*.003}px`;paint.fillText(labels==='full'?'STAFF & VOICING':MODES[mode].name.split(' · ')[0].toUpperCase(),left,top);paint.letterSpacing='0px';
    let shown=info?.name||'',number=info?reading.nns:null,key=reading.key?.name||'';
    if(info&&!info.root&&info.notes?.length>5&&shown.includes(' '))shown=`${info.notes.length} notes`;
    if(reading.nnsMode==='numbers'&&number)shown=number;
    if(!shown)shown='Listen to the space';
    let size=unit*(mobile?.095:.081);const title=natural(shown),parts=/^\d+ notes$/.test(title)?null:/^([A-G][♯♭]?|[♯♭]?[1-7])([^/]*)(.*)$/.exec(title);
    const runs=parts?[{t:parts[1],s:1,dy:0},{t:parts[2],s:.53,dy:-.30},{t:parts[3],s:.70,dy:0}]:[{t:title,s:.66,dy:0}];
    const measure=()=>runs.reduce((s,r)=>{paint.font=font(size*r.s,280);return s+paint.measureText(r.t).width+size*.05;},0);
    while(measure()>W*.84&&size>unit*.023)size*=.93;
    paint.fillStyle='#e4ecdf';let x=left;for(const r of runs){paint.font=font(size*r.s,280);paint.fillText(r.t,x,top+unit*.09+r.dy*size);x+=paint.measureText(r.t).width+size*.05;}
    const sub=labels==='chord'?'':[reading.nnsMode!=='off'&&reading.nnsMode!=='numbers'?number:null,key?`home · ${key}`:null].filter(Boolean).join('   /   ');
    paint.font=font(unit*.020,400);paint.fillStyle=reading.key?.dim?'#759296':'#b6c9c2';paint.fillText(natural(sub),left,top+unit*.129,W*.85);
    const spellings=new Map((info?.notes||[]).map(n=>[pc(n.midi),natural(n.name)]));
    paint.textAlign='center';paint.textBaseline='middle';
    if(labels!=='full'&&mainPoints.length){for(const p of mainPoints){const s=screenPoint(p);paint.font=font(unit*(mode==='glass'?.024:.019),p.root?600:400);paint.fillStyle=p.level>.07?'#f1f2df':'#6e939e';
      paint.shadowColor='#04131b';paint.shadowBlur=unit*.008;paint.fillText(spellings.get(p.pc)||NOTE_NAMES[p.pc],s.x,s.y-unit*.027);paint.shadowBlur=0;}}
    else if(labels!=='full'&&voicePoints.length<=18){for(const p of voicePoints){const s=screenPoint(p);paint.globalAlpha=Math.min(1,p.v.level*3);paint.font=font(unit*.020,400);paint.fillStyle='#e3ecdd';paint.fillText(`${spellings.get(pc(p.v.midi))||NOTE_NAMES[pc(p.v.midi)]}${Math.floor(p.v.midi/12)-1}`,s.x,s.y-unit*.036);}}
    paint.globalAlpha=1;
    // A chromatic, octave-aware rail anchors every abstract view to the actual keys.
    // Three label lanes alternate by semitone, so close inner voices remain readable.
    const visible=state.voices.filter(v=>v.level>.015).sort((a,b)=>a.x-b.x),y=H*.69;
    paint.strokeStyle='rgba(145,182,184,.23)';paint.lineWidth=1;paint.beginPath();paint.moveTo(W*.07,y);paint.lineTo(W*.93,y);paint.stroke();
    for(const v of visible){const rx=W*(.07+.86*Math.max(0,Math.min(1,(v.x-railLow)/(railHigh-railLow)))),c=voiceColour(v).getStyle(),lane=pc(v.midi)%3;
      projection.set(ctx.keyX(Math.round(v.midi)),1,-3.7).project(camera);const kx=(projection.x+1)*W/2,ky=(1-projection.y)*H/2;
      paint.globalAlpha=Math.min(1,v.level*2);paint.strokeStyle=c;paint.lineWidth=Math.max(1,unit*.001);paint.globalAlpha*=.2;paint.beginPath();paint.moveTo(rx,y);paint.bezierCurveTo(rx,y+H*.025,kx,ky-H*.025,kx,ky);paint.stroke();paint.globalAlpha=Math.min(1,v.level*2);
      paint.fillStyle=c;paint.beginPath();paint.arc(rx,y,unit*(.0025+v.velocity*v.velocity*.004),0,Math.PI*2);paint.fill();
      if(visible.length<=24){paint.font=font(unit*(mobile?.019:.016),450);paint.fillStyle='#d3e4dc';paint.fillText(`${spellings.get(pc(v.midi))||NOTE_NAMES[pc(v.midi)]}${Math.floor(v.midi/12)-1}`,rx,y-unit*(.022+lane*.024));}
    }
    paint.globalAlpha=1;paint.textAlign='left';paint.font=font(unit*.0125,400);paint.fillStyle='#8cabae';
    const hint=labels==='full'?`${visible.filter(v=>v.active).length} sounding voices`:mode==='folds'?'♭ below   ·   naturals on the plane   ·   ♯ above':mode==='yarn'?'thirds · gold    fifths · blue    close intervals · rose':mode==='compass'?'halo · root    diamond · bass    clockwise · fifths':`${visible.filter(v=>v.active).length} sounding voices${model.state.pedal?'   ·   pedal held':''}`;
    paint.fillText(hint,W*.07,H*.712,W*.86);texture.needsUpdate=true;
  }
  return{update,state,ownsTheory:()=>active,
    stats:()=>({active,mode:lastMode,frames:frameCount,voices:state.voices.map(v=>({id:v.id,midi:v.midi,x:v.x,phase:v.phase,born:v.born,level:v.level,heat:v.heat,active:v.active,pulses:v.pulses.length})),bass:state.bass,
      levels:[...state.levels],power:[...state.power],heading:reading.nns,key:reading.key?.name,texture:[canvas.width,canvas.height]}),
    dispose(){for(const r of resources)r.dispose();parent.remove(root);}};
}
