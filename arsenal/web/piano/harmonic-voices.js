// Visual part tracking, not a claim about a performer's intended counterpoint.
// Exact held pitches win; recently released neighbours can continue a moving part.
export const FIFTHS = Object.freeze([0, 7, 2, 9, 4, 11, 6, 1, 8, 3, 10, 5]);
export const fifthIndex = midi => ((midi % 12 + 12) % 12 * 7) % 12;
const ease = (a, b, dt, tau) => a + (b - a) * (1 - Math.exp(-dt / tau));

// Dense voicings get separate, bounded letter positions. Prefer vertical movement
// over crossing the neighbouring part; the renderer draws a leader when displaced.
export function packVoiceLabels(anchors,aspect){
  const width=(aspect<1?.13:.061)*Math.max(.5,Math.min(1,Math.sqrt(10/Math.max(1,anchors.length)))),height=width*aspect;
  const boxes=[],result=Array(anchors.length),left=-.88,right=.88,bottom=-.46,top=.48;
  const columns=Math.floor((right-left)/width)+1,rows=Math.floor((top-bottom)/height)+1;
  for(const {a,i} of anchors.map((a,i)=>({a,i})).sort((a,b)=>a.a.x-b.a.x)){
    const x=Math.max(left,Math.min(right,a.x)),y=Math.max(bottom,Math.min(top,a.y));
    const free=(x,y)=>!boxes.some(b=>Math.abs(x-b.x)<width*.98&&Math.abs(y-b.y)<height*.98);
    if(free(x,y)){const p={x,y,width,height};boxes.push(p);result[i]=p;continue;}
    let best=null,cost=Infinity;
    for(let row=0;row<rows;row++){
      const py=bottom+row*height;
      for(let column=0;column<columns;column++){
        const px=left+column*width,d=(px-x)**2*3+(py-y)**2;
        if(d<cost&&free(px,py)){best={x:px,y:py,width,height};cost=d;}
      }
    }
    // The grid fits all 88 MIDI keys at every supported aspect ratio.
    if(best){boxes.push(best);result[i]=best;}
  }
  return result;
}

export function createHarmonicVoices(keyX = x => x) {
  const voices = [];
  let serial = 0, lastTime = -Infinity;
  function reset() { voices.length = 0; serial = 0; lastTime = -Infinity; }
  function update(notes, dt, time) {
    if (time < lastTime) reset();
    lastTime = time;
    dt = Math.max(0, Math.min(.1, dt));
    const live = [...notes.values()].filter(n => n.end === null).sort((a,b) => a.midi-b.midi);
    const pitches = new Set(live.map(n => n.midi)), claimed = new Set();
    for (const v of voices) {
      if (v.active && !pitches.has(v.midi)) { v.active = false; v.releasedAt = time; }
    }
    const fresh = [];
    for (const n of live) {
      const same = voices.find(v => v.midi === n.midi && !claimed.has(v) && (v.active || time-v.releasedAt < .45));
      if (same) { same.active=true; same.velocity=n.velocity/127; same.targetX=keyX(n.midi); claimed.add(same); }
      else fresh.push(n);
    }
    // Globally sort candidate pairs. Each old and new voice can be claimed once.
    // The seven-semitone / 450ms bounds prevent linking unrelated phrases.
    const candidates = [];
    for (const n of fresh) for (const v of voices) {
      const distance = Math.abs(v.midi-n.midi);
      if (!claimed.has(v) && !v.active && time-v.releasedAt < .45 && distance <= 7)
        candidates.push({n,v,cost:distance+(time-v.releasedAt)*2});
    }
    candidates.sort((a,b)=>a.cost-b.cost || a.n.midi-b.n.midi || a.v.id-b.v.id);
    const assigned = new Set();
    for (const {n,v} of candidates) {
      if (assigned.has(n) || claimed.has(v)) continue;
      v.previousMidi=v.midi; v.midi=n.midi; v.targetX=keyX(n.midi);
      v.active=true; v.velocity=n.velocity/127; v.movedAt=time; v.moves++;
      assigned.add(n); claimed.add(v);
    }
    for (const n of fresh) if (!assigned.has(n)) {
      // Reserve enough room for all 88 held notes; only quiet tails may be evicted.
      if (voices.length >= 88) {
        let index=-1;
        for(let i=0;i<voices.length;i++)if(!voices[i].active && (index<0 || voices[i].level<voices[index].level))index=i;
        if(index>=0)voices.splice(index,1); else continue;
      }
      const v={id:serial++,midi:n.midi,previousMidi:n.midi,x:keyX(n.midi),targetX:keyX(n.midi),
        velocity:n.velocity/127,level:0,height:4,speed:0,phase:(serial*.61803398875)%1,born:time,
        releasedAt:Infinity,movedAt:-Infinity,moves:0,active:true,hue:fifthIndex(n.midi)/12};
      voices.push(v); claimed.add(v);
    }
    for (const v of voices) {
      v.style=notes.get(v.midi)?.style||0;
      v.x=ease(v.x,v.targetX,dt,.23);
      v.level=ease(v.level,v.active?.25+v.velocity*.75:0,dt,v.active?.12:v.style===1?.48:1.5);
      const target=v.style===1&&!v.active?1:9+v.velocity*v.velocity*25;
      const steps=Math.max(1,Math.ceil(dt*120)),h=dt/steps;
      for(let j=0;j<steps;j++){v.speed+=(18*(target-v.height)-7*v.speed)*h;v.height+=v.speed*h;}
      v.phase=(v.phase+dt*(.12+v.velocity*.1))%1;
    }
    for(let i=voices.length-1;i>=0;i--)if(!voices[i].active && voices[i].level<.003)voices.splice(i,1);
    return voices;
  }
  return {voices,update,reset};
}
