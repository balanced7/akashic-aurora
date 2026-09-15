import { createHarmonicVoices, FIFTHS, fifthIndex } from './harmonic-voices.js';

export const MODES = Object.freeze({
  atmosphere:{name:'Original atmosphere',hint:'The environment’s original note effects.'},
  tonnetz:{name:'Tonnetz · chord lattice',hint:'Thirds and fifths form triangles. Shared notes keep their places.'},
  folds:{name:'Chromatic folds · 3D lattice',hint:'Natural notes share a plane; sharps rise and flats descend.'},
  spiral:{name:'Spiral harmony',hint:'Fifths wind around a spiral. The chord gathers around its centre.'},
  glass:{name:'Stained glass',hint:'Notes share glass boundaries. Stronger notes displace their neighbours.'},
  rings:{name:'Flowing rings',hint:'Each voice carries a ring. New strikes send ripples through the same part.'},
  petals:{name:'Blooming petals',hint:'Each voice unfolds a petal. Sustain holds it open; release lets it close.'},
  yarn:{name:'Interval threads',hint:'Threads join adjacent voices: thirds gold, fifths blue, close intervals rose.'},
  compass:{name:'Harmonic compass',hint:'The circle follows fifths. A halo marks the root; a diamond marks the bass.'},
});
export const pc = midi => ((midi%12)+12)%12;
export const pitchClass = root => root ? pc([0,2,4,5,7,9,11][root.letter]+root.acc) : null;
export const NOTE_NAMES=Object.freeze(['C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B']);
export const TONNETZ=[];
const ids=new Map();
for(let r=-2;r<=2;r++)for(let q=-2;q<=2;q++){
  ids.set(`${q},${r}`,TONNETZ.length);
  TONNETZ.push({q,r,pc:pc(q*7+r*4),x:(q+r*.5)/3,y:r*Math.sqrt(3)/5,z:0});
}
export const TRIANGLES=[];
for(let r=-2;r<2;r++)for(let q=-2;q<2;q++){
  TRIANGLES.push({ids:[ids.get(`${q},${r}`),ids.get(`${q+1},${r}`),ids.get(`${q},${r+1}`)],root:pc(q*7+r*4),minor:false});
  TRIANGLES.push({ids:[ids.get(`${q+1},${r}`),ids.get(`${q},${r+1}`),ids.get(`${q+1},${r+1}`)],root:pc(q*7+r*4+4),minor:true});
}
export function spelling(name){
  const match=/^([A-G])([#♯b♭𝄪𝄫]*)/.exec(name||'');
  if(!match)return null;
  const letter='CDEFGAB'.indexOf(match[1]);let acc=0;
  for(const ch of match[2])acc+=ch==='#'||ch==='♯'?1:ch==='b'||ch==='♭'?-1:ch==='𝄪'?2:-2;
  return{letter,acc,pc:pc([0,2,4,5,7,9,11][letter]+acc),name:match[0].replaceAll('#','♯').replaceAll('b','♭')};
}
export function foldPosition(name){
  const s=spelling(name)||spelling('C');
  // Seven fixed natural-note sites: the accidental is an independent depth axis.
  const naturals=[{x:-.62,y:0},{x:.35,y:-.12},{x:-.3,y:.55},{x:-.94,y:-.48},{x:.02,y:.08},{x:.65,y:.50},{x:.94,y:-.45}];
  return{...naturals[s.letter],z:s.acc*.32};
}
export function spiralPosition(pitch){
  const index=fifthIndex(pitch),a=index*Math.PI/2;
  return{x:Math.cos(a)*.64,y:(index-5.5)*.137,z:Math.sin(a)*.64};
}
export function intervalFamily(semitones){const n=pc(semitones);return n===0?'octave':[3,4,8,9].includes(n)?'third':[5,7].includes(n)?'fifth':'tension';}
export function weightedCells(sites,bounds=[-1,-.78,1,.78]){
  const [l,b,r,t]=bounds;
  return sites.map((site,i)=>{
    let poly=[[l,b],[r,b],[r,t],[l,t]];
    for(let j=0;j<sites.length&&poly.length;j++){
      if(i===j)continue;const other=sites[j],a=other.x-site.x,bb=other.y-site.y;
      const c=(other.x**2+other.y**2-site.x**2-site.y**2+(site.weight||0)-(other.weight||0))/2;
      const output=[];
      for(let k=0;k<poly.length;k++){
        const from=poly[k],to=poly[(k+1)%poly.length],d0=a*from[0]+bb*from[1]-c,d1=a*to[0]+bb*to[1]-c;
        if(d0<=1e-9)output.push(from);
        if((d0<0)!==(d1<0)){const f=d0/(d0-d1);output.push([from[0]+(to[0]-from[0])*f,from[1]+(to[1]-from[1])*f]);}
      }
      poly=output;
    }
    return poly;
  });
}
export function createHarmonyState(){
  const tracker=createHarmonicVoices(),levels=new Float32Array(12),power=new Float32Array(12);
  let lastTime=-Infinity;
  return{voices:tracker.voices,levels,power,bass:null,
    update(notes,dt,time){
      dt=Math.max(0,Math.min(.1,dt));
      if(time<lastTime){levels.fill(0);power.fill(0);}lastTime=time;
      tracker.update(notes,dt,time);levels.fill(0);power.fill(0);this.bass=null;
      for(const v of tracker.voices){
        v.pulses??=[];v.heat??=0;
        const note=notes.get(v.midi);
        if(v.active&&note&&note.at!==v.lastAttack){
          v.lastAttack=note.at;v.heat=Math.min(2,v.heat+v.velocity**2);
          v.pulses.push({at:time,power:v.velocity**2});if(v.pulses.length>6)v.pulses.shift();
        }
        v.heat*=Math.exp(-dt*2.1);
        v.pulses=v.pulses.filter(p=>time-p.at<2.6);
        const pitch=pc(v.midi);levels[pitch]=Math.max(levels[pitch],v.level);
        power[pitch]=Math.max(power[pitch],v.velocity**2*v.level+v.heat*.25);
        if(v.active&&(this.bass===null||v.midi<this.bass))this.bass=v.midi;
      }
      return this;
    },
    reset(){tracker.reset();levels.fill(0);power.fill(0);lastTime=-Infinity;this.bass=null;},
  };
}
export { FIFTHS, fifthIndex };
